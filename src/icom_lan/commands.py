"""CI-V command encoding and decoding for Icom transceivers.

CI-V frame format: FE FE <to> <from> <cmd> [<sub>] [<data>...] FD

For dual-receiver radios (IC-7610), commands marked Command29=true use:
  FE FE <to> <from> 29 <receiver> <cmd> [<sub>] [<data>...] FD
where receiver = 0x00 (MAIN) or 0x01 (SUB).

Reference: wfview icomcommander.cpp, IC-7610.rig
"""

from .types import CivFrame, Mode, bcd_decode, bcd_encode

__all__ = [
    "IC_7610_ADDR",
    "CONTROLLER_ADDR",
    "RECEIVER_MAIN",
    "RECEIVER_SUB",
    "build_civ_frame",
    "build_cmd29_frame",
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
    "send_cw",
    "stop_cw",
    "power_on",
    "power_off",
    "get_attenuator",
    "set_attenuator",
    "set_attenuator_level",
    "get_preamp",
    "set_preamp",
    "get_digisel",
    "set_digisel",
    "get_data_mode",
    "set_data_mode",
    "parse_data_mode_response",
    "scope_on",
    "scope_off",
    "scope_data_output",
    "scope_data_output_on",
    "scope_data_output_off",
    "scope_main_sub",
    "scope_single_dual",
    "scope_set_mode",
    "scope_set_span",
    "scope_set_ref",
    "scope_set_speed",
    "scope_set_edge",
    "scope_set_hold",
    "scope_set_vbw",
    "scope_set_rbw",
]

# CI-V addresses
IC_7610_ADDR = 0x98
CONTROLLER_ADDR = 0xE0

# Receiver IDs for Command29 (dual-receiver radios)
RECEIVER_MAIN = 0x00
RECEIVER_SUB = 0x01
_CMD_RECEIVER_PREFIX = 0x29

# CI-V command codes
_CMD_FREQ_GET = 0x03
_CMD_MODE_GET = 0x04
_CMD_FREQ_SET = 0x05
_CMD_MODE_SET = 0x06
_CMD_LEVEL = 0x14  # Levels (RF power, etc.)
_CMD_METER = 0x15  # Meter readings
_CMD_PTT = 0x1C  # Transceiver status / PTT
_CMD_CTL_MEM = 0x1A  # Memory / configuration command
_CMD_ACK = 0xFB
_CMD_NAK = 0xFA

# Sub-commands
_SUB_RF_POWER = 0x0A
_SUB_S_METER = 0x02
_SUB_SWR_METER = 0x12
_SUB_ALC_METER = 0x13
_SUB_PTT = 0x00
_SUB_DATA_MODE = 0x06  # DATA mode sub-command for 0x1A

# CI-V frame markers
_PREAMBLE = b"\xfe\xfe"
_TERMINATOR = b"\xfd"

# Commands that use sub-commands (for parse disambiguation)
_COMMANDS_WITH_SUB: set[int] = {_CMD_LEVEL, _CMD_METER, _CMD_PTT, _CMD_CTL_MEM, 0x27}


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


def build_cmd29_frame(
    to_addr: int,
    from_addr: int,
    command: int,
    sub: int | None = None,
    data: bytes | None = None,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a Command29-wrapped CI-V frame for dual-receiver radios.

    For commands marked Command29=true in IC-7610.rig, the frame format is:
      FE FE <to> <from> 29 <receiver> <cmd> [<sub>] [<data>...] FD

    The 0x29 prefix tells the radio which receiver (MAIN/SUB) the command
    targets, without requiring a VFO select first.

    Args:
        to_addr: Destination CI-V address.
        from_addr: Source CI-V address.
        command: Original CI-V command byte (e.g. 0x11 for ATT, 0x16 for PREAMP).
        sub: Optional sub-command byte.
        data: Optional payload data.
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).

    Returns:
        Complete CI-V frame bytes with Command29 prefix.
    """
    inner = bytearray()
    inner.append(command)
    if sub is not None:
        inner.append(sub)
    if data:
        inner.extend(data)
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_RECEIVER_PREFIX,
        data=bytes([receiver]) + bytes(inner),
    )


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

    # Handle Command29 prefix (dual-receiver): unwrap 0x29 <receiver> <real_cmd> ...
    if command == _CMD_RECEIVER_PREFIX and len(payload) >= 2:
        receiver = payload[0]
        real_command = payload[1]
        inner_payload = payload[2:]
        # Check if real command uses sub-commands
        if real_command in _COMMANDS_WITH_SUB and len(inner_payload) >= 1:
            return CivFrame(
                to_addr=to_addr,
                from_addr=from_addr,
                command=real_command,
                sub=inner_payload[0],
                data=bytes(inner_payload[1:]),
                receiver=receiver,
            )
        # PREAMP (0x16) uses sub-commands too
        if real_command == _CMD_PREAMP and len(inner_payload) >= 1:
            return CivFrame(
                to_addr=to_addr,
                from_addr=from_addr,
                command=real_command,
                sub=inner_payload[0],
                data=bytes(inner_payload[1:]),
                receiver=receiver,
            )
        return CivFrame(
            to_addr=to_addr,
            from_addr=from_addr,
            command=real_command,
            sub=None,
            data=bytes(inner_payload),
            receiver=receiver,
        )

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


def get_mode(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
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


def get_power(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
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


def get_s_meter(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
    """Build a 'read S-meter' CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_S_METER)


def get_swr(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
    """Build a 'read SWR meter' CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_SWR_METER)


def get_alc(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
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


def ptt_on(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
    """Build a PTT-on CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_PTT, data=b"\x01")


def ptt_off(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
    """Build a PTT-off CI-V command."""
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_PTT, data=b"\x00")


# --- VFO commands ---

_CMD_VFO_SELECT = 0x07
_CMD_VFO_EQUAL = 0x07
_CMD_SPLIT = 0x0F
_CMD_ATT = 0x11
_CMD_PREAMP = 0x16
_SUB_PREAMP_STATUS = 0x02
_SUB_DIGISEL_STATUS = 0x4E


def select_vfo(
    vfo: str = "A",
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Select VFO.

    Args:
        vfo: "A", "B", "MAIN", or "SUB".
              IC-7610 uses MAIN/SUB (0xD0/0xD1).
              Simpler radios use A/B (0x00/0x01).
    """
    codes = {"A": 0x00, "B": 0x01, "MAIN": 0xD0, "SUB": 0xD1}
    code = codes.get(vfo.upper(), 0x00)
    return build_civ_frame(to_addr, from_addr, _CMD_VFO_SELECT, data=bytes([code]))


def vfo_a_equals_b(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Copy VFO A to VFO B (A=B)."""
    return build_civ_frame(to_addr, from_addr, _CMD_VFO_EQUAL, data=b"\xa0")


def vfo_swap(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
    """Swap VFO A and B."""
    return build_civ_frame(to_addr, from_addr, _CMD_VFO_EQUAL, data=b"\xb0")


def set_split(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Enable or disable split mode."""
    return build_civ_frame(
        to_addr, from_addr, _CMD_SPLIT, data=b"\x01" if on else b"\x00"
    )


def _bcd_byte(value: int) -> int:
    """Encode 0-99 integer into one BCD byte."""
    if not 0 <= value <= 99:
        raise ValueError(f"BCD byte value must be 0-99, got {value}")
    return ((value // 10) << 4) | (value % 10)


def get_attenuator(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build CI-V command to read attenuator level (Command29-aware)."""
    return build_cmd29_frame(to_addr, from_addr, _CMD_ATT, receiver=receiver)


def set_attenuator_level(
    db: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Set attenuator level in dB (IC-7610 supports 0..45 in 3 dB steps).

    Uses Command29 framing for dual-receiver compatibility.
    """
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_ATT,
        data=bytes([_bcd_byte(db)]),
        receiver=receiver,
    )


def set_attenuator(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Compatibility wrapper for attenuator toggle.

    Maps False->0 dB and True->18 dB (conservative default).
    Prefer set_attenuator_level() for deterministic control.
    """
    return set_attenuator_level(
        18 if on else 0,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
    )


def get_preamp(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build CI-V command to read preamp status (Command29-aware)."""
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_PREAMP,
        sub=_SUB_PREAMP_STATUS,
        receiver=receiver,
    )


def set_preamp(
    level: int = 1,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Set preamp level (0=off, 1=PREAMP1, 2=PREAMP2).

    Uses Command29 framing for dual-receiver compatibility.
    """
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_PREAMP,
        sub=_SUB_PREAMP_STATUS,
        data=bytes([_bcd_byte(level)]),
        receiver=receiver,
    )


def get_digisel(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build CI-V command to read DIGI-SEL status (0/1) (Command29-aware)."""
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_PREAMP,
        sub=_SUB_DIGISEL_STATUS,
        receiver=receiver,
    )


def set_digisel(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Set DIGI-SEL status (0/1) (Command29-aware)."""
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_PREAMP,
        sub=_SUB_DIGISEL_STATUS,
        data=bytes([_bcd_byte(1 if on else 0)]),
        receiver=receiver,
    )


# --- DATA mode commands (CI-V 0x1A 0x06) ---


def get_data_mode(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a 'get DATA mode' CI-V command (0x1A 0x06).

    Returns:
        CI-V frame bytes.
    """
    return build_civ_frame(to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_DATA_MODE)


def set_data_mode(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set DATA mode' CI-V command (0x1A 0x06 <0x00|0x01>).

    Args:
        on: True to enable DATA1 mode, False to disable.
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        CI-V frame bytes.
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_DATA_MODE,
        data=b"\x01" if on else b"\x00",
    )


def parse_data_mode_response(frame: CivFrame) -> bool:
    """Parse a DATA mode response frame.

    Args:
        frame: Parsed CivFrame (command 0x1A, sub 0x06, data byte).

    Returns:
        True if DATA mode is active (data[0] != 0x00), False otherwise.

    Raises:
        ValueError: If frame is not a DATA mode response.
    """
    if frame.command != _CMD_CTL_MEM or frame.sub != _SUB_DATA_MODE:
        raise ValueError(
            f"Not a DATA mode response: cmd=0x{frame.command:02x} sub=0x{frame.sub if frame.sub is not None else 0:02x}"
        )
    if not frame.data:
        raise ValueError("DATA mode response has no data byte")
    return frame.data[0] != 0x00


# --- Scope / Waterfall commands (CI-V 0x27) ---

_CMD_SCOPE = 0x27
_SUB_SCOPE_ON = 0x10
_SUB_SCOPE_DATA_OUTPUT = 0x11
_SUB_SCOPE_MAIN_SUB = 0x12
_SUB_SCOPE_SINGLE_DUAL = 0x13
_SUB_SCOPE_MODE = 0x14
_SUB_SCOPE_SPAN = 0x15
_SUB_SCOPE_EDGE = 0x16
_SUB_SCOPE_HOLD = 0x17
_SUB_SCOPE_REF = 0x19
_SUB_SCOPE_SPEED = 0x1A
_SUB_SCOPE_VBW = 0x1D
_SUB_SCOPE_RBW = 0x1F


def scope_on(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a 'scope on' CI-V command (0x27 0x10 0x01)."""
    return build_civ_frame(to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_ON, data=b"\x01")


def scope_off(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build a 'scope off' CI-V command (0x27 0x10 0x00)."""
    return build_civ_frame(to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_ON, data=b"\x00")


def scope_data_output(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'scope data output enable/disable' CI-V command (0x27 0x11).

    Args:
        on: True to enable wave data output, False to disable.
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_DATA_OUTPUT,
        data=b"\x01" if on else b"\x00",
    )


def scope_set_mode(
    mode: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set scope mode' CI-V command (0x27 0x14).

    Args:
        mode: 0=center, 1=fixed, 2=scroll-C, 3=scroll-F.
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_MODE, data=bytes([mode])
    )


def scope_set_span(
    span: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set scope span' CI-V command (0x27 0x15).

    Args:
        span: 0–7 (span index, radio-model dependent).
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_SPAN, data=bytes([span])
    )


def scope_set_edge(
    edge: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set scope edge' CI-V command (0x27 0x16).

    Args:
        edge: Edge number 1–4.
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_EDGE, data=bytes([edge])
    )


def scope_set_hold(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'scope hold on/off' CI-V command (0x27 0x17).

    Args:
        on: True to enable hold, False to disable.
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_HOLD,
        data=b"\x01" if on else b"\x00",
    )


def _scope_ref_encode(ref: float) -> bytes:
    """Encode scope reference level as 3-byte Icom BCD format.

    Reference: wfview icomcommander.cpp line 3357 (bcdEncodeInt + sign byte).

    Args:
        ref: Reference level in dB (-30.0 to +10.0).

    Returns:
        3 bytes: [BCD thousands/hundreds, BCD tens/units, sign(0=+, 1=-)].
    """
    is_negative = ref < 0
    val = int(round(abs(ref) * 10))  # e.g. 10.0 dB → 100
    thousands = val // 1000
    hundreds = (val % 1000) // 100
    tens = (val % 100) // 10
    units = val % 10
    b0 = (thousands << 4) | hundreds
    b1 = (tens << 4) | units
    sign = 0x01 if is_negative else 0x00
    return bytes([b0, b1, sign])


def scope_set_ref(
    ref: float,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set scope reference level' CI-V command (0x27 0x19).

    Args:
        ref: Reference level in dB (-30.0 to +10.0).
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_REF,
        data=_scope_ref_encode(ref),
    )


def scope_set_speed(
    speed: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set scope speed' CI-V command (0x27 0x1A).

    Args:
        speed: 0=fast, 1=mid, 2=slow.
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_SPEED, data=bytes([speed])
    )


def scope_set_vbw(
    narrow: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set scope VBW' CI-V command (0x27 0x1D).

    Args:
        narrow: True for narrow VBW, False for wide.
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_VBW,
        data=b"\x01" if narrow else b"\x00",
    )


def scope_set_rbw(
    rbw: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a 'set scope RBW' CI-V command (0x27 0x1F).

    Args:
        rbw: 0=wide, 1=mid, 2=narrow.
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_RBW, data=bytes([rbw])
    )


# --- Scope convenience aliases ---


def scope_data_output_on(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Enable scope wave data output (0x27 0x11 0x01)."""
    return scope_data_output(True, to_addr=to_addr, from_addr=from_addr)


def scope_data_output_off(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Disable scope wave data output (0x27 0x11 0x00)."""
    return scope_data_output(False, to_addr=to_addr, from_addr=from_addr)


def scope_main_sub(
    receiver: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Select scope receiver (0x27 0x12 <0x00|0x01>).

    Args:
        receiver: 0 for MAIN, 1 for SUB.
    """
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_MAIN_SUB,
        data=bytes([receiver & 0x01]),
    )


def scope_single_dual(
    dual: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Select scope single/dual mode (0x27 0x13 <0x00|0x01>).

    Args:
        dual: True for dual scope, False for single.
    """
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_SINGLE_DUAL,
        data=b"\x01" if dual else b"\x00",
    )


# --- CW keying ---

_CMD_SEND_CW = 0x17


def send_cw(
    text: str,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> list[bytes]:
    """Build CI-V frames to send CW text.

    CW text is sent in chunks of up to 30 characters per frame.
    Each character is sent as ASCII byte in the data field.

    Args:
        text: CW text to send (A-Z, 0-9, and common prosigns).
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        List of CI-V frame bytes (one per chunk).
    """
    frames = []
    text = text.upper()
    for i in range(0, len(text), 30):
        chunk = text[i : i + 30]
        data = chunk.encode("ascii")
        frames.append(build_civ_frame(to_addr, from_addr, _CMD_SEND_CW, data=data))
    return frames


def stop_cw(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
    """Build CI-V frame to stop CW sending."""
    return build_civ_frame(to_addr, from_addr, _CMD_SEND_CW, data=b"\xff")


# --- Power on/off ---

_CMD_POWER_CTRL = 0x18


def power_on(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
    """Build CI-V frame to power on the radio."""
    return build_civ_frame(to_addr, from_addr, _CMD_POWER_CTRL, data=b"\x01")


def power_off(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
    """Build CI-V frame to power off the radio."""
    return build_civ_frame(to_addr, from_addr, _CMD_POWER_CTRL, data=b"\x00")


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
