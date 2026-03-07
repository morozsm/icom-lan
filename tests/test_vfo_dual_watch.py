"""Unit tests for VFO/dual-watch/scanning commands (Issue #132)."""

import pytest

from icom_lan import commands
from icom_lan.commands import (
    IC_7610_ADDR,
    CONTROLLER_ADDR,
    parse_bool_response,
    parse_level_response,
)
from icom_lan.types import CivFrame

# CI-V frame constants
_PREAMBLE = b"\xfe\xfe"
_TERMINATOR = b"\xfd"

# Command bytes
_CMD_TUNING_STEP = 0x10
_CMD_SCANNING = 0x0E
_CMD_VFO = 0x07
_CMD_CTL_MEM = 0x1A
_SUB_CTL_MEM = 0x05

# VFO sub-codes
_VFO_DUAL_WATCH_OFF = 0xC0
_VFO_DUAL_WATCH_ON = 0xC1
_VFO_DUAL_WATCH_QUERY = 0xC2

# Quick command memory indices
_QUICK_DUAL_WATCH_IDX = b"\x00\x32"
_QUICK_SPLIT_IDX = b"\x00\x33"


def _frame(*payload: int) -> bytes:
    """Build a CI-V frame from raw payload bytes (to, from, cmd, ...)."""
    return _PREAMBLE + bytes([IC_7610_ADDR, CONTROLLER_ADDR, *payload]) + _TERMINATOR


def _response_frame_vfo(sub_byte: int, value: int | None = None) -> CivFrame:
    """Build a CivFrame as the radio returns for command 0x07.

    Since 0x07 is not in _COMMANDS_WITH_SUB, parse_civ_frame stores
    all payload bytes (including the sub-code) in frame.data.
    """
    data = bytes([sub_byte]) if value is None else bytes([sub_byte, value])
    return CivFrame(
        to_addr=CONTROLLER_ADDR,
        from_addr=IC_7610_ADDR,
        command=_CMD_VFO,
        sub=None,
        data=data,
    )


def _response_frame_ctl_mem(idx: bytes, value: int) -> CivFrame:
    """Build a CivFrame as the radio returns for command 0x1A sub 0x05."""
    return CivFrame(
        to_addr=CONTROLLER_ADDR,
        from_addr=IC_7610_ADDR,
        command=_CMD_CTL_MEM,
        sub=_SUB_CTL_MEM,
        data=idx + bytes([value]),
    )


def _response_frame_tuning_step(bcd_value: int) -> CivFrame:
    """Build a CivFrame as the radio returns for command 0x10."""
    return CivFrame(
        to_addr=CONTROLLER_ADDR,
        from_addr=IC_7610_ADDR,
        command=_CMD_TUNING_STEP,
        sub=None,
        data=bytes([bcd_value]),
    )


# ---------------------------------------------------------------------------
# Tuning Step (0x10)
# ---------------------------------------------------------------------------


class TestTuningStep:
    """Tests for get_tuning_step / set_tuning_step."""

    def test_get_tuning_step_builds_correct_frame(self) -> None:
        assert commands.get_tuning_step() == _frame(_CMD_TUNING_STEP)

    def test_set_tuning_step_index_0_builds_correct_frame(self) -> None:
        assert commands.set_tuning_step(0) == _frame(_CMD_TUNING_STEP, 0x00)

    def test_set_tuning_step_index_1_builds_correct_frame(self) -> None:
        assert commands.set_tuning_step(1) == _frame(_CMD_TUNING_STEP, 0x01)

    def test_set_tuning_step_index_5_builds_correct_frame(self) -> None:
        assert commands.set_tuning_step(5) == _frame(_CMD_TUNING_STEP, 0x05)

    def test_set_tuning_step_index_8_builds_correct_frame(self) -> None:
        # Max value per IC-7610.rig
        assert commands.set_tuning_step(8) == _frame(_CMD_TUNING_STEP, 0x08)

    def test_set_tuning_step_rejects_value_above_maximum(self) -> None:
        with pytest.raises(ValueError):
            commands.set_tuning_step(9)

    def test_set_tuning_step_rejects_negative_value(self) -> None:
        with pytest.raises(ValueError):
            commands.set_tuning_step(-1)

    def test_get_tuning_step_starts_with_preamble(self) -> None:
        assert commands.get_tuning_step().startswith(_PREAMBLE)

    def test_get_tuning_step_ends_with_terminator(self) -> None:
        assert commands.get_tuning_step().endswith(_TERMINATOR)

    def test_get_tuning_step_contains_command_byte(self) -> None:
        assert _CMD_TUNING_STEP in commands.get_tuning_step()

    def test_get_tuning_step_custom_addresses(self) -> None:
        frame = commands.get_tuning_step(to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1

    def test_set_tuning_step_custom_addresses(self) -> None:
        frame = commands.set_tuning_step(3, to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1

    def test_parse_tuning_step_response_index_0(self) -> None:
        frame = _response_frame_tuning_step(0x00)
        value = parse_level_response(
            frame, command=_CMD_TUNING_STEP, sub=None, bcd_bytes=1
        )
        assert value == 0

    def test_parse_tuning_step_response_index_5(self) -> None:
        frame = _response_frame_tuning_step(0x05)
        value = parse_level_response(
            frame, command=_CMD_TUNING_STEP, sub=None, bcd_bytes=1
        )
        assert value == 5

    def test_parse_tuning_step_response_index_8(self) -> None:
        frame = _response_frame_tuning_step(0x08)
        value = parse_level_response(
            frame, command=_CMD_TUNING_STEP, sub=None, bcd_bytes=1
        )
        assert value == 8

    def test_get_and_set_produce_distinct_frames(self) -> None:
        assert commands.get_tuning_step() != commands.set_tuning_step(0)


# ---------------------------------------------------------------------------
# Scanning (0x0E)
# ---------------------------------------------------------------------------


class TestScanning:
    """Tests for start_scan / stop_scan."""

    def test_start_scan_builds_correct_frame(self) -> None:
        assert commands.start_scan() == _frame(_CMD_SCANNING, 0x01)

    def test_stop_scan_builds_correct_frame(self) -> None:
        assert commands.stop_scan() == _frame(_CMD_SCANNING, 0x00)

    def test_start_scan_starts_with_preamble(self) -> None:
        assert commands.start_scan().startswith(_PREAMBLE)

    def test_stop_scan_ends_with_terminator(self) -> None:
        assert commands.stop_scan().endswith(_TERMINATOR)

    def test_start_and_stop_scan_differ_only_in_data_byte(self) -> None:
        start = commands.start_scan()
        stop = commands.stop_scan()
        # Same command byte, different data
        assert start != stop
        assert start[4] == _CMD_SCANNING
        assert stop[4] == _CMD_SCANNING

    def test_start_scan_data_byte_is_one(self) -> None:
        frame = commands.start_scan()
        assert frame[5] == 0x01

    def test_stop_scan_data_byte_is_zero(self) -> None:
        frame = commands.stop_scan()
        assert frame[5] == 0x00

    def test_start_scan_custom_addresses(self) -> None:
        frame = commands.start_scan(to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1

    def test_stop_scan_custom_addresses(self) -> None:
        frame = commands.stop_scan(to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1


# ---------------------------------------------------------------------------
# Dual Watch (0x07 0xC0 / 0xC1 / 0xC2)
# ---------------------------------------------------------------------------


class TestDualWatch:
    """Tests for set_dual_watch_off / set_dual_watch_on / get_dual_watch."""

    def test_set_dual_watch_off_builds_correct_frame(self) -> None:
        assert commands.set_dual_watch_off() == _frame(_CMD_VFO, _VFO_DUAL_WATCH_OFF)

    def test_set_dual_watch_on_builds_correct_frame(self) -> None:
        assert commands.set_dual_watch_on() == _frame(_CMD_VFO, _VFO_DUAL_WATCH_ON)

    def test_get_dual_watch_builds_correct_frame(self) -> None:
        assert commands.get_dual_watch() == _frame(_CMD_VFO, _VFO_DUAL_WATCH_QUERY)

    def test_set_dual_watch_wrapper_true_equals_set_on(self) -> None:
        assert commands.set_dual_watch(True) == commands.set_dual_watch_on()

    def test_set_dual_watch_wrapper_false_equals_set_off(self) -> None:
        assert commands.set_dual_watch(False) == commands.set_dual_watch_off()

    def test_dual_watch_on_and_off_are_distinct(self) -> None:
        assert commands.set_dual_watch_on() != commands.set_dual_watch_off()

    def test_dual_watch_on_and_query_are_distinct(self) -> None:
        assert commands.set_dual_watch_on() != commands.get_dual_watch()

    def test_dual_watch_off_and_query_are_distinct(self) -> None:
        assert commands.set_dual_watch_off() != commands.get_dual_watch()

    def test_set_dual_watch_off_starts_with_preamble(self) -> None:
        assert commands.set_dual_watch_off().startswith(_PREAMBLE)

    def test_set_dual_watch_on_ends_with_terminator(self) -> None:
        assert commands.set_dual_watch_on().endswith(_TERMINATOR)

    def test_get_dual_watch_command_byte(self) -> None:
        frame = commands.get_dual_watch()
        assert frame[4] == _CMD_VFO

    def test_set_dual_watch_off_custom_addresses(self) -> None:
        frame = commands.set_dual_watch_off(to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1

    def test_set_dual_watch_on_custom_addresses(self) -> None:
        frame = commands.set_dual_watch_on(to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1

    def test_get_dual_watch_custom_addresses(self) -> None:
        frame = commands.get_dual_watch(to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1

    def test_parse_dual_watch_response_on(self) -> None:
        # Radio responds: FE FE E0 98 07 C2 01 FD
        # Since 0x07 not in _COMMANDS_WITH_SUB, sub=None, data=b"\xC2\x01"
        frame = _response_frame_vfo(_VFO_DUAL_WATCH_QUERY, 0x01)
        result = parse_bool_response(
            frame, command=_CMD_VFO, prefix=bytes([_VFO_DUAL_WATCH_QUERY])
        )
        assert result is True

    def test_parse_dual_watch_response_off(self) -> None:
        frame = _response_frame_vfo(_VFO_DUAL_WATCH_QUERY, 0x00)
        result = parse_bool_response(
            frame, command=_CMD_VFO, prefix=bytes([_VFO_DUAL_WATCH_QUERY])
        )
        assert result is False




# ---------------------------------------------------------------------------
# Quick Commands (0x1A 0x05 0x00 0x32/0x33)
# ---------------------------------------------------------------------------


class TestQuickCommands:
    """Tests for quick_dual_watch / quick_split (fire-and-forget triggers)."""

    def test_quick_dual_watch_builds_correct_frame(self) -> None:
        """quick_dual_watch builds 0x1A 0x05 0x00 0x32 frame."""
        expected = _PREAMBLE + bytes(
            [IC_7610_ADDR, CONTROLLER_ADDR, _CMD_CTL_MEM, 0x05, 0x00, 0x32]
        ) + _TERMINATOR
        assert commands.quick_dual_watch() == expected

    def test_quick_split_builds_correct_frame(self) -> None:
        """quick_split builds 0x1A 0x05 0x00 0x33 frame."""
        expected = _PREAMBLE + bytes(
            [IC_7610_ADDR, CONTROLLER_ADDR, _CMD_CTL_MEM, 0x05, 0x00, 0x33]
        ) + _TERMINATOR
        assert commands.quick_split() == expected

    def test_quick_dual_watch_distinct_from_quick_split(self) -> None:
        """quick_dual_watch and quick_split produce distinct frames."""
        assert commands.quick_dual_watch() != commands.quick_split()

    def test_quick_dual_watch_custom_addresses(self) -> None:
        """quick_dual_watch accepts custom to_addr/from_addr."""
        frame = commands.quick_dual_watch(to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1

    def test_quick_split_custom_addresses(self) -> None:
        """quick_split accepts custom to_addr/from_addr."""
        frame = commands.quick_split(to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1


# ---------------------------------------------------------------------------
# Command Distinctness
# ---------------------------------------------------------------------------


class TestCommandDistinctness:
    """Verify that different commands produce distinct byte sequences."""

    def test_dual_watch_distinct_from_quick_dual_watch(self) -> None:
        """Regular dual watch != quick dual watch."""
        assert commands.get_dual_watch() != commands.quick_dual_watch()

    def test_scanning_distinct_from_tuning_step(self) -> None:
        """Scanning commands != tuning step commands."""
        assert commands.start_scan() != commands.get_tuning_step()
