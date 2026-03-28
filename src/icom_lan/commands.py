"""CI-V command encoding and decoding for Icom transceivers.

CI-V frame format::

    FE FE <to> <from> <cmd> [<sub>] [<data>...] FD

For dual-receiver radios (IC-7610), commands marked Command29=true use::

    FE FE <to> <from> 29 <receiver> <cmd> [<sub>] [<data>...] FD

where ``receiver`` = ``0x00`` (MAIN) or ``0x01`` (SUB).

Reference: wfview icomcommander.cpp, IC-7610.rig
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Callable, Sequence

from .types import (
    AgcMode,
    AudioPeakFilter,
    BreakInMode,
    CivFrame,
    FilterShape,
    Mode,
    ScopeFixedEdge,
    SsbTxBandwidth,
    bcd_decode,
    bcd_encode,
)

if TYPE_CHECKING:
    from .command_map import CommandMap
    from .types import BandStackRegister, MemoryChannel

__all__ = [
    "CONTROLLER_ADDR",
    "RECEIVER_MAIN",
    "RECEIVER_SUB",
    "bcd_decode",
    "build_civ_frame",
    "build_cmd29_frame",
    "bcd_encode_value",
    "filter_hz_to_index",
    "filter_index_to_hz",
    "table_index_to_hz",
    "hz_to_table_index",
    "parse_civ_frame",
    # TOML canonical names (primary)
    "get_freq",
    "set_freq",
    # Backward-compat aliases
    "get_frequency",
    "set_frequency",
    "get_mode",
    "set_mode",
    # TOML canonical names
    "get_rf_power",
    "set_rf_power",
    # Backward-compat aliases
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
    "get_vox_delay",
    "set_vox_delay",
    "get_af_mute",
    "set_af_mute",
    # Squelch (TOML canonical)
    "get_squelch",
    "set_squelch",
    # Backward-compat aliases
    "get_sql",
    "set_sql",
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
    # Manual notch width (TOML canonical)
    "get_manual_notch_width",
    "set_manual_notch_width",
    "get_twin_peak_filter",
    "set_twin_peak_filter",
    "get_dial_lock",
    "set_dial_lock",
    "get_filter_shape",
    "set_filter_shape",
    # Filter width (TOML canonical)
    "get_filter_width",
    "set_filter_width",
    "get_ssb_tx_bandwidth",
    "set_ssb_tx_bandwidth",
    "get_main_sub_tracking",
    "set_main_sub_tracking",
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
    "get_scope_main_sub",
    "scope_main_sub",
    "get_scope_single_dual",
    "scope_single_dual",
    "get_scope_mode",
    "scope_set_mode",
    "get_scope_span",
    "scope_set_span",
    "get_scope_ref",
    "scope_set_ref",
    "get_scope_speed",
    "scope_set_speed",
    "get_scope_edge",
    "scope_set_edge",
    "get_scope_hold",
    "scope_set_hold",
    "get_scope_during_tx",
    "scope_set_during_tx",
    "get_scope_center_type",
    "scope_set_center_type",
    "get_scope_vbw",
    "scope_set_vbw",
    "get_scope_fixed_edge",
    "scope_set_fixed_edge",
    "get_scope_rbw",
    "scope_set_rbw",
    "parse_scope_main_sub_response",
    "parse_scope_single_dual_response",
    "parse_scope_mode_response",
    "parse_scope_span_response",
    "parse_scope_ref_response",
    "parse_scope_speed_response",
    "parse_scope_edge_response",
    "parse_scope_hold_response",
    "parse_scope_during_tx_response",
    "parse_scope_center_type_response",
    "parse_scope_vbw_response",
    "parse_scope_fixed_edge_response",
    "parse_scope_rbw_response",
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
    # VFO (TOML canonical)
    "get_vfo",
    "set_vfo",
    "get_main_sub_band",
    # Backward-compat aliases
    "select_vfo",
    # VFO / Dual Watch / Scanning (#132)
    "get_tuning_step",
    "set_tuning_step",
    # Scanning (TOML canonical)
    "scan_start",
    "scan_stop",
    # Backward-compat aliases
    "start_scan",
    "stop_scan",
    "set_dual_watch_off",
    "set_dual_watch_on",
    "get_dual_watch",
    "set_dual_watch",
    "quick_dual_watch",
    "quick_split",
    # Quick commands (TOML canonical)
    "get_quick_dual_watch",
    "set_quick_dual_watch",
    "get_quick_split",
    "set_quick_split",
    # Speech (TOML canonical)
    "get_speech",
    # Backward-compat alias
    "speech",
    # Tone/TSQL (#134)
    "get_repeater_tone",
    "set_repeater_tone",
    "get_repeater_tsql",
    "set_repeater_tsql",
    "get_tone_freq",
    "set_tone_freq",
    "get_tsql_freq",
    "set_tsql_freq",
    "parse_tone_freq_response",
    "parse_tsql_freq_response",
    # System/Config commands (#135)
    "get_antenna_1",
    "set_antenna_1",
    "get_antenna_2",
    "set_antenna_2",
    "get_rx_antenna_ant1",
    "set_rx_antenna_ant1",
    "get_rx_antenna_ant2",
    "set_rx_antenna_ant2",
    # Antenna aliases (TOML canonical)
    "get_antenna",
    "set_antenna",
    "get_rx_antenna",
    "set_rx_antenna",
    "get_acc1_mod_level",
    "set_acc1_mod_level",
    "get_usb_mod_level",
    "set_usb_mod_level",
    "get_lan_mod_level",
    "set_lan_mod_level",
    "get_data_off_mod_input",
    "set_data_off_mod_input",
    "get_data1_mod_input",
    "set_data1_mod_input",
    "get_data2_mod_input",
    "set_data2_mod_input",
    "get_data3_mod_input",
    "set_data3_mod_input",
    "get_civ_transceive",
    "set_civ_transceive",
    "get_civ_output_ant",
    "set_civ_output_ant",
    "get_system_date",
    "set_system_date",
    "parse_system_date_response",
    "get_system_time",
    "set_system_time",
    "parse_system_time_response",
    "get_utc_offset",
    "set_utc_offset",
    "parse_utc_offset_response",
    # Band stacking (TOML canonical)
    "get_bsr",
    "set_bsr",
    # Backward-compat aliases
    "build_band_stack_get",
    "build_band_stack_set",
]

# CI-V addresses
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
_CMD_RIT = 0x21  # RIT/XIT
_CMD_TONE = 0x1B  # Tone/TSQL frequency
_CMD_MEMORY_MODE = 0x08  # Memory mode (select channel)
_CMD_MEMORY_WRITE = 0x09  # Memory write
_CMD_MEMORY_TO_VFO = 0x0A  # Memory to VFO
_CMD_MEMORY_CLEAR = 0x0B  # Memory clear
_CMD_ACK = 0xFB
_CMD_NAK = 0xFA

# Sub-commands
_SUB_AF_LEVEL = 0x01  # AF output level (0x14 0x01)
_SUB_RF_GAIN = 0x02  # RF Gain level (0x14 0x02)
_SUB_SQL = 0x03  # Squelch level (0x14 0x03)
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
_SUB_VARIOUS_SQUELCH = 0x05  # Various squelch (cmd29)
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

_CMD_ANTENNA = 0x12
_SUB_ANT1 = 0x00
_SUB_ANT2 = 0x01
_SUB_RX_ANT_ANT1 = 0x12
_SUB_RX_ANT_ANT2 = 0x13

_SUB_ACC1_MOD_LEVEL = 0x0B
_SUB_USB_MOD_LEVEL = 0x10
_SUB_LAN_MOD_LEVEL = 0x11

_CTL_MEM_REF_ADJUST = b"\x00\x70"
_CTL_MEM_DASH_RATIO = b"\x02\x28"
_CTL_MEM_NB_DEPTH = b"\x02\x90"
_CTL_MEM_NB_WIDTH = b"\x02\x91"
_CTL_MEM_VOX_DELAY = b"\x02\x92"
_CTL_MEM_DATA_OFF_MOD_INPUT = b"\x00\x91"
_CTL_MEM_DATA1_MOD_INPUT = b"\x00\x92"
_CTL_MEM_DATA2_MOD_INPUT = b"\x00\x93"
_CTL_MEM_DATA3_MOD_INPUT = b"\x00\x94"
_CTL_MEM_CIV_TRANSCEIVE = b"\x01\x29"
_CTL_MEM_CIV_OUTPUT_ANT = b"\x01\x30"
_CTL_MEM_SYSTEM_DATE = b"\x01\x58"
_CTL_MEM_SYSTEM_TIME = b"\x01\x59"
_CTL_MEM_UTC_OFFSET = b"\x01\x62"

# CI-V frame markers
_PREAMBLE = b"\xfe\xfe"
_TERMINATOR = b"\xfd"

# Commands that use sub-commands (for parse disambiguation)
_COMMANDS_WITH_SUB: set[int] = {
    _CMD_LEVEL,
    _CMD_METER,
    _CMD_PTT,
    _CMD_CTL_MEM,
    _CMD_RIT,
    0x27,
    0x16,
    _CMD_TONE,
    _CMD_ANTENNA,
    0x19,
}


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


def _build_from_map(
    cmd_map: CommandMap,
    name: str,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    data: bytes | None = None,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
) -> bytes:
    """Build a CI-V frame using wire bytes from a CommandMap.

    Wire bytes may have 1–N elements.  The first byte is the CI-V command,
    the second (if present) is the sub-command, and any remaining bytes are
    prepended to *data* as extended sub-command addressing (e.g. 0x1A 0x05
    0x00 0x64 for IC-7300 ACC1 mod level).
    """
    wire = cmd_map.get(name)
    command = wire[0]
    sub = wire[1] if len(wire) > 1 else None
    # Extra wire bytes beyond command+sub become a data prefix
    if len(wire) > 2:
        extra = bytes(wire[2:])
        data = extra + data if data else extra
    if command29:
        return build_cmd29_frame(
            to_addr, from_addr, command, sub=sub, data=data, receiver=receiver
        )
    return build_civ_frame(to_addr, from_addr, command, sub=sub, data=data)


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


def get_freq(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get frequency' CI-V command.

    Args:
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        CI-V frame bytes.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_freq", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_FREQ_GET)


def set_freq(
    freq_hz: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
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
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_freq",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bcd_encode(freq_hz),
            receiver=receiver,
            command29=(receiver != RECEIVER_MAIN),
        )
    bcd = bcd_encode(freq_hz)
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(
            to_addr, from_addr, _CMD_FREQ_SET, data=bcd, receiver=receiver
        )
    return build_civ_frame(to_addr, from_addr, _CMD_FREQ_SET, data=bcd)


def parse_frequency_response(frame: CivFrame) -> int:
    """Parse a frequency response frame.

    Args:
        frame: Parsed CivFrame (command 0x02/0x03/0x00 with 5-byte BCD data).

    Returns:
        Frequency in Hz.

    Raises:
        ValueError: If frame is not a frequency response.
    """
    if frame.command not in (_CMD_BAND_EDGE, _CMD_FREQ_GET, 0x00):
        raise ValueError(f"Not a frequency response: command 0x{frame.command:02x}")
    return bcd_decode(frame.data)


# --- Mode commands ---


def get_mode(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get mode' CI-V command."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_mode", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_MODE_GET)


def set_mode(
    mode: Mode,
    filter_width: int | None = None,
    *,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
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
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_mode",
            to_addr=to_addr,
            from_addr=from_addr,
            data=data,
            command29=receiver != RECEIVER_MAIN,
            receiver=receiver,
        )
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(
            to_addr, from_addr, _CMD_MODE_SET, data=data, receiver=receiver
        )
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


def bcd_encode_value(value: int, *, byte_count: int) -> bytes:
    """Encode an integer as packed BCD using a fixed byte width."""
    if value < 0:
        raise ValueError(f"BCD value must be non-negative, got {value}")
    digits = byte_count * 2
    maximum = (10**digits) - 1
    if value > maximum:
        raise ValueError(f"BCD value must fit in {byte_count} byte(s), got {value}")
    text = f"{value:0{digits}d}"
    return bytes(
        (int(text[index]) << 4) | int(text[index + 1])
        for index in range(0, len(text), 2)
    )


def _segment_value(segment: Any, key: str) -> int:
    if isinstance(segment, dict):
        return int(segment[key])
    return int(getattr(segment, key))


def filter_hz_to_index(hz: int, *, segments: Sequence[Any]) -> int:
    """Convert a filter width in Hz to a CI-V index using profile segments."""
    for segment in segments:
        hz_min = _segment_value(segment, "hz_min")
        hz_max = _segment_value(segment, "hz_max")
        step_hz = _segment_value(segment, "step_hz")
        index_min = _segment_value(segment, "index_min")
        if hz_min <= hz <= hz_max:
            delta = hz - hz_min
            if delta % step_hz != 0:
                raise ValueError(
                    f"Filter width {hz} is not aligned to {step_hz} Hz steps"
                )
            return index_min + (delta // step_hz)
    raise ValueError(f"Filter width {hz} is outside the configured segments")


def filter_index_to_hz(index: int, *, segments: Sequence[Any]) -> int:
    """Convert a CI-V filter-width index to Hz using profile segments."""
    ordered = sorted(segments, key=lambda segment: _segment_value(segment, "index_min"))
    for offset, segment in enumerate(ordered):
        hz_min = _segment_value(segment, "hz_min")
        hz_max = _segment_value(segment, "hz_max")
        step_hz = _segment_value(segment, "step_hz")
        index_min = _segment_value(segment, "index_min")
        step_count = ((hz_max - hz_min) // step_hz) + 1
        next_index = (
            _segment_value(ordered[offset + 1], "index_min")
            if offset + 1 < len(ordered)
            else index_min + step_count
        )
        if index_min <= index < next_index:
            return hz_min + ((index - index_min) * step_hz)
    raise ValueError(f"Filter width index {index} is outside the configured segments")


def table_index_to_hz(index: int, *, table: Sequence[int]) -> int:
    """Convert a table-based filter-width index to Hz.

    Used by rigs like FTX-1 where a 2-digit code maps directly to a
    position in a mode-dependent lookup table.
    """
    if not (0 <= index < len(table)):
        raise ValueError(
            f"Filter width index {index} is outside the table (0–{len(table) - 1})"
        )
    return table[index]


def hz_to_table_index(hz: int, *, table: Sequence[int]) -> int:
    """Convert Hz to the closest table-based filter-width index.

    Returns the index whose table entry is closest to *hz*.
    """
    if not table:
        raise ValueError("Filter width table is empty")
    best_idx = 0
    best_diff = abs(table[0] - hz)
    for idx, entry in enumerate(table):
        diff = abs(entry - hz)
        if diff < best_diff:
            best_diff = diff
            best_idx = idx
    return best_idx


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
        data = data[len(prefix) :]
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
        data = data[len(prefix) :]
    if not data:
        raise ValueError("Boolean response has no payload byte")
    return data[0] != 0x00


def _build_level_get(
    sub: int,
    *,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
    cmd_map: CommandMap | None = None,
    cmd_name: str | None = None,
) -> bytes:
    if cmd_map is not None and cmd_name is not None:
        return _build_from_map(
            cmd_map,
            cmd_name,
            to_addr=to_addr,
            from_addr=from_addr,
            receiver=receiver,
            command29=command29,
        )
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
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
    encoder: Callable[[int], bytes] = _level_bcd_encode,
    cmd_map: CommandMap | None = None,
    cmd_name: str | None = None,
) -> bytes:
    payload = encoder(value)
    if cmd_map is not None and cmd_name is not None:
        return _build_from_map(
            cmd_map,
            cmd_name,
            to_addr=to_addr,
            from_addr=from_addr,
            data=payload,
            receiver=receiver,
            command29=command29,
        )
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
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    cmd_name: str | None = None,
) -> bytes:
    if cmd_map is not None and cmd_name is not None:
        # When using cmd_map, wire bytes already include the full command structure
        # including any data prefix, so don't pass prefix as data
        return _build_from_map(
            cmd_map, cmd_name, to_addr=to_addr, from_addr=from_addr, data=None
        )
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
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    byte_count: int,
    cmd_map: CommandMap | None = None,
    cmd_name: str | None = None,
) -> bytes:
    data = prefix + bcd_encode_value(value, byte_count=byte_count)
    if cmd_map is not None and cmd_name is not None:
        return _build_from_map(
            cmd_map, cmd_name, to_addr=to_addr, from_addr=from_addr, data=data
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_CTL_MEM,
        data=prefix + bcd_encode_value(value, byte_count=byte_count),
    )


def _build_meter_bool_get(
    sub: int,
    *,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
    cmd_map: CommandMap | None = None,
    cmd_name: str | None = None,
) -> bytes:
    if cmd_map is not None and cmd_name is not None:
        return _build_from_map(
            cmd_map,
            cmd_name,
            to_addr=to_addr,
            from_addr=from_addr,
            receiver=receiver,
            command29=command29,
        )
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
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
    cmd_map: CommandMap | None = None,
    cmd_name: str | None = None,
) -> bytes:
    if cmd_map is not None and cmd_name is not None:
        return _build_from_map(
            cmd_map,
            cmd_name,
            to_addr=to_addr,
            from_addr=from_addr,
            receiver=receiver,
            command29=command29,
        )
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
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
    cmd_map: CommandMap | None = None,
    cmd_name: str | None = None,
) -> bytes:
    payload = b"\x01" if on else b"\x00"
    if cmd_map is not None and cmd_name is not None:
        return _build_from_map(
            cmd_map,
            cmd_name,
            to_addr=to_addr,
            from_addr=from_addr,
            data=payload,
            receiver=receiver,
            command29=command29,
        )
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
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
    cmd_map: CommandMap | None = None,
    cmd_name: str | None = None,
) -> bytes:
    if not minimum <= value <= maximum:
        raise ValueError(f"Value must be {minimum}-{maximum}, got {value}")
    payload = bytes([_bcd_byte(value)])
    if cmd_map is not None and cmd_name is not None:
        return _build_from_map(
            cmd_map,
            cmd_name,
            to_addr=to_addr,
            from_addr=from_addr,
            data=payload,
            receiver=receiver,
            command29=command29,
        )
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
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
    cmd_map: CommandMap | None = None,
    cmd_name: str | None = None,
) -> bytes:
    if cmd_map is not None and cmd_name is not None:
        return _build_from_map(
            cmd_map,
            cmd_name,
            to_addr=to_addr,
            from_addr=from_addr,
            receiver=receiver,
            command29=command29,
        )
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
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    command29: bool = False,
    cmd_map: CommandMap | None = None,
    cmd_name: str | None = None,
) -> bytes:
    if not minimum <= value <= maximum:
        raise ValueError(f"Value must be {minimum}-{maximum}, got {value}")
    payload = bytes([_bcd_byte(value)])
    if cmd_map is not None and cmd_name is not None:
        return _build_from_map(
            cmd_map,
            cmd_name,
            to_addr=to_addr,
            from_addr=from_addr,
            data=payload,
            receiver=receiver,
            command29=command29,
        )
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


def get_rf_power(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get RF power' CI-V command."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_rf_power", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_RF_POWER)


def set_rf_power(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'set RF power' CI-V command.

    Args:
        level: Power level 0-255 (radio maps to actual watts).
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        CI-V frame bytes.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_rf_power",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_level_bcd_encode(level),
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_LEVEL, sub=_SUB_RF_POWER, data=_level_bcd_encode(level)
    )


def get_rf_gain(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'read RF gain' CI-V command (0x14 0x02)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_rf_gain", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_RF_GAIN)


def set_rf_gain(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'set RF gain' CI-V command.

    Args:
        level: Gain level 0-255 (0=min, 255=max).
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_rf_gain",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_level_bcd_encode(level),
            receiver=receiver,
            command29=(receiver != RECEIVER_MAIN),
        )
    bcd = _level_bcd_encode(level)
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_LEVEL,
            sub=_SUB_RF_GAIN,
            data=bcd,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_RF_GAIN, data=bcd)


def get_af_level(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'read AF output level' CI-V command (0x14 0x01)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_af_level", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_AF_LEVEL)


def set_af_level(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'set AF output level' CI-V command.

    Args:
        level: AF level 0-255 (0=min, 255=max).
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_af_level",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_level_bcd_encode(level),
            receiver=receiver,
            command29=(receiver != RECEIVER_MAIN),
        )
    bcd = _level_bcd_encode(level)
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_LEVEL,
            sub=_SUB_AF_LEVEL,
            data=bcd,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_AF_LEVEL, data=bcd)


def get_squelch(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get squelch level' CI-V command (0x14 0x03)."""
    return _build_level_get(
        _SUB_SQL,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=(receiver != RECEIVER_MAIN),
        cmd_map=cmd_map,
        cmd_name="get_squelch",
    )


def set_squelch(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'set squelch level' CI-V command.

    Args:
        level: Squelch level 0-255 (0=open, 255=closed).
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_squelch",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_level_bcd_encode(level),
            receiver=receiver,
            command29=(receiver != RECEIVER_MAIN),
        )
    bcd = _level_bcd_encode(level)
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(
            to_addr, from_addr, _CMD_LEVEL, sub=_SUB_SQL, data=bcd, receiver=receiver
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_SQL, data=bcd)


def get_apf_type_level(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read APF Type Level command."""
    return _build_level_get(
        _SUB_APF_TYPE_LEVEL,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_apf_type_level",
    )


def set_apf_type_level(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set APF Type Level command."""
    return _build_level_set(
        _SUB_APF_TYPE_LEVEL,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_apf_type_level",
    )


def get_nr_level(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read NR Level command."""
    return _build_level_get(
        _SUB_NR_LEVEL,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_nr_level",
    )


def set_nr_level(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set NR Level command."""
    return _build_level_set(
        _SUB_NR_LEVEL,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_nr_level",
    )


def get_pbt_inner(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read PBT Inner command."""
    return _build_level_get(
        _SUB_PBT_INNER,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_pbt_inner",
    )


def set_pbt_inner(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set PBT Inner command."""
    return _build_level_set(
        _SUB_PBT_INNER,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_pbt_inner",
    )


def get_pbt_outer(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read PBT Outer command."""
    return _build_level_get(
        _SUB_PBT_OUTER,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_pbt_outer",
    )


def set_pbt_outer(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set PBT Outer command."""
    return _build_level_set(
        _SUB_PBT_OUTER,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_pbt_outer",
    )


def get_cw_pitch(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read CW Pitch command."""
    return _build_level_get(
        _SUB_CW_PITCH,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_cw_pitch",
    )


def set_cw_pitch(
    pitch_hz: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set CW Pitch command."""
    return _build_level_set(
        _SUB_CW_PITCH,
        _cw_pitch_to_level(pitch_hz),
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_cw_pitch",
    )


def get_mic_gain(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Mic Gain command."""
    return _build_level_get(
        _SUB_MIC_GAIN,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_mic_gain",
    )


def set_mic_gain(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set Mic Gain command."""
    return _build_level_set(
        _SUB_MIC_GAIN,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_mic_gain",
    )


def get_key_speed(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Key Speed command."""
    return _build_level_get(
        _SUB_KEY_SPEED,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_key_speed",
    )


def set_key_speed(
    wpm: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set Key Speed command."""
    return _build_level_set(
        _SUB_KEY_SPEED,
        _key_speed_to_level(wpm),
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_key_speed",
    )


def get_notch_filter(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Notch Filter level command."""
    return _build_level_get(
        _SUB_NOTCH_FILTER,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_notch_filter",
    )


def set_notch_filter(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set Notch Filter level command."""
    return _build_level_set(
        _SUB_NOTCH_FILTER,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_notch_filter",
    )


def get_compressor_level(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Compressor Level command."""
    return _build_level_get(
        _SUB_COMPRESSOR_LEVEL,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_compressor_level",
    )


def set_compressor_level(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set Compressor Level command."""
    return _build_level_set(
        _SUB_COMPRESSOR_LEVEL,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_compressor_level",
    )


def get_break_in_delay(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Break-In Delay command."""
    return _build_level_get(
        _SUB_BREAK_IN_DELAY,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_break_in_delay",
    )


def set_break_in_delay(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set Break-In Delay command."""
    return _build_level_set(
        _SUB_BREAK_IN_DELAY,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_break_in_delay",
    )


def get_nb_level(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read NB Level command."""
    return _build_level_get(
        _SUB_NB_LEVEL,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_nb_level",
    )


def set_nb_level(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set NB Level command."""
    return _build_level_set(
        _SUB_NB_LEVEL,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_nb_level",
    )


def get_digisel_shift(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read DIGI-SEL Shift command."""
    return _build_level_get(
        _SUB_DIGISEL_SHIFT,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_digisel_shift",
    )


def set_digisel_shift(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set DIGI-SEL Shift command."""
    return _build_level_set(
        _SUB_DIGISEL_SHIFT,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_digisel_shift",
    )


def get_drive_gain(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Drive Gain command."""
    return _build_level_get(
        _SUB_DRIVE_GAIN,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_drive_gain",
    )


def set_drive_gain(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set Drive Gain command."""
    return _build_level_set(
        _SUB_DRIVE_GAIN,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_drive_gain",
    )


def get_monitor_gain(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Monitor Gain command."""
    return _build_level_get(
        _SUB_MONITOR_GAIN,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_monitor_gain",
    )


def set_monitor_gain(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set Monitor Gain command."""
    return _build_level_set(
        _SUB_MONITOR_GAIN,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_monitor_gain",
    )


def get_vox_gain(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Vox Gain command."""
    return _build_level_get(
        _SUB_VOX_GAIN,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_vox_gain",
    )


def set_vox_gain(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set Vox Gain command."""
    return _build_level_set(
        _SUB_VOX_GAIN,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_vox_gain",
    )


def get_anti_vox_gain(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Anti-Vox Gain command."""
    return _build_level_get(
        _SUB_ANTI_VOX_GAIN,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_anti_vox_gain",
    )


def set_anti_vox_gain(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set Anti-Vox Gain command."""
    return _build_level_set(
        _SUB_ANTI_VOX_GAIN,
        level,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_anti_vox_gain",
    )


# --- Meter commands ---


def get_s_meter(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'read S-meter' CI-V command."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_s_meter", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_S_METER)


def get_swr(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'read SWR meter' CI-V command."""
    if cmd_map is not None:
        return _build_from_map(cmd_map, "get_swr", to_addr=to_addr, from_addr=from_addr)
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_SWR_METER)


def get_alc(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'read ALC meter' CI-V command."""
    if cmd_map is not None:
        return _build_from_map(cmd_map, "get_alc", to_addr=to_addr, from_addr=from_addr)
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


def ptt_on(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a PTT-on CI-V command."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "ptt_on", to_addr=to_addr, from_addr=from_addr, data=b"\x01"
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_PTT, data=b"\x01")


def ptt_off(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a PTT-off CI-V command."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "ptt_off", to_addr=to_addr, from_addr=from_addr, data=b"\x00"
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_PTT, data=b"\x00")


# --- VFO commands ---

_CMD_VFO_SELECT = 0x07
_CMD_VFO_EQUAL = 0x07
_CMD_SPLIT = 0x0F
_CMD_SCAN = 0x0E
_CMD_TUNING_STEP = 0x10
_VFO_DUAL_WATCH_OFF = 0xC0
_VFO_DUAL_WATCH_ON = 0xC1
_VFO_DUAL_WATCH_QUERY = 0xC2
_CTL_MEM_QUICK_DUAL_WATCH = b"\x00\x32"
_CTL_MEM_QUICK_SPLIT = b"\x00\x33"
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
_SUB_MANUAL_NOTCH_WIDTH = 0x57  # Manual notch width (0x16 0x57)
_SUB_DIGISEL_STATUS = 0x4E
_SUB_TWIN_PEAK_FILTER = 0x4F
_SUB_DIAL_LOCK = 0x50
_SUB_FILTER_SHAPE = 0x56
_SUB_FILTER_WIDTH = 0x03  # Filter width (0x1A 0x03, cmd29)
_SUB_SSB_TX_BANDWIDTH = 0x58
_SUB_NB = 0x22  # Noise Blanker on/off (0x16 0x22)
_SUB_NR = 0x40  # Noise Reduction on/off (0x16 0x40)
_SUB_IP_PLUS = 0x65  # IP+ on/off (0x16 0x65)
_SUB_MAIN_SUB_TRACKING = 0x5E  # Main/Sub Tracking on/off (0x16 0x5E)
_SUB_REPEATER_TONE = 0x42  # Repeater Tone on/off (0x16 0x42)
_SUB_REPEATER_TSQL = 0x43  # Repeater TSQL on/off (0x16 0x43)
# 0x1B subcodes (tone frequencies)
_SUB_TONE_FREQ = 0x00  # CTCSS Tone frequency (0x1B 0x00)
_SUB_TSQL_FREQ = 0x01  # TSQL frequency (0x1B 0x01)
_SUB_MEMORY_CONTENTS = 0x00  # Memory contents (0x1A 0x00)
_SUB_BAND_STACK = 0x01  # Band stacking register (0x1A 0x01)
_SUB_AGC_TIME_CONSTANT = 0x04


def get_vfo(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get VFO' CI-V command (0x07 read back current VFO)."""
    if cmd_map is not None:
        return _build_from_map(cmd_map, "get_vfo", to_addr=to_addr, from_addr=from_addr)
    return build_civ_frame(to_addr, from_addr, _CMD_VFO_SELECT)


def get_main_sub_band(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get main/sub band' CI-V command (0x07 0xD2).

    Returns:
        CI-V frame bytes. Response data: 0=MAIN, 1=SUB.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_main_sub_band",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\xd2",
        )
    return build_civ_frame(to_addr, from_addr, _CMD_VFO_SELECT, data=b"\xd2")


def set_vfo(
    vfo: str = "A",
    *,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Select VFO.

    Args:
        vfo: "A", "B", "MAIN", or "SUB".
              IC-7610 uses MAIN/SUB (0xD0/0xD1).
              Simpler radios use A/B (0x00/0x01).
    """
    codes = {"A": 0x00, "B": 0x01, "MAIN": 0xD0, "SUB": 0xD1}
    code = codes.get(vfo.upper(), 0x00)
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "set_vfo", to_addr=to_addr, from_addr=from_addr, data=bytes([code])
        )
    return build_civ_frame(to_addr, from_addr, _CMD_VFO_SELECT, data=bytes([code]))


def vfo_a_equals_b(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Copy VFO A to VFO B (A=B)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "set_vfo", to_addr=to_addr, from_addr=from_addr, data=b"\xa0"
        )
    return build_civ_frame(to_addr, from_addr, _CMD_VFO_EQUAL, data=b"\xa0")


def vfo_swap(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Swap VFO A and B."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "set_vfo", to_addr=to_addr, from_addr=from_addr, data=b"\xb0"
        )
    return build_civ_frame(to_addr, from_addr, _CMD_VFO_EQUAL, data=b"\xb0")


def set_split(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Enable or disable split mode."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_split",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x01" if on else b"\x00",
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_SPLIT, data=b"\x01" if on else b"\x00"
    )


def get_tuning_step(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to get tuning step (0x10).

    Returns:
        CI-V frame bytes.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_tuning_step", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_TUNING_STEP)


def set_tuning_step(
    step: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to set tuning step (0x10).

    Args:
        step: Tuning step index (0-8), BCD-encoded (as per wfview bcdEncodeChar).

    Returns:
        CI-V frame bytes.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_tuning_step",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_bcd_byte(step)]),
        )
    if not 0 <= step <= 8:
        raise ValueError(f"Tuning step must be 0-8, got {step}")
    return build_civ_frame(
        to_addr, from_addr, _CMD_TUNING_STEP, data=bytes([_bcd_byte(step)])
    )


def scan_start(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to start scanning (0x0E 0x01)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "scan_start", to_addr=to_addr, from_addr=from_addr, data=b"\x01"
        )
    return build_civ_frame(to_addr, from_addr, _CMD_SCAN, data=b"\x01")


def scan_stop(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to stop scanning (0x0E 0x00)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "scan_stop", to_addr=to_addr, from_addr=from_addr, data=b"\x00"
        )
    return build_civ_frame(to_addr, from_addr, _CMD_SCAN, data=b"\x00")


def set_dual_watch_off(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to turn off dual watch (0x07 0xC0)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_dual_watch",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_VFO_DUAL_WATCH_OFF]),
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_VFO_SELECT, data=bytes([_VFO_DUAL_WATCH_OFF])
    )


def set_dual_watch_on(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to turn on dual watch (0x07 0xC1)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_dual_watch",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_VFO_DUAL_WATCH_ON]),
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_VFO_SELECT, data=bytes([_VFO_DUAL_WATCH_ON])
    )


def get_dual_watch(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to query dual watch status (0x07 0xC2)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_dual_watch",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_VFO_DUAL_WATCH_QUERY]),
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_VFO_SELECT, data=bytes([_VFO_DUAL_WATCH_QUERY])
    )


def set_dual_watch(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to enable or disable dual watch.

    Args:
        on: True to enable dual watch, False to disable.

    Returns:
        CI-V frame bytes.
    """
    return (
        set_dual_watch_on(to_addr=to_addr, from_addr=from_addr, cmd_map=cmd_map)
        if on
        else set_dual_watch_off(to_addr=to_addr, from_addr=from_addr, cmd_map=cmd_map)
    )


def quick_dual_watch(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command for one-shot dual watch trigger (0x1A 0x05 0x00 0x32)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "quick_dual_watch",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_CTL_MEM_QUICK_DUAL_WATCH,
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_CTL_MEM,
        data=_CTL_MEM_QUICK_DUAL_WATCH,
    )


def quick_split(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command for one-shot split trigger (0x1A 0x05 0x00 0x33)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "quick_split",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_CTL_MEM_QUICK_SPLIT,
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_CTL_MEM, data=_CTL_MEM_QUICK_SPLIT
    )


# Aliases for TOML canonical names (get_/set_ prefix convention)
def get_quick_split(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Alias for quick_split — trigger quick split (0x1A 0x05 0x00 0x33)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_quick_split",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_CTL_MEM_QUICK_SPLIT,
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_CTL_MEM, data=_CTL_MEM_QUICK_SPLIT
    )


def set_quick_split(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Alias for quick_split — trigger quick split (0x1A 0x05 0x00 0x33)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_quick_split",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_CTL_MEM_QUICK_SPLIT,
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_CTL_MEM, data=_CTL_MEM_QUICK_SPLIT
    )


def get_quick_dual_watch(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Alias for quick_dual_watch — trigger quick dual watch (0x1A 0x05 0x00 0x32)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_quick_dual_watch",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_CTL_MEM_QUICK_DUAL_WATCH,
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_CTL_MEM,
        data=_CTL_MEM_QUICK_DUAL_WATCH,
    )


def set_quick_dual_watch(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Alias for quick_dual_watch — trigger quick dual watch (0x1A 0x05 0x00 0x32)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_quick_dual_watch",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_CTL_MEM_QUICK_DUAL_WATCH,
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_CTL_MEM,
        data=_CTL_MEM_QUICK_DUAL_WATCH,
    )


def _bcd_byte(value: int) -> int:
    """Encode 0-99 integer into one BCD byte."""
    if not 0 <= value <= 99:
        raise ValueError(f"BCD byte value must be 0-99, got {value}")
    return ((value // 10) << 4) | (value % 10)


def get_attenuator(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to read attenuator level (Command29-aware)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_attenuator",
            to_addr=to_addr,
            from_addr=from_addr,
            receiver=receiver,
            command29=True,
        )
    return build_cmd29_frame(to_addr, from_addr, _CMD_ATT, receiver=receiver)


def set_attenuator_level(
    db: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Set attenuator level in dB (IC-7610 supports 0..45 in 3 dB steps).

    Uses Command29 framing for dual-receiver compatibility.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_attenuator",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_bcd_byte(db)]),
            receiver=receiver,
            command29=True,
        )
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_ATT,
        data=bytes([_bcd_byte(db)]),
        receiver=receiver,
    )


def set_attenuator(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
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
        cmd_map=cmd_map,
    )


def get_preamp(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to read preamp status (Command29-aware)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_preamp",
            to_addr=to_addr,
            from_addr=from_addr,
            receiver=receiver,
            command29=True,
        )
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_PREAMP,
        sub=_SUB_PREAMP_STATUS,
        receiver=receiver,
    )


def set_preamp(
    level: int = 1,
    *,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Set preamp level (0=off, 1=PREAMP1, 2=PREAMP2).

    Uses Command29 framing for dual-receiver compatibility.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_preamp",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_bcd_byte(level)]),
            receiver=receiver,
            command29=True,
        )
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_PREAMP,
        sub=_SUB_PREAMP_STATUS,
        data=bytes([_bcd_byte(level)]),
        receiver=receiver,
    )


def get_digisel(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to read DIGI-SEL status (0/1) (Command29-aware)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_digisel",
            to_addr=to_addr,
            from_addr=from_addr,
            receiver=receiver,
            command29=True,
        )
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_PREAMP,
        sub=_SUB_DIGISEL_STATUS,
        receiver=receiver,
    )


def set_digisel(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Set DIGI-SEL status (0/1) (Command29-aware)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_digisel",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_bcd_byte(1 if on else 0)]),
            receiver=receiver,
            command29=True,
        )
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
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to read NB status (0/1)."""
    if cmd_map is not None:
        return _build_from_map(cmd_map, "get_nb", to_addr=to_addr, from_addr=from_addr)
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NB)


def set_nb(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Set Noise Blanker on/off."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_nb",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([0x01 if on else 0x00]),
            receiver=receiver,
            command29=(receiver != RECEIVER_MAIN),
        )
    data = bytes([0x01 if on else 0x00])
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(
            to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NB, data=data, receiver=receiver
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NB, data=data)


def get_nr(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to read NR status (0/1)."""
    if cmd_map is not None:
        return _build_from_map(cmd_map, "get_nr", to_addr=to_addr, from_addr=from_addr)
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NR)


def set_nr(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Set Noise Reduction on/off."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_nr",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([0x01 if on else 0x00]),
            receiver=receiver,
            command29=(receiver != RECEIVER_MAIN),
        )
    data = bytes([0x01 if on else 0x00])
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(
            to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NR, data=data, receiver=receiver
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_NR, data=data)


def get_ip_plus(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to read IP+ status (0/1)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_ip_plus", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_IP_PLUS)


def set_ip_plus(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Set IP+ on/off."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_ip_plus",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([0x01 if on else 0x00]),
            receiver=receiver,
            command29=(receiver != RECEIVER_MAIN),
        )
    data = bytes([0x01 if on else 0x00])
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_PREAMP,
            sub=_SUB_IP_PLUS,
            data=data,
            receiver=receiver,
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PREAMP, sub=_SUB_IP_PLUS, data=data)


def get_ref_adjust(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read REF Adjust command."""
    return _build_ctl_mem_get(
        _CTL_MEM_REF_ADJUST,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_ref_adjust",
    )


def set_ref_adjust(
    value: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
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
        cmd_map=cmd_map,
        cmd_name="set_ref_adjust",
    )


def get_dash_ratio(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Dash Ratio command."""
    return _build_ctl_mem_get(
        _CTL_MEM_DASH_RATIO,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_dash_ratio",
    )


def set_dash_ratio(
    value: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
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
        cmd_map=cmd_map,
        cmd_name="set_dash_ratio",
    )


def get_nb_depth(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read NB Depth command."""
    return _build_ctl_mem_get(
        _CTL_MEM_NB_DEPTH,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_nb_depth",
    )


def set_nb_depth(
    value: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
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
        cmd_map=cmd_map,
        cmd_name="set_nb_depth",
    )


def get_nb_width(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read NB Width command."""
    return _build_ctl_mem_get(
        _CTL_MEM_NB_WIDTH,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_nb_width",
    )


def set_nb_width(
    value: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
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
        cmd_map=cmd_map,
        cmd_name="set_nb_width",
    )


def get_vox_delay(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read VOX Delay command (0x1A 0x05 0x02 0x92).

    Returns:
        CI-V frame bytes. Response value: 0-20 (0.0-2.0 sec in 0.1s steps).
    """
    return _build_ctl_mem_get(
        _CTL_MEM_VOX_DELAY,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_vox_delay",
    )


def set_vox_delay(
    value: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set VOX Delay command (0x1A 0x05 0x02 0x92).

    Args:
        value: Delay value 0-20 (0.0-2.0 sec in 0.1s steps).
    """
    if not 0 <= value <= 20:
        raise ValueError(f"VOX Delay must be 0-20, got {value}")
    return _build_ctl_mem_set(
        _CTL_MEM_VOX_DELAY,
        value,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=1,
        cmd_map=cmd_map,
        cmd_name="set_vox_delay",
    )


def get_af_mute(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read AF Mute command."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_af_mute",
            to_addr=to_addr,
            from_addr=from_addr,
            receiver=receiver,
            command29=True,
        )
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_AF_MUTE,
        receiver=receiver,
    )


def set_af_mute(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set AF Mute command."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_af_mute",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x01" if on else b"\x00",
            receiver=receiver,
            command29=True,
        )
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_AF_MUTE,
        data=b"\x01" if on else b"\x00",
        receiver=receiver,
    )


def get_s_meter_sql_status(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read S-meter squelch status command."""
    return _build_meter_bool_get(
        _SUB_S_METER_SQL_STATUS,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_s_meter_sql_status",
    )


def get_overflow_status(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read overflow status command."""
    return _build_meter_bool_get(
        _SUB_OVERFLOW_STATUS,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_overflow_status",
    )


def get_agc(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read AGC mode command."""
    return _build_function_get(
        _SUB_AGC,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=receiver != RECEIVER_MAIN,
        cmd_map=cmd_map,
        cmd_name="get_agc",
    )


def set_agc(
    mode: AgcMode | int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set AGC mode command."""
    return _build_function_value_set(
        _SUB_AGC,
        int(AgcMode(mode)),
        minimum=int(AgcMode.FAST),
        maximum=int(AgcMode.SLOW),
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=receiver != RECEIVER_MAIN,
        cmd_map=cmd_map,
        cmd_name="set_agc",
    )


def get_audio_peak_filter(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read audio peak filter mode command."""
    return _build_function_get(
        _SUB_AUDIO_PEAK_FILTER,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_audio_peak_filter",
    )


def set_audio_peak_filter(
    mode: AudioPeakFilter | int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
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
        cmd_map=cmd_map,
        cmd_name="set_audio_peak_filter",
    )


def get_auto_notch(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read auto-notch status command."""
    return _build_function_get(
        _SUB_AUTO_NOTCH,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_auto_notch",
    )


def set_auto_notch(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set auto-notch status command."""
    return _build_function_bool_set(
        _SUB_AUTO_NOTCH,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_auto_notch",
    )


def get_compressor(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read compressor status command."""
    return _build_function_get(
        _SUB_COMPRESSOR,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_compressor",
    )


def set_compressor(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set compressor status command."""
    return _build_function_bool_set(
        _SUB_COMPRESSOR,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_compressor",
    )


def get_monitor(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read monitor status command."""
    return _build_function_get(
        _SUB_MONITOR,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_monitor",
    )


def set_monitor(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set monitor status command."""
    return _build_function_bool_set(
        _SUB_MONITOR,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_monitor",
    )


def get_vox(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read VOX status command."""
    return _build_function_get(
        _SUB_VOX,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_vox",
    )


def set_vox(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set VOX status command."""
    return _build_function_bool_set(
        _SUB_VOX,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_vox",
    )


def get_break_in(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read break-in mode command."""
    return _build_function_get(
        _SUB_BREAK_IN,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_break_in",
    )


def set_break_in(
    mode: BreakInMode | int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set break-in mode command."""
    return _build_function_value_set(
        _SUB_BREAK_IN,
        int(BreakInMode(mode)),
        minimum=int(BreakInMode.OFF),
        maximum=int(BreakInMode.FULL),
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_break_in",
    )


def get_manual_notch(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read manual-notch status command."""
    return _build_function_get(
        _SUB_MANUAL_NOTCH,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_manual_notch",
    )


def set_manual_notch(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set manual-notch status command."""
    return _build_function_bool_set(
        _SUB_MANUAL_NOTCH,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_manual_notch",
    )


def get_manual_notch_width(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get manual notch width' CI-V command (0x16 0x57).

    Returns:
        CI-V frame bytes. Response: 0=WIDE, 1=MID, 2=NAR.
    """
    return _build_function_get(
        _SUB_MANUAL_NOTCH_WIDTH,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_manual_notch_width",
    )


def set_manual_notch_width(
    width: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'set manual notch width' CI-V command (0x16 0x57).

    Args:
        width: 0=WIDE, 1=MID, 2=NAR.
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).

    Returns:
        CI-V frame bytes.
    """
    return _build_function_value_set(
        _SUB_MANUAL_NOTCH_WIDTH,
        width,
        minimum=0,
        maximum=2,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_manual_notch_width",
    )


def get_twin_peak_filter(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read twin-peak-filter status command."""
    return _build_function_get(
        _SUB_TWIN_PEAK_FILTER,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_twin_peak_filter",
    )


def set_twin_peak_filter(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set twin-peak-filter status command."""
    return _build_function_bool_set(
        _SUB_TWIN_PEAK_FILTER,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_twin_peak_filter",
    )


def get_dial_lock(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read dial-lock status command."""
    return _build_function_get(
        _SUB_DIAL_LOCK,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_dial_lock",
    )


def set_dial_lock(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set dial-lock status command."""
    return _build_function_bool_set(
        _SUB_DIAL_LOCK,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_dial_lock",
    )


def get_filter_shape(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read DSP IF filter shape command."""
    return _build_function_get(
        _SUB_FILTER_SHAPE,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_filter_shape",
    )


def set_filter_shape(
    shape: FilterShape | int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
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
        cmd_map=cmd_map,
        cmd_name="set_filter_shape",
    )


def get_filter_width(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get DSP IF filter width' CI-V command (0x1A 0x03, cmd29).

    Returns:
        CI-V frame bytes.
    """
    return _build_ctl_mem_single_bcd_get(
        _SUB_FILTER_WIDTH,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_filter_width",
    )


def set_filter_width(
    filter_index: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'set DSP IF filter width' CI-V command (0x1A 0x03, cmd29).

    Args:
        filter_index: Filter width index encoded by the active radio profile.
        receiver: RECEIVER_MAIN (0x00) or RECEIVER_SUB (0x01).

    Returns:
        CI-V frame bytes.
    """
    if filter_index < 0:
        raise ValueError(f"Filter index must be non-negative, got {filter_index}")
    payload = bcd_encode_value(filter_index, byte_count=2)
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_filter_width",
            to_addr=to_addr,
            from_addr=from_addr,
            data=payload,
            receiver=receiver,
            command29=True,
        )
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_FILTER_WIDTH,
        data=payload,
        receiver=receiver,
    )


def get_ssb_tx_bandwidth(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read SSB TX bandwidth preset command."""
    return _build_function_get(
        _SUB_SSB_TX_BANDWIDTH,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_ssb_tx_bandwidth",
    )


def set_ssb_tx_bandwidth(
    bandwidth: SsbTxBandwidth | int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set SSB TX bandwidth preset command."""
    return _build_function_value_set(
        _SUB_SSB_TX_BANDWIDTH,
        int(SsbTxBandwidth(bandwidth)),
        minimum=int(SsbTxBandwidth.WIDE),
        maximum=int(SsbTxBandwidth.NAR),
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_ssb_tx_bandwidth",
    )


def get_main_sub_tracking(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Main/Sub Tracking status command (0x16 0x5E)."""
    return _build_function_get(
        _SUB_MAIN_SUB_TRACKING,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_main_sub_tracking",
    )


def set_main_sub_tracking(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set Main/Sub Tracking status command (0x16 0x5E)."""
    return _build_function_bool_set(
        _SUB_MAIN_SUB_TRACKING,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="set_main_sub_tracking",
    )


def get_agc_time_constant(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read AGC time constant command."""
    return _build_ctl_mem_single_bcd_get(
        _SUB_AGC_TIME_CONSTANT,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_agc_time_constant",
    )


def set_agc_time_constant(
    value: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
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
        cmd_map=cmd_map,
        cmd_name="set_agc_time_constant",
    )


def get_data_mode(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get DATA mode' CI-V command (0x1A 0x06).

    Returns:
        CI-V frame bytes.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_data_mode", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_DATA_MODE)


def set_data_mode(
    on: int | bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'set DATA mode' CI-V command (0x1A 0x06 <0x00-0x03>).

    Args:
        on: False/0 to disable, True/1 to enable DATA1, or an explicit DATA mode 0-3.
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        CI-V frame bytes.
    """
    mode_value = int(on) if isinstance(on, bool) else int(on)
    if not 0 <= mode_value <= 3:
        raise ValueError(f"DATA mode must be 0-3, got {mode_value}")

    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_data_mode",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([mode_value]),
            receiver=receiver,
            command29=(receiver != RECEIVER_MAIN),
        )
    if receiver != RECEIVER_MAIN:
        return build_cmd29_frame(
            to_addr,
            from_addr,
            _CMD_CTL_MEM,
            sub=_SUB_DATA_MODE,
            data=bytes([mode_value]),
            receiver=receiver,
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_DATA_MODE,
        data=bytes([mode_value]),
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
_SUB_SCOPE_DURING_TX = 0x1B
_SUB_SCOPE_CENTER_TYPE = 0x1C
_SUB_SCOPE_VBW = 0x1D
_SUB_SCOPE_FIXED_EDGE = 0x1E
_SUB_SCOPE_RBW = 0x1F

_SCOPE_SPAN_PRESETS_HZ: tuple[int, ...] = (
    2_500,
    5_000,
    10_000,
    25_000,
    50_000,
    100_000,
    250_000,
    500_000,
)
_SCOPE_FIXED_EDGE_RANGE_STARTS_HZ: tuple[int, ...] = (
    50_000_000,
    28_000_000,
    24_890_000,
    21_000_000,
    18_068_000,
    14_000_000,
    10_100_000,
    7_000_000,
    5_250_000,
    3_500_000,
    1_800_000,
    472_000,
    135_000,
    10_000,
)


def _validate_scope_range(name: str, value: int, minimum: int, maximum: int) -> int:
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be {minimum}-{maximum}, got {value}")
    return value


def _validate_scope_receiver(receiver: int) -> int:
    if receiver not in (0, 1):
        raise ValueError(f"scope receiver must be 0 or 1, got {receiver}")
    return receiver


def _scope_payload(value: bytes, receiver: int | None = None) -> bytes:
    if receiver is None:
        return value
    return bytes([_validate_scope_receiver(receiver)]) + value


def _scope_query(
    sub: int,
    *,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int | None = None,
) -> bytes:
    data = None if receiver is None else bytes([_validate_scope_receiver(receiver)])
    return build_civ_frame(to_addr, from_addr, _CMD_SCOPE, sub=sub, data=data)


def _parse_scope_frame(frame: CivFrame, sub: int) -> bytes:
    if frame.command != _CMD_SCOPE or frame.sub != sub:
        got = 0 if frame.sub is None else frame.sub
        raise ValueError(
            f"Not a scope response: command 0x{frame.command:02x} sub 0x{got:02x}"
        )
    if not frame.data:
        raise ValueError("Scope response has no payload")
    return frame.data


def _split_scope_receiver_prefix(
    data: bytes,
    *,
    expected_lengths: tuple[int, ...],
) -> tuple[int | None, bytes]:
    if len(data) in {length + 1 for length in expected_lengths} and data[0] in (
        0x00,
        0x01,
    ):
        return data[0], data[1:]
    if len(data) not in expected_lengths:
        expected = " or ".join(str(length) for length in expected_lengths)
        raise ValueError(
            f"Unexpected scope payload length: expected {expected} byte(s), got {len(data)}"
        )
    return None, data


def _decode_scope_bool(frame: CivFrame, sub: int) -> bool:
    data = _parse_scope_frame(frame, sub)
    if len(data) != 1:
        raise ValueError(f"Scope bool response must be 1 byte, got {len(data)}")
    return data[0] != 0x00


def _decode_scope_value(
    frame: CivFrame,
    sub: int,
    *,
    minimum: int,
    maximum: int,
) -> tuple[int | None, int]:
    data = _parse_scope_frame(frame, sub)
    receiver, payload = _split_scope_receiver_prefix(data, expected_lengths=(1,))
    value = payload[0]
    _validate_scope_range("scope value", value, minimum, maximum)
    return receiver, value


def _decode_scope_bcd_value(
    frame: CivFrame,
    sub: int,
    *,
    minimum: int,
    maximum: int,
) -> tuple[int | None, int]:
    data = _parse_scope_frame(frame, sub)
    receiver, payload = _split_scope_receiver_prefix(data, expected_lengths=(1,))
    value = _bcd_decode_value(payload)
    _validate_scope_range("scope value", value, minimum, maximum)
    return receiver, value


def scope_on(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'scope on' CI-V command (0x27 0x10 0x01)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "scope_on", to_addr=to_addr, from_addr=from_addr, data=b"\x01"
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_ON, data=b"\x01"
    )


def scope_off(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'scope off' CI-V command (0x27 0x10 0x00)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "scope_off", to_addr=to_addr, from_addr=from_addr, data=b"\x00"
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_SCOPE, sub=_SUB_SCOPE_ON, data=b"\x00"
    )


def scope_data_output(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'scope data output enable/disable' CI-V command (0x27 0x11).

    Args:
        on: True to enable wave data output, False to disable.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "scope_data_output",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x01" if on else b"\x00",
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_DATA_OUTPUT,
        data=b"\x01" if on else b"\x00",
    )


def get_scope_main_sub(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get scope receiver' CI-V command (0x27 0x12)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_main_sub", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(_SUB_SCOPE_MAIN_SUB, to_addr=to_addr, from_addr=from_addr)


def get_scope_single_dual(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get scope single/dual mode' CI-V command (0x27 0x13)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_single_dual", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(_SUB_SCOPE_SINGLE_DUAL, to_addr=to_addr, from_addr=from_addr)


def get_scope_mode(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'get scope mode' CI-V command (0x27 0x14)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_mode", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(
        _SUB_SCOPE_MODE,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
    )


def scope_set_mode(
    mode: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'set scope mode' CI-V command (0x27 0x14).

    Args:
        mode: 0=center, 1=fixed, 2=scroll-C, 3=scroll-F.
    """
    _validate_scope_range("scope mode", mode, 0, 3)
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_mode",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_scope_payload(bytes([mode]), receiver),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_MODE,
        data=_scope_payload(bytes([mode]), receiver),
    )


def get_scope_span(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'get scope span' CI-V command (0x27 0x15)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_span", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(
        _SUB_SCOPE_SPAN,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
    )


def scope_set_span(
    span: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'set scope span' CI-V command (0x27 0x15).

    Args:
        span: 0–7 (span index, radio-model dependent).
    """
    _validate_scope_range("scope span", span, 0, 7)
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_span",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_scope_payload(bytes([span]), receiver),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_SPAN,
        data=_scope_payload(bytes([span]), receiver),
    )


def get_scope_edge(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'get scope edge' CI-V command (0x27 0x16)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_edge", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(
        _SUB_SCOPE_EDGE,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
    )


def scope_set_edge(
    edge: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'set scope edge' CI-V command (0x27 0x16).

    Args:
        edge: Edge number 1–4.
    """
    _validate_scope_range("scope edge", edge, 1, 4)
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_edge",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_scope_payload(bytes([edge]), receiver),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_EDGE,
        data=_scope_payload(bytes([edge]), receiver),
    )


def get_scope_hold(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'get scope hold' CI-V command (0x27 0x17)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_hold", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(
        _SUB_SCOPE_HOLD,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
    )


def scope_set_hold(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'scope hold on/off' CI-V command (0x27 0x17).

    Args:
        on: True to enable hold, False to disable.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_hold",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_scope_payload(b"\x01" if on else b"\x00", receiver),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_HOLD,
        data=_scope_payload(b"\x01" if on else b"\x00", receiver),
    )


def _scope_ref_encode(ref: float) -> bytes:
    """Encode scope reference level as 3-byte Icom BCD format.

    Reference: wfview icomcommander.cpp line 3357 (bcdEncodeInt + sign byte).

    Args:
        ref: Reference level in dB (-30.0 to +10.0).

    Returns:
        3 bytes: [BCD thousands/hundreds, BCD tens/units, sign(0=+, 1=-)].
    """
    if not -30.0 <= ref <= 10.0:
        raise ValueError(f"scope ref must be -30.0 to +10.0 dB, got {ref}")
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


def get_scope_ref(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'get scope reference level' CI-V command (0x27 0x19)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_ref", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(
        _SUB_SCOPE_REF,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
    )


def scope_set_ref(
    ref: float,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'set scope reference level' CI-V command (0x27 0x19).

    Args:
        ref: Reference level in dB (-30.0 to +10.0).
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_ref",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_scope_payload(_scope_ref_encode(ref), receiver),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_REF,
        data=_scope_payload(_scope_ref_encode(ref), receiver),
    )


def get_scope_speed(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'get scope speed' CI-V command (0x27 0x1A)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_speed", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(
        _SUB_SCOPE_SPEED,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
    )


def scope_set_speed(
    speed: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'set scope speed' CI-V command (0x27 0x1A).

    Args:
        speed: 0=fast, 1=mid, 2=slow.
    """
    _validate_scope_range("scope speed", speed, 0, 2)
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_speed",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_scope_payload(bytes([speed]), receiver),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_SPEED,
        data=_scope_payload(bytes([speed]), receiver),
    )


def get_scope_during_tx(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get scope during TX' CI-V command (0x27 0x1B)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_during_tx", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(_SUB_SCOPE_DURING_TX, to_addr=to_addr, from_addr=from_addr)


def scope_set_during_tx(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'set scope during TX' CI-V command (0x27 0x1B)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_during_tx",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x01" if on else b"\x00",
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_DURING_TX,
        data=b"\x01" if on else b"\x00",
    )


def get_scope_center_type(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'get scope center type' CI-V command (0x27 0x1C)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_center_type", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(
        _SUB_SCOPE_CENTER_TYPE,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
    )


def scope_set_center_type(
    center_type: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'set scope center type' CI-V command (0x27 0x1C)."""
    _validate_scope_range("scope center type", center_type, 0, 2)
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_center_type",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_scope_payload(bytes([center_type]), receiver),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_CENTER_TYPE,
        data=_scope_payload(bytes([center_type]), receiver),
    )


def get_scope_vbw(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'get scope VBW' CI-V command (0x27 0x1D)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_vbw", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(
        _SUB_SCOPE_VBW,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
    )


def scope_set_vbw(
    narrow: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'set scope VBW' CI-V command (0x27 0x1D).

    Args:
        narrow: True for narrow VBW, False for wide.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_vbw",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_scope_payload(b"\x01" if narrow else b"\x00", receiver),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_VBW,
        data=_scope_payload(b"\x01" if narrow else b"\x00", receiver),
    )


def _resolve_scope_fixed_edge_range(start_hz: int) -> int:
    if start_hz < 0:
        raise ValueError(f"scope fixed edge start_hz must be >= 0, got {start_hz}")
    for index, band_start in enumerate(_SCOPE_FIXED_EDGE_RANGE_STARTS_HZ, start=1):
        if start_hz >= band_start:
            return index
    raise ValueError(
        f"scope fixed edge start_hz {start_hz} is outside known IC-7610 bands"
    )


def get_scope_fixed_edge(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'get fixed-edge scope bounds' CI-V command (0x27 0x1E)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_fixed_edge", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(_SUB_SCOPE_FIXED_EDGE, to_addr=to_addr, from_addr=from_addr)


def scope_set_fixed_edge(
    *,
    edge: int,
    start_hz: int,
    end_hz: int,
    to_addr: int,
    range_index: int | None = None,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a 'set fixed-edge scope bounds' CI-V command (0x27 0x1E)."""
    _validate_scope_range("scope fixed edge", edge, 1, 4)
    if start_hz < 0:
        raise ValueError(f"scope fixed edge start_hz must be >= 0, got {start_hz}")
    if end_hz <= start_hz:
        raise ValueError(
            f"scope fixed edge end_hz must be greater than start_hz, got {start_hz}..{end_hz}"
        )
    resolved_range = (
        _resolve_scope_fixed_edge_range(start_hz)
        if range_index is None
        else _validate_scope_range("scope fixed edge range", range_index, 1, 99)
    )
    payload = (
        bcd_encode_value(resolved_range, byte_count=1)
        + bcd_encode_value(edge, byte_count=1)
        + bcd_encode(start_hz)
        + bcd_encode(end_hz)
    )
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_fixed_edge",
            to_addr=to_addr,
            from_addr=from_addr,
            data=payload,
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_FIXED_EDGE,
        data=payload,
    )


def get_scope_rbw(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'get scope RBW' CI-V command (0x27 0x1F)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_scope_rbw", to_addr=to_addr, from_addr=from_addr
        )
    return _scope_query(
        _SUB_SCOPE_RBW,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
    )


def scope_set_rbw(
    rbw: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Build a 'set scope RBW' CI-V command (0x27 0x1F).

    Args:
        rbw: 0=wide, 1=mid, 2=narrow.
    """
    _validate_scope_range("scope rbw", rbw, 0, 2)
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_rbw",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_scope_payload(bytes([rbw]), receiver),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_RBW,
        data=_scope_payload(bytes([rbw]), receiver),
    )


# --- Scope convenience aliases ---


def scope_data_output_on(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Enable scope wave data output (0x27 0x11 0x01)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "scope_data_output",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x01",
        )
    return scope_data_output(True, to_addr=to_addr, from_addr=from_addr)


def scope_data_output_off(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Disable scope wave data output (0x27 0x11 0x00)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "scope_data_output",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x00",
        )
    return scope_data_output(False, to_addr=to_addr, from_addr=from_addr)


def scope_main_sub(
    receiver: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Select scope receiver (0x27 0x12 <0x00|0x01>).

    Args:
        receiver: 0 for MAIN, 1 for SUB.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_main_sub",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_validate_scope_receiver(receiver)]),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_MAIN_SUB,
        data=bytes([_validate_scope_receiver(receiver)]),
    )


def scope_single_dual(
    dual: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
    *,
    receiver: int | None = None,
) -> bytes:
    """Select scope single/dual mode (0x27 0x13 <receiver> <0x00|0x01>).

    Args:
        dual: True for dual scope, False for single.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_scope_single_dual",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_scope_payload(b"\x01" if dual else b"\x00", receiver),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_SCOPE,
        sub=_SUB_SCOPE_SINGLE_DUAL,
        data=_scope_payload(b"\x01" if dual else b"\x00", receiver),
    )


def parse_scope_main_sub_response(frame: CivFrame) -> int:
    """Parse a scope receiver selection response."""
    data = _parse_scope_frame(frame, _SUB_SCOPE_MAIN_SUB)
    if len(data) != 1:
        raise ValueError(f"Scope receiver response must be 1 byte, got {len(data)}")
    return _validate_scope_range("scope receiver", data[0], 0, 1)


def parse_scope_single_dual_response(frame: CivFrame) -> bool:
    """Parse a scope single/dual response."""
    return _decode_scope_bool(frame, _SUB_SCOPE_SINGLE_DUAL)


def parse_scope_mode_response(frame: CivFrame) -> tuple[int | None, int]:
    """Parse a scope mode response."""
    return _decode_scope_value(frame, _SUB_SCOPE_MODE, minimum=0, maximum=3)


def parse_scope_span_response(frame: CivFrame) -> tuple[int | None, int]:
    """Parse a scope span response into the 0..7 span index."""
    data = _parse_scope_frame(frame, _SUB_SCOPE_SPAN)
    receiver, payload = _split_scope_receiver_prefix(data, expected_lengths=(1, 5))
    if len(payload) == 1:
        return receiver, _validate_scope_range("scope span", payload[0], 0, 7)
    hz = bcd_decode(payload)
    try:
        span = _SCOPE_SPAN_PRESETS_HZ.index(hz)
    except ValueError as exc:
        raise ValueError(f"Unknown scope span frequency {hz}") from exc
    return receiver, span


def parse_scope_ref_response(frame: CivFrame) -> tuple[int | None, float]:
    """Parse a scope reference response into dB."""
    data = _parse_scope_frame(frame, _SUB_SCOPE_REF)
    receiver, payload = _split_scope_receiver_prefix(data, expected_lengths=(3,))
    absolute_tenths = _bcd_decode_value(payload[:2])
    ref = absolute_tenths / 10.0
    if payload[2]:
        ref *= -1
    return receiver, ref


def parse_scope_speed_response(frame: CivFrame) -> tuple[int | None, int]:
    """Parse a scope speed response."""
    return _decode_scope_value(frame, _SUB_SCOPE_SPEED, minimum=0, maximum=2)


def parse_scope_edge_response(frame: CivFrame) -> tuple[int | None, int]:
    """Parse a scope edge response."""
    return _decode_scope_bcd_value(frame, _SUB_SCOPE_EDGE, minimum=1, maximum=4)


def parse_scope_hold_response(frame: CivFrame) -> tuple[int | None, bool]:
    """Parse a scope hold response."""
    data = _parse_scope_frame(frame, _SUB_SCOPE_HOLD)
    receiver, payload = _split_scope_receiver_prefix(data, expected_lengths=(1,))
    return receiver, payload[0] != 0x00


def parse_scope_during_tx_response(frame: CivFrame) -> bool:
    """Parse a scope during-TX response."""
    return _decode_scope_bool(frame, _SUB_SCOPE_DURING_TX)


def parse_scope_center_type_response(frame: CivFrame) -> tuple[int | None, int]:
    """Parse a scope center-type response."""
    return _decode_scope_value(frame, _SUB_SCOPE_CENTER_TYPE, minimum=0, maximum=2)


def parse_scope_vbw_response(frame: CivFrame) -> tuple[int | None, bool]:
    """Parse a scope VBW response."""
    data = _parse_scope_frame(frame, _SUB_SCOPE_VBW)
    receiver, payload = _split_scope_receiver_prefix(data, expected_lengths=(1,))
    return receiver, payload[0] != 0x00


def parse_scope_fixed_edge_response(frame: CivFrame) -> ScopeFixedEdge:
    """Parse a fixed-edge scope response."""
    data = _parse_scope_frame(frame, _SUB_SCOPE_FIXED_EDGE)
    _receiver, payload = _split_scope_receiver_prefix(data, expected_lengths=(12,))
    return ScopeFixedEdge(
        range_index=_bcd_decode_value(payload[:1]),
        edge=_bcd_decode_value(payload[1:2]),
        start_hz=bcd_decode(payload[2:7]),
        end_hz=bcd_decode(payload[7:12]),
    )


def parse_scope_rbw_response(frame: CivFrame) -> tuple[int | None, int]:
    """Parse a scope RBW response."""
    return _decode_scope_value(frame, _SUB_SCOPE_RBW, minimum=0, maximum=2)


# --- CW keying ---

_CMD_SEND_CW = 0x17


def send_cw(
    text: str,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
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
        if cmd_map is not None:
            frames.append(
                _build_from_map(
                    cmd_map, "send_cw", to_addr=to_addr, from_addr=from_addr, data=data
                )
            )
        else:
            frames.append(build_civ_frame(to_addr, from_addr, _CMD_SEND_CW, data=data))
    return frames


def stop_cw(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V frame to stop CW sending."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "stop_cw", to_addr=to_addr, from_addr=from_addr, data=b"\xff"
        )
    return build_civ_frame(to_addr, from_addr, _CMD_SEND_CW, data=b"\xff")


# --- Power on/off ---

_CMD_POWER_CTRL = 0x18


def get_powerstat(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V frame to query radio power status (0x18 GET)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_powerstat", to_addr=to_addr, from_addr=from_addr, data=b""
        )
    return build_civ_frame(to_addr, from_addr, _CMD_POWER_CTRL, data=b"")


def power_on(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V frame to power on the radio."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "power_on", to_addr=to_addr, from_addr=from_addr, data=b"\x01"
        )
    return build_civ_frame(to_addr, from_addr, _CMD_POWER_CTRL, data=b"\x01")


def power_off(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V frame to power off the radio."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "power_off", to_addr=to_addr, from_addr=from_addr, data=b"\x00"
        )
    return build_civ_frame(to_addr, from_addr, _CMD_POWER_CTRL, data=b"\x00")


def parse_powerstat(frame: CivFrame) -> bool:
    """Parse power status response (0x18 GET).

    Args:
        frame: CI-V response frame.

    Returns:
        True if powered on (data=0x01), False if powered off (data=0x00).

    Raises:
        ValueError: If response format is invalid.
    """
    if frame.command != _CMD_POWER_CTRL:
        raise ValueError(
            f"Expected power control response (0x18), got 0x{frame.command:02X}"
        )
    if len(frame.data) != 1:
        raise ValueError(
            f"Expected 1 byte power status, got {len(frame.data)} bytes"
        )
    val = frame.data[0]
    if val not in (0x00, 0x01):
        raise ValueError(f"Invalid power status value: 0x{val:02X} (expected 0x00 or 0x01)")
    return val == 0x01


# --- Speech (0x13) ---

_CMD_SPEECH = 0x13


def get_speech(
    what: int = 0,
    *,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a speech announcement CI-V command (0x13).

    Fire-and-forget.  Triggers the IC-7610 voice synthesizer.

    Args:
        what: 0 = all (S-meter, frequency, mode),
              1 = frequency + S-meter,
              2 = mode.
        to_addr: Radio CI-V address.
        from_addr: Controller CI-V address.

    Returns:
        CI-V frame bytes.

    Raises:
        ValueError: If *what* is not 0, 1, or 2.
    """
    if cmd_map is not None:
        speech_key = "set_speech" if cmd_map.has("set_speech") else "get_speech"
        return _build_from_map(
            cmd_map,
            speech_key,
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([what]),
        )
    if what not in (0, 1, 2):
        raise ValueError(f"speech 'what' must be 0, 1, or 2, got {what}")
    return build_civ_frame(to_addr, from_addr, _CMD_SPEECH, data=bytes([what]))


# --- Transceiver ID (0x19 0x00) ---

_CMD_TRANSCEIVER_ID = 0x19
_SUB_TRANSCEIVER_ID = 0x00


def get_transceiver_id(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read transceiver ID command (0x19 0x00).

    GET only.  Response data: 1 byte model ID (IC-7610 = 0x98).
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_transceiver_id", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_TRANSCEIVER_ID,
        sub=_SUB_TRANSCEIVER_ID,
    )


# --- Transceiver status family (#136) ---

# Sub-commands for 0x1C (Transceiver status register)
_SUB_TUNER_STATUS = 0x01
_SUB_XFC_STATUS = 0x02
_SUB_TX_FREQ_MONITOR = 0x03

# Sub-commands for 0x21 (RIT/XIT register)
_SUB_RIT_FREQ = 0x00
_SUB_RIT_STATUS = 0x01
_SUB_RIT_TX_STATUS = 0x02


def get_band_edge_freq(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read band-edge frequency command (0x02).

    Returns the current band-edge frequency (same BCD encoding as 0x03).
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_band_edge_freq", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_BAND_EDGE)


def get_various_squelch(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read various-squelch status command (0x15 0x05, Command29)."""
    return _build_meter_bool_get(
        _SUB_VARIOUS_SQUELCH,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_various_squelch",
    )


def get_power_meter(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read RF power meter command (0x15 0x11)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_power_meter", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_POWER_METER)


def get_comp_meter(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read compressor meter command (0x15 0x14)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_comp_meter", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_COMP_METER)


def get_vd_meter(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Vd (supply voltage) meter command (0x15 0x15)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_vd_meter", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_VD_METER)


def get_id_meter(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read Id (drain current) meter command (0x15 0x16)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_id_meter", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_METER, sub=_SUB_ID_METER)


def get_tuner_status(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read tuner/ATU status command (0x1C 0x01).

    Response data: 0x00=off, 0x01=on, 0x02=tuning.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_tuner_status", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_TUNER_STATUS)


def set_tuner_status(
    value: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set tuner/ATU status command (0x1C 0x01).

    Args:
        value: 0=off, 1=on, 2=tune.
    """
    if value not in (0, 1, 2):
        raise ValueError(f"Tuner status must be 0, 1, or 2, got {value}")
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_tuner_status",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([value]),
        )
    return build_civ_frame(
        to_addr, from_addr, _CMD_PTT, sub=_SUB_TUNER_STATUS, data=bytes([value])
    )


def get_xfc_status(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read XFC status command (0x1C 0x02).

    Response data: 0x00=off, 0x01=on.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_xfc_status", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_XFC_STATUS)


def set_xfc_status(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set XFC status command (0x1C 0x02).

    Args:
        on: True to enable XFC, False to disable.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_xfc_status",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x01" if on else b"\x00",
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_PTT,
        sub=_SUB_XFC_STATUS,
        data=b"\x01" if on else b"\x00",
    )


def get_tx_freq_monitor(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read TX frequency monitor status command (0x1C 0x03)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_tx_freq_monitor", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_PTT, sub=_SUB_TX_FREQ_MONITOR)


def set_tx_freq_monitor(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set TX frequency monitor command (0x1C 0x03)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_tx_freq_monitor",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x01" if on else b"\x00",
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_PTT,
        sub=_SUB_TX_FREQ_MONITOR,
        data=b"\x01" if on else b"\x00",
    )


def get_rit_frequency(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read RIT frequency offset command (0x21 0x00).

    Response: 2 bytes BCD Hz + 1 byte sign (0x00=positive, 0x01=negative).
    Range: ±9999 Hz.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_rit_frequency", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_RIT, sub=_SUB_RIT_FREQ)


def set_rit_frequency(
    offset_hz: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
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
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_rit_frequency",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([d0, d1]) + sign,
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_RIT,
        sub=_SUB_RIT_FREQ,
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
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read RIT on/off status command (0x21 0x01)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_rit_status", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_RIT, sub=_SUB_RIT_STATUS)


def set_rit_status(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set RIT on/off command (0x21 0x01)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_rit_status",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x01" if on else b"\x00",
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_RIT,
        sub=_SUB_RIT_STATUS,
        data=b"\x01" if on else b"\x00",
    )


def get_rit_tx_status(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a read RIT TX status command (0x21 0x02)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_rit_tx_status", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_RIT, sub=_SUB_RIT_TX_STATUS)


def set_rit_tx_status(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build a set RIT TX status command (0x21 0x02)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_rit_tx_status",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x01" if on else b"\x00",
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_RIT,
        sub=_SUB_RIT_TX_STATUS,
        data=b"\x01" if on else b"\x00",
    )


# --- Tone / TSQL frequency (#134) ---


def _encode_tone_freq(freq_hz: float) -> bytes:
    """Encode tone frequency (Hz) to 3-byte BCD.

    Args:
        freq_hz: Tone frequency in Hz (e.g. 88.5, 110.9).

    Returns:
        3 bytes: [hundreds BCD, tens+units BCD, tenths BCD]

    Example:
        88.5 → b'\\x00\\x88\\x05'
        110.9 → b'\\x01\\x10\\x09'
    """
    if not 67.0 <= freq_hz <= 254.1:
        raise ValueError(f"Tone frequency must be 67.0-254.1 Hz, got {freq_hz}")
    total_tenths = round(freq_hz * 10)
    integer_hz = total_tenths // 10
    hundreds = integer_hz // 100
    tens_units = integer_hz % 100
    tenths_digit = total_tenths % 10
    return bytes(
        [
            _bcd_byte(hundreds),
            _bcd_byte(tens_units),
            _bcd_byte(tenths_digit),
        ]
    )


def _decode_tone_freq(data: bytes) -> float:
    """Decode 3-byte BCD to tone frequency (Hz).

    Args:
        data: 3 bytes [hundreds BCD, tens+units BCD, tenths BCD].

    Returns:
        Frequency in Hz (e.g. 88.5, 110.9).
    """
    if len(data) < 3:
        raise ValueError(f"Expected 3 bytes for tone freq, got {len(data)}")
    hundreds = _bcd_decode_value(data[0:1])
    tens_units = _bcd_decode_value(data[1:2])
    tenths_digit = _bcd_decode_value(data[2:3])
    return float(hundreds * 100 + tens_units) + tenths_digit / 10.0


def get_repeater_tone(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to get repeater tone status (0x16 0x42)."""
    return _build_function_get(
        _SUB_REPEATER_TONE,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_repeater_tone",
    )


def set_repeater_tone(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to set repeater tone (0x16 0x42)."""
    return _build_function_bool_set(
        _SUB_REPEATER_TONE,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_repeater_tone",
    )


def get_repeater_tsql(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to get repeater TSQL status (0x16 0x43)."""
    return _build_function_get(
        _SUB_REPEATER_TSQL,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="get_repeater_tsql",
    )


def set_repeater_tsql(
    on: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to set repeater TSQL (0x16 0x43)."""
    return _build_function_bool_set(
        _SUB_REPEATER_TSQL,
        on,
        to_addr=to_addr,
        from_addr=from_addr,
        receiver=receiver,
        command29=True,
        cmd_map=cmd_map,
        cmd_name="set_repeater_tsql",
    )


def get_tone_freq(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to get tone frequency (0x1B 0x00)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_tone_freq",
            to_addr=to_addr,
            from_addr=from_addr,
            command29=True,
            receiver=receiver,
        )
    return build_cmd29_frame(
        to_addr, from_addr, _CMD_TONE, sub=_SUB_TONE_FREQ, receiver=receiver
    )


def set_tone_freq(
    freq_hz: float,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to set tone frequency (0x1B 0x00).

    Args:
        freq_hz: CTCSS tone frequency in Hz (67.0-254.1).
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_tone_freq",
            to_addr=to_addr,
            from_addr=from_addr,
            command29=True,
            receiver=receiver,
            data=_encode_tone_freq(freq_hz),
        )
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_TONE,
        sub=_SUB_TONE_FREQ,
        data=_encode_tone_freq(freq_hz),
        receiver=receiver,
    )


def get_tsql_freq(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to get TSQL frequency (0x1B 0x01)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_tsql_freq",
            to_addr=to_addr,
            from_addr=from_addr,
            command29=True,
            receiver=receiver,
        )
    return build_cmd29_frame(
        to_addr, from_addr, _CMD_TONE, sub=_SUB_TSQL_FREQ, receiver=receiver
    )


def set_tsql_freq(
    freq_hz: float,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    receiver: int = RECEIVER_MAIN,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build CI-V command to set TSQL frequency (0x1B 0x01).

    Args:
        freq_hz: TSQL tone frequency in Hz (67.0-254.1).
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_tsql_freq",
            to_addr=to_addr,
            from_addr=from_addr,
            command29=True,
            receiver=receiver,
            data=_encode_tone_freq(freq_hz),
        )
    return build_cmd29_frame(
        to_addr,
        from_addr,
        _CMD_TONE,
        sub=_SUB_TSQL_FREQ,
        data=_encode_tone_freq(freq_hz),
        receiver=receiver,
    )


def parse_tone_freq_response(frame: CivFrame) -> tuple[int | None, float]:
    """Parse tone frequency response (0x1B 0x00).

    Returns:
        (receiver | None, freq_hz)
    """
    if frame.command != _CMD_TONE or frame.sub != _SUB_TONE_FREQ:
        raise ValueError(
            f"Not a tone freq response: 0x{frame.command:02x} sub=0x{frame.sub!r}"
        )
    if len(frame.data) < 3:
        raise ValueError(f"Expected 3 bytes for tone freq, got {len(frame.data)}")
    return (frame.receiver, _decode_tone_freq(frame.data))


def parse_tsql_freq_response(frame: CivFrame) -> tuple[int | None, float]:
    """Parse TSQL frequency response (0x1B 0x01).

    Returns:
        (receiver | None, freq_hz)
    """
    if frame.command != _CMD_TONE or frame.sub != _SUB_TSQL_FREQ:
        raise ValueError(
            f"Not a TSQL freq response: 0x{frame.command:02x} sub=0x{frame.sub!r}"
        )
    if len(frame.data) < 3:
        raise ValueError(f"Expected 3 bytes for TSQL freq, got {len(frame.data)}")
    return (frame.receiver, _decode_tone_freq(frame.data))


# --- Memory Commands ---


def build_memory_mode_get(
    to_addr: int, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build CI-V frame to get current memory mode (0x08)."""
    return build_civ_frame(to_addr, from_addr, _CMD_MEMORY_MODE)


def build_memory_mode_set(
    channel: int, to_addr: int, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build CI-V frame to set memory mode (0x08).

    Args:
        channel: Memory channel number (1-101).
    """
    if not 1 <= channel <= 101:
        raise ValueError(f"Channel must be 1-101, got {channel}")
    data = bcd_encode_value(channel, byte_count=2)
    return build_civ_frame(to_addr, from_addr, _CMD_MEMORY_MODE, data=data)


def parse_memory_mode_response(frame: CivFrame) -> int:
    """Parse memory mode response (0x08).

    Returns:
        Memory channel number (1-101).
    """
    if frame.command != _CMD_MEMORY_MODE:
        raise ValueError(f"Not a memory mode response: 0x{frame.command:02x}")
    if len(frame.data) < 2:
        raise ValueError(f"Expected 2 bytes for memory mode, got {len(frame.data)}")
    return _bcd_decode_value(frame.data[:2])


def build_memory_write(
    to_addr: int, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build CI-V frame to write VFO to memory (0x09)."""
    return build_civ_frame(to_addr, from_addr, _CMD_MEMORY_WRITE)


def build_memory_to_vfo(
    channel: int, to_addr: int, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build CI-V frame to load memory to VFO (0x0A).

    Args:
        channel: Memory channel number (1-101).
    """
    if not 1 <= channel <= 101:
        raise ValueError(f"Channel must be 1-101, got {channel}")
    data = bcd_encode_value(channel, byte_count=2)
    return build_civ_frame(to_addr, from_addr, _CMD_MEMORY_TO_VFO, data=data)


def build_memory_clear(
    channel: int, to_addr: int, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build CI-V frame to clear memory channel (0x0B).

    Args:
        channel: Memory channel number (1-101).
    """
    if not 1 <= channel <= 101:
        raise ValueError(f"Channel must be 1-101, got {channel}")
    data = bcd_encode_value(channel, byte_count=2)
    return build_civ_frame(to_addr, from_addr, _CMD_MEMORY_CLEAR, data=data)


def build_memory_contents_get(
    channel: int, to_addr: int, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build CI-V frame to get memory contents (0x1A 0x00).

    Args:
        channel: Memory channel number (1-101).
    """
    if not 1 <= channel <= 101:
        raise ValueError(f"Channel must be 1-101, got {channel}")
    channel_bcd = bcd_encode_value(channel, byte_count=2)
    return build_civ_frame(
        to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_MEMORY_CONTENTS, data=channel_bcd
    )


def build_memory_contents_set(
    mem: "MemoryChannel", to_addr: int, from_addr: int = CONTROLLER_ADDR
) -> bytes:
    """Build CI-V frame to set memory contents (0x1A 0x00).

    Args:
        mem: MemoryChannel dataclass with all fields.
    """
    from .types import MemoryChannel

    if not isinstance(mem, MemoryChannel):
        raise TypeError(f"Expected MemoryChannel, got {type(mem)}")
    if not 1 <= mem.channel <= 101:
        raise ValueError(f"Channel must be 1-101, got {mem.channel}")

    # Build payload per IC-7610 MemFormat spec:
    # %1.2b %3.1c %4.5f %9.1g %10.1h %11.1k %12.3n %15.3o %18.10z
    # Positions are 1-based in wfview spec, but payload is 0-based array
    # Channel is sent separately in data prefix, payload starts with scan
    payload = bytearray(26)  # 28 - 2 (channel sent separately)
    payload[0] = mem.scan
    payload[1:6] = bcd_encode(mem.frequency_hz)
    payload[6] = bcd_encode_value(mem.mode, byte_count=1)[0]
    payload[7] = bcd_encode_value(mem.filter, byte_count=1)[0]
    payload[8] = (mem.datamode << 4) | (mem.tonemode & 0x0F)
    if mem.tone_freq_hz:
        payload[9:12] = bcd_encode_value(mem.tone_freq_hz, byte_count=3)
    if mem.tsql_freq_hz:
        payload[12:15] = bcd_encode_value(mem.tsql_freq_hz, byte_count=3)
    name_bytes = mem.name.encode("ascii", errors="replace")[:10]
    payload[15 : 15 + len(name_bytes)] = name_bytes

    channel_bcd = bcd_encode_value(mem.channel, byte_count=2)
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_MEMORY_CONTENTS,
        data=channel_bcd + bytes(payload),
    )


def parse_memory_contents_response(frame: CivFrame) -> "MemoryChannel":
    """Parse memory contents response (0x1A 0x00).

    Returns:
        MemoryChannel dataclass.
    """
    from .types import MemoryChannel

    if frame.command != _CMD_CTL_MEM or frame.sub != _SUB_MEMORY_CONTENTS:
        raise ValueError(
            f"Not a memory contents response: 0x{frame.command:02x} sub=0x{frame.sub!r}"
        )
    # data = channel(2) + payload(26)
    if len(frame.data) < 28:
        raise ValueError(f"Memory contents too short: {len(frame.data)} bytes")

    data = frame.data
    # Channel in first 2 bytes, payload starts at index 2
    return MemoryChannel(
        channel=_bcd_decode_value(data[0:2]),
        scan=data[2],
        frequency_hz=bcd_decode(data[3:8]),
        mode=_bcd_decode_value(data[8:9]),
        filter=_bcd_decode_value(data[9:10]),
        datamode=(data[10] >> 4) & 0x0F,
        tonemode=data[10] & 0x0F,
        tone_freq_hz=(
            _bcd_decode_value(data[11:14]) if data[11:14] != b"\x00\x00\x00" else None
        ),
        tsql_freq_hz=(
            _bcd_decode_value(data[14:17]) if data[14:17] != b"\x00\x00\x00" else None
        ),
        name=data[17:27].rstrip(b"\x00").decode("ascii", errors="replace"),
    )


def get_bsr(
    band: int,
    register: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build CI-V frame to get band stacking register (0x1A 0x01).

    Args:
        band: Band code (0x00-0x18).
        register: Register number (1-3).
    """
    if not 0 <= band <= 24:
        raise ValueError(f"Band must be 0-24, got {band}")
    if not 1 <= register <= 3:
        raise ValueError(f"Register must be 1-3, got {register}")
    data = bytes([band, register])
    return build_civ_frame(
        to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_BAND_STACK, data=data
    )


def set_bsr(
    bsr: "BandStackRegister",
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
) -> bytes:
    """Build CI-V frame to set band stacking register (0x1A 0x01).

    Args:
        bsr: BandStackRegister dataclass.
    """
    from .types import BandStackRegister

    if not isinstance(bsr, BandStackRegister):
        raise TypeError(f"Expected BandStackRegister, got {type(bsr)}")
    if not 0 <= bsr.band <= 24:
        raise ValueError(f"Band must be 0-24, got {bsr.band}")
    if not 1 <= bsr.register <= 3:
        raise ValueError(f"Register must be 1-3, got {bsr.register}")

    # Payload: band + reg + freq(5) + mode(1) + filter(1)
    payload = bytes([bsr.band, bsr.register])
    payload += bcd_encode(bsr.frequency_hz)
    payload += bcd_encode_value(bsr.mode, byte_count=1)
    payload += bcd_encode_value(bsr.filter, byte_count=1)
    return build_civ_frame(
        to_addr, from_addr, _CMD_CTL_MEM, sub=_SUB_BAND_STACK, data=payload
    )


def parse_band_stack_response(frame: CivFrame) -> "BandStackRegister":
    """Parse band stacking register response (0x1A 0x01).

    Returns:
        BandStackRegister dataclass.
    """
    from .types import BandStackRegister

    if frame.command != _CMD_CTL_MEM or frame.sub != _SUB_BAND_STACK:
        raise ValueError(
            f"Not a band stack response: 0x{frame.command:02x} sub=0x{frame.sub!r}"
        )
    if len(frame.data) < 9:
        raise ValueError(f"Band stack data too short: {len(frame.data)} bytes")

    data = frame.data
    return BandStackRegister(
        band=data[0],
        register=data[1],
        frequency_hz=bcd_decode(data[2:7]),
        mode=_bcd_decode_value(data[7:8]),
        filter=_bcd_decode_value(data[8:9]),
    )


# --- Antenna Selection (0x12) ---


def get_antenna_1(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read ANT1 selection command (0x12 0x00)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_antenna",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_SUB_ANT1]),
        )
    return build_civ_frame(to_addr, from_addr, _CMD_ANTENNA, sub=_SUB_ANT1)


def set_antenna_1(
    enabled: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set ANT1 selection command (0x12 0x00).

    Args:
        enabled: True to select ANT1, False to deselect.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_antenna",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_SUB_ANT1]) + (b"\x01" if enabled else b"\x00"),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_ANTENNA,
        sub=_SUB_ANT1,
        data=b"\x01" if enabled else b"\x00",
    )


def get_antenna_2(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read ANT2 selection command (0x12 0x01)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_antenna",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_SUB_ANT2]),
        )
    return build_civ_frame(to_addr, from_addr, _CMD_ANTENNA, sub=_SUB_ANT2)


def set_antenna_2(
    enabled: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set ANT2 selection command (0x12 0x01).

    Args:
        enabled: True to select ANT2, False to deselect.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_antenna",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_SUB_ANT2]) + (b"\x01" if enabled else b"\x00"),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_ANTENNA,
        sub=_SUB_ANT2,
        data=b"\x01" if enabled else b"\x00",
    )


def get_rx_antenna_ant1(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read RX antenna on ANT1 command (0x12 0x12)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "get_antenna",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_SUB_RX_ANT_ANT1]),
        )
    return build_civ_frame(to_addr, from_addr, _CMD_ANTENNA, sub=_SUB_RX_ANT_ANT1)


def set_rx_antenna_ant1(
    enabled: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set RX antenna on ANT1 command (0x12 0x12).

    Args:
        enabled: True to enable RX antenna on ANT1.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_antenna",
            to_addr=to_addr,
            from_addr=from_addr,
            data=bytes([_SUB_RX_ANT_ANT1]) + (b"\x01" if enabled else b"\x00"),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_ANTENNA,
        sub=_SUB_RX_ANT_ANT1,
        data=b"\x01" if enabled else b"\x00",
    )


def get_rx_antenna_ant2(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read RX antenna on ANT2 command (0x12 0x13)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_rx_antenna_ant2", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_ANTENNA, sub=_SUB_RX_ANT_ANT2)


def set_rx_antenna_ant2(
    enabled: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set RX antenna on ANT2 command (0x12 0x13).

    Args:
        enabled: True to enable RX antenna on ANT2.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_rx_antenna_ant2",
            to_addr=to_addr,
            from_addr=from_addr,
            data=b"\x01" if enabled else b"\x00",
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_ANTENNA,
        sub=_SUB_RX_ANT_ANT2,
        data=b"\x01" if enabled else b"\x00",
    )


# --- Modulation Levels (0x14 0x0B / 0x10 / 0x11) ---


def get_acc1_mod_level(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read ACC1 modulation level command (0x14 0x0B)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_acc1_mod_level", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_ACC1_MOD_LEVEL)


def set_acc1_mod_level(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set ACC1 modulation level command (0x14 0x0B).

    Args:
        level: Mod level 0-255.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_acc1_mod_level",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_level_bcd_encode(level),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_LEVEL,
        sub=_SUB_ACC1_MOD_LEVEL,
        data=_level_bcd_encode(level),
    )


def get_usb_mod_level(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read USB modulation level command (0x14 0x10)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_usb_mod_level", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_USB_MOD_LEVEL)


def set_usb_mod_level(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set USB modulation level command (0x14 0x10).

    Args:
        level: Mod level 0-255.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_usb_mod_level",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_level_bcd_encode(level),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_LEVEL,
        sub=_SUB_USB_MOD_LEVEL,
        data=_level_bcd_encode(level),
    )


def get_lan_mod_level(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read LAN modulation level command (0x14 0x11)."""
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "get_lan_mod_level", to_addr=to_addr, from_addr=from_addr
        )
    return build_civ_frame(to_addr, from_addr, _CMD_LEVEL, sub=_SUB_LAN_MOD_LEVEL)


def set_lan_mod_level(
    level: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set LAN modulation level command (0x14 0x11).

    Args:
        level: Mod level 0-255.
    """
    if cmd_map is not None:
        return _build_from_map(
            cmd_map,
            "set_lan_mod_level",
            to_addr=to_addr,
            from_addr=from_addr,
            data=_level_bcd_encode(level),
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_LEVEL,
        sub=_SUB_LAN_MOD_LEVEL,
        data=_level_bcd_encode(level),
    )


# --- Modulation Input Routing (0x1A 0x05 0x00 0x91-0x94) ---


def get_data_off_mod_input(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read Data Off modulation input command (0x1A 0x05 0x00 0x91)."""
    return _build_ctl_mem_get(
        _CTL_MEM_DATA_OFF_MOD_INPUT,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_data_off_mod_input",
    )


def set_data_off_mod_input(
    source: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set Data Off modulation input command (0x1A 0x05 0x00 0x91).

    Args:
        source: 0=MIC, 1=ACC, 2=MIC+ACC, 3=USB, 4=MIC+USB, 5=LAN.
    """
    if not 0 <= source <= 5:
        raise ValueError(f"Data Off mod input must be 0-5, got {source}")
    return _build_ctl_mem_set(
        _CTL_MEM_DATA_OFF_MOD_INPUT,
        source,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=1,
        cmd_map=cmd_map,
        cmd_name="set_data_off_mod_input",
    )


def get_data1_mod_input(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read DATA1 modulation input command (0x1A 0x05 0x00 0x92)."""
    return _build_ctl_mem_get(
        _CTL_MEM_DATA1_MOD_INPUT,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_data1_mod_input",
    )


def set_data1_mod_input(
    source: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set DATA1 modulation input command (0x1A 0x05 0x00 0x92).

    Args:
        source: 0=MIC, 1=ACC, 2=USB, 3=LAN, 4=LAN+USB.
    """
    if not 0 <= source <= 4:
        raise ValueError(f"DATA1 mod input must be 0-4, got {source}")
    return _build_ctl_mem_set(
        _CTL_MEM_DATA1_MOD_INPUT,
        source,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=1,
        cmd_map=cmd_map,
        cmd_name="set_data1_mod_input",
    )


def get_data2_mod_input(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read DATA2 modulation input command (0x1A 0x05 0x00 0x93)."""
    return _build_ctl_mem_get(
        _CTL_MEM_DATA2_MOD_INPUT,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_data2_mod_input",
    )


def set_data2_mod_input(
    source: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set DATA2 modulation input command (0x1A 0x05 0x00 0x93).

    Args:
        source: 0=MIC, 1=ACC, 2=USB, 3=LAN, 4=LAN+USB.
    """
    if not 0 <= source <= 4:
        raise ValueError(f"DATA2 mod input must be 0-4, got {source}")
    return _build_ctl_mem_set(
        _CTL_MEM_DATA2_MOD_INPUT,
        source,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=1,
        cmd_map=cmd_map,
        cmd_name="set_data2_mod_input",
    )


def get_data3_mod_input(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read DATA3 modulation input command (0x1A 0x05 0x00 0x94)."""
    return _build_ctl_mem_get(
        _CTL_MEM_DATA3_MOD_INPUT,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_data3_mod_input",
    )


def set_data3_mod_input(
    source: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set DATA3 modulation input command (0x1A 0x05 0x00 0x94).

    Args:
        source: 0=MIC, 1=ACC, 2=USB, 3=LAN, 4=LAN+USB.
    """
    if not 0 <= source <= 4:
        raise ValueError(f"DATA3 mod input must be 0-4, got {source}")
    return _build_ctl_mem_set(
        _CTL_MEM_DATA3_MOD_INPUT,
        source,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=1,
        cmd_map=cmd_map,
        cmd_name="set_data3_mod_input",
    )


# --- CI-V Options (0x1A 0x05 0x01 0x29 / 0x30) ---


def get_civ_transceive(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read CI-V transceive command (0x1A 0x05 0x01 0x29)."""
    return _build_ctl_mem_get(
        _CTL_MEM_CIV_TRANSCEIVE,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_civ_transceive",
    )


def set_civ_transceive(
    enabled: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set CI-V transceive command (0x1A 0x05 0x01 0x29).

    Args:
        enabled: True to enable CI-V transceive mode.
    """
    return _build_ctl_mem_set(
        _CTL_MEM_CIV_TRANSCEIVE,
        1 if enabled else 0,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=1,
        cmd_map=cmd_map,
        cmd_name="set_civ_transceive",
    )


def get_civ_output_ant(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read CI-V output (ANT) command (0x1A 0x05 0x01 0x30)."""
    return _build_ctl_mem_get(
        _CTL_MEM_CIV_OUTPUT_ANT,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="get_civ_output_ant",
    )


def set_civ_output_ant(
    enabled: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set CI-V output (ANT) command (0x1A 0x05 0x01 0x30).

    Args:
        enabled: True to enable CI-V output on ANT connector.
    """
    return _build_ctl_mem_set(
        _CTL_MEM_CIV_OUTPUT_ANT,
        1 if enabled else 0,
        to_addr=to_addr,
        from_addr=from_addr,
        byte_count=1,
        cmd_map=cmd_map,
        cmd_name="set_civ_output_ant",
    )


# --- Date / Time / UTC Offset (0x1A 0x05 0x01 0x58-0x62) ---


def get_system_date(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read system date command (0x1A 0x05 0x01 0x58)."""
    return _build_ctl_mem_get(
        _CTL_MEM_SYSTEM_DATE,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="system_date",
    )


def set_system_date(
    year: int,
    month: int,
    day: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set system date command (0x1A 0x05 0x01 0x58).

    Args:
        year: 4-digit year (2000-2099).
        month: Month 1-12.
        day: Day 1-31.
    """
    if not 2000 <= year <= 2099:
        raise ValueError(f"Year must be 2000-2099, got {year}")
    if not 1 <= month <= 12:
        raise ValueError(f"Month must be 1-12, got {month}")
    if not 1 <= day <= 31:
        raise ValueError(f"Day must be 1-31, got {day}")
    bcd = (
        bcd_encode_value(year, byte_count=2)
        + bcd_encode_value(month, byte_count=1)
        + bcd_encode_value(day, byte_count=1)
    )
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "system_date", to_addr=to_addr, from_addr=from_addr, data=bcd
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_CTL_MEM,
        data=_CTL_MEM_SYSTEM_DATE + bcd,
    )


def parse_system_date_response(frame: CivFrame) -> tuple[int, int, int]:
    """Parse system date response (0x1A 0x05 0x01 0x58).

    Returns:
        Tuple of (year, month, day).
    """
    if frame.command != _CMD_CTL_MEM or frame.sub != _SUB_CTL_MEM:
        raise ValueError(f"Not a system date response: 0x{frame.command:02x}")
    data = frame.data
    if not data.startswith(_CTL_MEM_SYSTEM_DATE):
        raise ValueError(f"System date prefix mismatch: {data.hex()}")
    data = data[len(_CTL_MEM_SYSTEM_DATE) :]
    if len(data) < 4:
        raise ValueError(f"System date payload too short: {len(data)} bytes")
    year = _bcd_decode_value(data[0:2])
    month = _bcd_decode_value(data[2:3])
    day = _bcd_decode_value(data[3:4])
    return (year, month, day)


def get_system_time(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read system time command (0x1A 0x05 0x01 0x59)."""
    return _build_ctl_mem_get(
        _CTL_MEM_SYSTEM_TIME,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="system_time",
    )


def set_system_time(
    hour: int,
    minute: int,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set system time command (0x1A 0x05 0x01 0x59).

    Args:
        hour: Hour 0-23.
        minute: Minute 0-59.
    """
    if not 0 <= hour <= 23:
        raise ValueError(f"Hour must be 0-23, got {hour}")
    if not 0 <= minute <= 59:
        raise ValueError(f"Minute must be 0-59, got {minute}")
    bcd = bcd_encode_value(hour, byte_count=1) + bcd_encode_value(minute, byte_count=1)
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "system_time", to_addr=to_addr, from_addr=from_addr, data=bcd
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_CTL_MEM,
        data=_CTL_MEM_SYSTEM_TIME + bcd,
    )


def parse_system_time_response(frame: CivFrame) -> tuple[int, int]:
    """Parse system time response (0x1A 0x05 0x01 0x59).

    Returns:
        Tuple of (hour, minute).
    """
    if frame.command != _CMD_CTL_MEM or frame.sub != _SUB_CTL_MEM:
        raise ValueError(f"Not a system time response: 0x{frame.command:02x}")
    data = frame.data
    if not data.startswith(_CTL_MEM_SYSTEM_TIME):
        raise ValueError(f"System time prefix mismatch: {data.hex()}")
    data = data[len(_CTL_MEM_SYSTEM_TIME) :]
    if len(data) < 2:
        raise ValueError(f"System time payload too short: {len(data)} bytes")
    hour = _bcd_decode_value(data[0:1])
    minute = _bcd_decode_value(data[1:2])
    return (hour, minute)


def get_utc_offset(
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build read UTC offset command (0x1A 0x05 0x01 0x62)."""
    return _build_ctl_mem_get(
        _CTL_MEM_UTC_OFFSET,
        to_addr=to_addr,
        from_addr=from_addr,
        cmd_map=cmd_map,
        cmd_name="utc_offset",
    )


def set_utc_offset(
    hours: int,
    minutes: int,
    is_negative: bool,
    to_addr: int,
    from_addr: int = CONTROLLER_ADDR,
    cmd_map: CommandMap | None = None,
) -> bytes:
    """Build set UTC offset command (0x1A 0x05 0x01 0x62).

    Args:
        hours: Offset hours 0-14.
        minutes: Offset minutes, one of 0/15/30/45.
        is_negative: True for negative (west) offset.
    """
    if not 0 <= hours <= 14:
        raise ValueError(f"UTC offset hours must be 0-14, got {hours}")
    if minutes not in (0, 15, 30, 45):
        raise ValueError(f"UTC offset minutes must be 0/15/30/45, got {minutes}")
    payload = (
        bcd_encode_value(hours, byte_count=1)
        + bcd_encode_value(minutes, byte_count=1)
        + (b"\x01" if is_negative else b"\x00")
    )
    if cmd_map is not None:
        return _build_from_map(
            cmd_map, "utc_offset", to_addr=to_addr, from_addr=from_addr, data=payload
        )
    return build_civ_frame(
        to_addr,
        from_addr,
        _CMD_CTL_MEM,
        sub=_SUB_CTL_MEM,
        data=_CTL_MEM_UTC_OFFSET + payload,
    )


def parse_utc_offset_response(frame: CivFrame) -> tuple[int, int, bool]:
    """Parse UTC offset response (0x1A 0x05 0x01 0x62).

    Returns:
        Tuple of (hours, minutes, is_negative).
    """
    if frame.command != _CMD_CTL_MEM or frame.sub != _SUB_CTL_MEM:
        raise ValueError(f"Not a UTC offset response: 0x{frame.command:02x}")
    data = frame.data
    if not data.startswith(_CTL_MEM_UTC_OFFSET):
        raise ValueError(f"UTC offset prefix mismatch: {data.hex()}")
    data = data[len(_CTL_MEM_UTC_OFFSET) :]
    if len(data) < 3:
        raise ValueError(f"UTC offset payload too short: {len(data)} bytes")
    hours = _bcd_decode_value(data[0:1])
    minutes = _bcd_decode_value(data[1:2])
    is_negative = data[2] != 0x00
    return (hours, minutes, is_negative)


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


# ---------------------------------------------------------------------------
# Backward-compat aliases — old names kept for existing callers
# ---------------------------------------------------------------------------

# Frequency
get_frequency = get_freq
set_frequency = set_freq

# RF power
get_power = get_rf_power
set_power = set_rf_power

# VFO
select_vfo = set_vfo

# Scanning
start_scan = scan_start
stop_scan = scan_stop

# Speech
speech = get_speech

# Band stacking register
build_band_stack_get = get_bsr
build_band_stack_set = set_bsr

# Squelch
get_sql = get_squelch
set_sql = set_squelch

# Antenna aliases (TOML canonical pointing to the _ant1 variants)
get_antenna = get_antenna_1
set_antenna = set_antenna_1
get_rx_antenna = get_rx_antenna_ant1
set_rx_antenna = set_rx_antenna_ant1
