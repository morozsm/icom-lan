"""Enums, dataclasses, and helper functions for the Icom LAN protocol."""

from dataclasses import dataclass
from enum import IntEnum

__all__ = [
    "PacketType",
    "Mode",
    "AudioCodec",
    "PacketHeader",
    "CivFrame",
    "HEADER_SIZE",
    "AUDIO_HEADER_SIZE",
    "bcd_encode",
    "bcd_decode",
]

# Fixed header size: 4 (len) + 2 (type) + 2 (seq) + 4 (sentid) + 4 (rcvdid) = 16 bytes
HEADER_SIZE = 0x10

# Audio packet header: standard 16-byte header + 8 bytes audio sub-header
AUDIO_HEADER_SIZE = 0x18


class PacketType(IntEnum):
    """Packet type codes from the Icom LAN UDP protocol.

    The type field is at offset 0x04 in every packet header (2 bytes LE).
    Values derived from wfview reference implementation.
    """

    DATA = 0x00
    CONTROL = 0x01
    ARE_YOU_THERE = 0x03
    I_AM_HERE = 0x04
    DISCONNECT = 0x05
    ARE_YOU_READY = 0x06
    PING = 0x07


class AudioCodec(IntEnum):
    """Audio codec identifiers used in conninfo packets.

    Values match the codec byte at offsets 0x72 (rxcodec) and 0x73 (txcodec)
    in the conninfo packet. Opus codecs (0x40/0x41) are only available
    when the radio reports connection_type == "WFVIEW".

    Reference: wfview audioconverter.h lines 123-133.
    """

    ULAW_1CH = 0x01
    PCM_1CH_8BIT = 0x02
    PCM_1CH_16BIT = 0x04
    PCM_2CH_8BIT = 0x08
    PCM_2CH_16BIT = 0x10
    ULAW_2CH = 0x20
    OPUS_1CH = 0x40
    OPUS_2CH = 0x41


class Mode(IntEnum):
    """Icom CI-V operating modes.

    Values match the CI-V mode byte sent/received in mode commands.
    """

    LSB = 0x00
    USB = 0x01
    AM = 0x02
    CW = 0x03
    RTTY = 0x04
    FM = 0x05
    WFM = 0x06
    CW_R = 0x07
    RTTY_R = 0x08
    DV = 0x17


@dataclass(frozen=True, slots=True)
class PacketHeader:
    """Fixed 16-byte header present in every Icom LAN UDP packet.

    Attributes:
        length: Total packet length in bytes (including this header).
        type: Packet type code.
        seq: Sequence number.
        sender_id: Sender's connection ID (assigned during handshake).
        receiver_id: Receiver's connection ID.
    """

    length: int
    type: int
    seq: int
    sender_id: int
    receiver_id: int


@dataclass(frozen=True, slots=True)
class CivFrame:
    """Parsed CI-V frame.

    Attributes:
        to_addr: Destination CI-V address.
        from_addr: Source CI-V address.
        command: CI-V command byte.
        sub: Optional sub-command byte.
        data: Payload data (excluding command and sub bytes).
    """

    to_addr: int
    from_addr: int
    command: int
    sub: int | None = None
    data: bytes = b""


def bcd_encode(freq_hz: int) -> bytes:
    """Encode a frequency in Hz to Icom BCD format (5 bytes).

    BCD encoding stores pairs of decimal digits in each byte,
    least-significant digits first (little-endian BCD).

    Args:
        freq_hz: Frequency in Hz (e.g. 14074000).

    Returns:
        5 bytes of BCD-encoded frequency.

    Raises:
        ValueError: If frequency is negative or exceeds 10 digits.

    Examples:
        >>> bcd_encode(14074000).hex()
        '0040071400'
    """
    if freq_hz < 0:
        raise ValueError(f"Frequency must be non-negative, got {freq_hz}")

    digits = f"{freq_hz:010d}"
    if len(digits) > 10:
        raise ValueError(f"Frequency {freq_hz} exceeds 10 digits")

    # BCD little-endian: byte[i] stores digit pair for positions 2i and 2i+1.
    # Low nibble = digit at position 2i (even power of 10).
    # High nibble = digit at position 2i+1 (odd power of 10).
    # Digits string is big-endian: digits[0]=most significant, digits[9]=units.
    result = bytearray(5)
    for i in range(5):
        low = int(digits[9 - 2 * i])  # position 2i
        high = int(digits[9 - 2 * i - 1])  # position 2i+1
        result[i] = (high << 4) | low
    return bytes(result)


def bcd_decode(data: bytes) -> int:
    """Decode Icom BCD-encoded frequency bytes to Hz.

    Args:
        data: 5 bytes of BCD-encoded frequency.

    Returns:
        Frequency in Hz.

    Raises:
        ValueError: If data is not exactly 5 bytes or contains invalid BCD.

    Examples:
        >>> bcd_decode(bytes.fromhex('0040071400'))
        14074000
    """
    if len(data) != 5:
        raise ValueError(f"BCD data must be exactly 5 bytes, got {len(data)}")

    freq = 0
    for i in range(len(data)):
        high = (data[i] >> 4) & 0x0F
        low = data[i] & 0x0F
        if high > 9 or low > 9:
            raise ValueError(f"Invalid BCD digit in byte {i}: 0x{data[i]:02x}")
        # low nibble = digit at position 2i, high nibble = position 2i+1
        freq += low * (10 ** (2 * i)) + high * (10 ** (2 * i + 1))
    return freq
