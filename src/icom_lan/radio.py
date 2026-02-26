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
import struct
import time
import warnings
from typing import TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable

from .auth import (
    build_conninfo_packet,
    build_login_packet,
    parse_auth_response,
)
from .commands import (
    CONTROLLER_ADDR,
    IC_7610_ADDR,
    RECEIVER_MAIN,
    _level_bcd_decode,
    build_civ_frame,
    get_alc,
    get_attenuator as get_attenuator_cmd,
    get_frequency,
    get_mode,
    get_power,
    get_digisel,
    get_preamp as get_preamp_cmd,
    get_s_meter,
    get_swr,
    parse_ack_nak,
    parse_civ_frame,
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
    set_digisel,
    set_frequency,
    set_mode,
    set_power,
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
from .audio import AudioPacket, AudioStream
from .commander import IcomCommander, Priority
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

__all__ = ["IcomRadio", "AudioCodec", "ScopeFrame", "ScopeCompletionPolicy"]

logger = logging.getLogger(__name__)

CIV_HEADER_SIZE = 0x15
OPENCLOSE_SIZE = 0x16  # per wfview packettypes.h
TOKEN_ACK_SIZE = 0x40
CONNINFO_SIZE = 0x90
STATUS_SIZE = 0x50
_AUDIO_CAPABILITIES = get_audio_capabilities()
_DEFAULT_AUDIO_CODEC = _AUDIO_CAPABILITIES.default_codec
_DEFAULT_AUDIO_SAMPLE_RATE = _AUDIO_CAPABILITIES.default_sample_rate_hz


class IcomRadio:
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
        self._connected = False
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
        self._intentional_disconnect = False
        self._scope_assembler: ScopeAssembler = ScopeAssembler()
        self._scope_callback: Callable[[ScopeFrame], Any] | None = None
        self._civ_rx_task: asyncio.Task[None] | None = None
        self._civ_request_tracker = CivRequestTracker()
        self._scope_frame_queue: asyncio.Queue[ScopeFrame] = asyncio.Queue(maxsize=64)
        self._scope_activity_counter: int = 0
        self._scope_activity_event = asyncio.Event()
        self._civ_event_queue: asyncio.Queue[CivEvent] = asyncio.Queue(maxsize=256)
        self._civ_ack_sink_grace: float = (
            float(os.environ.get("ICOM_CIV_ACK_SINK_GRACE_MS", "120")) / 1000.0
        )

    @property
    def connected(self) -> bool:
        """Whether the radio is currently connected."""
        return self._connected

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open connection to the radio and authenticate.

        Performs the full handshake sequence:
        1. Discovery on control port (Are You There → I Am Here).
        2. Login with credentials.
        3. Token acknowledgement.
        4. Conninfo exchange to learn CI-V port.
        5. Open CI-V connection and start CI-V data stream.

        Raises:
            ConnectionError: If UDP connection fails.
            AuthenticationError: If login is rejected.
            TimeoutError: If the radio doesn't respond.
        """
        # --- Phase 1: Control port ---
        try:
            await self._ctrl_transport.connect(self._host, self._port)
        except OSError as exc:
            raise ConnectionError(
                f"Failed to connect to {self._host}:{self._port}: {exc}"
            ) from exc

        self._ctrl_transport.start_ping_loop()
        self._ctrl_transport.start_retransmit_loop()

        # Login
        login_pkt = build_login_packet(
            self._username,
            self._password,
            sender_id=self._ctrl_transport.my_id,
            receiver_id=self._ctrl_transport.remote_id,
        )
        await self._ctrl_transport.send_tracked(login_pkt)
        resp_data = await self._wait_for_packet(
            self._ctrl_transport, size=0x60, label="login response"
        )
        auth = parse_auth_response(resp_data)
        if not auth.success:
            raise AuthenticationError(
                f"Authentication failed (error=0x{auth.error:08X})"
            )
        self._token = auth.token
        self._tok_request = auth.tok_request
        logger.info(
            "Authenticated with %s:%d, token=0x%08X",
            self._host,
            self._port,
            self._token,
        )

        # Token ack
        await self._send_token_ack()

        # Get GUID from radio's conninfo
        guid = await self._receive_guid()

        # Send our conninfo → triggers status packet with CI-V port
        await self._send_conninfo(guid)

        civ_port = await self._receive_civ_port()
        if civ_port == 0:
            civ_port = self._port + 1  # Fallback: assume control+1
            logger.debug("CI-V port not in status, using default %d", civ_port)
        self._civ_port = civ_port

        # wfview/protocol defaults: audio is typically control+2 (50003).
        # Keep this as a fallback if status didn't carry audio_port.
        if self._audio_port == 0:
            self._audio_port = self._port + 2
            logger.debug("Audio port not in status, using default %d", self._audio_port)

        # --- Phase 2: CI-V port ---
        self._civ_transport = IcomTransport()
        try:
            await self._civ_transport.connect(self._host, self._civ_port)
        except OSError as exc:
            await self._ctrl_transport.disconnect()
            raise ConnectionError(
                f"Failed to connect CI-V port {self._civ_port}: {exc}"
            ) from exc

        self._civ_transport.start_ping_loop()
        self._civ_transport.start_retransmit_loop()

        # Open CI-V data stream
        await self._send_open_close(open_stream=True)

        # Flush initial waterfall/status data
        await asyncio.sleep(0.3)
        await self._flush_queue(self._civ_transport)

        self._start_civ_rx_pump()
        self._connected = True
        self._intentional_disconnect = False
        self._ctrl_transport.state = ConnectionState.CONNECTED
        self._start_civ_worker()
        self._start_token_renewal()
        if self._auto_reconnect:
            self._start_watchdog()
        logger.info(
            "Connected to %s (control=%d, civ=%d)",
            self._host,
            self._port,
            self._civ_port,
        )

    async def disconnect(self) -> None:
        """Cleanly disconnect from the radio."""
        if self._connected:
            self._connected = False
            self._intentional_disconnect = True
            self._stop_watchdog()
            self._stop_reconnect()
            self._stop_token_renewal()
            # Stop audio streams
            if self._audio_stream is not None:
                await self._audio_stream.stop_rx()
                await self._audio_stream.stop_tx()
                self._audio_stream = None
            self._pcm_tx_fmt = None
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
            logger.info("Disconnected from %s:%d", self._host, self._port)

    async def __aenter__(self) -> "IcomRadio":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        await self.disconnect()

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
        callback: "Callable[[AudioPacket], None]",
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
        await self.stop_audio_rx_opus()

    async def stop_audio_rx_opus(self) -> None:
        """Stop receiving Opus audio from the radio."""
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
        rx_callback: "Callable[[AudioPacket], None]",
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

    async def start_audio_rx(self, callback: "Callable[[AudioPacket], None]") -> None:
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
        rx_callback: "Callable[[AudioPacket], None]",
        *,
        tx_enabled: bool = True,
    ) -> None:
        """Deprecated alias for :meth:`start_audio_opus`."""
        self._warn_audio_alias("start_audio", "start_audio_opus")
        await self.start_audio_opus(rx_callback, tx_enabled=tx_enabled)

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
    # CI-V RX + command queue
    # ------------------------------------------------------------------

    def _start_civ_rx_pump(self) -> None:
        """Start always-on CI-V receive pump."""
        if self._civ_rx_task is None or self._civ_rx_task.done():
            self._civ_rx_task = asyncio.create_task(self._civ_rx_loop())

    async def _stop_civ_rx_pump(self) -> None:
        """Stop CI-V receive pump and fail pending request futures."""
        self._civ_request_tracker.fail_all(ConnectionError("CI-V RX pump stopped"))
        if self._civ_rx_task is not None and not self._civ_rx_task.done():
            self._civ_rx_task.cancel()
            try:
                await self._civ_rx_task
            except asyncio.CancelledError:
                pass
        self._civ_rx_task = None

    def _ensure_civ_runtime(self) -> None:
        """Ensure CI-V transport exists (tests may bypass connect()).

        Note: we intentionally do NOT start the CI-V RX pump here.
        The RX pump should be started explicitly (connect() or right before
        sending) to avoid races with tests that pre-queue mock packets.
        """
        if self._civ_transport is None:
            raise ConnectionError("Not connected to radio")

    async def _civ_rx_loop(self) -> None:
        """Continuously consume CI-V transport packets and route events."""
        assert self._civ_transport is not None
        try:
            while self._civ_transport is not None:
                try:
                    packet = await self._civ_transport.receive_packet(timeout=0.2)
                except asyncio.TimeoutError:
                    continue
                if len(packet) <= CIV_HEADER_SIZE:
                    continue
                payload = packet[CIV_HEADER_SIZE:]
                for frame_bytes in iter_civ_frames(payload):
                    try:
                        frame = parse_civ_frame(frame_bytes)
                    except ValueError:
                        continue
                    try:
                        await self._route_civ_frame(frame)
                    except Exception:
                        logger.exception("Unhandled exception while routing CI-V frame")
        except asyncio.CancelledError:
            pass

    async def _route_civ_frame(self, frame: CivFrame) -> None:
        """Route one parsed CI-V frame into command/scope event paths."""
        if frame.from_addr != self._radio_addr or frame.to_addr != CONTROLLER_ADDR:
            return

        if frame.command == 0x27 and frame.sub == 0x00 and len(frame.data) >= 3:
            receiver = frame.data[0]
            self._scope_activity_counter += 1
            self._scope_activity_event.set()
            self._publish_civ_event(
                CivEvent(
                    type=CivEventType.SCOPE_CHUNK,
                    frame=frame,
                    receiver=receiver,
                )
            )
            scope_frame = self._scope_assembler.feed(frame.data[1:], receiver)
            if scope_frame is not None:
                self._publish_scope_frame(scope_frame)
            return

        if frame.command == 0xFB:
            event = CivEvent(type=CivEventType.ACK, frame=frame)
        elif frame.command == 0xFA:
            event = CivEvent(type=CivEventType.NAK, frame=frame)
        else:
            event = CivEvent(type=CivEventType.RESPONSE, frame=frame)

        self._publish_civ_event(event)
        self._civ_request_tracker.resolve(event)

    def _publish_scope_frame(self, frame: ScopeFrame) -> None:
        """Publish a complete scope frame to callback and bounded queue."""
        self._publish_civ_event(CivEvent(type=CivEventType.SCOPE_FRAME))
        if self._scope_frame_queue.full():
            try:
                self._scope_frame_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._scope_frame_queue.put_nowait(frame)
        callback = self._scope_callback
        if callback is not None:
            try:
                callback(frame)
            except Exception:
                logger.exception("Scope callback raised an exception")

    def _publish_civ_event(self, event: CivEvent) -> None:
        """Publish CI-V event to internal event queue (best effort)."""
        if self._civ_event_queue.full():
            try:
                self._civ_event_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._civ_event_queue.put_nowait(event)

    def _start_civ_worker(self) -> None:
        """Start serialized CI-V commander (wfview-like queueing)."""
        self._ensure_civ_runtime()
        self._start_civ_rx_pump()
        if self._commander is None:
            self._commander = IcomCommander(
                self._execute_civ_raw,
                min_interval=self._civ_min_interval,
            )
        self._commander.start()

    async def _stop_civ_worker(self) -> None:
        """Stop CI-V commander and fail pending commands."""
        if self._commander is not None:
            await self._commander.stop()

    # ------------------------------------------------------------------
    # Token renewal
    # ------------------------------------------------------------------

    TOKEN_RENEWAL_INTERVAL = 60.0  # seconds (wfview: TOKEN_RENEWAL = 60000ms)
    TOKEN_PACKET_SIZE = 0x40

    def _start_token_renewal(self) -> None:
        """Start periodic token renewal task."""
        if self._token_task is None or self._token_task.done():
            self._token_task = asyncio.create_task(self._token_renewal_loop())

    def _stop_token_renewal(self) -> None:
        """Cancel token renewal task."""
        if self._token_task is not None and not self._token_task.done():
            self._token_task.cancel()
            self._token_task = None

    async def _token_renewal_loop(self) -> None:
        """Background task: send token renewal every TOKEN_RENEWAL_INTERVAL."""
        try:
            while self._connected:
                await asyncio.sleep(self.TOKEN_RENEWAL_INTERVAL)
                if not self._connected:
                    break
                try:
                    await self._send_token(0x05)  # renewal magic
                    logger.debug("Token renewal sent")
                except Exception as exc:
                    logger.warning("Token renewal failed: %s", exc)
        except asyncio.CancelledError:
            pass

    async def _send_token(self, magic: int) -> None:
        """Send a token packet (renewal=0x05, ack=0x02, remove=0x01).

        Reference: wfview icomudphandler.cpp sendToken().

        Args:
            magic: Token request type (0x01=remove, 0x02=ack, 0x05=renewal).
        """
        pkt = bytearray(self.TOKEN_PACKET_SIZE)
        struct.pack_into("<I", pkt, 0x00, self.TOKEN_PACKET_SIZE)
        struct.pack_into("<H", pkt, 0x04, 0x00)  # type = data
        struct.pack_into("<I", pkt, 0x08, self._ctrl_transport.my_id)
        struct.pack_into("<I", pkt, 0x0C, self._ctrl_transport.remote_id)
        struct.pack_into(">I", pkt, 0x10, self.TOKEN_PACKET_SIZE - 0x10)
        pkt[0x14] = 0x01  # requestreply
        pkt[0x15] = magic  # requesttype
        struct.pack_into(">H", pkt, 0x16, self._auth_seq)
        self._auth_seq += 1
        struct.pack_into("<H", pkt, 0x1A, self._tok_request)
        struct.pack_into(">H", pkt, 0x24, 0x0798)  # resetcap
        struct.pack_into("<I", pkt, 0x1C, self._token)
        await self._ctrl_transport.send_tracked(bytes(pkt))

    # ------------------------------------------------------------------
    # Watchdog & Auto-reconnect
    # ------------------------------------------------------------------

    WATCHDOG_CHECK_INTERVAL = 0.5  # seconds (wfview: WATCHDOG_PERIOD = 500ms)

    def _start_watchdog(self) -> None:
        """Start connection watchdog task."""
        if self._watchdog_task is None or self._watchdog_task.done():
            self._watchdog_task = asyncio.create_task(self._watchdog_loop())

    def _stop_watchdog(self) -> None:
        """Stop watchdog task."""
        if self._watchdog_task is not None and not self._watchdog_task.done():
            self._watchdog_task.cancel()
            self._watchdog_task = None

    def _stop_reconnect(self) -> None:
        """Cancel any pending reconnect task."""
        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            self._reconnect_task = None

    async def _watchdog_loop(self) -> None:
        """Monitor connection health via transport packet queue activity.

        If no packets are received for ``watchdog_timeout`` seconds,
        triggers a reconnect attempt.

        Reference: wfview icomudpaudio.cpp watchdog() — 30s timeout.
        """
        import time as _time

        last_activity = _time.monotonic()
        try:
            while self._connected:
                await asyncio.sleep(self.WATCHDOG_CHECK_INTERVAL)
                if not self._connected:
                    break

                # Check if control transport has received anything recently
                # by looking at packet queue activity
                if self._ctrl_transport._packet_queue.qsize() > 0:
                    last_activity = _time.monotonic()
                elif (
                    self._civ_transport
                    and self._civ_transport._packet_queue.qsize() > 0
                ):
                    last_activity = _time.monotonic()
                elif self._ctrl_transport.ping_seq > 0:
                    # Ping responses reset activity implicitly via packet queue
                    pass

                idle = _time.monotonic() - last_activity
                if idle > self._watchdog_timeout:
                    logger.warning(
                        "Watchdog: no activity for %.1fs, triggering reconnect",
                        idle,
                    )
                    self._connected = False
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())
                    return
        except asyncio.CancelledError:
            pass

    async def _reconnect_loop(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        delay = self._reconnect_delay
        attempt = 0
        try:
            while not self._intentional_disconnect:
                attempt += 1
                logger.info("Reconnect attempt %d (delay=%.1fs)", attempt, delay)
                try:
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
                    logger.info("Reconnected successfully after %d attempts", attempt)
                    return
                except Exception as exc:
                    logger.warning("Reconnect attempt %d failed: %s", attempt, exc)
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self._reconnect_max_delay)
        except asyncio.CancelledError:
            logger.info("Reconnect cancelled")

    # ------------------------------------------------------------------
    # Internal connection helpers
    # ------------------------------------------------------------------

    async def _send_token_ack(self) -> None:
        """Send token acknowledgement (0x40-byte token packet).

        Layout per wfview packettypes.h (token_packet):
        0x10 payloadsize(4,BE)  0x14 requestreply(1)=0x01
        0x15 requesttype(1)=magic  0x16 innerseq(2,BE)
        0x1A tokrequest(2)  0x1C token(4)
        0x24 resetcap(2,BE)=0x0798
        """
        pkt = bytearray(TOKEN_ACK_SIZE)
        struct.pack_into("<I", pkt, 0x00, TOKEN_ACK_SIZE)
        struct.pack_into("<I", pkt, 0x08, self._ctrl_transport.my_id)
        struct.pack_into("<I", pkt, 0x0C, self._ctrl_transport.remote_id)
        struct.pack_into(">I", pkt, 0x10, TOKEN_ACK_SIZE - 0x10)  # payloadsize BE
        pkt[0x14] = 0x01  # requestreply
        pkt[0x15] = 0x02  # requesttype = token ack (magic=0x02)
        struct.pack_into(">H", pkt, 0x16, self._auth_seq)  # innerseq BE
        self._auth_seq += 1
        struct.pack_into("<H", pkt, 0x1A, self._tok_request)  # tokrequest
        struct.pack_into("<I", pkt, 0x1C, self._token)  # token
        struct.pack_into(">H", pkt, 0x24, 0x0798)  # resetcap
        await self._ctrl_transport.send_tracked(bytes(pkt))
        logger.debug("Token ack sent (token=0x%08X)", self._token)

    async def _receive_guid(self) -> bytes | None:
        """Receive the radio's conninfo and extract GUID/MAC area."""
        await asyncio.sleep(0.3)
        guid = None
        for _ in range(30):
            try:
                d = await self._ctrl_transport.receive_packet(timeout=0.1)
                if len(d) == CONNINFO_SIZE:
                    guid = d[0x20:0x30]
                    logger.debug("Got radio GUID: %s", guid.hex())
            except asyncio.TimeoutError:
                break
        return guid

    async def _send_conninfo(self, guid: bytes | None) -> None:
        """Send our conninfo to the radio."""
        conninfo = build_conninfo_packet(
            sender_id=self._ctrl_transport.my_id,
            receiver_id=self._ctrl_transport.remote_id,
            username=self._username,
            token=self._token,
            tok_request=self._tok_request,
            radio_name="IC-7610",
            mac_address=b"\x00" * 6,
            auth_seq=self._auth_seq,
            guid=guid,
            rx_codec=int(self._audio_codec),
            tx_codec=int(self._audio_codec),
            rx_sample_rate=self._audio_sample_rate,
            tx_sample_rate=self._audio_sample_rate,
        )
        self._auth_seq += 1
        await self._ctrl_transport.send_tracked(conninfo)
        logger.debug("Conninfo sent")

    async def _receive_civ_port(self) -> int:
        """Wait for status packet and extract CI-V port quickly.

        Audio port is optional at connect-time and can be resolved lazily on first
        audio use. This keeps non-audio CLI/API calls fast.
        """
        deadline = time.monotonic() + self._timeout
        civ_port = 0

        while time.monotonic() < deadline:
            try:
                remaining = max(0.1, deadline - time.monotonic())
                d = await self._ctrl_transport.receive_packet(
                    timeout=min(remaining, 0.3)
                )
                if len(d) != STATUS_SIZE:
                    continue

                got_civ = struct.unpack_from(">H", d, 0x42)[0]
                got_audio = struct.unpack_from(">H", d, 0x46)[0]
                logger.info(
                    "Status: civ_port=%d, audio_port=%d",
                    got_civ,
                    got_audio,
                )

                if got_audio > 0:
                    self._audio_port = got_audio
                if got_civ > 0:
                    civ_port = got_civ
                    return civ_port
            except asyncio.TimeoutError:
                continue

        return civ_port

    async def _send_open_close(self, *, open_stream: bool) -> None:
        """Send OpenClose packet on the CI-V port."""
        if self._civ_transport is None:
            return
        await self._send_open_close_on_transport(
            self._civ_transport,
            send_seq=self._civ_send_seq,
            open_stream=open_stream,
        )
        self._civ_send_seq += 1

    async def _send_audio_open_close(self, *, open_stream: bool) -> None:
        """Send OpenClose packet on the audio port (wfview behavior)."""
        if self._audio_transport is None:
            return
        await self._send_open_close_on_transport(
            self._audio_transport,
            send_seq=self._audio_send_seq,
            open_stream=open_stream,
        )
        self._audio_send_seq += 1

    async def _send_open_close_on_transport(
        self,
        transport: IcomTransport,
        *,
        send_seq: int,
        open_stream: bool,
    ) -> None:
        """Build/send OpenClose packet on a specific transport.

        Layout per wfview packettypes.h (0x16 bytes):
        0x00 len(4) 0x04 type(2) 0x06 seq(2)
        0x08 sentid(4) 0x0C rcvdid(4)
        0x10 data(2)=0x01C0  0x12 unused(1)
        0x13 sendseq(2,BE)   0x15 magic(1)
        """
        pkt = bytearray(OPENCLOSE_SIZE)
        struct.pack_into("<I", pkt, 0x00, OPENCLOSE_SIZE)
        struct.pack_into("<I", pkt, 0x08, transport.my_id)
        struct.pack_into("<I", pkt, 0x0C, transport.remote_id)
        struct.pack_into("<H", pkt, 0x10, 0x01C0)  # data
        struct.pack_into(">H", pkt, 0x13, send_seq)  # sendseq BE
        pkt[0x15] = 0x04 if open_stream else 0x00  # magic
        await transport.send_tracked(bytes(pkt))
        logger.debug("OpenClose(%s) sent", "open" if open_stream else "close")

    async def _wait_for_packet(
        self, transport: IcomTransport, *, size: int, label: str
    ) -> bytes:
        """Wait for a packet of a specific size, skipping others."""
        deadline = time.monotonic() + self._timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"{label} timed out")
            try:
                data = await transport.receive_packet(timeout=remaining)
            except asyncio.TimeoutError:
                raise TimeoutError(f"{label} timed out")
            if len(data) == size:
                return data
            logger.debug(
                "Skipping packet (len=%d) while waiting for %s", len(data), label
            )

    @staticmethod
    async def _flush_queue(transport: IcomTransport, max_pkts: int = 200) -> int:
        """Drain pending packets from a transport queue."""
        count = 0
        for _ in range(max_pkts):
            try:
                await transport.receive_packet(timeout=0.01)
                count += 1
            except asyncio.TimeoutError:
                break
        return count

    # ------------------------------------------------------------------
    # CI-V command infrastructure
    # ------------------------------------------------------------------

    def _check_connected(self) -> None:
        """Raise ConnectionError if not connected."""
        if not self._connected or self._civ_transport is None:
            raise ConnectionError("Not connected to radio")

    def _wrap_civ(self, civ_frame: bytes) -> bytes:
        """Wrap a CI-V frame in a UDP data packet for the CI-V port."""
        assert self._civ_transport is not None
        total_len = CIV_HEADER_SIZE + len(civ_frame)
        pkt = bytearray(total_len)
        struct.pack_into("<I", pkt, 0, total_len)
        struct.pack_into("<H", pkt, 4, 0x00)  # type = DATA
        struct.pack_into("<I", pkt, 8, self._civ_transport.my_id)
        struct.pack_into("<I", pkt, 0x0C, self._civ_transport.remote_id)
        pkt[0x10] = 0xC1  # reply marker for CI-V data
        struct.pack_into("<H", pkt, 0x11, len(civ_frame))
        struct.pack_into(">H", pkt, 0x13, self._civ_send_seq)
        self._civ_send_seq += 1
        pkt[CIV_HEADER_SIZE:] = civ_frame
        return bytes(pkt)

    async def _send_civ_raw(
        self,
        civ_frame: bytes,
        *,
        priority: Priority = Priority.NORMAL,
        key: str | None = None,
        dedupe: bool = False,
        wait_response: bool = True,
    ) -> CivFrame | None:
        """Enqueue a CI-V command and wait for its response."""
        assert self._civ_transport is not None
        self._ensure_civ_runtime()

        if self._commander is None:
            # Fallback path (e.g. during tests/mocks before queue init).
            return await self._execute_civ_raw(civ_frame, wait_response=wait_response)

        return await self._commander.send(
            civ_frame,
            priority=priority,
            key=key,
            dedupe=dedupe,
            wait_response=wait_response,
        )

    @staticmethod
    def _civ_expects_response(frame: CivFrame) -> bool:
        """Determine if a CI-V frame expects a data RESPONSE or just an ACK/NAK."""
        if frame.command in (0x03, 0x04):
            return True
        if frame.command == 0x17:
            return False
        if frame.command == 0x27:
            return False
        # If no further payload beyond command/sub is included, it's typically a GET
        return len(frame.data) == 0

    async def _drain_ack_sinks_before_blocking(self) -> None:
        """Give fire-and-forget ACK sinks a short chance to drain, then clear stale ones.

        This prevents a missing ACK from poisoning the ACK waiter queue for the
        next blocking command.
        """
        if self._civ_request_tracker.ack_sink_count == 0:
            return

        deadline = time.monotonic() + self._civ_ack_sink_grace
        while self._civ_request_tracker.ack_sink_count > 0 and time.monotonic() < deadline:
            await asyncio.sleep(0.005)

        dropped = self._civ_request_tracker.drop_ack_sinks()
        if dropped:
            logger.debug("Dropped %d stale ACK sink waiter(s) before blocking command", dropped)

    async def _execute_civ_raw(self, civ_frame: bytes, wait_response: bool = True) -> CivFrame | None:
        """Execute one CI-V command via request tracker (serialized by worker)."""
        assert self._civ_transport is not None
        self._ensure_civ_runtime()

        parsed_frame = parse_civ_frame(civ_frame)
        request_key = request_key_from_frame(parsed_frame)
        expects_response = self._civ_expects_response(parsed_frame)

        attempts = 3
        for attempt in range(1, attempts + 1):
            if not wait_response:
                ack_sink_token: int | None = None

                # Fire-and-forget: sink the ACK so it doesn't shift the queue.
                if not expects_response:
                    token_or_future = self._civ_request_tracker.register_ack(wait=False)
                    if isinstance(token_or_future, int):
                        ack_sink_token = token_or_future

                # Ensure RX pump is running for event routing.
                self._start_civ_rx_pump()

                # Rate limit applies to fire-and-forget as well
                now = time.monotonic()
                delta = now - self._last_civ_send_monotonic
                if delta < self._civ_min_interval:
                    await asyncio.sleep(self._civ_min_interval - delta)

                pkt = self._wrap_civ(civ_frame)
                try:
                    await self._civ_transport.send_tracked(pkt)
                except Exception:
                    if ack_sink_token is not None:
                        self._civ_request_tracker.unregister_ack_sink(ack_sink_token)
                    raise

                self._last_civ_send_monotonic = time.monotonic()
                return None

            await self._drain_ack_sinks_before_blocking()

            # Register future BEFORE starting RX pump / sending.
            if expects_response:
                pending = self._civ_request_tracker.register_response(request_key)
            else:
                pending_or_token = self._civ_request_tracker.register_ack(wait=True)
                if isinstance(pending_or_token, int):
                    raise RuntimeError("ACK waiter registration returned sink token")
                pending = pending_or_token

            # Ensure RX pump is running for event routing.
            self._start_civ_rx_pump()

            # Rate-limit CI-V commands slightly (wfview-like pacing).
            now = time.monotonic()
            delta = now - self._last_civ_send_monotonic
            if delta < self._civ_min_interval:
                await asyncio.sleep(self._civ_min_interval - delta)

            pkt = self._wrap_civ(civ_frame)

            try:
                await self._civ_transport.send_tracked(pkt)
                self._last_civ_send_monotonic = time.monotonic()
                assert pending is not None
                return await asyncio.wait_for(pending, timeout=self._timeout)
            except asyncio.TimeoutError:
                self._civ_request_tracker.unregister(pending)
                if attempt < attempts:
                    logger.debug(
                        "CI-V command 0x%02X timed out (attempt %d/%d), retrying",
                        request_key.command,
                        attempt,
                        attempts,
                    )
                    continue
            except Exception:
                self._civ_request_tracker.unregister(pending)
                raise

            if attempt < attempts:
                logger.debug(
                    "CI-V command 0x%02X timed out (attempt %d/%d), retrying",
                    request_key.command,
                    attempt,
                    attempts,
                )
                continue

        raise TimeoutError("CI-V response timed out")

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
        """Get the current operating frequency in Hz."""
        self._check_connected()
        civ = get_frequency(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ, key="get_frequency", dedupe=True)
        freq = parse_frequency_response(resp)
        self._last_freq_hz = freq
        return freq

    async def set_frequency(self, freq_hz: int) -> None:
        """Set the operating frequency.

        Args:
            freq_hz: Frequency in Hz.
        """
        self._check_connected()
        civ = set_frequency(freq_hz, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected set_frequency({freq_hz})")
        self._last_freq_hz = freq_hz

    async def get_mode(self) -> Mode:
        """Get the current operating mode."""
        mode, _ = await self.get_mode_info()
        return mode

    async def get_mode_info(self) -> tuple[Mode, int | None]:
        """Get current mode and filter number (if reported by radio)."""
        self._check_connected()
        civ = get_mode(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        mode, filt = parse_mode_response(resp)
        self._last_mode = mode
        if filt is not None:
            self._filter_width = filt
        return mode, filt

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
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(
                f"Radio rejected set_mode({mode}, filter_width={filter_width})"
            )
        self._last_mode = mode
        if filter_width is not None:
            self._filter_width = filter_width

    async def get_power(self) -> int:
        """Get the RF power level (0-255)."""
        self._check_connected()
        civ = get_power(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ, key="get_power", dedupe=True)
        level = _level_bcd_decode(resp.data)
        self._last_power = level
        return level

    async def set_power(self, level: int) -> None:
        """Set the RF power level (0-255).

        Args:
            level: Power level 0-255.
        """
        self._check_connected()
        civ = set_power(level, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected set_power({level})")
        self._last_power = level

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

        Args:
            on: True for TX, False for RX.
        """
        self._check_connected()
        civ = (
            ptt_on(to_addr=self._radio_addr)
            if on
            else ptt_off(to_addr=self._radio_addr)
        )
        resp = await self._send_civ_raw(civ, priority=Priority.IMMEDIATE)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected PTT {'on' if on else 'off'}")

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

        Args:
            db: Attenuation in dB (0..45 in 3 dB steps).
            receiver: RECEIVER_MAIN (0) or RECEIVER_SUB (1).
        """
        self._check_connected()
        if db < 0 or db > 45 or db % 3 != 0:
            raise ValueError(f"Attenuator level must be 0..45 in 3 dB steps, got {db}")
        civ = set_attenuator_level(db, to_addr=self._radio_addr, receiver=receiver)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected attenuator level {db}")
        self._attenuator_state = db > 0

    async def set_attenuator(self, on: bool, receiver: int = RECEIVER_MAIN) -> None:
        """Enable or disable attenuator (compat wrapper, Command29-aware)."""
        self._check_connected()
        civ = set_attenuator(on, to_addr=self._radio_addr, receiver=receiver)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected attenuator {'on' if on else 'off'}")
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
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected preamp level {level}")
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
                await asyncio.wait_for(self._scope_activity_event.wait(), timeout=timeout)
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
