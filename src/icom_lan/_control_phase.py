"""Auth/login FSM, token renewal, watchdog, and reconnect for IcomRadio."""

from __future__ import annotations

import asyncio
import logging
import socket as _socket
import struct
import time

from .auth import (
    build_conninfo_packet,
    build_login_packet,
    parse_auth_response,
)
from ._connection_state import RadioConnectionState
from .exceptions import AuthenticationError, ConnectionError, TimeoutError
from .transport import ConnectionState, IcomTransport

logger = logging.getLogger(__name__)

# Packet size constants (per wfview packettypes.h).
OPENCLOSE_SIZE = 0x16
TOKEN_ACK_SIZE = 0x40
CONNINFO_SIZE = 0x90
STATUS_SIZE = 0x50


class _ControlPhaseMixin:
    """Mixin providing auth/login FSM, token renewal, and watchdog for IcomRadio."""

    # Class-level timing constants (mirrors wfview defaults).
    TOKEN_RENEWAL_INTERVAL = 60.0  # seconds (wfview: TOKEN_RENEWAL = 60000ms)
    TOKEN_PACKET_SIZE = 0x40
    WATCHDOG_CHECK_INTERVAL = 0.5  # seconds (wfview: WATCHDOG_PERIOD = 500ms)
    _WATCHDOG_HEALTH_LOG_INTERVAL = 30.0  # seconds

    # ------------------------------------------------------------------
    # Public lifecycle
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
        self._conn_state = RadioConnectionState.CONNECTING  # type: ignore[attr-defined]

        # --- Phase 1: Control port ---
        # On reconnect, skip discovery — reuse cached remote_id.
        _reconnect = getattr(self, "_has_connected_once", False)
        try:
            if _reconnect:
                await self._ctrl_transport.reconnect(self._host, self._port)  # type: ignore[attr-defined]
            else:
                await self._ctrl_transport.connect(self._host, self._port)  # type: ignore[attr-defined]
        except OSError as exc:
            raise ConnectionError(
                f"Failed to connect to {self._host}:{self._port}: {exc}"  # type: ignore[attr-defined]
            ) from exc

        self._ctrl_transport.start_ping_loop()  # type: ignore[attr-defined]
        self._ctrl_transport.start_retransmit_loop()  # type: ignore[attr-defined]

        # Login
        login_pkt = build_login_packet(
            self._username,  # type: ignore[attr-defined]
            self._password,  # type: ignore[attr-defined]
            sender_id=self._ctrl_transport.my_id,  # type: ignore[attr-defined]
            receiver_id=self._ctrl_transport.remote_id,  # type: ignore[attr-defined]
        )
        await self._ctrl_transport.send_tracked(login_pkt)  # type: ignore[attr-defined]
        resp_data = await self._wait_for_packet(
            self._ctrl_transport,  # type: ignore[attr-defined]
            size=0x60,
            label="login response",
        )
        auth = parse_auth_response(resp_data)
        if not auth.success:
            raise AuthenticationError(
                f"Authentication failed (error=0x{auth.error:08X})"
            )
        self._token = auth.token  # type: ignore[attr-defined]
        self._tok_request = auth.tok_request  # type: ignore[attr-defined]
        logger.info(
            "Authenticated with %s:%d, token=0x%08X",
            self._host,  # type: ignore[attr-defined]
            self._port,  # type: ignore[attr-defined]
            self._token,  # type: ignore[attr-defined]
        )

        # Token ack
        await self._send_token_ack()

        # Get GUID from radio's conninfo
        guid = await self._receive_guid()

        # Reserve local UDP ports for CI-V and audio (wfview-style).
        _civ_sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        _civ_sock.bind(("", 0))
        _civ_local_port = _civ_sock.getsockname()[1]
        _civ_sock.close()
        _audio_sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        _audio_sock.bind(("", 0))
        _audio_local_port = _audio_sock.getsockname()[1]
        _audio_sock.close()
        logger.debug(
            "Reserved local ports: civ=%d, audio=%d",
            _civ_local_port,
            _audio_local_port,
        )

        # Use default ports (control+1, control+2) optimistically — this is
        # correct for all known Icom radios.  Send conninfo and try to read
        # the status packet in the background; if the radio reports different
        # ports we'll log a warning (future: reconnect).
        self._civ_port = self._port + 1  # type: ignore[attr-defined]
        self._audio_port = self._port + 2  # type: ignore[attr-defined]

        self._civ_local_port = _civ_local_port  # type: ignore[attr-defined]
        self._audio_local_port = _audio_local_port  # type: ignore[attr-defined]
        await self._send_conninfo(guid, _civ_local_port, _audio_local_port)

        # Non-blocking: try to read status once (short timeout).
        # If radio responds with real ports, verify they match defaults.
        try:
            civ_port = await self._receive_civ_port()
            if civ_port > 0 and civ_port != self._civ_port:
                logger.warning(
                    "Radio reported non-default civ_port=%d (expected %d), using radio value",
                    civ_port, self._civ_port,
                )
                self._civ_port = civ_port
            elif civ_port == 0:
                logger.debug("Status returned civ_port=0, using default %d", self._civ_port)
        except asyncio.TimeoutError:
            logger.debug("No status packet received, using default ports")
            logger.warning(
                "Audio port not in status, using default %d", self._audio_port  # type: ignore[attr-defined]
            )

        # --- Phase 2: CI-V port ---
        self._civ_transport = IcomTransport()  # type: ignore[attr-defined]
        try:
            await self._civ_transport.connect(  # type: ignore[attr-defined]
                self._host, self._civ_port,
                local_port=self._civ_local_port,  # type: ignore[attr-defined]
            )
        except OSError as exc:
            await self._ctrl_transport.disconnect()  # type: ignore[attr-defined]
            raise ConnectionError(
                f"Failed to connect CI-V port {self._civ_port}: {exc}"  # type: ignore[attr-defined]
            ) from exc

        self._civ_transport.start_ping_loop()  # type: ignore[attr-defined]
        self._civ_transport.start_retransmit_loop()  # type: ignore[attr-defined]
        # ⚠️ DO NOT REMOVE idle_loop! The IC-7610 kills CI-V sessions after ~40s
        # without tracked control packets. CI-V payload commands do NOT substitute
        # for transport-level keepalive. This was learned the hard way (2026-03-02).
        self._civ_transport.start_idle_loop()  # type: ignore[attr-defined]
        # NOTE: no idle_loop on CI-V — fire-and-forget CI-V commands already
        # keep the session alive; idle tracked packets flood tx_buffer.

        # Open CI-V data stream
        await self._send_open_close(open_stream=True)

        # Flush initial waterfall/status data
        await asyncio.sleep(0.3)
        await self._flush_queue(self._civ_transport)  # type: ignore[attr-defined]

        self._advance_civ_generation("connect")  # type: ignore[attr-defined]
        self._civ_last_waiter_gc_monotonic = time.monotonic()  # type: ignore[attr-defined]
        self._start_civ_rx_pump()  # type: ignore[attr-defined]
        self._start_civ_data_watchdog()  # type: ignore[attr-defined]
        self._conn_state = RadioConnectionState.CONNECTED  # type: ignore[attr-defined]
        self._ctrl_transport.state = ConnectionState.CONNECTED  # type: ignore[attr-defined]
        self._start_civ_worker()  # type: ignore[attr-defined]
        self._start_token_renewal()
        if self._auto_reconnect:  # type: ignore[attr-defined]
            self._start_watchdog()
        self._has_connected_once = True  # type: ignore[attr-defined]
        logger.info(
            "Connected to %s (control=%d, civ=%d)",
            self._host,  # type: ignore[attr-defined]
            self._port,  # type: ignore[attr-defined]
            self._civ_port,  # type: ignore[attr-defined]
        )

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
        struct.pack_into("<I", pkt, 0x08, self._ctrl_transport.my_id)  # type: ignore[attr-defined]
        struct.pack_into("<I", pkt, 0x0C, self._ctrl_transport.remote_id)  # type: ignore[attr-defined]
        struct.pack_into(">I", pkt, 0x10, TOKEN_ACK_SIZE - 0x10)  # payloadsize BE
        pkt[0x14] = 0x01  # requestreply
        pkt[0x15] = 0x02  # requesttype = token ack (magic=0x02)
        struct.pack_into(">H", pkt, 0x16, self._auth_seq)  # innerseq BE  # type: ignore[attr-defined]
        self._auth_seq += 1  # type: ignore[attr-defined]
        struct.pack_into("<H", pkt, 0x1A, self._tok_request)  # tokrequest  # type: ignore[attr-defined]
        struct.pack_into("<I", pkt, 0x1C, self._token)  # token  # type: ignore[attr-defined]
        struct.pack_into(">H", pkt, 0x24, 0x0798)  # resetcap
        await self._ctrl_transport.send_tracked(bytes(pkt))  # type: ignore[attr-defined]
        logger.debug("Token ack sent (token=0x%08X)", self._token)  # type: ignore[attr-defined]

    async def _receive_guid(self) -> "bytes | None":
        """Receive the radio's conninfo and extract GUID/MAC area."""
        await asyncio.sleep(0.3)
        guid = None
        for _ in range(30):
            try:
                d = await self._ctrl_transport.receive_packet(timeout=0.1)  # type: ignore[attr-defined]
                if len(d) == CONNINFO_SIZE:
                    guid = d[0x20:0x30]
                    logger.debug("Got radio GUID: %s", guid.hex())
            except asyncio.TimeoutError:
                break
        return guid

    async def _send_conninfo(
        self,
        guid: "bytes | None",
        civ_local_port: int = 0,
        audio_local_port: int = 0,
    ) -> None:
        """Send our conninfo to the radio."""
        conninfo = build_conninfo_packet(
            sender_id=self._ctrl_transport.my_id,  # type: ignore[attr-defined]
            receiver_id=self._ctrl_transport.remote_id,  # type: ignore[attr-defined]
            username=self._username,  # type: ignore[attr-defined]
            token=self._token,  # type: ignore[attr-defined]
            tok_request=self._tok_request,  # type: ignore[attr-defined]
            radio_name="IC-7610",
            mac_address=b"\x00" * 6,
            auth_seq=self._auth_seq,  # type: ignore[attr-defined]
            guid=guid,
            rx_codec=int(self._audio_codec),  # type: ignore[attr-defined]
            tx_codec=int(self._audio_codec),  # type: ignore[attr-defined]
            rx_sample_rate=self._audio_sample_rate,  # type: ignore[attr-defined]
            tx_sample_rate=self._audio_sample_rate,  # type: ignore[attr-defined]
            civ_local_port=civ_local_port,
            audio_local_port=audio_local_port,
        )
        self._auth_seq += 1  # type: ignore[attr-defined]
        await self._ctrl_transport.send_tracked(conninfo)  # type: ignore[attr-defined]
        logger.debug(
            "Conninfo sent (civ_local=%d, audio_local=%d)",
            civ_local_port,
            audio_local_port,
        )

    async def _receive_civ_port(self) -> int:
        """Wait for status packet and extract CI-V port quickly.

        Audio port is optional at connect-time and can be resolved lazily on first
        audio use. This keeps non-audio CLI/API calls fast.
        """
        deadline = time.monotonic() + 2.0  # Short timeout — default ports used anyway
        civ_port = 0
        status_packets_seen = 0

        while time.monotonic() < deadline:
            try:
                remaining = max(0.1, deadline - time.monotonic())
                d = await self._ctrl_transport.receive_packet(  # type: ignore[attr-defined]
                    timeout=min(remaining, 0.3)
                )
                if len(d) != STATUS_SIZE:
                    continue

                got_civ = struct.unpack_from(">H", d, 0x42)[0]
                got_audio = struct.unpack_from(">H", d, 0x46)[0]
                status_packets_seen += 1
                logger.info(
                    "Status: civ_port=%d, audio_port=%d",
                    got_civ,
                    got_audio,
                )

                if got_audio > 0:
                    self._audio_port = got_audio  # type: ignore[attr-defined]
                if got_civ > 0:
                    civ_port = got_civ
                    return civ_port
                if status_packets_seen >= 2:
                    logger.warning(
                        "Status packet has civ_port=0, falling back to default"
                    )
                    break
            except asyncio.TimeoutError:
                continue

        return civ_port

    async def _send_open_close(self, *, open_stream: bool) -> None:
        """Send OpenClose packet on the CI-V port."""
        if self._civ_transport is None:  # type: ignore[attr-defined]
            return
        await self._send_open_close_on_transport(
            self._civ_transport,  # type: ignore[attr-defined]
            send_seq=self._civ_send_seq,  # type: ignore[attr-defined]
            open_stream=open_stream,
        )
        self._civ_send_seq = (self._civ_send_seq + 1) & 0xFFFF  # type: ignore[attr-defined]

    async def _send_audio_open_close(self, *, open_stream: bool) -> None:
        """Send OpenClose packet on the audio port (wfview behavior)."""
        if self._audio_transport is None:  # type: ignore[attr-defined]
            return
        await self._send_open_close_on_transport(
            self._audio_transport,  # type: ignore[attr-defined]
            send_seq=self._audio_send_seq,  # type: ignore[attr-defined]
            open_stream=open_stream,
        )
        self._audio_send_seq = (self._audio_send_seq + 1) & 0xFFFF  # type: ignore[attr-defined]

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
        deadline = time.monotonic() + 2.0  # Short timeout — default ports used anyway
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
    # Token renewal
    # ------------------------------------------------------------------

    def _start_token_renewal(self) -> None:
        """Start periodic token renewal task."""
        if (
            self._token_task is None  # type: ignore[attr-defined]
            or self._token_task.done()  # type: ignore[attr-defined]
        ):
            self._token_task = asyncio.create_task(self._token_renewal_loop())  # type: ignore[attr-defined]

    def _stop_token_renewal(self) -> None:
        """Cancel token renewal task."""
        if (
            self._token_task is not None  # type: ignore[attr-defined]
            and not self._token_task.done()  # type: ignore[attr-defined]
        ):
            self._token_task.cancel()  # type: ignore[attr-defined]
            self._token_task = None  # type: ignore[attr-defined]

    async def _token_renewal_loop(self) -> None:
        """Background task: send token renewal every TOKEN_RENEWAL_INTERVAL."""
        try:
            while self._conn_state == RadioConnectionState.CONNECTED:  # type: ignore[attr-defined]
                await asyncio.sleep(self.TOKEN_RENEWAL_INTERVAL)
                if self._conn_state != RadioConnectionState.CONNECTED:  # type: ignore[attr-defined]
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
        struct.pack_into("<I", pkt, 0x08, self._ctrl_transport.my_id)  # type: ignore[attr-defined]
        struct.pack_into("<I", pkt, 0x0C, self._ctrl_transport.remote_id)  # type: ignore[attr-defined]
        struct.pack_into(">I", pkt, 0x10, self.TOKEN_PACKET_SIZE - 0x10)
        pkt[0x14] = 0x01  # requestreply
        pkt[0x15] = magic  # requesttype
        struct.pack_into(">H", pkt, 0x16, self._auth_seq)  # type: ignore[attr-defined]
        self._auth_seq += 1  # type: ignore[attr-defined]
        struct.pack_into("<H", pkt, 0x1A, self._tok_request)  # type: ignore[attr-defined]
        struct.pack_into(">H", pkt, 0x24, 0x0798)  # resetcap
        struct.pack_into("<I", pkt, 0x1C, self._token)  # type: ignore[attr-defined]
        await self._ctrl_transport.send_tracked(bytes(pkt))  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Watchdog & Auto-reconnect
    # ------------------------------------------------------------------

    def _start_watchdog(self) -> None:
        """Start connection watchdog task."""
        if (
            self._watchdog_task is None  # type: ignore[attr-defined]
            or self._watchdog_task.done()  # type: ignore[attr-defined]
        ):
            self._watchdog_task = asyncio.create_task(self._watchdog_loop())  # type: ignore[attr-defined]

    def _stop_watchdog(self) -> None:
        """Stop watchdog task."""
        if (
            self._watchdog_task is not None  # type: ignore[attr-defined]
            and not self._watchdog_task.done()  # type: ignore[attr-defined]
        ):
            self._watchdog_task.cancel()  # type: ignore[attr-defined]
            self._watchdog_task = None  # type: ignore[attr-defined]

    def _stop_reconnect(self) -> None:
        """Cancel any pending reconnect task."""
        if (
            self._reconnect_task is not None  # type: ignore[attr-defined]
            and not self._reconnect_task.done()  # type: ignore[attr-defined]
        ):
            self._reconnect_task.cancel()  # type: ignore[attr-defined]
            self._reconnect_task = None  # type: ignore[attr-defined]

