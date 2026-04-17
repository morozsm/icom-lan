"""Unit tests for VFO/dual-watch/scanning commands (Issue #132)."""

import warnings
from unittest.mock import patch

import pytest

from icom_lan import commands
from icom_lan import IC_7610_ADDR
from icom_lan.commands import (
    CONTROLLER_ADDR,
    parse_bool_response,
    parse_level_response
)
from icom_lan.exceptions import CommandError
from icom_lan.radio import IcomRadio
from icom_lan.types import CivFrame
from _command_test_helpers import bind_default_addr_globals

bind_default_addr_globals(globals(), to_addr=IC_7610_ADDR)

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
        assert commands.scan_start() == _frame(_CMD_SCANNING, 0x01)

    def test_stop_scan_builds_correct_frame(self) -> None:
        assert commands.scan_stop() == _frame(_CMD_SCANNING, 0x00)

    def test_start_scan_starts_with_preamble(self) -> None:
        assert commands.scan_start().startswith(_PREAMBLE)

    def test_stop_scan_ends_with_terminator(self) -> None:
        assert commands.scan_stop().endswith(_TERMINATOR)

    def test_start_and_stop_scan_differ_only_in_data_byte(self) -> None:
        start = commands.scan_start()
        stop = commands.scan_stop()
        # Same command byte, different data
        assert start != stop
        assert start[4] == _CMD_SCANNING
        assert stop[4] == _CMD_SCANNING

    def test_start_scan_data_byte_is_one(self) -> None:
        frame = commands.scan_start()
        assert frame[5] == 0x01

    def test_stop_scan_data_byte_is_zero(self) -> None:
        frame = commands.scan_stop()
        assert frame[5] == 0x00

    def test_start_scan_custom_addresses(self) -> None:
        frame = commands.scan_start(to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1

    def test_stop_scan_custom_addresses(self) -> None:
        frame = commands.scan_stop(to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1


class TestScanTypes:
    """Tests for extended scan type commands (0x0E with various sub-bytes)."""

    def test_scan_start_type_programmed(self) -> None:
        """scan_start_type(0x01) builds programmed scan frame."""
        assert commands.scan_start_type(0x01) == _frame(_CMD_SCANNING, 0x01)

    def test_scan_start_type_programmed_p2(self) -> None:
        """scan_start_type(0x02) builds programmed scan P2 frame."""
        assert commands.scan_start_type(0x02) == _frame(_CMD_SCANNING, 0x02)

    def test_scan_start_type_df(self) -> None:
        """scan_start_type(0x03) builds delta-F scan frame."""
        assert commands.scan_start_type(0x03) == _frame(_CMD_SCANNING, 0x03)

    def test_scan_start_type_fine_programmed(self) -> None:
        """scan_start_type(0x12) builds fine programmed scan frame."""
        assert commands.scan_start_type(0x12) == _frame(_CMD_SCANNING, 0x12)

    def test_scan_start_type_memory(self) -> None:
        """scan_start_type(0x22) builds memory scan frame."""
        assert commands.scan_start_type(0x22) == _frame(_CMD_SCANNING, 0x22)

    def test_scan_start_type_select_memory(self) -> None:
        """scan_start_type(0x23) builds select memory scan frame."""
        assert commands.scan_start_type(0x23) == _frame(_CMD_SCANNING, 0x23)

    def test_scan_start_type_custom_addresses(self) -> None:
        frame = commands.scan_start_type(0x03, to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1

    def test_scan_start_type_rejects_invalid(self) -> None:
        """scan_start_type rejects values not in VALID_SCAN_TYPES."""
        with pytest.raises(ValueError, match="scan_type"):
            commands.scan_start_type(0xFF)


class TestScanDfSpan:
    """Tests for ΔF scan span selection (0x0E 0xA1-0xA7)."""

    def test_scan_set_df_span_5k(self) -> None:
        assert commands.scan_set_df_span(0xA1) == _frame(_CMD_SCANNING, 0xA1)

    def test_scan_set_df_span_10k(self) -> None:
        assert commands.scan_set_df_span(0xA2) == _frame(_CMD_SCANNING, 0xA2)

    def test_scan_set_df_span_20k(self) -> None:
        assert commands.scan_set_df_span(0xA3) == _frame(_CMD_SCANNING, 0xA3)

    def test_scan_set_df_span_50k(self) -> None:
        assert commands.scan_set_df_span(0xA4) == _frame(_CMD_SCANNING, 0xA4)

    def test_scan_set_df_span_100k(self) -> None:
        assert commands.scan_set_df_span(0xA5) == _frame(_CMD_SCANNING, 0xA5)

    def test_scan_set_df_span_500k(self) -> None:
        assert commands.scan_set_df_span(0xA6) == _frame(_CMD_SCANNING, 0xA6)

    def test_scan_set_df_span_1m(self) -> None:
        assert commands.scan_set_df_span(0xA7) == _frame(_CMD_SCANNING, 0xA7)

    def test_scan_set_df_span_rejects_invalid(self) -> None:
        with pytest.raises(ValueError, match="df_span"):
            commands.scan_set_df_span(0xA0)

    def test_scan_set_df_span_custom_addresses(self) -> None:
        frame = commands.scan_set_df_span(0xA3, to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1


class TestScanResume:
    """Tests for scan resume mode (0x0E 0xD0-0xD3)."""

    def test_scan_set_resume_off(self) -> None:
        assert commands.scan_set_resume(0xD0) == _frame(_CMD_SCANNING, 0xD0)

    def test_scan_set_resume_5s(self) -> None:
        assert commands.scan_set_resume(0xD1) == _frame(_CMD_SCANNING, 0xD1)

    def test_scan_set_resume_10s(self) -> None:
        assert commands.scan_set_resume(0xD2) == _frame(_CMD_SCANNING, 0xD2)

    def test_scan_set_resume_15s(self) -> None:
        assert commands.scan_set_resume(0xD3) == _frame(_CMD_SCANNING, 0xD3)

    def test_scan_set_resume_rejects_invalid(self) -> None:
        with pytest.raises(ValueError, match="resume_mode"):
            commands.scan_set_resume(0xD4)

    def test_scan_set_resume_custom_addresses(self) -> None:
        frame = commands.scan_set_resume(0xD1, to_addr=0xA4, from_addr=0xE1)
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
        expected = (
            _PREAMBLE
            + bytes([IC_7610_ADDR, CONTROLLER_ADDR, _CMD_CTL_MEM, 0x05, 0x00, 0x32])
            + _TERMINATOR
        )
        assert commands.quick_dual_watch() == expected

    def test_quick_split_builds_correct_frame(self) -> None:
        """quick_split builds 0x1A 0x05 0x00 0x33 frame."""
        expected = (
            _PREAMBLE
            + bytes([IC_7610_ADDR, CONTROLLER_ADDR, _CMD_CTL_MEM, 0x05, 0x00, 0x33])
            + _TERMINATOR
        )
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
        assert commands.scan_start() != commands.get_tuning_step()


# ---------------------------------------------------------------------------
# swap_main_sub / swap_vfo_ab distinct methods (Issue #714)
# ---------------------------------------------------------------------------


def _make_radio(model: str) -> IcomRadio:
    """Build a connected IcomRadio for ``model`` with a recording stub for sends."""
    r = IcomRadio("127.0.0.1", model=model, timeout=0.05)
    r._connected = True
    r._check_connected = lambda: None  # type: ignore[method-assign]
    return r


class _RecordingSend:
    """Stand-in for ``_send_civ_raw`` that captures CI-V payloads."""

    def __init__(self) -> None:
        self.frames: list[bytes] = []

    async def __call__(self, civ: bytes, **_: object) -> None:
        self.frames.append(civ)
        return None


class TestSwapMainSubVsSwapVfoAb:
    """Issue #714 — distinct MAIN/SUB vs A/B swap/equalize methods."""

    @pytest.mark.asyncio
    async def test_ic7610_swap_main_sub_sends_0x07_0xb0(self) -> None:
        r = _make_radio("IC-7610")
        send = _RecordingSend()
        with patch.object(r, "_send_civ_raw", send):
            await r.swap_main_sub()
        assert len(send.frames) == 1
        # Frame tail is 07 B0 FD (command + data + terminator)
        assert send.frames[0].endswith(b"\x07\xb0\xfd")

    @pytest.mark.asyncio
    async def test_ic7610_equalize_main_sub_sends_0x07_0xb1(self) -> None:
        r = _make_radio("IC-7610")
        send = _RecordingSend()
        with patch.object(r, "_send_civ_raw", send):
            await r.equalize_main_sub()
        assert len(send.frames) == 1
        assert send.frames[0].endswith(b"\x07\xb1\xfd")

    @pytest.mark.asyncio
    async def test_ic7610_swap_vfo_ab_selects_main_then_swaps(self) -> None:
        """On dual-RX, swap_vfo_ab(0) first selects MAIN, then sends swap code."""
        r = _make_radio("IC-7610")
        set_vfo_calls: list[str] = []

        async def _fake_set_vfo(vfo: str = "A") -> None:
            set_vfo_calls.append(vfo.upper())

        send = _RecordingSend()
        with patch.object(r, "set_vfo", _fake_set_vfo), patch.object(
            r, "_send_civ_raw", send
        ):
            await r.swap_vfo_ab(receiver=0)

        assert set_vfo_calls == ["MAIN"]
        # Falls back to swap_main_sub_code (0xB0) since ic7610.toml declares
        # only the legacy ``swap`` key which maps to swap_main_sub_code.
        assert len(send.frames) == 1
        assert send.frames[0].endswith(b"\x07\xb0\xfd")

    @pytest.mark.asyncio
    async def test_ic7300_swap_main_sub_raises(self) -> None:
        """Single-RX profile rejects swap_main_sub with CommandError."""
        r = _make_radio("IC-7300")
        with pytest.raises(CommandError, match="not dual-RX"):
            await r.swap_main_sub()

    @pytest.mark.asyncio
    async def test_ic7300_equalize_main_sub_raises(self) -> None:
        r = _make_radio("IC-7300")
        with pytest.raises(CommandError, match="not dual-RX"):
            await r.equalize_main_sub()

    @pytest.mark.asyncio
    async def test_ic7300_swap_vfo_ab_sends_directly(self) -> None:
        """Single-RX: no receiver select, just the swap opcode."""
        r = _make_radio("IC-7300")
        set_vfo_calls: list[str] = []

        async def _fake_set_vfo(vfo: str = "A") -> None:
            set_vfo_calls.append(vfo.upper())

        send = _RecordingSend()
        with patch.object(r, "set_vfo", _fake_set_vfo), patch.object(
            r, "_send_civ_raw", send
        ):
            await r.swap_vfo_ab(receiver=0)

        # No receiver-select step on 1-Rx.
        assert set_vfo_calls == []
        assert len(send.frames) == 1
        # IC-7300 profile declares swap_ab_code = 0xB0 via legacy mapping.
        assert send.frames[0].endswith(b"\x07\xb0\xfd")

    @pytest.mark.asyncio
    async def test_ic7300_equalize_vfo_ab_sends_0x07_0xa0(self) -> None:
        r = _make_radio("IC-7300")
        send = _RecordingSend()
        with patch.object(r, "_send_civ_raw", send):
            await r.equalize_vfo_ab(receiver=0)
        assert len(send.frames) == 1
        # IC-7300 declares equal = [0xA0] in scheme=ab → equal_ab_code.
        assert send.frames[0].endswith(b"\x07\xa0\xfd")

    @pytest.mark.asyncio
    async def test_vfo_exchange_alias_emits_deprecation_warning(self) -> None:
        r = _make_radio("IC-7610")
        send = _RecordingSend()
        with patch.object(r, "_send_civ_raw", send):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                await r.vfo_exchange()
        # DeprecationWarning raised once, pointing to caller (this test file).
        dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep) == 1
        assert "vfo_exchange" in str(dep[0].message)
        assert dep[0].filename.endswith("test_vfo_dual_watch.py")
        # Still dispatches to swap_main_sub under the hood.
        assert len(send.frames) == 1
        assert send.frames[0].endswith(b"\x07\xb0\xfd")

    @pytest.mark.asyncio
    async def test_vfo_equalize_alias_emits_deprecation_warning(self) -> None:
        r = _make_radio("IC-7300")
        send = _RecordingSend()
        with patch.object(r, "_send_civ_raw", send):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                await r.vfo_equalize()
        dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep) == 1
        assert "vfo_equalize" in str(dep[0].message)
        assert dep[0].filename.endswith("test_vfo_dual_watch.py")
        assert len(send.frames) == 1
        assert send.frames[0].endswith(b"\x07\xa0\xfd")
