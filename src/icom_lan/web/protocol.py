"""Web UI binary frame protocol for scope and meter data.

Binary Scope Frame (RFC):
    Offset  Size  Field           Description
    0       1     msg_type        0x01 = scope_frame
    1       1     receiver        0=Main, 1=Sub
    2       1     mode            0=center, 1=fixed, 2=scroll-C, 3=scroll-F
    3       4     start_freq      uint32 LE, Hz
    7       4     end_freq        uint32 LE, Hz
    11      2     sequence        uint16 LE
    13      1     flags           bit 0: out_of_range
    14      2     pixel_count     uint16 LE
    16      N     pixels          uint8[], amplitude 0-160

Binary Meter Frame (RFC):
    Offset  Size  Field        Description
    0       1     msg_type     0x20 = meter_frame
    1       2     sequence     uint16 LE
    3       1     count        number of meters
    4       N×3   meters[]     [meter_id(u8), value_lo(u8), value_hi(u8)]
"""

from __future__ import annotations

import json
import struct
from typing import Any

from ..scope import ScopeFrame

__all__ = [
    "MSG_TYPE_SCOPE",
    "MSG_TYPE_METER",
    "MSG_TYPE_AUDIO_RX",
    "MSG_TYPE_AUDIO_TX",
    "METER_SMETER_MAIN",
    "METER_SMETER_SUB",
    "METER_POWER",
    "METER_SWR",
    "METER_ALC",
    "METER_COMP",
    "METER_ID_DRAIN",
    "METER_VD",
    "METER_TEMP",
    "SCOPE_HEADER_SIZE",
    "METER_HEADER_SIZE",
    "encode_scope_frame",
    "encode_meter_frame",
    "encode_json",
    "decode_json",
]

# Message type constants
MSG_TYPE_SCOPE: int = 0x01
MSG_TYPE_METER: int = 0x20
MSG_TYPE_AUDIO_RX: int = 0x10
MSG_TYPE_AUDIO_TX: int = 0x11

# Meter ID constants
METER_SMETER_MAIN: int = 0x01
METER_SMETER_SUB: int = 0x02
METER_POWER: int = 0x03
METER_SWR: int = 0x04
METER_ALC: int = 0x05
METER_COMP: int = 0x06
METER_ID_DRAIN: int = 0x07
METER_VD: int = 0x08
METER_TEMP: int = 0x09

# Header sizes
SCOPE_HEADER_SIZE: int = 16
METER_HEADER_SIZE: int = 4  # msg_type(1) + sequence(2) + count(1)


def encode_scope_frame(frame: ScopeFrame, sequence: int) -> bytes:
    """Serialize a scope frame to binary wire format (RFC).

    Args:
        frame: Complete scope frame from the radio.
        sequence: Wrapping sequence counter (uint16).

    Returns:
        16-byte header + pixel bytes.
    """
    pixel_count = len(frame.pixels)
    flags = 0x01 if frame.out_of_range else 0x00
    seq_u16 = sequence & 0xFFFF

    header = (
        bytes([MSG_TYPE_SCOPE, frame.receiver, frame.mode])
        + struct.pack("<I", frame.start_freq_hz)
        + struct.pack("<I", frame.end_freq_hz)
        + struct.pack("<H", seq_u16)
        + bytes([flags])
        + struct.pack("<H", pixel_count)
    )
    # header is exactly 3 + 4 + 4 + 2 + 1 + 2 = 16 bytes
    return header + frame.pixels


def encode_meter_frame(meters: list[tuple[int, int]], sequence: int) -> bytes:
    """Serialize a meter frame to binary wire format (RFC).

    Args:
        meters: List of (meter_id, value) pairs. Values are uint16.
        sequence: Wrapping sequence counter (uint16).

    Returns:
        4-byte header + (3 × count) meter bytes.
    """
    count = len(meters)
    seq_u16 = sequence & 0xFFFF

    header = (
        bytes([MSG_TYPE_METER])
        + struct.pack("<H", seq_u16)
        + bytes([count])
    )
    data = b"".join(
        bytes([meter_id, value & 0xFF, (value >> 8) & 0xFF])
        for meter_id, value in meters
    )
    return header + data


def encode_json(msg: dict[str, Any]) -> str:
    """Serialize a JSON message dict to a string.

    Args:
        msg: Message dict (must include 'type' field).

    Returns:
        JSON string.
    """
    return json.dumps(msg, separators=(",", ":"))


def decode_json(text: str) -> dict[str, Any]:
    """Deserialize a JSON message string to a dict.

    Args:
        text: JSON text received from client.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If text is not valid JSON or not a dict.
    """
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("expected a JSON object")
    return obj
