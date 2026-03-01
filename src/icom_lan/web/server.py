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

The server holds a reference to an IcomRadio instance (optional) and uses
it for command dispatch and scope/meter data delivery.
"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import pathlib
import urllib.parse
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .. import __version__
from .handlers import AudioHandler, ControlHandler, MetersHandler, ScopeHandler
from .protocol import METER_ALC, METER_POWER, METER_SMETER_MAIN, METER_SWR
from .websocket import WS_KEEPALIVE_INTERVAL, WebSocketConnection, make_accept_key

if TYPE_CHECKING:
    from ..radio import IcomRadio

__all__ = ["WebConfig", "WebServer", "run_web_server"]

logger = logging.getLogger(__name__)

_DEFAULT_STATIC_DIR = pathlib.Path(__file__).parent / "static"
_RADIO_MODEL = "IC-7610"


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


class WebServer:
    """Asyncio HTTP + WebSocket server for the icom-lan Web UI.

    Args:
        radio: Connected IcomRadio instance (optional; needed for live data).
        config: Server configuration (defaults to WebConfig()).
    """

    def __init__(
        self,
        radio: "IcomRadio | None" = None,
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
        self._meter_handlers: set["MetersHandler"] = set()
        self._meter_poller_task: asyncio.Task[None] | None = None
        self._meter_lock: asyncio.Lock = asyncio.Lock()
        self._meter_cache: list[tuple[int, int]] | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def ensure_scope_enabled(self, handler: "ScopeHandler") -> None:
        """Register a scope handler and enable scope on radio if needed.

        This is the single entry point for scope lifecycle — handlers must
        not call enable_scope() directly. Uses a lock to guarantee that
        enable_scope() is called at most once regardless of concurrent callers.
        """
        async with self._scope_enable_lock:
            self._scope_handlers.add(handler)
            if self._radio is not None:
                self._radio.on_scope_data(self._broadcast_scope)
            if self._radio is not None:
                try:
                    await self._radio.enable_scope(policy="fast")
                    self._scope_enabled = True
                    logger.info("scope: enabled on radio")
                except Exception:
                    logger.warning("scope: failed to enable", exc_info=True)

    def unregister_scope_handler(self, handler: "ScopeHandler") -> None:
        """Unregister a scope handler."""
        self._scope_handlers.discard(handler)
        if not self._scope_handlers and self._radio is not None:
            self._radio.on_scope_data(None)
            if self._scope_enabled:
                loop = asyncio.get_event_loop()
                loop.create_task(self._disable_scope_async())

    async def _disable_scope_async(self) -> None:
        """Disable scope on the radio when no more handlers are connected."""
        if self._radio is None:
            return
        await asyncio.sleep(self._scope_disable_grace)
        if self._scope_handlers:
            logger.debug("scope: disable task aborted — handler reconnected")
            if self._radio is not None:
                self._radio.on_scope_data(self._broadcast_scope)
            return
        try:
            await self._radio.disable_scope()
            # Double-check: another handler may have connected during the await.
            if not self._scope_handlers:
                self._scope_enabled = False
                logger.info("scope: disabled on radio (no active handlers)")
            else:
                logger.debug("scope: disable succeeded but new handler present — re-enabling")
                # Re-register broadcast so the new handler gets data.
                self._radio.on_scope_data(self._broadcast_scope)
        except Exception:
            logger.warning("scope: failed to disable on radio", exc_info=True)

    def _broadcast_scope(self, frame: Any) -> None:
        """Broadcast scope frame to all registered handlers."""
        for h in list(self._scope_handlers):
            h.enqueue_frame(frame)

    # ------------------------------------------------------------------
    # Meter poller lifecycle
    # ------------------------------------------------------------------

    async def ensure_meters_enabled(self, handler: "MetersHandler") -> None:
        """Register a meter handler and start the shared poller if needed.

        This is the single entry point for meter polling — handlers must not
        poll CI-V directly. Uses a lock to guarantee that the poller task is
        created at most once regardless of concurrent callers.

        New clients immediately receive the cached meter readings (if any)
        without waiting for the next poll cycle.
        """
        async with self._meter_lock:
            self._meter_handlers.add(handler)
            # Deliver cached readings to the new handler immediately.
            if self._meter_cache is not None:
                handler.enqueue_frame(self._meter_cache)
            # Start the shared poller if not already running.
            if (
                self._meter_poller_task is None
                or self._meter_poller_task.done()
            ):
                loop = asyncio.get_running_loop()
                self._meter_poller_task = loop.create_task(self._meter_poll_loop())
                logger.info("meters: poller started")

    def unregister_meter_handler(self, handler: "MetersHandler") -> None:
        """Unregister a meter handler and stop the poller when no handlers remain."""
        self._meter_handlers.discard(handler)
        if not self._meter_handlers:
            if self._meter_poller_task is not None:
                self._meter_poller_task.cancel()
                self._meter_poller_task = None
                logger.info("meters: poller stopped (no active handlers)")
            self._meter_cache = None

    async def _meter_poll_loop(self) -> None:
        """Poll CI-V meters at the fastest requested rate and broadcast to all handlers."""
        try:
            while True:
                if not self._meter_handlers:
                    break
                interval = min(
                    (h.poll_interval for h in list(self._meter_handlers)),
                    default=0.1,
                )
                if self._radio is not None:
                    try:
                        readings = await self._poll_meters()
                        if readings:
                            self._meter_cache = readings
                            self._broadcast_meters(readings)
                    except Exception:
                        logger.debug("meters: poll error", exc_info=True)
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass

    async def _poll_meters(self) -> list[tuple[int, int]]:
        """Read meter values from the radio using the union of all handlers' requests."""
        assert self._radio is not None
        wanted: set[str] = set()
        for h in list(self._meter_handlers):
            wanted.update(h.requested_meters)
        if not wanted:
            wanted = {"smeter", "power", "swr", "alc"}

        meter_map = [
            ("smeter", METER_SMETER_MAIN, self._radio.get_s_meter),
            ("power", METER_POWER, self._radio.get_power),
            ("swr", METER_SWR, self._radio.get_swr),
            ("alc", METER_ALC, self._radio.get_alc),
        ]
        readings: list[tuple[int, int]] = []
        for meter_name, meter_id, getter in meter_map:
            if meter_name not in wanted:
                continue
            try:
                value = await getter()
                readings.append((meter_id, int(value)))
            except Exception:
                pass
        return readings

    def _broadcast_meters(self, readings: list[tuple[int, int]]) -> None:
        """Broadcast meter readings to all registered handlers."""
        for h in list(self._meter_handlers):
            h.enqueue_frame(readings)

    async def start(self) -> None:
        """Start the HTTP/WS listener."""
        self._server = await asyncio.start_server(
            self._accept_client,
            host=self._config.host,
            port=self._config.port,
        )
        addr = self._server.sockets[0].getsockname()
        logger.info("web server listening on %s:%d", addr[0], addr[1])

    async def stop(self) -> None:
        """Close the listener and cancel all active client tasks."""
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
        """Start and block until cancelled."""
        await self.start()
        assert self._server is not None
        try:
            await self._server.serve_forever()
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
        return self._server.sockets[0].getsockname()[1]

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
    ) -> tuple[str, str, dict[str, str]] | None:
        """Read and parse an HTTP request line + headers.

        Returns:
            Tuple of (method, path, headers_dict) or None on EOF/error.
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

        # Decode path (strip query string)
        parsed = urllib.parse.urlparse(raw_path)
        path = urllib.parse.unquote(parsed.path)

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

        return method, path, headers

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
            method, path, headers = result

            logger.debug("request: %s %s from %s:%s", method, path, peer[0], peer[1])

            # WebSocket upgrade?
            if (
                headers.get("upgrade", "").lower() == "websocket"
                and headers.get("connection", "").lower().find("upgrade") >= 0
            ):
                await self._handle_websocket(reader, writer, path, headers)
            else:
                await self._handle_http(writer, method, path)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("connection error from %s:%s: %s", peer[0], peer[1], exc)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # HTTP handlers
    # ------------------------------------------------------------------

    async def _handle_http(
        self,
        writer: asyncio.StreamWriter,
        method: str,
        path: str,
    ) -> None:
        if method not in ("GET", "HEAD"):
            await _send_response(writer, 405, "Method Not Allowed", b"", {})
            return

        if path == "/api/v1/info":
            await self._serve_info(writer)
        elif path == "/api/v1/capabilities":
            await self._serve_capabilities(writer)
        elif path == "/" or path == "/index.html":
            await self._serve_static(writer, "index.html")
        elif path.startswith("/"):
            # Try to serve as static file
            rel = path.lstrip("/") or "index.html"
            await self._serve_static(writer, rel)
        else:
            await _send_response(writer, 404, "Not Found", b"404 Not Found", {})

    async def _serve_info(self, writer: asyncio.StreamWriter) -> None:
        body = json.dumps(
            {
                "server": "icom-lan",
                "version": __version__,
                "proto": 1,
                "radio": self._config.radio_model,
            },
            separators=(",", ":"),
        ).encode()
        await _send_response(
            writer, 200, "OK", body, {"Content-Type": "application/json"}
        )

    async def _serve_capabilities(self, writer: asyncio.StreamWriter) -> None:
        body = json.dumps(
            {
                "scope": True,
                "audio": True,
                "tx": True,
                "freq_ranges": [
                    {"start": 30000, "end": 60000000, "label": "HF"},
                    {"start": 50000000, "end": 54000000, "label": "6m"},
                ],
                "modes": ["USB", "LSB", "CW", "AM", "FM", "RTTY", "CWR"],
                "filters": ["FIL1", "FIL2", "FIL3"],
            },
            separators=(",", ":"),
        ).encode()
        await _send_response(
            writer, 200, "OK", body, {"Content-Type": "application/json"}
        )

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
    ) -> None:
        ws_key = headers.get("sec-websocket-key", "")
        if not ws_key:
            await _send_response(writer, 400, "Bad Request", b"Missing key", {})
            return

        accept = make_accept_key(ws_key)
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        writer.write(response.encode("ascii"))
        await writer.drain()

        ws = WebSocketConnection(reader, writer)

        if path == "/api/v1/ws":
            handler: Any = ControlHandler(
                ws, self._radio, __version__, self._config.radio_model
            )
        elif path == "/api/v1/scope":
            handler = ScopeHandler(ws, self._radio, server=self)
        elif path == "/api/v1/meters":
            handler = MetersHandler(ws, self._radio, server=self)
        elif path == "/api/v1/audio":
            handler = AudioHandler(ws, self._radio)
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
    radio: "IcomRadio | None" = None, **kwargs: Any
) -> None:
    """Create a :class:`WebServer` from *kwargs* and run it forever.

    Keyword arguments are forwarded to :class:`WebConfig`.

    Example::

        await run_web_server(radio, host="0.0.0.0", port=8080)
    """
    config = WebConfig(**kwargs)  # type: ignore[arg-type]
    server = WebServer(radio, config)
    await server.serve_forever()
