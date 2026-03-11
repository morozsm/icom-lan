"""WebSocket + HTTP server for the icom-lan Web UI.

Implements:
- Minimal asyncio HTTP server (no external deps)
- RFC 6455 WebSocket upgrade
- HTTP endpoints: GET /, GET /api/v1/info, GET /api/v1/capabilities
- WebSocket channels: /api/v1/ws, /api/v1/scope, /api/v1/meters, /api/v1/audio

Architecture
------------
Single asyncio.start_server accepts raw TCP. For each connection:
1. Read HTTP request line + headers
2. If Upgrade: websocket → perform RFC 6455 handshake, route to WS handler
3. Else → serve HTTP response (static file or JSON API)

The server holds an optional radio protocol instance and uses it for
command dispatch and scope/meter data delivery.
"""

from __future__ import annotations

import asyncio
import datetime
import gzip as _gzip
import json
import logging
import mimetypes
import pathlib
import urllib.parse
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from .. import __version__
from ..radio_state import RadioState
from ..rigctld.state_cache import StateCache
from .dx_cluster import DXClusterClient, SpotBuffer
from .handlers import AudioBroadcaster, AudioHandler, ControlHandler, MetersHandler, ScopeHandler
from .runtime_helpers import radio_ready, runtime_capabilities
from .radio_poller import CommandQueue, DisableScope, EnableScope, RadioPoller
from .websocket import (
    WS_KEEPALIVE_INTERVAL,
    WebSocketConnection,
    make_accept_key,
    negotiate_deflate,
)

if TYPE_CHECKING:
    from ..audio_bridge import AudioBridge
    from ..profiles import RadioProfile
    from ..radio_protocol import Radio

__all__ = ["WebConfig", "WebServer", "run_web_server"]

logger = logging.getLogger(__name__)

_DEFAULT_STATIC_DIR = pathlib.Path(__file__).parent / "static"
_RADIO_MODEL = "IC-7610"

# Mode/filter lists moved to RadioProfile (profiles.py)

_RECEIVER_KEY_MAP = {"freq": "freqHz"}


def _to_camel(s: str) -> str:
    """Convert a snake_case identifier to camelCase."""
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _camel_keys(d: dict) -> dict:
    """Recursively convert all dict keys from snake_case to camelCase."""
    return {
        _to_camel(k): (_camel_keys(v) if isinstance(v, dict) else v)
        for k, v in d.items()
    }


def _camel_case_state(d: dict) -> dict:
    """Transform ``RadioState.to_dict()`` output to camelCase for the frontend.

    - All snake_case keys become camelCase.
    - ``freq`` inside receiver dicts (``main``, ``sub``) is renamed to
      ``freqHz``.
    - Flat ``connected`` / ``radio_ready`` / ``control_connected`` keys are
      removed from the top level and wrapped in a nested ``connection`` object.
    """
    connection = {
        "rigConnected": d.get("connected", False),
        "radioReady": d.get("radio_ready", False),
        "controlConnected": d.get("control_connected", False),
    }
    skip = {"connected", "radio_ready", "control_connected"}
    result: dict = {}
    for key, value in d.items():
        if key in skip:
            continue
        if key in ("main", "sub") and isinstance(value, dict):
            inner = {}
            for k, v in value.items():
                new_k = _RECEIVER_KEY_MAP.get(k, _to_camel(k))
                inner[new_k] = _camel_keys(v) if isinstance(v, dict) else v
            result[key] = inner
        elif isinstance(value, dict):
            result[_to_camel(key)] = _camel_keys(value)
        else:
            result[_to_camel(key)] = value
    result["connection"] = connection
    return result


def _runtime_capabilities(radio: "Radio | None") -> set[str]:
    """Backward-compatible alias to shared runtime_capabilities helper."""
    return runtime_capabilities(radio)


def _supports_scope(radio: "Radio | None") -> bool:
    return "scope" in runtime_capabilities(radio)


def _supports_audio(radio: "Radio | None") -> bool:
    return "audio" in runtime_capabilities(radio)


@dataclass
class WebConfig:
    """Configuration for :class:`WebServer`.

    Attributes:
        host: Bind address (default: 0.0.0.0).
        port: HTTP/WS port (default: 8080).
        static_dir: Directory to serve static files from.
        radio_model: Radio model string for the hello/info response.
        max_clients: Maximum concurrent WebSocket clients.
        keepalive_interval: Seconds between WebSocket keepalive pings.
            Set to a very large value (e.g. 9999) to disable during tests.
    """

    host: str = "0.0.0.0"
    port: int = 8080
    static_dir: pathlib.Path = field(default_factory=lambda: _DEFAULT_STATIC_DIR)
    radio_model: str = _RADIO_MODEL
    max_clients: int = 100
    keepalive_interval: float = WS_KEEPALIVE_INTERVAL
    dx_cluster_host: str = ""
    dx_cluster_port: int = 0
    dx_callsign: str = ""
    auth_token: str = ""  # empty = no auth required


class WebServer:
    """Asyncio HTTP + WebSocket server for the icom-lan Web UI.

    Args:
        radio: Connected Radio protocol instance (optional; needed for live data).
        config: Server configuration (defaults to WebConfig()).
    """

    def __init__(
        self,
        radio: "Radio | None" = None,
        config: WebConfig | None = None,
    ) -> None:
        self._radio = radio
        self._config = config or WebConfig()
        self._server: asyncio.Server | None = None
        self._client_tasks: set[asyncio.Task[None]] = set()
        self._scope_handlers: set["ScopeHandler"] = set()
        self._scope_enabled = False
        self._scope_enable_lock: asyncio.Lock = asyncio.Lock()
        self._scope_disable_grace: float = 2.0
        # RadioPoller: single CI-V serialiser
        if radio is not None:
            from ..radio_protocol import StateCacheCapable
            if isinstance(radio, StateCacheCapable):
                self._state_cache: StateCache = cast(StateCache, radio.state_cache)
            else:
                self._state_cache = StateCache()
        else:
            self._state_cache = StateCache()
        raw_radio_state = getattr(radio, "radio_state", None) if radio is not None else None
        self._radio_state: RadioState = (
            raw_radio_state if isinstance(raw_radio_state, RadioState) else RadioState()
        )
        self._audio_broadcaster = AudioBroadcaster(radio)
        self._command_queue: CommandQueue = CommandQueue()
        self._radio_poller: RadioPoller | None = None
        # Meter broadcast
        self._meter_handlers: set["MetersHandler"] = set()
        self._meter_cache: list[tuple[int, int]] | None = None
        # Control handler event queues
        self._control_event_queues: set[asyncio.Queue[dict[str, Any]]] = set()
        # State broadcast throttle
        self._last_state_broadcast: float = 0.0
        # Audio bridge (virtual device integration)
        self._audio_bridge: "AudioBridge | None" = None
        # Scope health monitor
        self._scope_last_nonzero: float = 0.0
        self._scope_health_task: asyncio.Task[None] | None = None
        self._scope_health_interval: float = 10.0  # seconds of zero frames before re-enable
        self._scope_reenable_task: asyncio.Task[None] | None = None
        self._scope_reenable_poll_interval: float = 0.5
        self._scope_reenable_timeout: float = 30.0
        # DX cluster
        self._spot_buffer: SpotBuffer = SpotBuffer()
        self._dx_client: DXClusterClient | None = None
        self._dx_client_task: asyncio.Task[None] | None = None

    def __del__(self) -> None:
        """Emit WARN if instance is collected while server is still running (forgotten teardown)."""
        try:
            if self._server is not None:
                logger.warning(
                    "WebServer collected while still running; "
                    "ensure stop() or async context manager is used."
                )
        except Exception:
            pass  # avoid raising in destructor

    # ------------------------------------------------------------------
    # Helpers for scope callback operations
    # ------------------------------------------------------------------

    def _get_profile(self) -> "RadioProfile":
        """Resolve the RadioProfile for the connected radio."""
        from ..profiles import RadioProfile, resolve_radio_profile

        raw_profile = getattr(self._radio, "profile", None) if self._radio else None
        if isinstance(raw_profile, RadioProfile):
            return raw_profile
        try:
            return resolve_radio_profile(model=self._config.radio_model)
        except KeyError:
            return resolve_radio_profile(model="IC-7610")

    def _radio_ready(self) -> bool:
        """Backend view of radio readiness (CI-V healthy)."""
        return radio_ready(self._radio)

    def _set_scope_data_callback(self, callback: Any) -> None:
        """Set the scope data callback on the radio if it supports it."""
        from ..radio_protocol import ScopeCapable
        if self._radio is not None and isinstance(self._radio, ScopeCapable):
            self._radio.on_scope_data(callback)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def ensure_scope_enabled(self, handler: "ScopeHandler") -> None:
        """Register a scope handler and enable scope on radio if needed.

        Scope enable goes through the RadioPoller command queue to avoid
        concurrent CI-V access.
        """
        async with self._scope_enable_lock:
            self._scope_handlers.add(handler)
            if self._radio is not None:
                if not _supports_scope(self._radio):
                    logger.info("scope: active radio does not expose runtime scope support")
                    return
                if self._radio_ready():
                    self._set_scope_data_callback(self._broadcast_scope)
                    self._command_queue.put(EnableScope())
                    self._scope_enabled = True
                    logger.info("scope: enable queued")
                else:
                    self._schedule_scope_enable_when_ready(reason="handler_connect")
                    logger.info("scope: defer enable until radio_ready")

    def unregister_scope_handler(self, handler: "ScopeHandler") -> None:
        """Unregister a scope handler."""
        self._scope_handlers.discard(handler)
        if not self._scope_handlers and self._radio is not None and _supports_scope(self._radio):
            self._set_scope_data_callback(None)
            if self._scope_enabled:
                loop = asyncio.get_event_loop()
                loop.create_task(self._disable_scope_async())

    async def _disable_scope_async(self) -> None:
        """Disable scope on the radio when no more handlers are connected."""
        if self._radio is None or not _supports_scope(self._radio):
            return
        await asyncio.sleep(self._scope_disable_grace)
        if self._scope_handlers:
            logger.debug("scope: disable task aborted — handler reconnected")
            if self._radio is not None:
                self._set_scope_data_callback(self._broadcast_scope)
            return
        self._command_queue.put(DisableScope())
        if not self._scope_handlers:
            self._scope_enabled = False
            logger.info("scope: disable queued (no active handlers)")
        else:
            logger.debug("scope: disable queued but new handler present — will re-enable")
            if self._radio is not None:
                self._set_scope_data_callback(self._broadcast_scope)

    def _broadcast_scope(self, frame: Any) -> None:
        """Broadcast scope frame to all registered handlers.
        
        Also extract VFO frequency from scope center mode frames
        and update state cache — bypasses CI-V polling for freq.
        """
        for h in list(self._scope_handlers):
            h.enqueue_frame(frame)
        # Scope health: track whether frames carry real data
        self._scope_health_check(frame)

    # ------------------------------------------------------------------
    # RadioPoller integration
    # ------------------------------------------------------------------

    @property
    def state_cache(self) -> StateCache:
        """Shared state cache (populated by RadioPoller)."""
        return self._state_cache

    @property
    def command_queue(self) -> CommandQueue:
        """Command queue consumed by RadioPoller."""
        return self._command_queue

    def register_control_event_queue(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        """Register a ControlHandler event queue for broadcast."""
        self._control_event_queues.add(q)

    def unregister_control_event_queue(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        """Unregister a ControlHandler event queue."""
        self._control_event_queues.discard(q)

    def broadcast_event(self, name: str, data: dict[str, Any]) -> None:
        """Push an event to all ControlHandler event queues."""
        event = {"type": "event", "name": name, "data": data}
        for q in list(self._control_event_queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def _broadcast_state_update(self) -> None:
        """Broadcast current state to all control WS clients (throttled)."""
        import time

        now = time.monotonic()
        if now - self._last_state_broadcast < 0.05:
            return
        self._last_state_broadcast = now

        d = self._radio_state.to_dict()
        d["revision"] = self._radio_poller.revision if self._radio_poller is not None else 0
        raw_connected = getattr(self._radio, "connected", False) if self._radio else False
        d["connected"] = raw_connected if isinstance(raw_connected, bool) else False
        d["radio_ready"] = self._radio_ready()
        raw_control = getattr(self._radio, "control_connected", False) if self._radio else False
        d["control_connected"] = raw_control if isinstance(raw_control, bool) else False

        body = _camel_case_state(d)
        event = {"type": "state_update", "data": body}
        for q in list(self._control_event_queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def broadcast_notification(
        self,
        level: str,
        message: str,
        category: str = "system",
    ) -> None:
        """Broadcast a notification to all connected WebSocket clients.

        Args:
            level: Severity level — "info", "warning", "error", or "success".
            message: Human-readable notification text.
            category: Logical category — "connection", "dx_cluster", "bridge", "system".
        """
        notification: dict[str, Any] = {
            "type": "notification",
            "level": level,
            "message": message,
            "category": category,
        }
        for q in list(self._control_event_queues):
            try:
                q.put_nowait(notification)
            except asyncio.QueueFull:
                pass

    def _broadcast_dx_spot(self, spot: Any) -> None:
        """Add DX spot to buffer and push dx_spot message to all control clients."""
        self._spot_buffer.add(spot)
        msg = {
            "type": "dx_spot",
            "spot": {
                "spotter": spot.spotter,
                "freq": spot.freq,
                "call": spot.call,
                "comment": spot.comment,
                "time_utc": spot.time_utc,
                "timestamp": spot.timestamp,
            },
        }
        for q in list(self._control_event_queues):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass

    # ------------------------------------------------------------------
    # Meter handler registration (no poller — RadioPoller broadcasts)
    # ------------------------------------------------------------------

    def register_meter_handler(self, handler: "MetersHandler") -> None:
        """Register a meter handler for broadcast."""
        self._meter_handlers.add(handler)
        if self._meter_cache is not None:
            handler.enqueue_frame(self._meter_cache)

    def unregister_meter_handler(self, handler: "MetersHandler") -> None:
        """Unregister a meter handler."""
        self._meter_handlers.discard(handler)

    def _broadcast_meters(self, readings: list[tuple[int, int]]) -> None:
        """Broadcast meter readings to all registered handlers."""
        self._meter_cache = readings
        for h in list(self._meter_handlers):
            h.enqueue_frame(readings)

    def _on_radio_state_change(self, name: str, data: dict[str, Any]) -> None:
        """Callback from CI-V RX stream (_update_state_cache_from_frame).

        This is the PRIMARY update path.  Called whenever the radio sends
        a CI-V frame (solicited response or unsolicited change).
        """
        if self._radio_poller is not None:
            self._radio_poller.bump_revision()
        self.broadcast_event(name, data)
        self._broadcast_state_update()
        if name == "connection_state":
            if data.get("connected"):
                self.broadcast_notification("success", "Radio connected", "connection")
            else:
                self.broadcast_notification("warning", "Radio disconnected", "connection")
        # Also broadcast meter readings to MetersHandler clients
        if name == "meter":
            from .protocol import (
                METER_SMETER_MAIN, METER_POWER, METER_SWR, METER_ALC,
                METER_ID_DRAIN, METER_VD, METER_TEMP,
            )
            meter_map = {
                "smeter": METER_SMETER_MAIN,
                "power": METER_POWER,
                "swr": METER_SWR,
                "alc": METER_ALC,
                "id": METER_ID_DRAIN,
                "vd": METER_VD,
                "temp": METER_TEMP,
            }
            meter_type = data.get("type")
            meter_id = meter_map.get(meter_type) if isinstance(meter_type, str) else None
            if meter_id is not None:
                # Binary protocol uses raw for bar width
                raw = data.get("raw", 0)
                value = raw if isinstance(raw, int) else 0
                self._broadcast_meters([(meter_id, value)])

    def _on_radio_reconnect(self) -> None:
        """Called after soft_reconnect — re-enable scope if clients are connected."""
        if self._scope_handlers and self._radio is not None and _supports_scope(self._radio):
            if self._radio_ready():
                self._set_scope_data_callback(self._broadcast_scope)
                self._command_queue.put(EnableScope())
                self._scope_enabled = True
                logger.info(
                    "scope: re-enable queued after reconnect (%d handlers)",
                    len(self._scope_handlers),
                )
            else:
                self._schedule_scope_enable_when_ready(reason="radio_reconnect")

    def _schedule_scope_enable_when_ready(self, *, reason: str) -> None:
        """Schedule delayed scope enable once radio becomes ready."""
        if (
            self._scope_reenable_task is not None
            and not self._scope_reenable_task.done()
        ):
            return
        loop = asyncio.get_running_loop()
        self._scope_reenable_task = loop.create_task(
            self._wait_and_enable_scope(reason=reason),
            name="scope-reenable-when-ready",
        )

    async def _wait_and_enable_scope(self, *, reason: str) -> None:
        """Wait until radio_ready before queuing EnableScope."""
        import time
        deadline = time.monotonic() + self._scope_reenable_timeout
        try:
            while True:
                if not self._scope_handlers or self._radio is None:
                    return
                if not _supports_scope(self._radio):
                    return
                if self._radio_ready():
                    self._set_scope_data_callback(self._broadcast_scope)
                    self._command_queue.put(EnableScope())
                    self._scope_enabled = True
                    logger.info(
                        "scope: enable queued after %s (%d handlers)",
                        reason,
                        len(self._scope_handlers),
                    )
                    return
                if time.monotonic() >= deadline:
                    logger.warning(
                        "scope: radio not ready after %.0fs (%s), skipping re-enable",
                        self._scope_reenable_timeout,
                        reason,
                    )
                    return
                await asyncio.sleep(self._scope_reenable_poll_interval)
        except asyncio.CancelledError:
            pass
        finally:
            self._scope_reenable_task = None

    def _scope_health_check(self, frame: Any) -> None:
        """Track whether scope frames contain real data (non-zero pixels)."""
        import time
        try:
            # ScopeFrame has .pixels (bytes-like)
            pixels = getattr(frame, "pixels", None) or b""
            if any(b != 0 for b in pixels):
                self._scope_last_nonzero = time.monotonic()
        except (AttributeError, TypeError):
            logger.debug("scope health check: unexpected frame type", exc_info=True)

    async def _scope_health_monitor(self) -> None:
        """Background task: re-enable scope if frames are all-zero for too long."""
        import time
        try:
            while True:
                await asyncio.sleep(self._scope_health_interval)
                if not self._scope_handlers or self._radio is None:
                    continue
                if not _supports_scope(self._radio):
                    continue
                # Don't re-enable scope while radio is disconnected
                if not self._radio_ready():
                    self._scope_last_nonzero = time.monotonic()  # reset timer
                    continue
                now = time.monotonic()
                if self._scope_last_nonzero == 0.0:
                    # Never seen non-zero — might be starting up
                    self._scope_last_nonzero = now
                    continue
                elapsed = now - self._scope_last_nonzero
                if elapsed > self._scope_health_interval:
                    self._command_queue.put(EnableScope())
                    self._scope_last_nonzero = now  # reset to avoid spam
                    logger.warning(
                        "scope-health: all-zero frames for %.0fs, re-enabling scope",
                        elapsed,
                    )
        except asyncio.CancelledError:
            pass

    def _on_poller_state_event(self, name: str, data: dict[str, Any]) -> None:
        """Callback from RadioPoller (legacy, kept for compatibility)."""
        self.broadcast_event(name, data)

    def _on_poller_meter_readings(self, readings: list[tuple[int, int]]) -> None:
        """Callback from RadioPoller when meter values are polled."""
        self._broadcast_meters(readings)

    async def start(self) -> None:
        """Start the HTTP/WS listener and RadioPoller (if radio is connected)."""
        self._server = await asyncio.start_server(
            self._accept_client,
            host=self._config.host,
            port=self._config.port,
        )
        addr = self._server.sockets[0].getsockname()
        logger.info("web server listening on %s:%d", addr[0], addr[1])
        if self._radio is not None:
            # Register callback so CI-V RX stream can notify us of state changes.
            # This is the primary path for freq/mode/meter updates (fire-and-forget).
            self._radio.set_state_change_callback(self._on_radio_state_change)
            # Re-enable scope after soft_reconnect (CI-V stream reset loses scope state)
            self._radio.set_reconnect_callback(self._on_radio_reconnect)
            self._radio_poller = RadioPoller(
                self._radio,
                self._state_cache,
                self._command_queue,
                on_state_event=self._on_poller_state_event,
                on_meter_readings=self._on_poller_meter_readings,
            )
            self._radio_poller.start()
            if _supports_scope(self._radio):
                self._scope_health_task = asyncio.get_running_loop().create_task(
                    self._scope_health_monitor(), name="scope-health"
                )
        if self._config.dx_cluster_host:
            self._dx_client = DXClusterClient(
                self._config.dx_cluster_host,
                self._config.dx_cluster_port,
                self._config.dx_callsign,
                on_spot=self._broadcast_dx_spot,
            )
            self._dx_client_task = asyncio.get_running_loop().create_task(
                self._dx_client.start(), name="dx-cluster"
            )
            logger.info(
                "dx-cluster: connecting to %s:%d as %s",
                self._config.dx_cluster_host,
                self._config.dx_cluster_port,
                self._config.dx_callsign,
            )

    # ------------------------------------------------------------------
    # Audio Bridge (virtual device integration)
    # ------------------------------------------------------------------

    async def start_audio_bridge(
        self,
        device_name: str | None = None,
        tx_device_name: str | None = None,
        tx_enabled: bool = True,
    ) -> None:
        """Start the audio bridge to a virtual audio device.

        Args:
            device_name: Device name for RX (e.g. "BlackHole 2ch"). Auto-detects if None.
            tx_device_name: Separate device for TX (e.g. "BlackHole 16ch").
                            Required for bidirectional audio to avoid feedback.
            tx_enabled: Whether to bridge TX (device → radio).
        """
        from ..audio_bridge import AudioBridge

        if self._audio_bridge is not None and self._audio_bridge.running:
            logger.warning("audio-bridge: already running")
            return
        if self._radio is None:
            raise RuntimeError("No radio connected")
        if not _supports_audio(self._radio):
            raise RuntimeError(
                "Audio bridge is unavailable: active radio does not support audio streaming."
            )

        self._audio_bridge = AudioBridge(
            self._radio,
            device_name=device_name,
            tx_device_name=tx_device_name,
            tx_enabled=tx_enabled,
        )
        await self._audio_bridge.start()
        self.broadcast_notification("success", "Audio bridge started", "bridge")

    async def stop_audio_bridge(self) -> None:
        """Stop the audio bridge."""
        if self._audio_bridge is not None:
            await self._audio_bridge.stop()
            self._audio_bridge = None
            self.broadcast_notification("info", "Audio bridge stopped", "bridge")

    @property
    def audio_bridge_stats(self) -> dict[str, Any] | None:
        """Audio bridge stats, or None if not running."""
        if self._audio_bridge is not None:
            stats = self._audio_bridge.stats
            return stats if isinstance(stats, dict) else None
        return None

    async def stop(self) -> None:
        """Close the listener, stop RadioPoller, disconnect radio, cancel tasks."""
        # Stop DX cluster client
        if self._dx_client is not None:
            await self._dx_client.stop()
            self._dx_client = None
        if self._dx_client_task is not None:
            self._dx_client_task.cancel()
            try:
                await self._dx_client_task
            except asyncio.CancelledError:
                pass
            self._dx_client_task = None
        # Stop audio bridge first
        if self._audio_bridge is not None:
            await self.stop_audio_bridge()
        if self._scope_health_task is not None:
            self._scope_health_task.cancel()
            self._scope_health_task = None
        if self._scope_reenable_task is not None:
            self._scope_reenable_task.cancel()
            self._scope_reenable_task = None
        if self._radio_poller is not None:
            self._radio_poller.stop()
            self._radio_poller = None

        # Graceful radio disconnect — frees LAN slots immediately
        if self._radio is not None:
            try:
                _disconnect = self._radio.disconnect
                await asyncio.wait_for(_disconnect(), timeout=3.0)
                logger.info("radio: graceful disconnect")
            except Exception:
                logger.warning("radio: disconnect failed", exc_info=True)

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        tasks = list(self._client_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("web server stopped")

    async def serve_forever(self) -> None:
        """Start and block until cancelled.  Handles SIGTERM/SIGINT gracefully."""
        import signal as _signal

        await self.start()
        assert self._server is not None

        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        def _on_signal() -> None:
            logger.info("received shutdown signal")
            stop_event.set()

        for sig in (_signal.SIGTERM, _signal.SIGINT):
            loop.add_signal_handler(sig, _on_signal)

        try:
            await stop_event.wait()
        finally:
            await self.stop()

    async def __aenter__(self) -> WebServer:
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.stop()

    @property
    def port(self) -> int:
        """Actual bound port (useful when config.port == 0)."""
        if self._server is None:
            return self._config.port
        return int(self._server.sockets[0].getsockname()[1])

    # ------------------------------------------------------------------
    # Connection acceptance
    # ------------------------------------------------------------------

    def _accept_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        if len(self._client_tasks) >= self._config.max_clients:
            logger.warning(
                "max_clients reached (%d), rejecting connection",
                self._config.max_clients,
            )
            writer.close()
            return
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._handle_connection(reader, writer))
        self._client_tasks.add(task)
        task.add_done_callback(self._client_tasks.discard)

    # ------------------------------------------------------------------
    # HTTP request parsing
    # ------------------------------------------------------------------

    async def _read_request(
        self, reader: asyncio.StreamReader
    ) -> tuple[str, str, dict[str, str], dict[str, list[str]]] | None:
        """Read and parse an HTTP request line + headers.

        Returns:
            Tuple of (method, path, headers_dict, query_params) or None on EOF/error.
        """
        try:
            request_line = await asyncio.wait_for(
                reader.readline(), timeout=10.0
            )
        except asyncio.TimeoutError:
            return None
        if not request_line:
            return None

        parts = request_line.decode("ascii", errors="replace").strip().split(" ", 2)
        if len(parts) < 2:
            return None
        method, raw_path = parts[0], parts[1]

        # Decode path (preserve query string separately)
        parsed = urllib.parse.urlparse(raw_path)
        path = urllib.parse.unquote(parsed.path)
        query = urllib.parse.parse_qs(parsed.query)

        headers: dict[str, str] = {}
        while True:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=5.0)
            except asyncio.TimeoutError:
                break
            stripped = line.strip()
            if not stripped:
                break
            if b":" in stripped:
                key, _, value = stripped.partition(b":")
                headers[key.decode("ascii", errors="replace").strip().lower()] = (
                    value.decode("ascii", errors="replace").strip()
                )

        return method, path, headers, query

    # ------------------------------------------------------------------
    # Main connection handler
    # ------------------------------------------------------------------

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername", ("?", 0))
        try:
            result = await self._read_request(reader)
            if result is None:
                return
            method, path, headers, query = result

            logger.debug("request: %s %s from %s:%s", method, path, peer[0], peer[1])

            # WebSocket upgrade?
            if (
                headers.get("upgrade", "").lower() == "websocket"
                and headers.get("connection", "").lower().find("upgrade") >= 0
            ):
                await self._handle_websocket(reader, writer, path, headers, query)
            else:
                await self._handle_http(writer, method, path, headers)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("connection error from %s:%s: %s", peer[0], peer[1], exc)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # HTTP handlers
    # ------------------------------------------------------------------

    async def _handle_http(
        self,
        writer: asyncio.StreamWriter,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        if method not in ("GET", "HEAD"):
            await _send_response(writer, 405, "Method Not Allowed", b"", {})
            return

        # Auth check for API endpoints
        if self._config.auth_token and path.startswith("/api/"):
            auth_header = (headers or {}).get("authorization", "")
            if auth_header != f"Bearer {self._config.auth_token}":
                await _send_response(
                    writer, 401, "Unauthorized",
                    b'{"error":"unauthorized","message":"Valid auth token required"}',
                    {"Content-Type": "application/json", "WWW-Authenticate": "Bearer"},
                )
                return

        # Nuclear SW cleanup: Clear-Site-Data on /?clearcache
        if path == "/clearcache":
            await _send_response(
                writer, 200, "OK",
                b"<h2>Site data cleared. <a href='/'>Reload</a></h2>",
                {
                    "Content-Type": "text/html",
                    "Clear-Site-Data": '"cache", "storage"',
                },
            )
            return

        if path == "/api/v1/info":
            await self._serve_info(writer, headers)
        elif path == "/api/v1/state":
            await self._serve_state(writer, headers)
        elif path == "/api/v1/capabilities":
            await self._serve_capabilities(writer, headers)
        elif path == "/api/v1/dx/spots":
            await self._serve_dx_spots(writer)
        elif path == "/api/v1/bridge":
            await self._handle_bridge(method, writer)
        elif path == "/" or path == "/index.html":
            await self._serve_static(writer, "index.html")
        elif path.startswith("/"):
            # Try to serve as static file
            rel = path.lstrip("/") or "index.html"
            await self._serve_static(writer, rel)
        else:
            await _send_response(writer, 404, "Not Found", b"404 Not Found", {})

    async def _serve_info(self, writer: asyncio.StreamWriter, headers: dict[str, str] | None = None) -> None:
        raw_model = (
            getattr(self._radio, "model", None)
            if self._radio is not None
            else None
        )
        model = raw_model if isinstance(raw_model, str) else self._config.radio_model
        caps = _runtime_capabilities(self._radio)
        has_dual_rx = "dual_rx" in caps
        raw_connected = (
            getattr(self._radio, "connected", False) if self._radio else False
        )
        connected = raw_connected if isinstance(raw_connected, bool) else False
        raw_control_connected = (
            getattr(self._radio, "control_connected", False) if self._radio else False
        )
        control_connected = (
            raw_control_connected if isinstance(raw_control_connected, bool) else False
        )
        body = json.dumps(
            {
                # Backward-compatible legacy fields
                "server": "icom-lan",
                "version": __version__,
                "proto": 1,
                "radio": model,
                # New structured fields
                "model": model,
                "capabilities": {
                    "hasSpectrum": "scope" in caps,
                    "hasAudio": "audio" in caps,
                    "hasTx": "tx" in caps,
                    "hasDualReceiver": has_dual_rx,
                    "hasTuner": "tuner" in caps,
                    "hasCw": "cw" in caps,
                    "maxReceivers": 2 if has_dual_rx else 1,
                    "tags": sorted(caps),
                    "modes": list(self._get_profile().modes),
                    "filters": list(self._get_profile().filters),
                },
                "connection": {
                    "rigConnected": connected,
                    "radioReady": self._radio_ready(),
                    "controlConnected": control_connected,
                    "wsClients": len(self._client_tasks),
                },
            },
            separators=(",", ":"),
        ).encode()
        await _send_json(writer, body, headers)

    async def _serve_state(self, writer: asyncio.StreamWriter, headers: dict[str, str] | None = None) -> None:
        d = self._radio_state.to_dict()
        raw_connected = (
            getattr(self._radio, "connected", False) if self._radio else False
        )
        d["connected"] = raw_connected if isinstance(raw_connected, bool) else False
        d["radio_ready"] = self._radio_ready()
        raw_control_connected = (
            getattr(self._radio, "control_connected", False)
            if self._radio else False
        )
        d["control_connected"] = (
            raw_control_connected
            if isinstance(raw_control_connected, bool)
            else False
        )
        revision = self._radio_poller.revision if self._radio_poller is not None else 0
        d["revision"] = revision
        d["updatedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        body = json.dumps(_camel_case_state(d), separators=(",", ":")).encode()
        await _send_json(writer, body, headers, etag=f'"{revision}"')

    async def _serve_capabilities(self, writer: asyncio.StreamWriter, headers: dict[str, str] | None = None) -> None:
        caps = _runtime_capabilities(self._radio)
        _raw_model = getattr(self._radio, "model", None) if self._radio is not None else None
        model: str = _raw_model if isinstance(_raw_model, str) else self._config.radio_model
        profile = self._get_profile()

        freq_ranges = [
            {
                "start": r.start,
                "end": r.end,
                "label": r.label,
                "bands": [
                    {"name": b.name, "start": b.start, "end": b.end, "default": b.default}
                    for b in r.bands
                ],
            }
            for r in profile.freq_ranges
        ]

        body = json.dumps(
            {
                "model": model,
                "scope": "scope" in caps,
                "audio": "audio" in caps,
                "tx": "tx" in caps,
                "capabilities": sorted(caps),
                "freqRanges": freq_ranges,
                "modes": list(profile.modes),
                "filters": list(profile.filters),
                "scopeConfig": {
                    "centerMode": True,
                    "amplitudeMax": 160,
                    "defaultSpan": 500000,
                },
                "audioConfig": {
                    "sampleRate": 48000,
                    "channels": 1,
                    "codecs": ["opus"],
                },
            },
            separators=(",", ":"),
        ).encode()
        await _send_json(writer, body, headers)

    async def _serve_dx_spots(self, writer: asyncio.StreamWriter) -> None:
        spots = self._spot_buffer.get_spots()
        body = json.dumps({"spots": spots}, separators=(",", ":")).encode()
        await _send_response(
            writer, 200, "OK", body, {"Content-Type": "application/json"}
        )

    async def _handle_bridge(
        self, method: str, writer: asyncio.StreamWriter,
    ) -> None:
        """Handle /api/v1/bridge — GET status, POST start, DELETE stop."""
        if method == "GET":
            stats = self.audio_bridge_stats
            body = json.dumps(
                {"running": stats is not None and stats.get("running", False),
                 **(stats or {})},
                separators=(",", ":"),
            ).encode()
            await _send_response(
                writer, 200, "OK", body, {"Content-Type": "application/json"},
            )
        elif method == "POST":
            try:
                await self.start_audio_bridge()
                body = json.dumps({"status": "started"}, separators=(",", ":")).encode()
                await _send_response(
                    writer, 200, "OK", body, {"Content-Type": "application/json"},
                )
            except Exception as exc:
                body = json.dumps(
                    {"error": str(exc)}, separators=(",", ":"),
                ).encode()
                await _send_response(
                    writer, 500, "Error", body, {"Content-Type": "application/json"},
                )
        elif method == "DELETE":
            await self.stop_audio_bridge()
            body = json.dumps({"status": "stopped"}, separators=(",", ":")).encode()
            await _send_response(
                writer, 200, "OK", body, {"Content-Type": "application/json"},
            )
        else:
            await _send_response(writer, 405, "Method Not Allowed", b"", {})

    async def _serve_static(
        self, writer: asyncio.StreamWriter, filename: str
    ) -> None:
        # Prevent path traversal
        static_dir = self._config.static_dir.resolve()
        target = (static_dir / filename).resolve()
        if not str(target).startswith(str(static_dir)):
            await _send_response(writer, 403, "Forbidden", b"Forbidden", {})
            return

        if not target.exists() or not target.is_file():
            await _send_response(writer, 404, "Not Found", b"Not Found", {})
            return

        try:
            body = target.read_bytes()
        except OSError:
            await _send_response(
                writer, 500, "Internal Server Error", b"Read error", {}
            )
            return

        mime, _ = mimetypes.guess_type(str(target))
        ct = mime or "application/octet-stream"
        await _send_response(
            writer,
            200,
            "OK",
            body,
            {
                "Content-Type": ct,
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )

    # ------------------------------------------------------------------
    # WebSocket upgrade + routing
    # ------------------------------------------------------------------

    async def _handle_websocket(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        path: str,
        headers: dict[str, str],
        query: dict[str, list[str]] | None = None,
    ) -> None:
        # Auth check: accept Bearer header or ?token= query param
        if self._config.auth_token:
            auth_header = headers.get("authorization", "")
            token_param = (query or {}).get("token", [""])[0]
            if auth_header != f"Bearer {self._config.auth_token}" and token_param != self._config.auth_token:
                await _send_response(writer, 401, "Unauthorized", b"Unauthorized", {})
                return

        ws_key = headers.get("sec-websocket-key", "")
        if not ws_key:
            await _send_response(writer, 400, "Bad Request", b"Missing key", {})
            return

        accept = make_accept_key(ws_key)
        # Negotiate permessage-deflate (RFC 7692)
        ext_header = headers.get("sec-websocket-extensions", "")
        deflate_resp = negotiate_deflate(ext_header) if ext_header else None
        ext_line = (
            f"Sec-WebSocket-Extensions: {deflate_resp}\r\n"
            if deflate_resp
            else ""
        )
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            f"{ext_line}"
            "\r\n"
        )
        writer.write(response.encode("ascii"))
        await writer.drain()

        ws = WebSocketConnection(reader, writer, deflate=bool(deflate_resp))
        raw_model = (
            getattr(self._radio, "model", None)
            if self._radio is not None
            else None
        )
        model = raw_model if isinstance(raw_model, str) else self._config.radio_model

        if path == "/api/v1/ws":
            handler: Any = ControlHandler(
                ws, self._radio, __version__, model,
                server=self,
            )
        elif path == "/api/v1/scope":
            handler = ScopeHandler(ws, self._radio, server=self)
        elif path == "/api/v1/meters":
            handler = MetersHandler(ws, self._radio, server=self)
        elif path == "/api/v1/audio":
            handler = AudioHandler(ws, self._radio, self._audio_broadcaster)
        else:
            await ws.close(1008, "unknown channel")
            return

        peer = writer.get_extra_info("peername", ("?", 0))
        logger.info(
            "ws connect: %s %s:%s (active=%d)",
            path, peer[0], peer[1], len(self._client_tasks),
        )
        keepalive = asyncio.create_task(ws.keepalive_loop(self._config.keepalive_interval))
        try:
            await handler.run()
        except Exception as exc:
            logger.debug("ws handler error on %s: %s", path, exc)
        finally:
            keepalive.cancel()
            try:
                await keepalive
            except asyncio.CancelledError:
                pass
            logger.info(
                "ws disconnect: %s %s:%s (active=%d)",
                path, peer[0], peer[1], len(self._client_tasks) - 1,
            )


# ------------------------------------------------------------------
# HTTP response helper
# ------------------------------------------------------------------


async def _send_json(
    writer: asyncio.StreamWriter,
    body: bytes,
    headers: dict[str, str] | None = None,
    *,
    etag: str | None = None,
) -> None:
    """Send a JSON response with optional gzip and ETag support."""
    extra: dict[str, str] = {"Content-Type": "application/json"}
    if etag:
        if_none_match = (headers or {}).get("if-none-match", "")
        if if_none_match == etag:
            await _send_response(writer, 304, "Not Modified", b"", {"ETag": etag})
            return
        extra["ETag"] = etag
    if len(body) > 1024 and "gzip" in (headers or {}).get("accept-encoding", ""):
        body = _gzip.compress(body, compresslevel=1)
        extra["Content-Encoding"] = "gzip"
        extra["Vary"] = "Accept-Encoding"
    await _send_response(writer, 200, "OK", body, extra)


async def _send_response(
    writer: asyncio.StreamWriter,
    status: int,
    reason: str,
    body: bytes,
    extra_headers: dict[str, str],
) -> None:
    headers = {
        "Content-Length": str(len(body)),
        "Connection": "close",
        **extra_headers,
    }
    header_lines = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    response = (
        f"HTTP/1.1 {status} {reason}\r\n"
        f"{header_lines}"
        "\r\n"
    ).encode("ascii") + body
    writer.write(response)
    await writer.drain()


# ------------------------------------------------------------------
# Convenience entry point
# ------------------------------------------------------------------


async def run_web_server(
    radio: "Radio | None" = None, **kwargs: Any
) -> None:
    """Create a :class:`WebServer` from *kwargs* and run it forever.

    Keyword arguments are forwarded to :class:`WebConfig`.

    Example::

        await run_web_server(radio, host="0.0.0.0", port=8080)
    """
    config = WebConfig(**kwargs)
    server = WebServer(radio, config)
    await server.serve_forever()
