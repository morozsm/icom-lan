"""CI-V command encoding and decoding for Icom transceivers.

CI-V frame format: FE FE <to> <from> <cmd> [<sub>] [<data>...] FD

Reference: wfview icomcommander.cpp, IC-7610.rig
"""

from .types import CivFrame, Mode, bcd_decode, bcd_encode

__all__ = [
    "IC_7610_ADDR",
    "CONTROLLER_ADDR",
    "build_civ_frame",
    "parse_civ_frame",
    "get_frequency",
    "set_frequency",
    "get_mode",
    "set_mode",
    "get_power",
    "set_power",
    "get_s_meter",
    "get_swr",
    "get_alc",
    "ptt_on",
    "ptt_off",
    "parse_frequency_response",
    "parse_mode_response",
    "parse_meter_response",
    "parse_ack_nak",
]

# CI-V addresses
IC_7610_ADDR = 0x98
CONTROLLER_ADDR = 0xE0

# CI-V command codes
_CMD_FREQ_GET = 0x03
_CMD_MODE_GET = 0x04
_CMD_FREQ_SET = 0x05
_CMD_MODE_SET = 0x06
_CMD_LEVEL = 0x14  # Levels (RF power, etc.)
_CMD_METER = 0x15  # Meter readings
_CMD_PTT = 0x1C  # Transceiver status / PTT
_CMD_ACK = 0xFB
_CMD_NAK = 0xFA

# Sub-commands
_SUB_RF_POWER = 0x0A
_SUB_S_METER = 0x02
_SUB_SWR_METER = 0x12
_SUB_ALC_METER = 0x13
_SUB_PTT = 0x00

# CI-V frame markers
_PREAMBLE = b"\xfe\xfe"
_TERMINATOR = b"\xfd"

# Commands that use sub-commands (for parse disambiguation)
_COMMANDS_WITH_SUB: set[int] = {_CMD_LEVEL, _CMD_METER, _CMD_PTT}


def build_civ_frame(
    to_addr: int,
    from_addr: int,
    command: int,
    sub: int | None = None,
    data: bytes | None = None,
) -> bytes:
    """Build a CI-V frame.

    Args:
        to_addr: Destination CI-V address.
        from_addr: Source CI-V address.
        command: CI-V command byte.
        sub: Optional sub-command byte.
        data: Optional payload data.

    Returns:
        Complete CI-V frame bytes.
    """
    frame = bytearray(_PREAMBLE)
    frame.append(to_addr)
    frame.append(from_addr)
    frame.append(command)
    if sub is not None:
        frame.append(sub)
    if data:
        frame.extend(data)
    frame.extend(_TERMINATOR)
    return bytes(frame)


def parse_civ_frame(data: bytes) -> CivFrame:
    """Parse a CI-V frame into a CivFrame.

    Args:
        data: Raw CI-V frame bytes (including FE FE preamble and FD terminator).

    Returns:
        Parsed CivFrame.

    Raises:
        ValueError: If frame is malformed.
    """
    if len(data) < 6:
        raise ValueError(f"CI-V frame too short: {len(data)} bytes")
    if data[:2] != _PREAMBLE:
        raise ValueError(f"Invalid CI-V preamble: {data[:2].hex()}")
    if data[-1:] != _TERMINATOR:
        raise ValueError(f"Missing CI-V terminator: {data[-1]:02x}")

    to_addr = data[2]
    from_addr = data[3]
    command = data[4]
    payload = data[5:-1]

    # Determine if first payload byte is a sub-command
    if command in _COMMANDS_WITH_SUB and len(payload) >= 1:
        return CivFrame(
            to_addr=to_addr,
            from_addr=from_addr,
            command=command,
            sub=payload[0],
            data=bytes(payload[1:]),
        )

    return CivFrame(
        to_addr=to_addr,
        from_addr=from_addr,
        command=command,
        sub=None,
        data=bytes(payload),
    )


# --- Frequency commands ---


def get_frequency(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a 'get frequency' CI-V command.

    Args:
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        CI-V frame bytes.
    """
    return build_civ_frame(to_addr, from_addr, _CMD_FREQ_GET)


def set_frequency(
    freq_hz: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set frequency' CI-V command.

    Args:
        freq_hz: Frequency in Hz.
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        CI-V frame bytes.
    """
    return build_civ_frame(to_addr, from_addr, _CMD_FREQ_SET, data=bcd_encode(freq_hz))


def parse_frequency_response(frame: CivFrame) -> int:
    """Parse a frequency response frame.

    Args:
        frame: Parsed CivFrame (command 0x03 with 5-byte BCD data).

    Returns:
        Frequency in Hz.

    Raises:
        ValueError: If frame is not a frequency response.
    """
    if frame.command not in (_CMD_FREQ_GET, 0x00):
        raise ValueError(f"Not a frequency response: command 0x{frame.command:02x}")
    return bcd_decode(frame.data)


# --- Mode commands ---


def get_mode(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a 'get mode' CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_MODE_GET)


def set_mode(
    mode: Mode,
    filter_width: int | None = None,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set mode' CI-V command.

    Args:
        mode: Operating mode.
        filter_width: Optional filter number (1-3).
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        CI-V frame bytes.
    """
    data = bytes([mode])
    if filter_width is not None:
        data += bytes([filter_width])
    return build_civ_frame(to_addr, from_addr, _CMD_MODE_SET, data=data)


def parse_mode_response(frame: CivFrame) -> tuple[Mode, int | None]:
    """Parse a mode response frame.

    Args:
        frame: Parsed CivFrame (command 0x04 or 0x01).

    Returns:
        Tuple of (mode, filter_width or None).

    Raises:
        ValueError: If frame is not a mode response.
    """
    if frame.command not in (_CMD_MODE_GET, 0x01):
        raise ValueError(f"Not a mode response: command 0x{frame.command:02x}")
    mode = Mode(frame.data[0])
    filt = frame.data[1] if len(frame.data) > 1 else None
    return mode, filt


# --- Power commands ---


def _level_bcd_encode(value: int) -> bytes:
    """Encode a 0-255 level as 2-byte BCD (0x00 0x00 to 0x02 0x55).

    Each byte holds two BCD digits: high nibble = tens, low nibble = units.
    Byte 0 = hundreds and tens, Byte 1 = tens and units... actually:
    Byte 0 = digit[2] digit[1], Byte 1 = digit[0] 0? No —
    The Icom format is: byte[0] = (d2 << 4 | d1), byte[1] = (d0 << 4 | 0)?
    No. Looking at wfview: bcdHexToUChar reads 2 bytes as hundreds, tens, units.
    128 -> 0x01 0x28: byte0=0x01 (0,1), byte1=0x28 (2,8). So:
    byte0 high=0, low=1 -> 0*10+1=01, byte1 high=2, low=8 -> 28. Total=128.
    """
    if not 0 <= value <= 255:
        raise ValueError(f"Level must be 0-255, got {value}")
    d = f"{value:04d}"  # e.g. "0128"
    b0 = (int(d[0]) << 4) | int(d[1])
    b1 = (int(d[2]) << 4) | int(d[3])
    return bytes([b0, b1])


def _level_bcd_decode(data: bytes) -> int:
    """Decode 2-byte BCD level to 0-255 int."""
    d0 = (data[0] >> 4) & 0x0F
    d1 = data[0] & 0x0F
    d2 = (data[1] >> 4) & 0x0F
    d3 = data[1] & 0x0F
    return d0 * 1000 + d1 * 100 + d2 * 10 + d3


def get_power(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a 'get RF power' CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_RF_POWER)


def set_power(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set RF power' CI-V command.

    Args:
        level: Power level 0-255 (radio maps to actual watts).
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        CI-V frame bytes.
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_LEVEL, sub=_SUB_RF_POWER, data=_level_bcd_encode(level)
    )


# --- Meter commands ---


def get_s_meter(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a 'read S-meter' CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_S_METER)


def get_swr(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a 'read SWR meter' CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_SWR_METER)


def get_alc(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a 'read ALC meter' CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_ALC_METER)


def parse_meter_response(frame: CivFrame) -> int:
    """Parse a meter response frame.

    Args:
        frame: Parsed CivFrame (command 0x15 with 2-byte BCD data).

    Returns:
        Meter value 0-255.

    Raises:
        ValueError: If frame is not a meter response.
    """
    if frame.command != _CMD_METER:
        raise ValueError(f"Not a meter response: command 0x{frame.command:02x}")
    return _level_bcd_decode(frame.data)


# --- PTT commands ---


def ptt_on(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a PTT-on CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_PTT, data=b"\x01")


def ptt_off(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a PTT-off CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_PTT, data=b"\x00")


# --- ACK/NAK ---


def parse_ack_nak(frame: CivFrame) -> bool | None:
    """Check if frame is ACK (0xFB) or NAK (0xFA).

    Args:
        frame: Parsed CivFrame.

    Returns:
        True for ACK, False for NAK, None if neither.
    """
    if frame.command == _CMD_ACK:
        return True
    if frame.command == _CMD_NAK:
        return False
    return None
