"""Audio streaming for Icom transceivers over LAN (UDP).

Handles RX (receive from radio) and TX (transmit to radio) audio
via the audio UDP port. Audio data is Opus-encoded; codec handling
is pluggable via callbacks.
"""

import asyncio
import logging
import struct
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from .transport import IcomTransport
from .types import PacketType

__all__ = [
    "AudioStream",
    "AudioPacket",
    "AudioState",
    "AUDIO_HEADER_SIZE",
    "TX_IDENT",
    "RX_IDENT_0xA0",
]

logger = logging.getLogger(__name__)

# Audio packet header is 0x18 bytes (standard 0x10 header + 8 audio-specific)
AUDIO_HEADER_SIZE = 0x18

# TX audio ident value
TX_IDENT = 0x0080

# RX ident for 0xa0-length frames
RX_IDENT_0xA0 = 0x9781


@dataclass(frozen=True, slots=True)
class AudioPacket:
    """Parsed audio packet.

    Attributes:
        ident: Audio stream identifier (0x0080 for TX, varies for RX).
        send_seq: Audio-level sequence number.
        data: Opus-encoded audio data (raw bytes after header).
    """

    ident: int
    send_seq: int
    data: bytes


class AudioState(StrEnum):
    """Audio stream state."""

    IDLE = "idle"
    RECEIVING = "receiving"
    TRANSMITTING = "transmitting"


class AudioStream:
    """Manages audio RX/TX on the Icom audio UDP port.

    Uses an :class:`IcomTransport` for the underlying UDP communication
    (discovery, pings, retransmit). Audio-specific packet framing is
    handled here.

    Args:
        transport: Connected IcomTransport for the audio port.

    Example::

        stream = AudioStream(audio_transport)
        await stream.start_rx(my_callback)
        # ... later
        await stream.stop_rx()
    """

    def __init__(self, transport: IcomTransport) -> None:
        self._transport = transport
        self._state: AudioState = AudioState.IDLE
        self._rx_callback: Callable[[AudioPacket], None] | None = None
        self._rx_task: asyncio.Task[None] | None = None
        self._tx_seq: int = 0

    @property
    def state(self) -> AudioState:
        """Current audio stream state."""
        return self._state

    @property
    def transport(self) -> IcomTransport:
        """Underlying transport."""
        return self._transport

    # ------------------------------------------------------------------
    # RX
    # ------------------------------------------------------------------

    async def start_rx(
        self, callback: Callable[[AudioPacket], None]
    ) -> None:
        """Start receiving audio from the radio.

        Args:
            callback: Called with each decoded :class:`AudioPacket`.

        Raises:
            RuntimeError: If already receiving or transmitting.
        """
        if self._state != AudioState.IDLE:
            raise RuntimeError(f"Cannot start RX in state {self._state}")

        self._rx_callback = callback
        self._state = AudioState.RECEIVING
        self._rx_task = asyncio.create_task(self._rx_loop())
        logger.info("Audio RX started")

    async def stop_rx(self) -> None:
        """Stop receiving audio."""
        if self._state != AudioState.RECEIVING:
            return
        self._state = AudioState.IDLE
        if self._rx_task is not None:
            self._rx_task.cancel()
            try:
                await self._rx_task
            except asyncio.CancelledError:
                pass
            self._rx_task = None
        self._rx_callback = None
        logger.info("Audio RX stopped")

    async def _rx_loop(self) -> None:
        """Background loop that reads audio packets from transport."""
        while self._state == AudioState.RECEIVING:
            try:
                data = await self._transport.receive_packet(timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            if len(data) <= AUDIO_HEADER_SIZE:
                continue  # Control/ping packet, not audio

            pkt = parse_audio_packet(data)
            if pkt is not None and self._rx_callback is not None:
                self._rx_callback(pkt)

    # ------------------------------------------------------------------
    # TX
    # ------------------------------------------------------------------

    async def start_tx(self) -> None:
        """Start transmitting audio to the radio.

        Raises:
            RuntimeError: If already receiving or transmitting.
        """
        if self._state != AudioState.IDLE:
            raise RuntimeError(f"Cannot start TX in state {self._state}")
        self._state = AudioState.TRANSMITTING
        self._tx_seq = 0
        logger.info("Audio TX started")

    async def push_tx(self, opus_data: bytes) -> None:
        """Send an Opus-encoded audio frame to the radio.

        Args:
            opus_data: Opus-encoded audio data.

        Raises:
            RuntimeError: If not in transmitting state.
        """
        if self._state != AudioState.TRANSMITTING:
            raise RuntimeError(f"Cannot push TX in state {self._state}")

        pkt = build_audio_packet(
            opus_data,
            sender_id=self._transport.my_id,
            receiver_id=self._transport.remote_id,
            send_seq=self._tx_seq,
        )
        await self._transport.send_tracked(pkt)
        self._tx_seq = (self._tx_seq + 1) & 0xFFFF

    async def stop_tx(self) -> None:
        """Stop transmitting audio."""
        if self._state != AudioState.TRANSMITTING:
            return
        self._state = AudioState.IDLE
        logger.info("Audio TX stopped")


# ------------------------------------------------------------------
# Packet parsing / building (module-level for easy testing)
# ------------------------------------------------------------------


def parse_audio_packet(data: bytes) -> AudioPacket | None:
    """Parse a raw UDP audio packet into an :class:`AudioPacket`.

    Args:
        data: Raw UDP packet bytes (must be > 0x18 bytes).

    Returns:
        Parsed AudioPacket, or None if the packet is too short or
        is a control/retransmit packet (type != DATA).
    """
    if len(data) <= AUDIO_HEADER_SIZE:
        return None

    pkt_type = struct.unpack_from("<H", data, 0x04)[0]
    if pkt_type != PacketType.DATA:
        return None

    ident = struct.unpack_from("<H", data, 0x10)[0]
    send_seq = struct.unpack_from(">H", data, 0x12)[0]
    # datalen at 0x16 is BE, but we use actual remaining bytes
    audio_data = data[AUDIO_HEADER_SIZE:]

    return AudioPacket(ident=ident, send_seq=send_seq, data=audio_data)


def build_audio_packet(
    opus_data: bytes,
    *,
    sender_id: int,
    receiver_id: int,
    send_seq: int,
    ident: int = TX_IDENT,
) -> bytes:
    """Build a raw UDP audio packet from Opus data.

    Args:
        opus_data: Opus-encoded audio frame.
        sender_id: Our connection ID.
        receiver_id: Radio's connection ID.
        send_seq: Audio-level sequence number.
        ident: Audio ident field (default TX_IDENT=0x0080).

    Returns:
        Complete UDP packet bytes ready to send.
    """
    total_len = AUDIO_HEADER_SIZE + len(opus_data)
    pkt = bytearray(total_len)

    struct.pack_into("<I", pkt, 0x00, total_len)           # len (LE)
    struct.pack_into("<H", pkt, 0x04, PacketType.DATA)     # type (LE)
    # seq at 0x06 left as 0 — transport will fill it
    struct.pack_into("<I", pkt, 0x08, sender_id)           # sentid (LE)
    struct.pack_into("<I", pkt, 0x0C, receiver_id)         # rcvdid (LE)
    struct.pack_into("<H", pkt, 0x10, ident)               # ident (LE)
    struct.pack_into(">H", pkt, 0x12, send_seq)            # sendseq (BE)
    # 0x14: unused (stays 0)
    struct.pack_into(">H", pkt, 0x16, len(opus_data))      # datalen (BE)

    pkt[AUDIO_HEADER_SIZE:] = opus_data
    return bytes(pkt)
