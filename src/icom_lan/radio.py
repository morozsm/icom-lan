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
import struct
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Callable

from .auth import (
    build_conninfo_packet,
    build_login_packet,
    parse_auth_response,
)
from .commands import (
    CONTROLLER_ADDR,
    IC_7610_ADDR,
    _level_bcd_decode,
    build_civ_frame,
    get_alc,
    get_frequency,
    get_mode,
    get_power,
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
    select_vfo as _select_vfo_cmd,
    send_cw,
    set_attenuator,
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
from .audio import AudioPacket, AudioStream
from .transport import ConnectionState, IcomTransport
from .types import AudioCodec, CivFrame, Mode

__all__ = ["IcomRadio", "AudioCodec"]

logger = logging.getLogger(__name__)

CIV_HEADER_SIZE = 0x15
OPENCLOSE_SIZE = 0x16  # per wfview packettypes.h
TOKEN_ACK_SIZE = 0x40
CONNINFO_SIZE = 0x90
STATUS_SIZE = 0x50


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
        audio_codec: AudioCodec | int = AudioCodec.PCM_1CH_16BIT,
        audio_sample_rate: int = 48000,
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
        self._connected = False
        self._token: int = 0
        self._tok_request: int = 0
        self._auth_seq: int = 0
        self._civ_port: int = 0
        self._audio_port: int = 0
        self._civ_send_seq: int = 0
        self._token_task: asyncio.Task | None = None
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay
        self._reconnect_max_delay = reconnect_max_delay
        self._watchdog_timeout = watchdog_timeout
        self._watchdog_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._intentional_disconnect = False

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

        self._connected = True
        self._intentional_disconnect = False
        self._ctrl_transport.state = ConnectionState.CONNECTED
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
            if self._audio_transport is not None:
                await self._audio_transport.disconnect()
                self._audio_transport = None
            if self._civ_transport:
                try:
                    await self._send_open_close(open_stream=False)
                except Exception:
                    pass
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

    async def start_audio_rx(
        self, callback: "Callable[[AudioPacket], None]"
    ) -> None:
        """Start receiving audio from the radio.

        Connects the audio transport if not already connected,
        then begins streaming RX audio to the callback.

        Args:
            callback: Called with each :class:`AudioPacket`.

        Raises:
            ConnectionError: If not connected or audio port unavailable.
        """
        self._check_connected()
        await self._ensure_audio_transport()
        assert self._audio_stream is not None
        await self._audio_stream.start_rx(callback)

    async def stop_audio_rx(self) -> None:
        """Stop receiving audio from the radio."""
        if self._audio_stream is not None:
            await self._audio_stream.stop_rx()

    async def start_audio_tx(self) -> None:
        """Start transmitting audio to the radio.

        Connects the audio transport if not already connected.

        Raises:
            ConnectionError: If not connected or audio port unavailable.
        """
        self._check_connected()
        await self._ensure_audio_transport()
        assert self._audio_stream is not None
        await self._audio_stream.start_tx()

    async def push_audio_tx(self, opus_data: bytes) -> None:
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

    async def stop_audio_tx(self) -> None:
        """Stop transmitting audio to the radio."""
        if self._audio_stream is not None:
            await self._audio_stream.stop_tx()

    async def start_audio(
        self,
        rx_callback: "Callable[[AudioPacket], None]",
        *,
        tx_enabled: bool = True,
    ) -> None:
        """Start full-duplex audio (RX + optional TX).

        Convenience method that starts both RX and TX audio streams
        on the same transport.

        Args:
            rx_callback: Called with each :class:`AudioPacket` (or None for gaps).
            tx_enabled: Whether to also enable TX (default True).

        Raises:
            ConnectionError: If not connected or audio port unavailable.
        """
        await self.start_audio_rx(rx_callback)
        if tx_enabled:
            assert self._audio_stream is not None
            await self._audio_stream.start_tx()

    async def stop_audio(self) -> None:
        """Stop all audio streams (RX and TX)."""
        await self.stop_audio_tx()
        await self.stop_audio_rx()

    @property
    def audio_codec(self) -> "AudioCodec":
        """Configured audio codec."""
        return self._audio_codec

    @property
    def audio_sample_rate(self) -> int:
        """Configured audio sample rate in Hz."""
        return self._audio_sample_rate

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
        self._audio_stream = AudioStream(self._audio_transport)
        logger.info("Audio transport connected on port %d", self._audio_port)

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
                elif self._civ_transport and self._civ_transport._packet_queue.qsize() > 0:
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
                logger.info(
                    "Reconnect attempt %d (delay=%.1fs)", attempt, delay
                )
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
        """Wait for the status packet with CI-V and audio ports."""
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            try:
                remaining = max(0.1, deadline - time.monotonic())
                d = await self._ctrl_transport.receive_packet(
                    timeout=min(remaining, 0.3)
                )
                if len(d) == STATUS_SIZE:
                    civ_port = struct.unpack_from(">H", d, 0x42)[0]
                    audio_port = struct.unpack_from(">H", d, 0x46)[0]
                    if civ_port > 0:
                        logger.info(
                            "Status: civ_port=%d, audio_port=%d",
                            civ_port,
                            audio_port,
                        )
                        self._audio_port = audio_port
                        return civ_port
            except asyncio.TimeoutError:
                continue
        return 0

    async def _send_open_close(self, *, open_stream: bool) -> None:
        """Send OpenClose packet on the CI-V port.

        Layout per wfview packettypes.h (0x16 bytes):
        0x00 len(4) 0x04 type(2) 0x06 seq(2)
        0x08 sentid(4) 0x0C rcvdid(4)
        0x10 data(2)=0x01C0  0x12 unused(1)
        0x13 sendseq(2,BE)   0x15 magic(1)
        """
        if self._civ_transport is None:
            return
        pkt = bytearray(OPENCLOSE_SIZE)
        struct.pack_into("<I", pkt, 0x00, OPENCLOSE_SIZE)
        struct.pack_into("<I", pkt, 0x08, self._civ_transport.my_id)
        struct.pack_into("<I", pkt, 0x0C, self._civ_transport.remote_id)
        struct.pack_into("<H", pkt, 0x10, 0x01C0)  # data
        # 0x12 = unused (stays 0x00)
        struct.pack_into(">H", pkt, 0x13, self._civ_send_seq)  # sendseq BE
        pkt[0x15] = 0x04 if open_stream else 0x00  # magic
        self._civ_send_seq += 1
        await self._civ_transport.send_tracked(bytes(pkt))
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

    async def _send_civ_raw(self, civ_frame: bytes) -> CivFrame:
        """Send a CI-V frame and wait for the response.

        Filters through incoming packets (waterfall, echoes, idle) to find
        the actual CI-V response from the radio.

        Args:
            civ_frame: Raw CI-V frame bytes.

        Returns:
            Parsed response CivFrame.

        Raises:
            TimeoutError: If no response within timeout.
        """
        assert self._civ_transport is not None
        pkt = self._wrap_civ(civ_frame)
        await self._civ_transport.send_tracked(pkt)

        # Extract our command byte for matching the response
        # Frame: FE FE <to> <from> <cmd> [sub] [data] FD
        our_cmd = civ_frame[4] if len(civ_frame) > 4 else 0xFF

        deadline = time.monotonic() + self._timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("CI-V response timed out")
            try:
                resp = await self._civ_transport.receive_packet(
                    timeout=remaining
                )
            except asyncio.TimeoutError:
                raise TimeoutError("CI-V response timed out")

            if len(resp) <= CIV_HEADER_SIZE:
                continue  # idle/control packet

            payload = resp[CIV_HEADER_SIZE:]

            # Scan payload for CI-V frames (there may be waterfall data too)
            idx = 0
            while idx < len(payload) - 4:
                if payload[idx] == 0xFE and payload[idx + 1] == 0xFE:
                    fd_pos = payload.find(b"\xfd", idx + 4)
                    if fd_pos < 0:
                        break
                    frame_bytes = payload[idx : fd_pos + 1]
                    to_addr = frame_bytes[2]
                    from_addr = frame_bytes[3]
                    cmd = frame_bytes[4]

                    # Skip echoes (our command reflected back) and waterfall
                    if (
                        from_addr == self._radio_addr
                        and to_addr == CONTROLLER_ADDR
                        and cmd != 0x27  # not waterfall
                        and (cmd == our_cmd or cmd in (0xFB, 0xFA))
                    ):
                        return parse_civ_frame(frame_bytes)

                    idx = fd_pos + 1
                else:
                    idx += 1

    # ------------------------------------------------------------------
    # Public CI-V API
    # ------------------------------------------------------------------

    async def send_civ(
        self, command: int, sub: int | None = None, data: bytes | None = None
    ) -> CivFrame:
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
        resp = await self._send_civ_raw(civ)
        return parse_frequency_response(resp)

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

    async def get_mode(self) -> Mode:
        """Get the current operating mode."""
        self._check_connected()
        civ = get_mode(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        mode, _ = parse_mode_response(resp)
        return mode

    async def set_mode(self, mode: Mode | str) -> None:
        """Set the operating mode.

        Args:
            mode: Mode enum or string name (e.g. "USB", "LSB").
        """
        self._check_connected()
        if isinstance(mode, str):
            mode = Mode[mode]
        civ = set_mode(mode, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected set_mode({mode})")

    async def get_power(self) -> int:
        """Get the RF power level (0-255)."""
        self._check_connected()
        civ = get_power(to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        return _level_bcd_decode(resp.data)

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
        resp = await self._send_civ_raw(civ)
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

    async def set_attenuator(self, on: bool) -> None:
        """Enable or disable attenuator."""
        self._check_connected()
        civ = set_attenuator(on, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected attenuator {'on' if on else 'off'}")

    async def set_preamp(self, level: int = 1) -> None:
        """Set preamp level (0=off, 1=PREAMP1, 2=PREAMP2)."""
        self._check_connected()
        civ = set_preamp(level, to_addr=self._radio_addr)
        resp = await self._send_civ_raw(civ)
        ack = parse_ack_nak(resp)
        if ack is False:
            raise CommandError(f"Radio rejected preamp level {level}")

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
        await self._send_civ_raw(civ)
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
            raise CommandError(
                f"Radio rejected power {'on' if on else 'off'}"
            )
