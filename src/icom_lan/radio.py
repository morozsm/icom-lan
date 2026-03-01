"""IcomRadio — high-level async API for Icom transceivers over LAN.

Usage::

    async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
        freq = await radio.get_frequency()
        print(f"Freq: {freq / 1e6:.3f} MHz")
        await radio.set_frequency(7_074_000)
        await radio.set_mode("USB")
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import warnings
from typing import TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable

from .commands import (
    CONTROLLER_ADDR,
    IC_7610_ADDR,
    RECEIVER_MAIN,
    _level_bcd_decode,
    build_civ_frame,
    get_alc,
    get_attenuator as get_attenuator_cmd,
    get_data_mode as get_data_mode_cmd,
    get_frequency,
    get_mode,
    get_power,
    get_digisel,
    get_preamp as get_preamp_cmd,
    get_s_meter,
    get_swr,
    parse_ack_nak,
    parse_civ_frame,
    parse_data_mode_response,
    parse_frequency_response,
    parse_meter_response,
    parse_mode_response,
    power_off,
    power_on,
    ptt_off,
    ptt_on,
    scope_data_output as _scope_data_output_cmd,
    scope_on as _scope_on_cmd,
    select_vfo as _select_vfo_cmd,
    send_cw,
    set_attenuator,
    set_attenuator_level,
    set_data_mode as set_data_mode_cmd,
    set_digisel,
    set_frequency,
    set_mode,
    set_power,
    get_rf_gain,
    set_rf_gain,
    get_af_level,
    set_af_level,
    set_preamp,
    set_split,
    stop_cw,
    vfo_a_equals_b,
    vfo_swap,
)
from .exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    TimeoutError,
)
from ._audio_transcoder import PcmOpusTranscoder, create_pcm_opus_transcoder
from .audio import AudioPacket, AudioState, AudioStats, AudioStream
from .commander import IcomCommander, Priority
from .rigctld.state_cache import StateCache
from .civ import (
    CivEvent,
    CivEventType,
    CivRequestTracker,
    iter_civ_frames,
    request_key_from_frame,
)
from .scope import ScopeAssembler, ScopeFrame
from .transport import ConnectionState, IcomTransport
from .types import (
    AudioCapabilities,
    AudioCodec,
    CivFrame,
    Mode,
    ScopeCompletionPolicy,
    get_audio_capabilities,
)

# Import split modules
from ._connection_state import RadioConnectionState
from ._audio_recovery import AudioRecoveryState, _AudioSnapshot, _AudioRecoveryMixin
from ._civ_rx import CIV_HEADER_SIZE, _CivRxMixin
from ._control_phase import (
    CONNINFO_SIZE,
    OPENCLOSE_SIZE,
    STATUS_SIZE,
    TOKEN_ACK_SIZE,
    _ControlPhaseMixin,
)

__all__ = [
    "AudioRecoveryState",
    "IcomRadio",
    "AudioCodec",
    "RadioConnectionState",
    "ScopeFrame",
    "ScopeCompletionPolicy",
]


logger = logging.getLogger(__name__)

_AUDIO_CAPABILITIES = get_audio_capabilities()
_DEFAULT_AUDIO_CODEC = _AUDIO_CAPABILITIES.default_codec
_DEFAULT_AUDIO_SAMPLE_RATE = _AUDIO_CAPABILITIES.default_sample_rate_hz
# Default TTLs (seconds) for the GET-command cache fallback paths.
_DEFAULT_CACHE_TTL: dict[str, float] = {"freq": 10.0, "mode": 10.0, "rf_power": 30.0}


class IcomRadio(_ControlPhaseMixin, _CivRxMixin, _AudioRecoveryMixin):
    """High-level async interface for controlling an Icom transceiver over LAN.

    Manages two UDP connections:
    - Control port (default 50001): authentication and session management.
    - CI-V port (default 50002): CI-V command exchange.

    Args:
        host: Radio IP address or hostname.
        port: Radio control port.
        username: Authentication username.
        password: Authentication password.
        radio_addr: CI-V address of the radio (0x98 for IC-7610).
        timeout: Default timeout for operations in seconds.

    Example::

        async with IcomRadio("192.168.1.100", username="u", password="p") as radio:
            freq = await radio.get_frequency()
            await radio.set_frequency(7_074_000)
    """

    def __init__(
        self,
        host: str,
        port: int = 50001,
        username: str = "",
        password: str = "",
        radio_addr: int = IC_7610_ADDR,
        timeout: float = 5.0,
        audio_codec: AudioCodec | int = _DEFAULT_AUDIO_CODEC,
        audio_sample_rate: int = _DEFAULT_AUDIO_SAMPLE_RATE,
        auto_reconnect: bool = False,
        reconnect_delay: float = 2.0,
        reconnect_max_delay: float = 60.0,
        watchdog_timeout: float = 30.0,
        auto_recover_audio: bool = True,
        on_audio_recovery: "Callable[[AudioRecoveryState], None] | None" = None,
        cache_ttl_s: "dict[str, float] | None" = None,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._radio_addr = radio_addr
        self._timeout = timeout
        self._audio_codec = AudioCodec(audio_codec)
        self._audio_sample_rate = audio_sample_rate
        self._ctrl_transport = IcomTransport()
        self._civ_transport: IcomTransport | None = None
        self._audio_transport: IcomTransport | None = None
        self._audio_stream: AudioStream | None = None
        self._pcm_transcoder: PcmOpusTranscoder | None = None
        self._pcm_transcoder_fmt: tuple[int, int, int] | None = None
        self._pcm_tx_fmt: tuple[int, int, int] | None = None
        self._conn_state = RadioConnectionState.DISCONNECTED
        self._token: int = 0
        self._tok_request: int = 0
        self._auth_seq: int = 0
        self._civ_port: int = 0
        self._audio_port: int = 0
        self._civ_send_seq: int = 0
        self._audio_send_seq: int = 0
        self._civ_lock = asyncio.Lock()
        self._last_civ_send_monotonic: float = 0.0
        self._civ_min_interval: float = (
            float(os.environ.get("ICOM_CIV_MIN_INTERVAL_MS", "35")) / 1000.0
        )
        self._commander: IcomCommander | None = None
        self._filter_width: int | None = None
        self._attenuator_state: bool | None = None
        self._preamp_level: int | None = None
        self._last_freq_hz: int | None = None
        self._last_mode: Mode | None = None
        self._last_power: int | None = None
        self._last_split: bool | None = None
        self._last_vfo: str | None = None
        self._token_task: asyncio.Task | None = None
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay
        self._reconnect_max_delay = reconnect_max_delay
        self._watchdog_timeout = watchdog_timeout
        self._watchdog_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._auto_recover_audio = auto_recover_audio
        self._on_audio_recovery = on_audio_recovery
        self._pcm_rx_user_callback: Callable[[bytes | None], None] | None = None
        self._pcm_rx_jitter_depth: int = 5
        self._opus_rx_user_callback: Callable[[AudioPacket | None], None] | None = None
        self._opus_rx_jitter_depth: int = 5
        self._scope_assembler: ScopeAssembler = ScopeAssembler()
        self._scope_callback: Callable[[ScopeFrame], Any] | None = None
        self._civ_rx_task: asyncio.Task[None] | None = None
        self._civ_request_tracker = CivRequestTracker()
        self._civ_epoch = self._civ_request_tracker.generation
        self._scope_frame_queue: asyncio.Queue[ScopeFrame] = asyncio.Queue(maxsize=64)
        self._scope_activity_counter: int = 0
        self._scope_activity_event = asyncio.Event()
        self._civ_event_queue: asyncio.Queue[CivEvent] = asyncio.Queue(maxsize=256)
        self._civ_ack_sink_grace: float = (
            float(os.environ.get("ICOM_CIV_ACK_SINK_GRACE_MS", "120")) / 1000.0
        )
        self._civ_waiter_ttl_gc_interval: float = 1.0
        self._civ_last_waiter_gc_monotonic: float = time.monotonic()
        self._civ_retry_slice_timeout: float = (
            float(os.environ.get("ICOM_CIV_RETRY_SLICE_MS", "150")) / 1000.0
        )
        self._state_cache: StateCache = StateCache()
        _ttl = {**_DEFAULT_CACHE_TTL, **(cache_ttl_s or {})}
        self._cache_ttl_freq: float = _ttl["freq"]
        self._cache_ttl_mode: float = _ttl["mode"]
        self._cache_ttl_rf_power: float = _ttl["rf_power"]
        # GET commands use a shorter timeout than the general connection timeout.
        # wfview-style: send once, short deadline, fall back to cache.
        self._civ_get_timeout: float = min(timeout, 2.0)

    @property
    def conn_state(self) -> RadioConnectionState:
        """Current connection state."""
        return self._conn_state

    @property
    def connected(self) -> bool:
        """Whether the radio is currently connected."""
        return self._conn_state == RadioConnectionState.CONNECTED

    # ------------------------------------------------------------------
    # Backwards-compatible property shims for _connected / _intentional_disconnect
    # (used by tests and internal loops — keep in sync with _conn_state)
    # ------------------------------------------------------------------

    @property
    def _connected(self) -> bool:
        return self._conn_state == RadioConnectionState.CONNECTED

    @_connected.setter
    def _connected(self, value: bool) -> None:
        if value:
            self._conn_state = RadioConnectionState.CONNECTED
        elif self._conn_state == RadioConnectionState.CONNECTED:
            self._conn_state = RadioConnectionState.DISCONNECTED

    @property
    def _intentional_disconnect(self) -> bool:
        return self._conn_state == RadioConnectionState.DISCONNECTED

    @_intentional_disconnect.setter
    def _intentional_disconnect(self, value: bool) -> None:
        if value:
            self._conn_state = RadioConnectionState.DISCONNECTED
        elif self._conn_state == RadioConnectionState.DISCONNECTED:
            # Clearing intentional disconnect means reconnect is allowed.
            self._conn_state = RadioConnectionState.RECONNECTING

    @property
    def state_cache(self) -> StateCache:
        """Last-known radio state cache (frequency, mode, PTT, meters).

        Updated from both explicit GET responses and unsolicited CI-V frames
        (e.g. VFO knob turns).  Callers can read this directly for a
        non-blocking snapshot of recent state.
        """
        return self._state_cache

    def civ_stats(self) -> dict[str, int]:
        """Return CI-V request tracker statistics for monitoring.

        Returns:
            Dict with keys ``active_waiters``, ``stale_cleaned``,
            ``timeouts``, and ``generation``.
        """
        return self._civ_request_tracker.snapshot_stats()

    async def __aenter__(self) -> "IcomRadio":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        await self.disconnect()

    async def disconnect(self) -> None:
        """Cleanly disconnect from the radio."""
        if self._conn_state == RadioConnectionState.CONNECTED:
            self._conn_state = RadioConnectionState.DISCONNECTING
            self._advance_civ_generation("disconnect")
            self._stop_watchdog()
            self._stop_reconnect()
            self._stop_token_renewal()
            # Stop audio streams
            if self._audio_stream is not None:
                await self._audio_stream.stop_rx()
                await self._audio_stream.stop_tx()
                self._audio_stream = None
            self._pcm_tx_fmt = None
            self._pcm_rx_user_callback = None
            self._opus_rx_user_callback = None
            if self._audio_transport is not None:
                try:
                    await self._send_audio_open_close(open_stream=False)
                except Exception:
                    pass
                await self._audio_transport.disconnect()
                self._audio_transport = None
            if self._civ_transport:
                try:
                    await self._send_open_close(open_stream=False)
                except Exception:
                    pass
                await self._stop_civ_worker()
                await self._stop_civ_rx_pump()
                await self._civ_transport.disconnect()
                self._civ_transport = None
            await self._ctrl_transport.disconnect()
            self._conn_state = RadioConnectionState.DISCONNECTED
            logger.info("Disconnected from %s:%d", self._host, self._port)

    async def soft_disconnect(self) -> None:
        """Disconnect CI-V and audio but keep control transport alive.

        This allows fast reconnect without re-authentication — the radio
        keeps the session open on the control port.
        """
        if self._conn_state != RadioConnectionState.CONNECTED:
            return
        self._conn_state = RadioConnectionState.DISCONNECTING
        self._advance_civ_generation("soft_disconnect")

        # Stop audio
        if self._audio_stream is not None:
            await self._audio_stream.stop_rx()
            await self._audio_stream.stop_tx()
            self._audio_stream = None
        self._pcm_tx_fmt = None
        self._pcm_rx_user_callback = None
        self._opus_rx_user_callback = None
        if self._audio_transport is not None:
            try:
                await self._send_audio_open_close(open_stream=False)
            except Exception:
                pass
            await self._audio_transport.disconnect()
            self._audio_transport = None

        # Stop CI-V
        if self._civ_transport:
            try:
                await self._send_open_close(open_stream=False)
            except Exception:
                pass
            await self._stop_civ_worker()
            await self._stop_civ_rx_pump()
            await self._civ_transport.disconnect()
            self._civ_transport = None

        self._conn_state = RadioConnectionState.DISCONNECTED
        logger.info("Soft disconnect from %s:%d (control kept alive)", self._host, self._port)

    async def soft_reconnect(self) -> None:
        """Reconnect CI-V transport using existing control session.

        Skips discovery and authentication — reuses the existing control
        transport and token. Only re-opens the CI-V data stream.
        """
        if self._civ_transport is not None:
            logger.warning("soft_reconnect: CI-V transport already open")
            return
        if not self._ctrl_transport or not self._ctrl_transport._udp_transport:
            # Control transport dead — need full connect
            logger.info("soft_reconnect: control transport gone, doing full connect")
            await self.connect()
            return

        self._conn_state = RadioConnectionState.CONNECTING

        # Re-open CI-V transport (reuse known port)
        from .transport import IcomTransport
        self._civ_transport = IcomTransport()
        try:
            await self._civ_transport.connect(self._host, self._civ_port)
        except OSError as exc:
            self._civ_transport = None
            self._conn_state = RadioConnectionState.DISCONNECTED
            raise ConnectionError(f"Failed to reconnect CI-V: {exc}") from exc

        self._civ_transport.start_ping_loop()
        self._civ_transport.start_retransmit_loop()
        await self._send_open_close(open_stream=True)

        self._advance_civ_generation("soft_reconnect")
        self._civ_last_waiter_gc_monotonic = __import__("time").monotonic()
        self._start_civ_rx_pump()
        self._conn_state = RadioConnectionState.CONNECTED
        self._start_civ_worker()
        logger.info("Soft reconnect to %s (civ=%d)", self._host, self._civ_port)

    # ------------------------------------------------------------------
    # Watchdog & reconnect loops
    # ------------------------------------------------------------------

    async def _watchdog_loop(self) -> None:
        """Monitor connection health via transport packet queue activity.

        If no packets are received for ``watchdog_timeout`` seconds,
        triggers a reconnect attempt.

        Reference: wfview icomudpaudio.cpp watchdog() — 30s timeout.
        """
        last_activity = time.monotonic()
        last_health_log = time.monotonic()
        last_rx_count = self._ctrl_transport.rx_packet_count
        last_civ_count = (
            self._civ_transport.rx_packet_count if self._civ_transport else 0
        )
        try:
            while self._connected:
                await asyncio.sleep(self.WATCHDOG_CHECK_INTERVAL)
                if not self._connected:
                    break

                # Check if any transport has received new packets since last check
                ctrl_count = self._ctrl_transport.rx_packet_count
                civ_count = (
                    self._civ_transport.rx_packet_count
                    if self._civ_transport
                    else 0
                )
                if ctrl_count != last_rx_count or civ_count != last_civ_count:
                    last_activity = time.monotonic()
                    last_rx_count = ctrl_count
                    last_civ_count = civ_count

                now = time.monotonic()
                idle = now - last_activity

                # Periodic health status log
                if now - last_health_log >= self._WATCHDOG_HEALTH_LOG_INTERVAL:
                    logger.info(
                        "Transport health: ctrl_rx=%d civ_rx=%d idle=%.1fs",
                        ctrl_count,
                        civ_count,
                        idle,
                    )
                    last_health_log = now

                if idle > self._watchdog_timeout:
                    logger.warning(
                        "Watchdog: no activity for %.1fs, triggering reconnect",
                        idle,
                    )
                    self._conn_state = RadioConnectionState.RECONNECTING
                    self._advance_civ_generation("watchdog-timeout")
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())
                    return
        except asyncio.CancelledError:
            pass

    async def _reconnect_loop(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        delay = self._reconnect_delay
        attempt = 0
        try:
            while self._conn_state != RadioConnectionState.DISCONNECTED:
                attempt += 1
                logger.info("Reconnect attempt %d (delay=%.1fs)", attempt, delay)
                try:
                    self._advance_civ_generation("reconnect-attempt")
                    # Capture audio state for auto-recovery.
                    audio_snapshot = self._capture_audio_snapshot()
                    # Clean up old transports
                    self._stop_token_renewal()
                    if self._audio_stream is not None:
                        try:
                            await self._audio_stream.stop_rx()
                            await self._audio_stream.stop_tx()
                        except Exception:
                            pass
                        self._audio_stream = None
                    if self._audio_transport is not None:
                        try:
                            await self._audio_transport.disconnect()
                        except Exception:
                            pass
                        self._audio_transport = None
                    if self._civ_transport is not None:
                        try:
                            await self._civ_transport.disconnect()
                        except Exception:
                            pass
                        self._civ_transport = None
                    try:
                        await self._ctrl_transport.disconnect()
                    except Exception:
                        pass

                    # Re-initialize transport
                    self._ctrl_transport = IcomTransport()
                    await self.connect()
                    logger.info(
                        "Reconnected successfully after %d attempts", attempt
                    )
                    if self._auto_recover_audio and audio_snapshot is not None:
                        await self._recover_audio(audio_snapshot)
                    return
                except Exception as exc:
                    self._conn_state = RadioConnectionState.RECONNECTING
                    logger.warning("Reconnect attempt %d failed: %s", attempt, exc)
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self._reconnect_max_delay)
        except asyncio.CancelledError:
            logger.info("Reconnect cancelled")

    # ------------------------------------------------------------------
    # Audio streaming
    # ------------------------------------------------------------------

    @staticmethod
    def _warn_audio_alias(old_name: str, replacement: str) -> None:
        warnings.warn(
            (
                f"IcomRadio.{old_name}() is deprecated and will be removed after two "
                f"minor releases; use IcomRadio.{replacement}() instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )

    async def start_audio_rx_opus(
        self,
        callback: "Callable[[AudioPacket | None], None]",
        *,
        jitter_depth: int = 5,
    ) -> None:
        """Start receiving Opus audio from the radio.

        Connects the audio transport if not already connected,
        then begins streaming RX audio to the callback.

        Args:
            callback: Called with each :class:`AudioPacket`.
            jitter_depth: Jitter buffer depth (0 to disable, default 5).

        Raises:
            ConnectionError: If not connected or audio port unavailable.
        """
        self._check_connected()
        await self._ensure_audio_transport()
        assert self._audio_stream is not None
        self._opus_rx_user_callback = callback
        self._opus_rx_jitter_depth = jitter_depth
        await self._audio_stream.start_rx(callback, jitter_depth=jitter_depth)

    async def start_audio_rx_pcm(
        self,
        callback: "Callable[[bytes | None], None]",
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
        jitter_depth: int = 5,
    ) -> None:
        """Start receiving decoded PCM audio from the radio.

        This high-level API decodes incoming Opus RX frames to fixed-size
        PCM frames and delivers them to ``callback``. Gap placeholders are
        passed through as ``None`` when jitter buffering detects loss.

        Args:
            callback: Called with decoded PCM frame bytes, or ``None`` for gaps.
            sample_rate: PCM sample rate in Hz (Opus-supported values only).
            channels: PCM channels (1 or 2).
            frame_ms: Frame duration in ms (10/20/40/60).
            jitter_depth: Jitter buffer depth (0 to disable, default 5).

        Raises:
            ConnectionError: If not connected or audio port unavailable.
            TypeError: If callback is not callable or numeric args are not ints.
            ValueError: If ``jitter_depth`` is negative.
            AudioCodecBackendError: If Opus backend is unavailable.
            AudioFormatError: If PCM format is unsupported.
        """
        if not callable(callback):
            raise TypeError("callback must be callable and accept bytes | None.")

        for name, value in (
            ("sample_rate", sample_rate),
            ("channels", channels),
            ("frame_ms", frame_ms),
            ("jitter_depth", jitter_depth),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int, got {type(value).__name__}.")
        if jitter_depth < 0:
            raise ValueError(f"jitter_depth must be >= 0, got {jitter_depth}.")

        self._check_connected()

        # Validate codec/backend and PCM format before stream startup.
        self._get_pcm_transcoder(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )
        self._pcm_rx_user_callback = callback
        self._pcm_rx_jitter_depth = jitter_depth
        await self.start_audio_rx_opus(
            self._build_pcm_rx_callback(
                callback,
                sample_rate=sample_rate,
                channels=channels,
                frame_ms=frame_ms,
            ),
            jitter_depth=jitter_depth,
        )

    async def stop_audio_rx_pcm(self) -> None:
        """Stop receiving decoded PCM audio from the radio."""
        self._pcm_rx_user_callback = None
        await self.stop_audio_rx_opus()

    async def stop_audio_rx_opus(self) -> None:
        """Stop receiving Opus audio from the radio."""
        self._opus_rx_user_callback = None
        if self._audio_stream is not None:
            await self._audio_stream.stop_rx()

    async def start_audio_tx_opus(self) -> None:
        """Start transmitting Opus audio to the radio.

        Connects the audio transport if not already connected.

        Raises:
            ConnectionError: If not connected or audio port unavailable.
        """
        self._check_connected()
        await self._ensure_audio_transport()
        assert self._audio_stream is not None
        await self._audio_stream.start_tx()

    async def start_audio_tx_pcm(
        self,
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> None:
        """Start transmitting PCM audio to the radio.

        This high-level API validates PCM format settings, initializes
        the Opus transcoder backend, and starts the underlying Opus TX stream.

        Args:
            sample_rate: PCM sample rate in Hz (Opus-supported values only).
            channels: PCM channels (1 or 2).
            frame_ms: Frame duration in ms (10/20/40/60).

        Raises:
            ConnectionError: If not connected or audio port unavailable.
            TypeError: If numeric args are not ints.
            AudioCodecBackendError: If Opus backend is unavailable.
            AudioFormatError: If PCM format is unsupported.
        """
        for name, value in (
            ("sample_rate", sample_rate),
            ("channels", channels),
            ("frame_ms", frame_ms),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int, got {type(value).__name__}.")

        self._check_connected()

        # Validate codec/backend and PCM format before stream startup.
        self._get_pcm_transcoder(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )
        await self.start_audio_tx_opus()
        self._pcm_tx_fmt = (sample_rate, channels, frame_ms)

    async def push_audio_tx_opus(self, opus_data: bytes) -> None:
        """Send an Opus-encoded audio frame to the radio.

        Args:
            opus_data: Opus-encoded audio data.

        Raises:
            ConnectionError: If not connected.
            RuntimeError: If audio TX not started.
        """
        self._check_connected()
        if self._audio_stream is None:
            raise RuntimeError("Audio TX not started")
        await self._audio_stream.push_tx(opus_data)

    async def push_audio_tx_pcm(
        self,
        pcm_bytes: bytes | bytearray | memoryview,
    ) -> None:
        """Encode and send one PCM audio frame to the radio.

        Args:
            pcm_bytes: One fixed-size PCM frame (s16le, interleaved).

        Raises:
            ConnectionError: If not connected.
            RuntimeError: If PCM TX not started with :meth:`start_audio_tx_pcm`.
            AudioFormatError: If frame type/size is invalid.
            AudioTranscodeError: If encode operation fails.
        """
        self._check_connected()
        if self._pcm_tx_fmt is None:
            raise RuntimeError(
                "PCM TX not started; call start_audio_tx_pcm() before push_audio_tx_pcm()."
            )
        sample_rate, channels, frame_ms = self._pcm_tx_fmt
        await self._push_audio_tx_pcm_internal(
            pcm_bytes,
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )

    async def stop_audio_tx_pcm(self) -> None:
        """Stop transmitting PCM audio to the radio."""
        await self.stop_audio_tx_opus()

    async def stop_audio_tx_opus(self) -> None:
        """Stop transmitting Opus audio to the radio."""
        if self._audio_stream is not None:
            await self._audio_stream.stop_tx()
        self._pcm_tx_fmt = None

    async def start_audio_opus(
        self,
        rx_callback: "Callable[[AudioPacket | None], None]",
        *,
        tx_enabled: bool = True,
        jitter_depth: int = 5,
    ) -> None:
        """Start full-duplex Opus audio (RX + optional TX).

        Convenience method that starts both RX and TX audio streams
        on the same transport.

        Args:
            rx_callback: Called with each :class:`AudioPacket` (or None for gaps).
            tx_enabled: Whether to also enable TX (default True).
            jitter_depth: Jitter buffer depth (0 to disable, default 5).

        Raises:
            ConnectionError: If not connected or audio port unavailable.
        """
        await self.start_audio_rx_opus(rx_callback, jitter_depth=jitter_depth)
        if tx_enabled:
            assert self._audio_stream is not None
            await self._audio_stream.start_tx()

    async def stop_audio_opus(self) -> None:
        """Stop all Opus audio streams (RX and TX)."""
        await self.stop_audio_tx_opus()
        await self.stop_audio_rx_opus()

    async def start_audio_rx(
        self, callback: "Callable[[AudioPacket | None], None]"
    ) -> None:
        """Deprecated alias for :meth:`start_audio_rx_opus`."""
        self._warn_audio_alias("start_audio_rx", "start_audio_rx_opus")
        await self.start_audio_rx_opus(callback)

    async def stop_audio_rx(self) -> None:
        """Deprecated alias for :meth:`stop_audio_rx_opus`."""
        self._warn_audio_alias("stop_audio_rx", "stop_audio_rx_opus")
        await self.stop_audio_rx_opus()

    async def start_audio_tx(self) -> None:
        """Deprecated alias for :meth:`start_audio_tx_opus`."""
        self._warn_audio_alias("start_audio_tx", "start_audio_tx_opus")
        await self.start_audio_tx_opus()

    async def push_audio_tx(self, opus_data: bytes) -> None:
        """Deprecated alias for :meth:`push_audio_tx_opus`."""
        self._warn_audio_alias("push_audio_tx", "push_audio_tx_opus")
        await self.push_audio_tx_opus(opus_data)

    async def stop_audio_tx(self) -> None:
        """Deprecated alias for :meth:`stop_audio_tx_opus`."""
        self._warn_audio_alias("stop_audio_tx", "stop_audio_tx_opus")
        await self.stop_audio_tx_opus()

    async def start_audio(
        self,
        rx_callback: "Callable[[AudioPacket | None], None]",
        *,
        tx_enabled: bool = True,
    ) -> None:
        """Deprecated alias for :meth:`start_audio_opus`."""
        self._warn_audio_alias("start_audio", "start_audio_opus")
        await self.start_audio_opus(rx_callback, tx_enabled=tx_enabled)

    def get_audio_stats(self) -> dict[str, bool | int | float | str]:
        """Return runtime audio stats for the active stream.

        Returns a JSON-friendly dictionary with packet/loss/jitter/buffer/latency
        metrics. If no audio stream is active, returns a zeroed idle snapshot.
        """
        if self._audio_stream is None:
            return AudioStats.inactive().to_dict()
        return self._audio_stream.get_audio_stats()

    async def stop_audio(self) -> None:
        """Deprecated alias for :meth:`stop_audio_opus`."""
        self._warn_audio_alias("stop_audio", "stop_audio_opus")
        await self.stop_audio_opus()

    def _get_pcm_transcoder(
        self,
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> PcmOpusTranscoder:
        """Get/create cached PCM<->Opus transcoder for internal PCM hooks."""
        key = (sample_rate, channels, frame_ms)
        if self._pcm_transcoder is not None and self._pcm_transcoder_fmt == key:
            return self._pcm_transcoder
        self._pcm_transcoder = create_pcm_opus_transcoder(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )
        self._pcm_transcoder_fmt = key
        return self._pcm_transcoder

    def _build_pcm_rx_callback(
        self,
        callback: "Callable[[bytes | None], None]",
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> "Callable[[AudioPacket | None], None]":
        """Internal adapter: AudioPacket callback -> PCM callback."""

        def _on_audio_packet(packet: AudioPacket | None) -> None:
            if packet is None:
                callback(None)
                return
            pcm_frame = self._decode_audio_packet_to_pcm(
                packet,
                sample_rate=sample_rate,
                channels=channels,
                frame_ms=frame_ms,
            )
            callback(pcm_frame)

        return _on_audio_packet

    def _decode_audio_packet_to_pcm(
        self,
        packet: AudioPacket,
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> bytes:
        """Internal helper for future high-level RX PCM APIs."""
        transcoder = self._get_pcm_transcoder(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )
        return transcoder.opus_to_pcm(packet.data)

    async def _push_audio_tx_pcm_internal(
        self,
        pcm_data: bytes | bytearray | memoryview,
        *,
        sample_rate: int = 48000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> None:
        """Internal helper for future high-level TX PCM APIs."""
        transcoder = self._get_pcm_transcoder(
            sample_rate=sample_rate,
            channels=channels,
            frame_ms=frame_ms,
        )
        opus_data = transcoder.pcm_to_opus(pcm_data)
        await self.push_audio_tx_opus(opus_data)

    @property
    def audio_codec(self) -> "AudioCodec":
        """Configured audio codec."""
        return self._audio_codec

    @property
    def audio_sample_rate(self) -> int:
        """Configured audio sample rate in Hz."""
        return self._audio_sample_rate

    @staticmethod
    def audio_capabilities() -> AudioCapabilities:
        """Return icom-lan audio capabilities and deterministic defaults."""
        return get_audio_capabilities()

    async def _ensure_audio_transport(self) -> None:
        """Connect the audio transport if not already connected."""
        if self._audio_stream is not None:
            return

        if self._audio_port == 0:
            raise ConnectionError("Audio port not available")

        self._audio_transport = IcomTransport()
        try:
            await self._audio_transport.connect(self._host, self._audio_port)
        except OSError as exc:
            self._audio_transport = None
            raise ConnectionError(
                f"Failed to connect audio port {self._audio_port}: {exc}"
            ) from exc

        self._audio_transport.start_ping_loop()
        self._audio_transport.start_retransmit_loop()

        # Per wfview, audio stream also uses OpenClose on its own UDP channel.
        await self._send_audio_open_close(open_stream=True)

        self._audio_stream = AudioStream(self._audio_transport)
        logger.info("Audio transport connected on port %d", self._audio_port)

    # ------------------------------------------------------------------
    # Public CI-V API
    # ------------------------------------------------------------------

    async def send_civ(
        self, command: int, sub: int | None = None, data: bytes | None = None
    ) -> CivFrame | None:
        """Send a CI-V command and return the response.

        Args:
            command: CI-V command byte.
            sub: Optional sub-command byte.
            data: Optional payload data.

        Returns:
            Parsed response CivFrame.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If no response.
        """
        self._check_connected()
        frame = build_civ_frame(
            self._radio_addr, CONTROLLER_ADDR, command, sub=sub, data=data
        )
        return await self._send_civ_raw(frame)

    async def get_frequency(self) -> int:
        """Get the current operating frequency in Hz.

        On timeout falls back to the state cache (if populated) rather than
        raising immediately, allowing callers to remain responsive while the
        radio is busy streaming scope data.
        """
        self._check_connected()
        civ = get_frequency(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_raw(civ, key="get_frequency", dedupe=True)
            freq = parse_frequency_response(resp)
            self._last_freq_hz = freq
            self._state_cache.update_freq(freq)
            return freq
        except TimeoutError:
            if self._state_cache.is_fresh("freq", self._cache_ttl_freq):
                logger.debug(
                    "get_frequency: timeout, returning cached %d Hz",
                    self._state_cache.freq,
                )
                return self._state_cache.freq
            raise

    async def set_frequency(self, freq_hz: int) -> None:
        """Set the operating frequency.

        Args:
            freq_hz: Frequency in Hz.
        """
        self._check_connected()
        civ = set_frequency(freq_hz, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)
        self._last_freq_hz = freq_hz
        self._state_cache.update_freq(freq_hz)

    async def get_mode(self) -> Mode:
        """Get the current operating mode."""
        mode, _ = await self.get_mode_info()
        return mode

    async def get_mode_info(self) -> tuple[Mode, int | None]:
        """Get current mode and filter number (if reported by radio).

        On timeout falls back to the state cache when populated.
        """
        self._check_connected()
        civ = get_mode(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_raw(civ)
            mode, filt = parse_mode_response(resp)
            self._last_mode = mode
            if filt is not None:
                self._filter_width = filt
            self._state_cache.update_mode(mode.name, filt)
            return mode, filt
        except TimeoutError:
            if self._state_cache.is_fresh("mode", self._cache_ttl_mode):
                logger.debug(
                    "get_mode_info: timeout, returning cached %s",
                    self._state_cache.mode,
                )
                return Mode[self._state_cache.mode], self._state_cache.filter_width
            raise

    async def get_filter(self) -> int | None:
        """Get current mode filter number (1-3) when available."""
        _, filt = await self.get_mode_info()
        return filt if filt is not None else self._filter_width

    async def set_filter(self, filter_width: int) -> None:
        """Set filter number (1-3) while keeping current mode unchanged."""
        mode = await self.get_mode()
        await self.set_mode(mode, filter_width=filter_width)

    async def set_mode(self, mode: Mode | str, filter_width: int | None = None) -> None:
        """Set the operating mode.

        Args:
            mode: Mode enum or string name (e.g. "USB", "LSB").
            filter_width: Optional filter number (1-3).
        """
        self._check_connected()
        if isinstance(mode, str):
            mode = Mode[mode]
        civ = set_mode(mode, filter_width=filter_width, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)
        self._last_mode = mode
        if filter_width is not None:
            self._filter_width = filter_width
        cached_filter = filter_width if filter_width is not None else self._filter_width
        self._state_cache.update_mode(mode.name, cached_filter)

    async def get_data_mode(self) -> bool:
        """Get the IC-7610 DATA mode state (command 0x1A 0x06).

        Returns:
            True if DATA mode is active (DATA1/2/3), False if off.
        """
        self._check_connected()
        civ = get_data_mode_cmd(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_data_mode_response(resp)

    async def set_data_mode(self, on: bool) -> None:
        """Set the IC-7610 DATA mode (command 0x1A 0x06).

        Args:
            on: True to enable DATA1 mode, False to disable.
        """
        self._check_connected()
        civ = set_data_mode_cmd(on, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected set_data_mode({on})")

    async def get_power(self) -> int:
        """Get the RF power level (0-255).

        On timeout falls back to the state cache if populated.
        """
        self._check_connected()
        civ = get_power(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_raw(civ, key="get_power", dedupe=True)
            level = _level_bcd_decode(resp.data)
            self._last_power = level
            self._state_cache.update_rf_power(level / 255.0)
            return level
        except TimeoutError:
            if (
                self._state_cache.is_fresh("rf_power", self._cache_ttl_rf_power)
                and self._state_cache.rf_power is not None
            ):
                cached_level = round(self._state_cache.rf_power * 255)
                logger.debug(
                    "get_power: timeout, returning cached %d", cached_level
                )
                return cached_level
            raise

    async def set_power(self, level: int) -> None:
        """Set the RF power level (0-255).

        Args:
            level: Power level 0-255.
        """
        self._check_connected()
        civ = set_power(level, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)
        self._last_power = level

    async def get_rf_gain(self) -> int:
        """Read the current RF gain level (0-255)."""
        self._check_connected()
        civ = get_rf_gain(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_raw(civ, key="get_rf_gain", dedupe=True)
            return self._parse_level(resp)
        except TimeoutError:
            raise

    async def set_rf_gain(self, level: int) -> None:
        """Set RF gain level (0-255)."""
        if not 0 <= level <= 255:
            raise ValueError(f"RF gain must be 0-255, got {level}")
        self._check_connected()
        civ = set_rf_gain(level, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_af_level(self) -> int:
        """Read the current AF output level (0-255)."""
        self._check_connected()
        civ = get_af_level(to_addr=self._radio_addr)
        try:
            resp = await self._send_civ_raw(civ, key="get_af_level", dedupe=True)
            return self._parse_level(resp)
        except TimeoutError:
            raise

    async def set_af_level(self, level: int) -> None:
        """Set AF output level (0-255)."""
        if not 0 <= level <= 255:
            raise ValueError(f"AF level must be 0-255, got {level}")
        self._check_connected()
        civ = set_af_level(level, to_addr=self._radio_addr)
        await self._send_civ_raw(civ, wait_response=False)

    async def get_s_meter(self) -> int:
        """Read the S-meter value (0-255)."""
        self._check_connected()
        civ = get_s_meter(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def get_swr(self) -> int:
        """Read the SWR meter value (0-255)."""
        self._check_connected()
        civ = get_swr(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def get_alc(self) -> int:
        """Read the ALC meter value (0-255)."""
        self._check_connected()
        civ = get_alc(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return parse_meter_response(resp)

    async def set_ptt(self, on: bool) -> None:
        """Toggle PTT (Push-To-Talk).

        Fire-and-forget: the command is sent at IMMEDIATE priority without
        blocking for an ACK.  The state cache is updated optimistically.

        Args:
            on: True for TX, False for RX.
        """
        self._check_connected()
        civ = (
            ptt_on(to_addr=self._radio_addr)
            if on
            else ptt_off(to_addr=self._radio_addr)
        )
        await self._send_civ_raw(civ, priority=Priority.IMMEDIATE, wait_response=False)
        self._state_cache.update_ptt(on)
        logger.debug("set_ptt(%s) sent (fire-and-forget)", on)

    # ------------------------------------------------------------------
    # VFO / Split
    # ------------------------------------------------------------------

    async def select_vfo(self, vfo: str = "A") -> None:
        """Select VFO.

        Args:
            vfo: "A", "B", "MAIN", or "SUB".
                 IC-7610 uses MAIN/SUB.
        """
        self._check_connected()
        civ = _select_vfo_cmd(vfo, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected VFO select {vfo}")
        self._last_vfo = vfo.upper()

    async def vfo_equalize(self) -> None:
        """Copy VFO A to VFO B (A=B)."""
        self._check_connected()
        civ = vfo_a_equals_b(to_addr=self._radio_addr)
        await self._send_civ_raw(civ)

    async def vfo_exchange(self) -> None:
        """Swap VFO A and B."""
        self._check_connected()
        civ = vfo_swap(to_addr=self._radio_addr)
        await self._send_civ_raw(civ)

    async def set_split_mode(self, on: bool) -> None:
        """Enable or disable split mode."""
        self._check_connected()
        civ = set_split(on, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected split {'on' if on else 'off'}")
        self._last_split = on

    async def get_attenuator_level(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read attenuator level in dB (Command29-aware).

        Args:
            receiver: RECEIVER_MAIN (0) or RECEIVER_SUB (1).
        """
        self._check_connected()
        civ = get_attenuator_cmd(to_addr=self._radio_addr, receiver=receiver)
        try:
            resp = await self._send_civ_raw(civ)
            if resp.data:
                raw = resp.data[0]
                val = ((raw >> 4) & 0x0F) * 10 + (raw & 0x0F)
                self._attenuator_state = val != 0
                return val
        except TimeoutError:
            pass

        if self._attenuator_state is not None:
            return 18 if self._attenuator_state else 0
        raise CommandError("Radio returned empty attenuator response")

    async def get_attenuator(self) -> bool:
        """Read attenuator state (compat wrapper)."""
        return (await self.get_attenuator_level()) > 0

    async def set_attenuator_level(
        self, db: int, receiver: int = RECEIVER_MAIN
    ) -> None:
        """Set attenuator level in dB (Command29-aware).

        Fire-and-forget: the command is sent without waiting for an ACK.
        The attenuator state is updated optimistically.

        Args:
            db: Attenuation in dB (0..45 in 3 dB steps).
            receiver: RECEIVER_MAIN (0) or RECEIVER_SUB (1).
        """
        self._check_connected()
        if db < 0 or db > 45 or db % 3 != 0:
            raise ValueError(f"Attenuator level must be 0..45 in 3 dB steps, got {db}")
        civ = set_attenuator_level(db, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)
        self._attenuator_state = db > 0
        logger.debug("set_attenuator(%d dB) sent (fire-and-forget)", db)

    async def set_attenuator(self, on: bool, receiver: int = RECEIVER_MAIN) -> None:
        """Enable or disable attenuator (compat wrapper, Command29-aware)."""
        self._check_connected()
        civ = set_attenuator(on, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)
        self._attenuator_state = on

    async def get_preamp(self, receiver: int = RECEIVER_MAIN) -> int:
        """Read preamp level (0=off, 1=PREAMP1, 2=PREAMP2) (Command29-aware).

        Args:
            receiver: RECEIVER_MAIN (0) or RECEIVER_SUB (1).
        """
        self._check_connected()
        civ = get_preamp_cmd(to_addr=self._radio_addr, receiver=receiver)
        try:
            resp = await self._send_civ_raw(civ)
            if resp.data:
                raw = resp.data[0]
                self._preamp_level = ((raw >> 4) & 0x0F) * 10 + (raw & 0x0F)
                return self._preamp_level
        except TimeoutError:
            pass

        if self._preamp_level is not None:
            return self._preamp_level
        raise CommandError("Radio returned empty preamp response")

    async def set_preamp(self, level: int = 1, receiver: int = RECEIVER_MAIN) -> None:
        """Set preamp level (0=off, 1=PREAMP1, 2=PREAMP2) (Command29-aware).

        Args:
            level: 0=off, 1=PREAMP1, 2=PREAMP2.
            receiver: RECEIVER_MAIN (0) or RECEIVER_SUB (1).

        Raises:
            CommandError: If DIGI-SEL (IP+) is enabled. On IC-7610, PREAMP and
                DIGI-SEL are mutually exclusive — disable DIGI-SEL first.
        """
        self._check_connected()

        # Pre-flight: check DIGI-SEL / PREAMP mutual exclusion
        if level > 0:
            try:
                if await self.get_digisel():
                    raise CommandError(
                        f"Cannot set preamp level {level}: DIGI-SEL (IP+) is ON. "
                        "PREAMP and DIGI-SEL are mutually exclusive — disable DIGI-SEL first."
                    )
            except CommandError as exc:
                if "DIGI-SEL" in str(exc) and "mutually exclusive" in str(exc):
                    raise  # Our own error — propagate
                # get_digisel() failed (radio doesn't support it, timeout, etc.) — ignore
            except Exception:
                pass  # Unexpected error — proceed anyway

        civ = set_preamp(level, to_addr=self._radio_addr, receiver=receiver)
        await self._send_civ_raw(civ, wait_response=False)
        self._preamp_level = level

    async def get_digisel(self) -> bool:
        """Read DIGI-SEL status (IC-7610 frontend selector)."""
        self._check_connected()
        civ = get_digisel(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        if not resp.data:
            raise CommandError("Radio returned empty DIGI-SEL response")
        raw = resp.data[0]
        val = ((raw >> 4) & 0x0F) * 10 + (raw & 0x0F)
        return bool(val)

    async def set_digisel(self, on: bool) -> None:
        """Set DIGI-SEL status."""
        self._check_connected()
        civ = set_digisel(on, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected DIGI-SEL {'on' if on else 'off'}")

    async def snapshot_state(self) -> dict[str, object]:
        """Best-effort snapshot of core rig state for safe restore."""
        self._check_connected()
        state: dict[str, object] = {}

        try:
            state["frequency"] = await self.get_frequency()
        except Exception:
            if self._last_freq_hz is not None:
                state["frequency"] = self._last_freq_hz

        try:
            mode, filt = await self.get_mode_info()
            state["mode"] = mode
            if filt is not None:
                state["filter"] = filt
        except Exception:
            if self._last_mode is not None:
                state["mode"] = self._last_mode
            if self._filter_width is not None:
                state["filter"] = self._filter_width

        try:
            state["power"] = await self.get_power()
        except Exception:
            if self._last_power is not None:
                state["power"] = self._last_power

        if self._last_split is not None:
            state["split"] = self._last_split
        if self._last_vfo is not None:
            state["vfo"] = self._last_vfo
        if self._attenuator_state is not None:
            state["attenuator"] = self._attenuator_state
        if self._preamp_level is not None:
            state["preamp"] = self._preamp_level

        return state

    async def restore_state(self, state: dict[str, object]) -> None:
        """Best-effort restore of state produced by snapshot_state()."""
        self._check_connected()

        if "split" in state:
            try:
                await self.set_split_mode(bool(state["split"]))
            except Exception:
                pass
        if "vfo" in state:
            try:
                await self.select_vfo(str(state["vfo"]))
            except Exception:
                pass

        if "power" in state:
            try:
                await self.set_power(int(state["power"]))
            except Exception:
                pass

        mode = state.get("mode")
        filt = state.get("filter")
        if isinstance(mode, Mode):
            try:
                await self.set_mode(
                    mode, filter_width=int(filt) if isinstance(filt, int) else None
                )
            except Exception:
                pass

        if "frequency" in state:
            try:
                await self.set_frequency(int(state["frequency"]))
            except Exception:
                pass

        if "attenuator" in state:
            try:
                await self.set_attenuator(bool(state["attenuator"]))
            except Exception:
                pass

        if "preamp" in state:
            try:
                await self.set_preamp(int(state["preamp"]))
            except Exception:
                pass

    async def run_state_transaction(
        self,
        body: "Callable[[], Awaitable[None]]",
    ) -> None:
        """Run operation with snapshot/restore guard (wfview-style safety pattern)."""
        self._check_connected()

        async def _body() -> dict[str, object]:
            await body()
            return {}

        if self._commander is None:
            snapshot = await self.snapshot_state()
            try:
                await body()
            finally:
                await self.restore_state(snapshot)
            return

        await self._commander.transaction(
            snapshot=self.snapshot_state,
            restore=self.restore_state,
            body=_body,
        )

    # ------------------------------------------------------------------
    # CW keying
    # ------------------------------------------------------------------

    async def send_cw_text(self, text: str) -> None:
        """Send CW text via the radio's built-in keyer.

        Text is split into 30-character chunks.

        Args:
            text: CW text (A-Z, 0-9, prosigns).
        """
        self._check_connected()
        frames = send_cw(text, to_addr=self._radio_addr)
        for frame in frames:
            resp = await self._send_civ_raw(frame)
            ack = parse_ack_nak(resp)
            if ack is False:
                raise CommandError("Radio rejected CW text")

    async def stop_cw_text(self) -> None:
        """Stop CW sending."""
        self._check_connected()
        civ = stop_cw(to_addr=self._radio_addr)
        await self._send_civ_raw(civ, priority=Priority.IMMEDIATE)
        # Stop CW may not return ACK, just ignore

    async def power_control(self, on: bool) -> None:
        """Power the radio on or off.

        Args:
            on: True to power on, False to power off.
        """
        self._check_connected()
        civ = (
            power_on(to_addr=self._radio_addr)
            if on
            else power_off(to_addr=self._radio_addr)
        )
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected power {'on' if on else 'off'}")

    # ------------------------------------------------------------------
    # Scope / Waterfall API
    # ------------------------------------------------------------------

    def on_scope_data(self, callback: "Callable[[ScopeFrame], None] | None") -> None:
        """Register a callback for completed scope frames.

        Args:
            callback: Function taking a ScopeFrame, or None to unregister.
        """
        self._scope_callback = callback

    async def scope_stream(self) -> AsyncGenerator[ScopeFrame, None]:
        """Consume scope frames asynchronously.

        Yields:
            ScopeFrame objects as they are assembled.
            Stops yielding if the radio disconnects.

        Note:
            Uses a bounded queue (maxsize=64) that drops oldest frames if not
            consumed fast enough. Call enable_scope() separately to start data.
        """
        while self._connected:
            try:
                frame = await asyncio.wait_for(
                    self._scope_frame_queue.get(), timeout=1.0
                )
                yield frame
                self._scope_frame_queue.task_done()
            except asyncio.TimeoutError:
                continue

    async def enable_scope(
        self,
        *,
        output: bool = True,
        policy: ScopeCompletionPolicy | str = ScopeCompletionPolicy.VERIFY,
        timeout: float = 5.0,
    ) -> None:
        """Enable scope display and data output on the radio.

        Args:
            output: Also enable wave data output (default True).
            policy: Completion policy (strict, fast, verify).
            timeout: Verification timeout in seconds.

        Raises:
            CommandError: If the radio rejects the command (in strict mode).
            TimeoutError: If verification times out (in verify mode).
        """
        self._check_connected()
        pol = ScopeCompletionPolicy(policy)
        wait_resp = pol == ScopeCompletionPolicy.STRICT

        if pol == ScopeCompletionPolicy.VERIFY:
            self._scope_activity_event.clear()

        resp = await self._send_civ_raw(
            _scope_on_cmd(to_addr=self._radio_addr), wait_response=wait_resp
        )
        if wait_resp and resp is not None:
            if parse_ack_nak(resp) is False:
                raise CommandError("Radio rejected scope enable")
        if output:
            resp = await self._send_civ_raw(
                _scope_data_output_cmd(True, to_addr=self._radio_addr),
                wait_response=wait_resp,
            )
            if wait_resp and resp is not None:
                if parse_ack_nak(resp) is False:
                    raise CommandError("Radio rejected scope data output enable")

        if pol == ScopeCompletionPolicy.VERIFY:
            try:
                await asyncio.wait_for(
                    self._scope_activity_event.wait(), timeout=timeout
                )
            except asyncio.TimeoutError:
                raise TimeoutError("Scope enable verification timed out (no data seen)")

    async def disable_scope(
        self, *, policy: ScopeCompletionPolicy | str = ScopeCompletionPolicy.FAST
    ) -> None:
        """Disable scope data output on the radio.

        Args:
            policy: Completion policy, usually fast.

        Raises:
            CommandError: If the radio rejects the command (strict mode).
        """
        self._check_connected()
        pol = ScopeCompletionPolicy(policy)
        wait_resp = pol == ScopeCompletionPolicy.STRICT

        resp = await self._send_civ_raw(
            _scope_data_output_cmd(False, to_addr=self._radio_addr),
            wait_response=wait_resp,
        )
        if wait_resp and resp is not None:
            if parse_ack_nak(resp) is False:
                raise CommandError("Radio rejected scope data output disable")

    async def capture_scope_frame(self, timeout: float = 5.0) -> ScopeFrame:
        """Enable scope and capture one complete frame.

        Does NOT disable scope after — caller decides when to stop.

        Args:
            timeout: Maximum time to wait for a frame in seconds.

        Returns:
            First complete ScopeFrame received.

        Raises:
            TimeoutError: If no frame is received within timeout.
        """
        frames = await self.capture_scope_frames(count=1, timeout=timeout)
        return frames[0]

    async def capture_scope_frames(
        self, count: int = 50, timeout: float = 10.0
    ) -> list[ScopeFrame]:
        """Enable scope and capture *count* complete frames.

        Does NOT disable scope after — caller decides when to stop.

        Args:
            count: Number of complete frames to capture.
            timeout: Maximum time to wait in seconds.

        Returns:
            List of ScopeFrame objects, oldest first.

        Raises:
            TimeoutError: If fewer than *count* frames arrive within timeout.
        """
        self._check_connected()

        collected: list[ScopeFrame] = []
        frame_ready = asyncio.Event()

        def _on_frame(frame: ScopeFrame) -> None:
            collected.append(frame)
            if len(collected) >= count:
                frame_ready.set()

        old_callback = self._scope_callback
        self.on_scope_data(_on_frame)
        try:
            await self.enable_scope(policy=ScopeCompletionPolicy.VERIFY, timeout=timeout)
            try:
                await asyncio.wait_for(frame_ready.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Scope capture timed out: received {len(collected)}/{count} frames"
                )
        finally:
            self.on_scope_data(old_callback)

        return collected[:count]
