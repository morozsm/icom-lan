"""Async UDP transport for the Icom LAN protocol.

Handles connection lifecycle, keep-alive pings, sequence tracking,
and retransmit requests using asyncio.DatagramProtocol.
"""

import asyncio
import logging
import struct
import time
from enum import StrEnum

from .exceptions import TimeoutError as _TimeoutError
from .types import HEADER_SIZE, PacketType

__all__ = [
    "ConnectionState",
    "IcomTransport",
]

logger = logging.getLogger(__name__)

CONTROL_SIZE = 0x10
PING_SIZE = 0x15
PING_PERIOD = 0.5  # seconds
IDLE_PERIOD = 0.1
RETRANSMIT_PERIOD = 0.1
DISCOVERY_RETRIES = 10
DISCOVERY_TIMEOUT = 1.0  # seconds per attempt
BUFSIZE = 500
MAX_MISSING = 50


class ConnectionState(StrEnum):
    """Transport connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"


class _UdpProtocol(asyncio.DatagramProtocol):
    """Internal asyncio datagram protocol for IcomTransport."""

    def __init__(self, transport_owner: "IcomTransport") -> None:
        self._owner = transport_owner

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self._owner._udp_transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self._owner._handle_packet(data)

    def error_received(self, exc: Exception) -> None:
        logger.error("UDP error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        logger.info("UDP connection lost: %s", exc)


class IcomTransport:
    """Async UDP transport for Icom radio communication.

    Manages the UDP socket, keep-alive pings, sequence numbers,
    and retransmit tracking.

    Attributes:
        state: Current connection state.
        my_id: Local connection identifier.
        remote_id: Remote (radio) connection identifier.
        send_seq: Next outgoing tracked sequence number.
        ping_seq: Next outgoing ping sequence number.
    """

    def __init__(self) -> None:
        self.state: ConnectionState = ConnectionState.DISCONNECTED
        self.my_id: int = 0
        self.remote_id: int = 0
        self.send_seq: int = 0
        self.ping_seq: int = 0
        self.tx_buffer: dict[int, bytes] = {}
        self.rx_last_seq: int | None = None
        self.rx_missing: dict[int, int] = {}  # seq -> retry count
        self._udp_transport: asyncio.DatagramTransport | None = None
        self._ping_task: asyncio.Task | None = None
        self._retransmit_task: asyncio.Task | None = None
        self._packet_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._raw_send = self._default_raw_send
        self.rx_packet_count: int = 0  # total packets received (incl. pings)

    def _default_raw_send(self, data: bytes) -> None:
        """Send raw bytes via UDP transport."""
        if self._udp_transport is not None:
            self._udp_transport.sendto(data)

    async def connect(self, host: str, port: int) -> None:
        """Open UDP connection and perform discovery handshake.

        Sends "Are You There" until the radio replies with "I Am Here",
        then sends "Are You Ready" and waits for acknowledgement.

        Args:
            host: Radio IP address or hostname.
            port: Radio control port.

        Raises:
            TimeoutError: If the radio does not respond to discovery.
        """
        self.state = ConnectionState.CONNECTING
        loop = asyncio.get_event_loop()
        await loop.create_datagram_endpoint(
            lambda: _UdpProtocol(self),
            remote_addr=(host, port),
        )
        # Generate local ID from local address info
        if self._udp_transport is not None:
            info = self._udp_transport.get_extra_info("sockname")
            if info:
                lport = info[1] if isinstance(info, tuple) else 0
                self.my_id = (lport & 0xFFFF) | 0x10000
        logger.info("UDP open to %s:%d, my_id=0x%08X", host, port, self.my_id)

        # Phase 1: Are You There → I Am Here
        await self._discover()

        # Phase 2: Are You Ready
        await self._ready_handshake()

        logger.info("Discovery complete, remote_id=0x%08X", self.remote_id)

    async def _discover(self) -> None:
        """Send 'Are You There' and wait for 'I Am Here' to learn remote_id.

        Raises:
            TimeoutError: If radio does not respond after retries.
        """
        for attempt in range(DISCOVERY_RETRIES):
            pkt = self._build_control(ptype=PacketType.ARE_YOU_THERE, seq=0)
            self._raw_send(pkt)
            try:
                resp = await asyncio.wait_for(
                    self._packet_queue.get(), timeout=DISCOVERY_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.debug(
                    "Are You There attempt %d/%d — no response",
                    attempt + 1,
                    DISCOVERY_RETRIES,
                )
                continue

            if len(resp) >= CONTROL_SIZE:
                ptype = struct.unpack_from("<H", resp, 4)[0]
                if ptype == PacketType.I_AM_HERE:
                    self.remote_id = struct.unpack_from("<I", resp, 8)[0]
                    logger.info(
                        "I Am Here received, remote_id=0x%08X",
                        self.remote_id,
                    )
                    return

        raise _TimeoutError(
            f"Radio did not respond to discovery after {DISCOVERY_RETRIES} attempts"
        )

    async def _ready_handshake(self) -> None:
        """Send 'Are You Ready' and wait for acknowledgement.

        Raises:
            TimeoutError: If radio does not respond.
        """
        pkt = self._build_control(ptype=PacketType.ARE_YOU_READY, seq=0)
        self._raw_send(pkt)

        # Radio may send multiple packets; look for ARE_YOU_READY echo
        for _ in range(5):
            try:
                resp = await asyncio.wait_for(
                    self._packet_queue.get(), timeout=DISCOVERY_TIMEOUT
                )
            except asyncio.TimeoutError:
                break

            if len(resp) >= CONTROL_SIZE:
                ptype = struct.unpack_from("<H", resp, 4)[0]
                if ptype == PacketType.ARE_YOU_READY:
                    logger.info("I Am Ready received")
                    return

        # Some radios don't send an explicit reply; proceed anyway
        logger.warning("No explicit 'I Am Ready' reply, proceeding")

    async def disconnect(self) -> None:
        """Close the UDP connection and stop background tasks."""
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        if self._retransmit_task and not self._retransmit_task.done():
            self._retransmit_task.cancel()

        if self.state != ConnectionState.DISCONNECTED and self.remote_id:
            pkt = self._build_control(ptype=PacketType.DISCONNECT, seq=0)
            self._raw_send(pkt)

        if self._udp_transport is not None:
            self._udp_transport.close()
            self._udp_transport = None

        self.state = ConnectionState.DISCONNECTED
        logger.info("Disconnected")

    def start_ping_loop(self) -> None:
        """Start the periodic ping task."""
        if self._ping_task is None or self._ping_task.done():
            self._ping_task = asyncio.create_task(self._ping_loop())

    def start_retransmit_loop(self) -> None:
        """Start the periodic retransmit request task."""
        if self._retransmit_task is None or self._retransmit_task.done():
            self._retransmit_task = asyncio.create_task(self._retransmit_loop())

    async def send_tracked(self, data: bytes) -> None:
        """Send a packet with sequence tracking.

        The sequence number is written into the packet header at offset 6-7,
        and the packet is buffered for potential retransmission.

        Args:
            data: Packet bytes (header already filled except seq).
        """
        seq = self._next_send_seq()
        pkt = bytearray(data)
        struct.pack_into("<H", pkt, 6, seq)
        pkt = bytes(pkt)
        self._track_sent(seq, pkt)
        self._raw_send(pkt)

    async def receive_packet(self, timeout: float = 5.0) -> bytes:
        """Wait for the next incoming packet.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            Raw packet bytes.

        Raises:
            asyncio.TimeoutError: If no packet arrives within timeout.
        """
        return await asyncio.wait_for(self._packet_queue.get(), timeout=timeout)

    # --- Internal helpers ---

    def _next_send_seq(self) -> int:
        """Get and increment the send sequence number (wraps at 0x10000)."""
        seq = self.send_seq
        self.send_seq = (self.send_seq + 1) & 0xFFFF
        return seq

    def _build_control(self, *, ptype: int, seq: int) -> bytes:
        """Build a 0x10-byte control packet."""
        pkt = bytearray(CONTROL_SIZE)
        struct.pack_into("<I", pkt, 0, CONTROL_SIZE)
        struct.pack_into("<H", pkt, 4, ptype)
        struct.pack_into("<H", pkt, 6, seq)
        struct.pack_into("<I", pkt, 8, self.my_id)
        struct.pack_into("<I", pkt, 0x0C, self.remote_id)
        return bytes(pkt)

    def _build_ping(self) -> bytes:
        """Build a 0x15-byte ping request packet."""
        pkt = bytearray(PING_SIZE)
        struct.pack_into("<I", pkt, 0, PING_SIZE)
        struct.pack_into("<H", pkt, 4, PacketType.PING)
        struct.pack_into("<H", pkt, 6, self.ping_seq)
        struct.pack_into("<I", pkt, 8, self.my_id)
        struct.pack_into("<I", pkt, 0x0C, self.remote_id)
        pkt[0x10] = 0x00  # reply = request
        ms = int(time.monotonic() * 1000) & 0xFFFFFFFF
        struct.pack_into("<I", pkt, 0x11, ms)
        return bytes(pkt)

    def _send_ping(self) -> None:
        """Send a single ping packet and increment ping_seq."""
        pkt = self._build_ping()
        self._raw_send(pkt)
        self.ping_seq = (self.ping_seq + 1) & 0xFFFF

    def _track_sent(self, seq: int, data: bytes) -> None:
        """Store a sent packet for potential retransmission."""
        if len(self.tx_buffer) >= BUFSIZE:
            oldest = min(self.tx_buffer)
            del self.tx_buffer[oldest]
        self.tx_buffer[seq] = data

    def _record_rx_seq(self, seq: int) -> None:
        """Record a received sequence number and detect gaps."""
        if seq in self.rx_missing:
            del self.rx_missing[seq]

        if self.rx_last_seq is None:
            self.rx_last_seq = seq
            return

        if seq > self.rx_last_seq + 1:
            # Gap detected
            if seq - self.rx_last_seq > MAX_MISSING:
                logger.warning(
                    "Large seq gap: %d -> %d, resetting", self.rx_last_seq, seq
                )
                self.rx_missing.clear()
                self.rx_last_seq = seq
                return
            for missing in range(self.rx_last_seq + 1, seq):
                if missing not in self.rx_missing:
                    self.rx_missing[missing] = 0

        if seq > self.rx_last_seq:
            self.rx_last_seq = seq

    def _build_retransmit_requests(self) -> list[bytes]:
        """Build retransmit request packets for missing sequences."""
        if not self.rx_missing:
            return []

        seqs = list(self.rx_missing.keys())

        if len(seqs) == 1:
            # Single: use control packet with seq field
            return [self._build_control(ptype=0x01, seq=seqs[0])]

        # Multiple: control header + pairs of (seq, seq) for each missing
        pkt = bytearray(CONTROL_SIZE + 4 * len(seqs))
        struct.pack_into("<I", pkt, 0, len(pkt))
        struct.pack_into("<H", pkt, 4, 0x01)  # type = CONTROL
        struct.pack_into("<H", pkt, 6, 0x00)
        struct.pack_into("<I", pkt, 8, self.my_id)
        struct.pack_into("<I", pkt, 0x0C, self.remote_id)
        offset = CONTROL_SIZE
        for s in seqs:
            struct.pack_into("<H", pkt, offset, s)
            struct.pack_into("<H", pkt, offset + 2, s)
            offset += 4
        return [bytes(pkt)]

    def _handle_packet(self, data: bytes) -> None:
        """Process an incoming UDP packet."""
        if len(data) < HEADER_SIZE:
            return
        self.rx_packet_count += 1

        length = struct.unpack_from("<I", data, 0)[0]
        ptype = struct.unpack_from("<H", data, 4)[0]
        seq = struct.unpack_from("<H", data, 6)[0]
        sender_id = struct.unpack_from("<I", data, 8)[0]

        if length == CONTROL_SIZE and ptype == 0x01 and len(data) == CONTROL_SIZE:
            # Single retransmit request from radio
            if seq in self.tx_buffer:
                logger.debug("Retransmitting seq 0x%04X", seq)
                self._raw_send(self.tx_buffer[seq])
            return

        if length != CONTROL_SIZE and ptype == 0x01:
            # Multi retransmit request
            for i in range(CONTROL_SIZE, len(data), 2):
                if i + 2 <= len(data):
                    rseq = struct.unpack_from("<H", data, i)[0]
                    if rseq in self.tx_buffer:
                        self._raw_send(self.tx_buffer[rseq])
            return

        if len(data) == PING_SIZE and ptype == PacketType.PING:
            reply_flag = data[0x10]
            if reply_flag == 0x00:
                # Ping request from radio — send reply
                reply = bytearray(PING_SIZE)
                struct.pack_into("<I", reply, 0, PING_SIZE)
                struct.pack_into("<H", reply, 4, PacketType.PING)
                struct.pack_into("<H", reply, 6, seq)
                struct.pack_into("<I", reply, 8, self.my_id)
                struct.pack_into("<I", reply, 0x0C, self.remote_id)
                reply[0x10] = 0x01  # reply flag
                reply[0x11:0x15] = data[0x11:0x15]  # echo time
                self._raw_send(bytes(reply))
            elif reply_flag == 0x01:
                # Response to our ping
                if seq == self.ping_seq - 1 or seq == self.ping_seq:
                    pass  # Latency measurement could go here
            return

        # Track sequence for data packets
        if ptype == 0x00 and seq != 0:
            self._record_rx_seq(seq)

        # Update remote_id if needed
        if self.remote_id == 0 and sender_id != 0:
            self.remote_id = sender_id

        # Queue for consumer
        self._packet_queue.put_nowait(data)

    async def _ping_loop(self) -> None:
        """Background task: send pings every PING_PERIOD."""
        try:
            while self.state != ConnectionState.DISCONNECTED:
                self._send_ping()
                await asyncio.sleep(PING_PERIOD)
        except asyncio.CancelledError:
            pass

    async def _retransmit_loop(self) -> None:
        """Background task: send retransmit requests periodically."""
        try:
            while self.state != ConnectionState.DISCONNECTED:
                await asyncio.sleep(RETRANSMIT_PERIOD)
                pkts = self._build_retransmit_requests()
                for pkt in pkts:
                    self._raw_send(pkt)
                # Increment retry counters, drop after 4 tries
                to_delete = []
                for s, count in self.rx_missing.items():
                    if count >= 4:
                        to_delete.append(s)
                    else:
                        self.rx_missing[s] = count + 1
                for s in to_delete:
                    del self.rx_missing[s]
        except asyncio.CancelledError:
            pass
