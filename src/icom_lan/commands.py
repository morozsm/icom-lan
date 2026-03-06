"""CI-V command encoding and decoding for Icom transceivers.

CI-V frame format::

    FE FE <to> <from> <cmd> [<sub>] [<data>...] FD

For dual-receiver radios (IC-7610), commands marked Command29=true use::

    FE FE <to> <from> 29 <receiver> <cmd> [<sub>] [<data>...] FD

where ``receiver`` = ``0x00`` (MAIN) or ``0x01`` (SUB).

Reference: wfview icomcommander.cpp, IC-7610.rig
"""

import math

from .types import (
    AgcMode,
    AudioPeakFilter,
    BreakInMode,
    CivFrame,
    FilterShape,
    Mode,
    SsbTxBandwidth,
    bcd_decode,
    bcd_encode,
)

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
    "get_apf_type_level",
    "set_apf_type_level",
    "get_nr_level",
    "set_nr_level",
    "get_pbt_inner",
    "set_pbt_inner",
    "get_pbt_outer",
    "set_pbt_outer",
    "get_cw_pitch",
    "set_cw_pitch",
    "get_mic_gain",
    "set_mic_gain",
    "get_key_speed",
    "set_key_speed",
    "get_notch_filter",
    "set_notch_filter",
    "get_compressor_level",
    "set_compressor_level",
    "get_break_in_delay",
    "set_break_in_delay",
    "get_nb_level",
    "set_nb_level",
    "get_digisel_shift",
    "set_digisel_shift",
    "get_drive_gain",
    "set_drive_gain",
    "get_monitor_gain",
    "set_monitor_gain",
    "get_vox_gain",
    "set_vox_gain",
    "get_anti_vox_gain",
    "set_anti_vox_gain",
    "get_ref_adjust",
    "set_ref_adjust",
    "get_dash_ratio",
    "set_dash_ratio",
    "get_nb_depth",
    "set_nb_depth",
    "get_nb_width",
    "set_nb_width",
    "get_af_mute",
    "set_af_mute",
    "get_s_meter_sql_status",
    "get_overflow_status",
    "get_agc",
    "set_agc",
    "get_audio_peak_filter",
    "set_audio_peak_filter",
    "get_auto_notch",
    "set_auto_notch",
    "get_compressor",
    "set_compressor",
    "get_monitor",
    "set_monitor",
    "get_vox",
    "set_vox",
    "get_break_in",
    "set_break_in",
    "get_manual_notch",
    "set_manual_notch",
    "get_twin_peak_filter",
    "set_twin_peak_filter",
    "get_dial_lock",
    "set_dial_lock",
    "get_filter_shape",
    "set_filter_shape",
    "get_ssb_tx_bandwidth",
    "set_ssb_tx_bandwidth",
    "get_agc_time_constant",
    "set_agc_time_constant",
    "get_data_mode",
    "set_data_mode",
    "parse_data_mode_response",
    "parse_level_response",
    "parse_bool_response",
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
    # Transceiver status family (#136)
    "get_band_edge_freq",
    "get_various_squelch",
    "get_power_meter",
    "get_comp_meter",
    "get_vd_meter",
    "get_id_meter",
    "get_tuner_status",
    "set_tuner_status",
    "get_tx_freq_monitor",
    "set_tx_freq_monitor",
    "get_rit_frequency",
    "set_rit_frequency",
    "get_rit_status",
    "set_rit_status",
    "get_rit_tx_status",
    "set_rit_tx_status",
    "parse_rit_frequency_response",
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
_CMD_BAND_EDGE = 0x02  # Band edge frequency
_CMD_RIT = 0x21       # RIT/XIT
_CMD_ACK = 0xFB
_CMD_NAK = 0xFA

# Sub-commands
_SUB_AF_LEVEL = 0x01  # AF output level (0x14 0x01)
_SUB_RF_GAIN = 0x02   # RF Gain level (0x14 0x02)
_SUB_SQL = 0x03       # Squelch level (0x14 0x03)
_SUB_APF_TYPE_LEVEL = 0x05
_SUB_NR_LEVEL = 0x06
_SUB_PBT_INNER = 0x07
_SUB_PBT_OUTER = 0x08
_SUB_CW_PITCH = 0x09
_SUB_RF_POWER = 0x0A
_SUB_MIC_GAIN = 0x0B
_SUB_KEY_SPEED = 0x0C
_SUB_NOTCH_FILTER = 0x0D
_SUB_COMPRESSOR_LEVEL = 0x0E
_SUB_BREAK_IN_DELAY = 0x0F
_SUB_NB_LEVEL = 0x12
_SUB_DIGISEL_SHIFT = 0x13
_SUB_DRIVE_GAIN = 0x14
_SUB_MONITOR_GAIN = 0x15
_SUB_VOX_GAIN = 0x16
_SUB_ANTI_VOX_GAIN = 0x17
_SUB_S_METER = 0x02
_SUB_VARIOUS_SQUELCH = 0x05   # Various squelch (cmd29)
_SUB_POWER_METER = 0x11
_SUB_SWR_METER = 0x12
_SUB_ALC_METER = 0x13
_SUB_COMP_METER = 0x14
_SUB_VD_METER = 0x15
_SUB_ID_METER = 0x16
_SUB_PTT = 0x00
_SUB_CTL_MEM = 0x05
_SUB_DATA_MODE = 0x06  # DATA mode sub-command for 0x1A
_SUB_AF_MUTE = 0x09

_CTL_MEM_REF_ADJUST = b"\x00\x70"
_CTL_MEM_DASH_RATIO = b"\x02\x28"
_CTL_MEM_NB_DEPTH = b"\x02\x90"
_CTL_MEM_NB_WIDTH = b"\x02\x91"

# CI-V frame markers
_PREAMBLE = b"\xfe\xfe"
_TERMINATOR = b"\xfd"

# Commands that use sub-commands (for parse disambiguation)
_COMMANDS_WITH_SUB: set[int] = {_CMD_LEVEL, _CMD_METER, _CMD_PTT, _CMD_CTL_MEM, _CMD_RIT, 0x27, 0x16}


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

    For commands marked Command29=true in IC-7610.rig, the frame format is::

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
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a 'set frequency' CI-V command.

    Note:
        BCD encoding uses 5 bytes (10 decimal digits), so the maximum
        representable frequency is 9,999,999,999 Hz (~10 GHz).  Frequencies
        outside this range will raise ``ValueError`` from :func:`bcd_encode`.

    Args:
        freq_hz: Frequency in Hz (0 – 9,999,999,999).
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).

    Returns:
        CI-V frame bytes.
    """
    bcd = bcd_encode(freq_hz)
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(to_addr, from_addr, _CMD_FREQ_SET, data=bcd, receiver=receiver)
    return build_civ_frame(to_addr, from_addr, _CMD_FREQ_SET, data=bcd)


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
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a 'set mode' CI-V command.

    Args:
        mode: Operating mode.
        filter_width: Optional filter number (1-3).
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).

    Returns:
        CI-V frame bytes.
    """
    data = bytes([mode])
    if filter_width is not None:
        data += bytes([filter_width])
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(to_addr, from_addr, _CMD_MODE_SET, data=data, receiver=receiver)
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
    if len(frame.data) < 1:
        raise ValueError(
            "Mode response payload too short: expected at least 1 byte, "
            f"got {len(frame.data)}"
        )
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
    if len(data) < 2:
        raise ValueError(
            f"Level payload too short: expected at least 2 bytes, got {len(data)}"
        )
    return _bcd_decode_value(data[:2])


def _bcd_decode_value(data: bytes) -> int:
    """Decode packed BCD bytes into an integer."""
    value = 0
    for index, byte in enumerate(data):
        high = (byte >> 4) & 0x0F
        low = byte & 0x0F
        if high > 9 or low > 9:
            raise ValueError(f"Invalid BCD digit in byte {index}: 0x{byte:02x}")
        value = (value * 100) + (high * 10) + low
    return value


def _bcd_encode_value(value: int, *, byte_count: int) -> bytes:
    """Encode an integer as packed BCD using a fixed byte width."""
    if value < 0:
        raise ValueError(f"BCD value must be non-negative, got {value}")
    digits = byte_count * 2
    maximum = (10 ** digits) - 1
    if value > maximum:
        raise ValueError(
            f"BCD value must fit in {byte_count} byte(s), got {value}"
        )
    text = f"{value:0{digits}d}"
    return bytes(
        (int(text[index]) << 4) | int(text[index + 1])
        for index in range(0, len(text), 2)
    )


def parse_level_response(
    frame: CivFrame,
    *,
    command: int = _CMD_LEVEL,
    sub: int | None = None,
    prefix: bytes = b"",
    bcd_bytes: int = 2,
) -> int:
    """Parse a BCD-encoded level/config response."""
    if frame.command != command:
        raise ValueError(f"Not a level response: command 0x{frame.command:02x}")
    if sub is not None and frame.sub != sub:
        got = 0 if frame.sub is None else frame.sub
        raise ValueError(
            f"Not a level response: sub-command 0x{got:02x} != 0x{sub:02x}"
        )
    data = frame.data
    if prefix:
        if not data.startswith(prefix):
            raise ValueError(
                f"Level response prefix mismatch: expected {prefix.hex()}, got {data.hex()}"
            )
        data = data[len(prefix):]
    if len(data) < bcd_bytes:
        raise ValueError(
            f"Level response payload too short: expected at least {bcd_bytes} bytes, got {len(data)}"
        )
    return _bcd_decode_value(data[:bcd_bytes])


def parse_bool_response(
    frame: CivFrame,
    *,
    command: int,
    sub: int | None = None,
    prefix: bytes = b"",
) -> bool:
    """Parse a boolean CI-V response payload."""
    if frame.command != command:
        raise ValueError(f"Not a boolean response: command 0x{frame.command:02x}")
    if sub is not None and frame.sub != sub:
        got = 0 if frame.sub is None else frame.sub
        raise ValueError(
            f"Not a boolean response: sub-command 0x{got:02x} != 0x{sub:02x}"
        )
    data = frame.data
    if prefix:
        if not data.startswith(prefix):
            raise ValueError(
                f"Boolean response prefix mismatch: expected {prefix.hex()}, got {data.hex()}"
            )
        data = data[len(prefix):]
    if not data:
        raise ValueError("Boolean response has no payload byte")
    return data[0] != 0x00


def _build_level_get(
    sub: int,
    *,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
) -> bytes:
    if command29:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_LEVEL,
            sub=sub,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=sub)


def _build_level_set(
    sub: int,
    value: int,
    *,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
    encoder=_level_bcd_encode,
) -> bytes:
    payload = encoder(value)
    if command29:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_LEVEL,
            sub=sub,
            data=payload,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=sub, data=payload)


def _build_ctl_mem_get(
    prefix: bytes,
    *,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_CTL_MEM,
        data=prefix,
    )


def _build_ctl_mem_set(
    prefix: bytes,
    value: int,
    *,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    byte_count: int,
) -> bytes:
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_CTL_MEM,
        data=prefix + _bcd_encode_value(value, byte_count=byte_count),
    )


def _build_meter_bool_get(
    sub: int,
    *,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
) -> bytes:
    if command29:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_METER,
            sub=sub,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=sub)


def _build_function_get(
    sub: int,
    *,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
) -> bytes:
    if command29:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_PREAMP,
            sub=sub,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=sub)


def _build_function_bool_set(
    sub: int,
    on: bool,
    *,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
) -> bytes:
    payload = b"\x01" if on else b"\x00"
    if command29:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_PREAMP,
            sub=sub,
            data=payload,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=sub, data=payload)


def _build_function_value_set(
    sub: int,
    value: int,
    *,
    minimum: int,
    maximum: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
) -> bytes:
    if not minimum <= value <= maximum:
        raise ValueError(f"Value must be {minimum}-{maximum}, got {value}")
    payload = bytes([_bcd_byte(value)])
    if command29:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_PREAMP,
            sub=sub,
            data=payload,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=sub, data=payload)


def _build_ctl_mem_single_bcd_get(
    sub: int,
    *,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
) -> bytes:
    if command29:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_CTL_MEM,
            sub=sub,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_CTL_MEM, sub=sub)


def _build_ctl_mem_single_bcd_set(
    sub: int,
    value: int,
    *,
    minimum: int,
    maximum: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
) -> bytes:
    if not minimum <= value <= maximum:
        raise ValueError(f"Value must be {minimum}-{maximum}, got {value}")
    payload = bytes([_bcd_byte(value)])
    if command29:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_CTL_MEM,
            sub=sub,
            data=payload,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_CTL_MEM, sub=sub, data=payload)


def _cw_pitch_from_level(level: int) -> int:
    return int(round((((600.0 / 255.0) * level) + 300) / 5.0) * 5.0)


def _cw_pitch_to_level(pitch_hz: int) -> int:
    if not 300 <= pitch_hz <= 900:
        raise ValueError(f"CW pitch must be 300-900 Hz, got {pitch_hz}")
    return math.ceil((pitch_hz - 300) * (255.0 / 600.0))


def _key_speed_from_level(level: int) -> int:
    return round((level / 6.071) + 6)


def _key_speed_to_level(wpm: int) -> int:
    if not 6 <= wpm <= 48:
        raise ValueError(f"Key speed must be 6-48 WPM, got {wpm}")
    return round((wpm - 6) * 6.071)


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


def get_rf_gain(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
    """Build a 'read RF gain' CI-V command (0x14 0x02)."""
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_RF_GAIN)


def set_rf_gain(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a 'set RF gain' CI-V command.

    Args:
        level: Gain level 0-255 (0=min, 255=max).
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).
    """
    bcd = _level_bcd_encode(level)
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_RF_GAIN, data=bcd, receiver=receiver)
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_RF_GAIN, data=bcd)


def get_af_level(to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR) -> bytes:
    """Build a 'read AF output level' CI-V command (0x14 0x01)."""
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_AF_LEVEL)


def set_af_level(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a 'set AF output level' CI-V command.

    Args:
        level: AF level 0-255 (0=min, 255=max).
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).
    """
    bcd = _level_bcd_encode(level)
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_AF_LEVEL, data=bcd, receiver=receiver)
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_AF_LEVEL, data=bcd)


def set_squelch(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a 'set squelch level' CI-V command.

    Args:
        level: Squelch level 0-255 (0=open, 255=closed).
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).
    """
    bcd = _level_bcd_encode(level)
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_SQL, data=bcd, receiver=receiver)
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_SQL, data=bcd)


def get_apf_type_level(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read APF Type Level command."""
    return _build_level_get(
        _SUB_APF_TYPE_LEVEL,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_apf_type_level(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set APF Type Level command."""
    return _build_level_set(
        _SUB_APF_TYPE_LEVEL,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_nr_level(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read NR Level command."""
    return _build_level_get(
        _SUB_NR_LEVEL,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_nr_level(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set NR Level command."""
    return _build_level_set(
        _SUB_NR_LEVEL,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_pbt_inner(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read PBT Inner command."""
    return _build_level_get(
        _SUB_PBT_INNER,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_pbt_inner(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set PBT Inner command."""
    return _build_level_set(
        _SUB_PBT_INNER,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_pbt_outer(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read PBT Outer command."""
    return _build_level_get(
        _SUB_PBT_OUTER,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_pbt_outer(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set PBT Outer command."""
    return _build_level_set(
        _SUB_PBT_OUTER,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_cw_pitch(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read CW Pitch command."""
    return _build_level_get(_SUB_CW_PITCH, to_addr=to_addr, from_addr=from_addr)


def set_cw_pitch(
    pitch_hz: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set CW Pitch command."""
    return _build_level_set(
        _SUB_CW_PITCH,
        _cw_pitch_to_level(pitch_hz),
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_mic_gain(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Mic Gain command."""
    return _build_level_get(_SUB_MIC_GAIN, to_addr=to_addr, from_addr=from_addr)


def set_mic_gain(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set Mic Gain command."""
    return _build_level_set(_SUB_MIC_GAIN, level, to_addr=to_addr, from_addr=from_addr)


def get_key_speed(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Key Speed command."""
    return _build_level_get(_SUB_KEY_SPEED, to_addr=to_addr, from_addr=from_addr)


def set_key_speed(
    wpm: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set Key Speed command."""
    return _build_level_set(
        _SUB_KEY_SPEED,
        _key_speed_to_level(wpm),
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_notch_filter(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Notch Filter level command."""
    return _build_level_get(_SUB_NOTCH_FILTER, to_addr=to_addr, from_addr=from_addr)


def set_notch_filter(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set Notch Filter level command."""
    return _build_level_set(
        _SUB_NOTCH_FILTER,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_compressor_level(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Compressor Level command."""
    return _build_level_get(
        _SUB_COMPRESSOR_LEVEL, to_addr=to_addr, from_addr=from_addr
    )


def set_compressor_level(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set Compressor Level command."""
    return _build_level_set(
        _SUB_COMPRESSOR_LEVEL,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_break_in_delay(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Break-In Delay command."""
    return _build_level_get(
        _SUB_BREAK_IN_DELAY, to_addr=to_addr, from_addr=from_addr
    )


def set_break_in_delay(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set Break-In Delay command."""
    return _build_level_set(
        _SUB_BREAK_IN_DELAY,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_nb_level(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read NB Level command."""
    return _build_level_get(
        _SUB_NB_LEVEL,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_nb_level(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set NB Level command."""
    return _build_level_set(
        _SUB_NB_LEVEL,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_digisel_shift(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read DIGI-SEL Shift command."""
    return _build_level_get(
        _SUB_DIGISEL_SHIFT,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_digisel_shift(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set DIGI-SEL Shift command."""
    return _build_level_set(
        _SUB_DIGISEL_SHIFT,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_drive_gain(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Drive Gain command."""
    return _build_level_get(_SUB_DRIVE_GAIN, to_addr=to_addr, from_addr=from_addr)


def set_drive_gain(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set Drive Gain command."""
    return _build_level_set(
        _SUB_DRIVE_GAIN,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_monitor_gain(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Monitor Gain command."""
    return _build_level_get(_SUB_MONITOR_GAIN, to_addr=to_addr, from_addr=from_addr)


def set_monitor_gain(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set Monitor Gain command."""
    return _build_level_set(
        _SUB_MONITOR_GAIN,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_vox_gain(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Vox Gain command."""
    return _build_level_get(_SUB_VOX_GAIN, to_addr=to_addr, from_addr=from_addr)


def set_vox_gain(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set Vox Gain command."""
    return _build_level_set(_SUB_VOX_GAIN, level, to_addr=to_addr, from_addr=from_addr)


def get_anti_vox_gain(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Anti-Vox Gain command."""
    return _build_level_get(
        _SUB_ANTI_VOX_GAIN, to_addr=to_addr, from_addr=from_addr
    )


def set_anti_vox_gain(
    level: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set Anti-Vox Gain command."""
    return _build_level_set(
        _SUB_ANTI_VOX_GAIN,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
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
    if len(frame.data) < 2:
        raise ValueError(
            "Meter response payload too short: expected at least 2 bytes, "
            f"got {len(frame.data)}"
        )
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
_SUB_S_METER_SQL_STATUS = 0x01
_SUB_OVERFLOW_STATUS = 0x07
_SUB_PREAMP_STATUS = 0x02
_SUB_AGC = 0x12
_SUB_AUDIO_PEAK_FILTER = 0x32
_SUB_AUTO_NOTCH = 0x41
_SUB_COMPRESSOR = 0x44
_SUB_MONITOR = 0x45
_SUB_VOX = 0x46
_SUB_BREAK_IN = 0x47
_SUB_MANUAL_NOTCH = 0x48
_SUB_DIGISEL_STATUS = 0x4E
_SUB_TWIN_PEAK_FILTER = 0x4F
_SUB_DIAL_LOCK = 0x50
_SUB_FILTER_SHAPE = 0x56
_SUB_SSB_TX_BANDWIDTH = 0x58
_SUB_NB = 0x22        # Noise Blanker on/off (0x16 0x22)
_SUB_NR = 0x40        # Noise Reduction on/off (0x16 0x40)
_SUB_IP_PLUS = 0x65   # IP+ on/off (0x16 0x65)
_SUB_AGC_TIME_CONSTANT = 0x04


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



def get_nb(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build CI-V command to read NB status (0/1)."""
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NB)


def set_nb(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Set Noise Blanker on/off."""
    data = bytes([0x01 if on else 0x00])
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NB, data=data, receiver=receiver)
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NB, data=data)


def get_nr(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build CI-V command to read NR status (0/1)."""
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NR)


def set_nr(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Set Noise Reduction on/off."""
    data = bytes([0x01 if on else 0x00])
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NR, data=data, receiver=receiver)
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NR, data=data)


def get_ip_plus(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build CI-V command to read IP+ status (0/1)."""
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_IP_PLUS)


def set_ip_plus(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Set IP+ on/off."""
    data = bytes([0x01 if on else 0x00])
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_IP_PLUS, data=data, receiver=receiver)
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_IP_PLUS, data=data)


def get_ref_adjust(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read REF Adjust command."""
    return _build_ctl_mem_get(_CTL_MEM_REF_ADJUST, to_addr=to_addr, from_addr=from_addr)


def set_ref_adjust(
    value: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set REF Adjust command."""
    if not 0 <= value <= 511:
        raise ValueError(f"REF Adjust must be 0-511, got {value}")
    return _build_ctl_mem_set(
        _CTL_MEM_REF_ADJUST,
        value,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=2,
    )


def get_dash_ratio(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Dash Ratio command."""
    return _build_ctl_mem_get(_CTL_MEM_DASH_RATIO, to_addr=to_addr, from_addr=from_addr)


def set_dash_ratio(
    value: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set Dash Ratio command."""
    if not 28 <= value <= 45:
        raise ValueError(f"Dash Ratio must be 28-45, got {value}")
    return _build_ctl_mem_set(
        _CTL_MEM_DASH_RATIO,
        value,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=1,
    )


def get_nb_depth(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read NB Depth command."""
    return _build_ctl_mem_get(_CTL_MEM_NB_DEPTH, to_addr=to_addr, from_addr=from_addr)


def set_nb_depth(
    value: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set NB Depth command."""
    if not 0 <= value <= 9:
        raise ValueError(f"NB Depth must be 0-9, got {value}")
    return _build_ctl_mem_set(
        _CTL_MEM_NB_DEPTH,
        value,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=1,
    )


def get_nb_width(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read NB Width command."""
    return _build_ctl_mem_get(_CTL_MEM_NB_WIDTH, to_addr=to_addr, from_addr=from_addr)


def set_nb_width(
    value: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set NB Width command."""
    if not 0 <= value <= 255:
        raise ValueError(f"NB Width must be 0-255, got {value}")
    return _build_ctl_mem_set(
        _CTL_MEM_NB_WIDTH,
        value,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=2,
    )


def get_af_mute(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read AF Mute command."""
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_AF_MUTE,
        receiver=receiver,
    )


def set_af_mute(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set AF Mute command."""
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_AF_MUTE,
        data=b"\x01" if on else b"\x00",
        receiver=receiver,
    )


def get_s_meter_sql_status(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read S-meter squelch status command."""
    return _build_meter_bool_get(
        _SUB_S_METER_SQL_STATUS,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_overflow_status(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read overflow status command."""
    return _build_meter_bool_get(
        _SUB_OVERFLOW_STATUS,
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_agc(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read AGC mode command."""
    return _build_function_get(_SUB_AGC, to_addr=to_addr, from_addr=from_addr)


def set_agc(
    mode: AgcMode | int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set AGC mode command."""
    return _build_function_value_set(
        _SUB_AGC,
        int(AgcMode(mode)),
        minimum=int(AgcMode.FAST),
        maximum=int(AgcMode.SLOW),
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_audio_peak_filter(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read audio peak filter mode command."""
    return _build_function_get(
        _SUB_AUDIO_PEAK_FILTER,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_audio_peak_filter(
    mode: AudioPeakFilter | int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set audio peak filter mode command."""
    return _build_function_value_set(
        _SUB_AUDIO_PEAK_FILTER,
        int(AudioPeakFilter(mode)),
        minimum=int(AudioPeakFilter.OFF),
        maximum=int(AudioPeakFilter.NAR),
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_auto_notch(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read auto-notch status command."""
    return _build_function_get(
        _SUB_AUTO_NOTCH,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_auto_notch(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set auto-notch status command."""
    return _build_function_bool_set(
        _SUB_AUTO_NOTCH,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_compressor(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read compressor status command."""
    return _build_function_get(_SUB_COMPRESSOR, to_addr=to_addr, from_addr=from_addr)


def set_compressor(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set compressor status command."""
    return _build_function_bool_set(
        _SUB_COMPRESSOR,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_monitor(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read monitor status command."""
    return _build_function_get(_SUB_MONITOR, to_addr=to_addr, from_addr=from_addr)


def set_monitor(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set monitor status command."""
    return _build_function_bool_set(
        _SUB_MONITOR,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_vox(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read VOX status command."""
    return _build_function_get(_SUB_VOX, to_addr=to_addr, from_addr=from_addr)


def set_vox(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set VOX status command."""
    return _build_function_bool_set(_SUB_VOX, on, to_addr=to_addr, from_addr=from_addr)


def get_break_in(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read break-in mode command."""
    return _build_function_get(_SUB_BREAK_IN, to_addr=to_addr, from_addr=from_addr)


def set_break_in(
    mode: BreakInMode | int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set break-in mode command."""
    return _build_function_value_set(
        _SUB_BREAK_IN,
        int(BreakInMode(mode)),
        minimum=int(BreakInMode.OFF),
        maximum=int(BreakInMode.FULL),
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_manual_notch(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read manual-notch status command."""
    return _build_function_get(
        _SUB_MANUAL_NOTCH,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_manual_notch(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set manual-notch status command."""
    return _build_function_bool_set(
        _SUB_MANUAL_NOTCH,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_twin_peak_filter(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read twin-peak-filter status command."""
    return _build_function_get(
        _SUB_TWIN_PEAK_FILTER,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_twin_peak_filter(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set twin-peak-filter status command."""
    return _build_function_bool_set(
        _SUB_TWIN_PEAK_FILTER,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_dial_lock(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read dial-lock status command."""
    return _build_function_get(_SUB_DIAL_LOCK, to_addr=to_addr, from_addr=from_addr)


def set_dial_lock(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set dial-lock status command."""
    return _build_function_bool_set(
        _SUB_DIAL_LOCK,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_filter_shape(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read DSP IF filter shape command."""
    return _build_function_get(
        _SUB_FILTER_SHAPE,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_filter_shape(
    shape: FilterShape | int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set DSP IF filter shape command."""
    return _build_function_value_set(
        _SUB_FILTER_SHAPE,
        int(FilterShape(shape)),
        minimum=int(FilterShape.SHARP),
        maximum=int(FilterShape.SOFT),
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_ssb_tx_bandwidth(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read SSB TX bandwidth preset command."""
    return _build_function_get(
        _SUB_SSB_TX_BANDWIDTH,
        to_addr=to_addr,
        from_addr=from_addr,
    )


def set_ssb_tx_bandwidth(
    bandwidth: SsbTxBandwidth | int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set SSB TX bandwidth preset command."""
    return _build_function_value_set(
        _SUB_SSB_TX_BANDWIDTH,
        int(SsbTxBandwidth(bandwidth)),
        minimum=int(SsbTxBandwidth.WIDE),
        maximum=int(SsbTxBandwidth.NAR),
        to_addr=to_addr,
        from_addr=from_addr,
    )


def get_agc_time_constant(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read AGC time constant command."""
    return _build_ctl_mem_single_bcd_get(
        _SUB_AGC_TIME_CONSTANT,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def set_agc_time_constant(
    value: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a set AGC time constant command."""
    return _build_ctl_mem_single_bcd_set(
        _SUB_AGC_TIME_CONSTANT,
        value,
        minimum=0,
        maximum=13,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


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


# --- Transceiver status family (#136) ---

# Sub-commands for 0x1C (Transceiver status register)
_SUB_TUNER_STATUS = 0x01
_SUB_TX_FREQ_MONITOR = 0x03

# Sub-commands for 0x21 (RIT/XIT register)
_SUB_RIT_FREQ = 0x00
_SUB_RIT_STATUS = 0x01
_SUB_RIT_TX_STATUS = 0x02


def get_band_edge_freq(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read band-edge frequency command (0x02).

    Returns the current band-edge frequency (same BCD encoding as 0x03).
    """
    return build_civ_frame(to_addr, from_addr, _CMD_BAND_EDGE)


def get_various_squelch(
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
) -> bytes:
    """Build a read various-squelch status command (0x15 0x05, Command29)."""
    return _build_meter_bool_get(
        _SUB_VARIOUS_SQUELCH,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
    )


def get_power_meter(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read RF power meter command (0x15 0x11)."""
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_POWER_METER)


def get_comp_meter(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read compressor meter command (0x15 0x14)."""
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_COMP_METER)


def get_vd_meter(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Vd (supply voltage) meter command (0x15 0x15)."""
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_VD_METER)


def get_id_meter(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read Id (drain current) meter command (0x15 0x16)."""
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_ID_METER)


def get_tuner_status(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read tuner/ATU status command (0x1C 0x01).

    Response data: 0x00=off, 0x01=on, 0x02=tuning.
    """
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_TUNER_STATUS)


def set_tuner_status(
    value: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set tuner/ATU status command (0x1C 0x01).

    Args:
        value: 0=off, 1=on, 2=tune.
    """
    if value not in (0, 1, 2):
        raise ValueError(f"Tuner status must be 0, 1, or 2, got {value}")
    return build_civ_frame(
        to_addr, from_addr, _CMD_PTT, sub=_SUB_TUNER_STATUS, data=bytes([value])
    )


def get_tx_freq_monitor(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read TX frequency monitor status command (0x1C 0x03)."""
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_TX_FREQ_MONITOR)


def set_tx_freq_monitor(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set TX frequency monitor command (0x1C 0x03)."""
    return build_civ_frame(
        to_addr, from_addr, _CMD_PTT, sub=_SUB_TX_FREQ_MONITOR,
        data=b"\x01" if on else b"\x00",
    )


def get_rit_frequency(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read RIT frequency offset command (0x21 0x00).

    Response: 2 bytes BCD Hz + 1 byte sign (0x00=positive, 0x01=negative).
    Range: ±9999 Hz.
    """
    return build_civ_frame(to_addr, from_addr, _CMD_RIT, sub=_SUB_RIT_FREQ)


def set_rit_frequency(
    offset_hz: int,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set RIT frequency offset command (0x21 0x00).

    Args:
        offset_hz: RIT offset in Hz (±9999).
    """
    if not -9999 <= offset_hz <= 9999:
        raise ValueError(f"RIT offset must be ±9999 Hz, got {offset_hz}")
    abs_hz = abs(offset_hz)
    # Encode as 2-byte BCD: e.g. 150 → 0x01 0x50
    d0 = ((abs_hz % 100 // 10) << 4) | (abs_hz % 10)
    d1 = ((abs_hz % 10000 // 1000) << 4) | (abs_hz % 1000 // 100)
    sign = b"\x01" if offset_hz < 0 else b"\x00"
    return build_civ_frame(
        to_addr, from_addr, _CMD_RIT, sub=_SUB_RIT_FREQ,
        data=bytes([d0, d1]) + sign,
    )


def parse_rit_frequency_response(data: bytes) -> int:
    """Parse RIT frequency response data (2-byte BCD + sign byte).

    Args:
        data: 3 bytes — BCD Hz (2 bytes LE) + sign (0x00=pos, 0x01=neg).

    Returns:
        Signed RIT offset in Hz.
    """
    if len(data) < 3:
        return 0
    d0, d1, sign = data[0], data[1], data[2]
    hz = (d1 >> 4) * 1000 + (d1 & 0x0F) * 100 + (d0 >> 4) * 10 + (d0 & 0x0F)
    return -hz if sign else hz


def get_rit_status(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read RIT on/off status command (0x21 0x01)."""
    return build_civ_frame(to_addr, from_addr, _CMD_RIT, sub=_SUB_RIT_STATUS)


def set_rit_status(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set RIT on/off command (0x21 0x01)."""
    return build_civ_frame(
        to_addr, from_addr, _CMD_RIT, sub=_SUB_RIT_STATUS,
        data=b"\x01" if on else b"\x00",
    )


def get_rit_tx_status(
    to_addr: int = IC_7610_ADDR, from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a read RIT TX status command (0x21 0x02)."""
    return build_civ_frame(to_addr, from_addr, _CMD_RIT, sub=_SUB_RIT_TX_STATUS)


def set_rit_tx_status(
    on: bool,
    to_addr: int = IC_7610_ADDR,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build a set RIT TX status command (0x21 0x02)."""
    return build_civ_frame(
        to_addr, from_addr, _CMD_RIT, sub=_SUB_RIT_TX_STATUS,
        data=b"\x01" if on else b"\x00",
    )


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
