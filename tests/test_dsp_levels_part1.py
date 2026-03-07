"""Unit tests for DSP level commands — Part 1: APF/NR/PBT/NB (Issue #130)."""

import pytest

from icom_lan import commands
from icom_lan.commands import (
    IC_7610_ADDR,
    CONTROLLER_ADDR,
    RECEIVER_MAIN,
    RECEIVER_SUB,
    parse_level_response,
)
from icom_lan.types import CivFrame

# CI-V frame constants
_PREAMBLE = b"\xfe\xfe"
_TERMINATOR = b"\xfd"
_CMD_LEVEL = 0x14
_CMD_CMD29 = 0x29

# Sub-command bytes under 0x14
_SUB_APF_TYPE_LEVEL = 0x05
_SUB_NR_LEVEL = 0x06
_SUB_PBT_INNER = 0x07
_SUB_PBT_OUTER = 0x08
_SUB_NB_LEVEL = 0x12


def _cmd29_level_get(sub: int, receiver: int = RECEIVER_MAIN) -> bytes:
    """Expected bytes for a cmd29-wrapped level get frame."""
    return (
        _PREAMBLE
        + bytes([IC_7610_ADDR, CONTROLLER_ADDR, _CMD_CMD29, receiver, _CMD_LEVEL, sub])
        + _TERMINATOR
    )


def _level_bcd(value: int) -> bytes:
    """Encode 0-255 level as 2-byte BCD (mirrors _level_bcd_encode)."""
    d = f"{value:04d}"
    return bytes([(int(d[0]) << 4) | int(d[1]), (int(d[2]) << 4) | int(d[3])])


def _cmd29_level_set(sub: int, level: int, receiver: int = RECEIVER_MAIN) -> bytes:
    """Expected bytes for a cmd29-wrapped level set frame."""
    return (
        _PREAMBLE
        + bytes([IC_7610_ADDR, CONTROLLER_ADDR, _CMD_CMD29, receiver, _CMD_LEVEL, sub])
        + _level_bcd(level)
        + _TERMINATOR
    )


def _level_response_frame(sub: int, level: int) -> CivFrame:
    """Build a CivFrame as a radio would return for a level command."""
    return CivFrame(
        to_addr=CONTROLLER_ADDR,
        from_addr=IC_7610_ADDR,
        command=_CMD_LEVEL,
        sub=sub,
        data=_level_bcd(level),
    )


# ---------------------------------------------------------------------------
# APF Type Level (cmd29, int 0-255)
# ---------------------------------------------------------------------------


class TestAPFTypeLevel:
    """Tests for get_apf_type_level / set_apf_type_level."""

    def test_get_apf_type_level_main_receiver(self) -> None:
        assert commands.get_apf_type_level(receiver=RECEIVER_MAIN) == _cmd29_level_get(
            _SUB_APF_TYPE_LEVEL, RECEIVER_MAIN
        )

    def test_get_apf_type_level_sub_receiver(self) -> None:
        assert commands.get_apf_type_level(receiver=RECEIVER_SUB) == _cmd29_level_get(
            _SUB_APF_TYPE_LEVEL, RECEIVER_SUB
        )

    def test_get_apf_type_level_default_is_main(self) -> None:
        assert commands.get_apf_type_level() == commands.get_apf_type_level(receiver=RECEIVER_MAIN)

    def test_set_apf_type_level_main_receiver(self) -> None:
        assert commands.set_apf_type_level(128, receiver=RECEIVER_MAIN) == _cmd29_level_set(
            _SUB_APF_TYPE_LEVEL, 128, RECEIVER_MAIN
        )

    def test_set_apf_type_level_sub_receiver(self) -> None:
        assert commands.set_apf_type_level(64, receiver=RECEIVER_SUB) == _cmd29_level_set(
            _SUB_APF_TYPE_LEVEL, 64, RECEIVER_SUB
        )

    def test_set_apf_type_level_boundary_zero(self) -> None:
        assert commands.set_apf_type_level(0) == _cmd29_level_set(_SUB_APF_TYPE_LEVEL, 0)

    def test_set_apf_type_level_boundary_255(self) -> None:
        assert commands.set_apf_type_level(255) == _cmd29_level_set(_SUB_APF_TYPE_LEVEL, 255)

    def test_set_apf_type_level_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            commands.set_apf_type_level(-1)

    def test_set_apf_type_level_rejects_over_255(self) -> None:
        with pytest.raises(ValueError):
            commands.set_apf_type_level(256)

    def test_parse_apf_type_level_response(self) -> None:
        frame = _level_response_frame(_SUB_APF_TYPE_LEVEL, 128)
        value = parse_level_response(frame, sub=_SUB_APF_TYPE_LEVEL)
        assert value == 128

    def test_parse_apf_type_level_response_zero(self) -> None:
        frame = _level_response_frame(_SUB_APF_TYPE_LEVEL, 0)
        value = parse_level_response(frame, sub=_SUB_APF_TYPE_LEVEL)
        assert value == 0

    def test_parse_apf_type_level_response_max(self) -> None:
        frame = _level_response_frame(_SUB_APF_TYPE_LEVEL, 255)
        value = parse_level_response(frame, sub=_SUB_APF_TYPE_LEVEL)
        assert value == 255


# ---------------------------------------------------------------------------
# NR Level (cmd29, int 0-255)
# ---------------------------------------------------------------------------


class TestNRLevel:
    """Tests for get_nr_level / set_nr_level."""

    def test_get_nr_level_main_receiver(self) -> None:
        assert commands.get_nr_level(receiver=RECEIVER_MAIN) == _cmd29_level_get(
            _SUB_NR_LEVEL, RECEIVER_MAIN
        )

    def test_get_nr_level_sub_receiver(self) -> None:
        assert commands.get_nr_level(receiver=RECEIVER_SUB) == _cmd29_level_get(
            _SUB_NR_LEVEL, RECEIVER_SUB
        )

    def test_get_nr_level_default_is_main(self) -> None:
        assert commands.get_nr_level() == commands.get_nr_level(receiver=RECEIVER_MAIN)

    def test_set_nr_level_main_receiver(self) -> None:
        assert commands.set_nr_level(100, receiver=RECEIVER_MAIN) == _cmd29_level_set(
            _SUB_NR_LEVEL, 100, RECEIVER_MAIN
        )

    def test_set_nr_level_sub_receiver(self) -> None:
        assert commands.set_nr_level(200, receiver=RECEIVER_SUB) == _cmd29_level_set(
            _SUB_NR_LEVEL, 200, RECEIVER_SUB
        )

    def test_set_nr_level_boundary_zero(self) -> None:
        assert commands.set_nr_level(0) == _cmd29_level_set(_SUB_NR_LEVEL, 0)

    def test_set_nr_level_boundary_255(self) -> None:
        assert commands.set_nr_level(255) == _cmd29_level_set(_SUB_NR_LEVEL, 255)

    def test_set_nr_level_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            commands.set_nr_level(-1)

    def test_set_nr_level_rejects_over_255(self) -> None:
        with pytest.raises(ValueError):
            commands.set_nr_level(256)

    def test_parse_nr_level_response(self) -> None:
        frame = _level_response_frame(_SUB_NR_LEVEL, 50)
        value = parse_level_response(frame, sub=_SUB_NR_LEVEL)
        assert value == 50

    def test_parse_nr_level_response_zero(self) -> None:
        frame = _level_response_frame(_SUB_NR_LEVEL, 0)
        value = parse_level_response(frame, sub=_SUB_NR_LEVEL)
        assert value == 0

    def test_parse_nr_level_response_max(self) -> None:
        frame = _level_response_frame(_SUB_NR_LEVEL, 255)
        value = parse_level_response(frame, sub=_SUB_NR_LEVEL)
        assert value == 255


# ---------------------------------------------------------------------------
# PBT Inner (cmd29, int 0-255)
# ---------------------------------------------------------------------------


class TestPBTInner:
    """Tests for get_pbt_inner / set_pbt_inner."""

    def test_get_pbt_inner_main_receiver(self) -> None:
        assert commands.get_pbt_inner(receiver=RECEIVER_MAIN) == _cmd29_level_get(
            _SUB_PBT_INNER, RECEIVER_MAIN
        )

    def test_get_pbt_inner_sub_receiver(self) -> None:
        assert commands.get_pbt_inner(receiver=RECEIVER_SUB) == _cmd29_level_get(
            _SUB_PBT_INNER, RECEIVER_SUB
        )

    def test_get_pbt_inner_default_is_main(self) -> None:
        assert commands.get_pbt_inner() == commands.get_pbt_inner(receiver=RECEIVER_MAIN)

    def test_set_pbt_inner_main_receiver(self) -> None:
        assert commands.set_pbt_inner(75, receiver=RECEIVER_MAIN) == _cmd29_level_set(
            _SUB_PBT_INNER, 75, RECEIVER_MAIN
        )

    def test_set_pbt_inner_sub_receiver(self) -> None:
        assert commands.set_pbt_inner(150, receiver=RECEIVER_SUB) == _cmd29_level_set(
            _SUB_PBT_INNER, 150, RECEIVER_SUB
        )

    def test_set_pbt_inner_boundary_zero(self) -> None:
        assert commands.set_pbt_inner(0) == _cmd29_level_set(_SUB_PBT_INNER, 0)

    def test_set_pbt_inner_boundary_255(self) -> None:
        assert commands.set_pbt_inner(255) == _cmd29_level_set(_SUB_PBT_INNER, 255)

    def test_set_pbt_inner_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            commands.set_pbt_inner(-1)

    def test_set_pbt_inner_rejects_over_255(self) -> None:
        with pytest.raises(ValueError):
            commands.set_pbt_inner(256)

    def test_parse_pbt_inner_response(self) -> None:
        frame = _level_response_frame(_SUB_PBT_INNER, 75)
        value = parse_level_response(frame, sub=_SUB_PBT_INNER)
        assert value == 75

    def test_parse_pbt_inner_response_zero(self) -> None:
        frame = _level_response_frame(_SUB_PBT_INNER, 0)
        value = parse_level_response(frame, sub=_SUB_PBT_INNER)
        assert value == 0

    def test_parse_pbt_inner_response_max(self) -> None:
        frame = _level_response_frame(_SUB_PBT_INNER, 255)
        value = parse_level_response(frame, sub=_SUB_PBT_INNER)
        assert value == 255

    def test_pbt_inner_sub_distinct_from_pbt_outer(self) -> None:
        assert commands.get_pbt_inner() != commands.get_pbt_outer()


# ---------------------------------------------------------------------------
# PBT Outer (cmd29, int 0-255)
# ---------------------------------------------------------------------------


class TestPBTOuter:
    """Tests for get_pbt_outer / set_pbt_outer."""

    def test_get_pbt_outer_main_receiver(self) -> None:
        assert commands.get_pbt_outer(receiver=RECEIVER_MAIN) == _cmd29_level_get(
            _SUB_PBT_OUTER, RECEIVER_MAIN
        )

    def test_get_pbt_outer_sub_receiver(self) -> None:
        assert commands.get_pbt_outer(receiver=RECEIVER_SUB) == _cmd29_level_get(
            _SUB_PBT_OUTER, RECEIVER_SUB
        )

    def test_get_pbt_outer_default_is_main(self) -> None:
        assert commands.get_pbt_outer() == commands.get_pbt_outer(receiver=RECEIVER_MAIN)

    def test_set_pbt_outer_main_receiver(self) -> None:
        assert commands.set_pbt_outer(90, receiver=RECEIVER_MAIN) == _cmd29_level_set(
            _SUB_PBT_OUTER, 90, RECEIVER_MAIN
        )

    def test_set_pbt_outer_sub_receiver(self) -> None:
        assert commands.set_pbt_outer(180, receiver=RECEIVER_SUB) == _cmd29_level_set(
            _SUB_PBT_OUTER, 180, RECEIVER_SUB
        )

    def test_set_pbt_outer_boundary_zero(self) -> None:
        assert commands.set_pbt_outer(0) == _cmd29_level_set(_SUB_PBT_OUTER, 0)

    def test_set_pbt_outer_boundary_255(self) -> None:
        assert commands.set_pbt_outer(255) == _cmd29_level_set(_SUB_PBT_OUTER, 255)

    def test_set_pbt_outer_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            commands.set_pbt_outer(-1)

    def test_set_pbt_outer_rejects_over_255(self) -> None:
        with pytest.raises(ValueError):
            commands.set_pbt_outer(256)

    def test_parse_pbt_outer_response(self) -> None:
        frame = _level_response_frame(_SUB_PBT_OUTER, 90)
        value = parse_level_response(frame, sub=_SUB_PBT_OUTER)
        assert value == 90

    def test_parse_pbt_outer_response_zero(self) -> None:
        frame = _level_response_frame(_SUB_PBT_OUTER, 0)
        value = parse_level_response(frame, sub=_SUB_PBT_OUTER)
        assert value == 0

    def test_parse_pbt_outer_response_max(self) -> None:
        frame = _level_response_frame(_SUB_PBT_OUTER, 255)
        value = parse_level_response(frame, sub=_SUB_PBT_OUTER)
        assert value == 255


# ---------------------------------------------------------------------------
# NB Level (cmd29, int 0-255)
# ---------------------------------------------------------------------------


class TestNBLevel:
    """Tests for get_nb_level / set_nb_level."""

    def test_get_nb_level_main_receiver(self) -> None:
        assert commands.get_nb_level(receiver=RECEIVER_MAIN) == _cmd29_level_get(
            _SUB_NB_LEVEL, RECEIVER_MAIN
        )

    def test_get_nb_level_sub_receiver(self) -> None:
        assert commands.get_nb_level(receiver=RECEIVER_SUB) == _cmd29_level_get(
            _SUB_NB_LEVEL, RECEIVER_SUB
        )

    def test_get_nb_level_default_is_main(self) -> None:
        assert commands.get_nb_level() == commands.get_nb_level(receiver=RECEIVER_MAIN)

    def test_set_nb_level_main_receiver(self) -> None:
        assert commands.set_nb_level(55, receiver=RECEIVER_MAIN) == _cmd29_level_set(
            _SUB_NB_LEVEL, 55, RECEIVER_MAIN
        )

    def test_set_nb_level_sub_receiver(self) -> None:
        assert commands.set_nb_level(210, receiver=RECEIVER_SUB) == _cmd29_level_set(
            _SUB_NB_LEVEL, 210, RECEIVER_SUB
        )

    def test_set_nb_level_boundary_zero(self) -> None:
        assert commands.set_nb_level(0) == _cmd29_level_set(_SUB_NB_LEVEL, 0)

    def test_set_nb_level_boundary_255(self) -> None:
        assert commands.set_nb_level(255) == _cmd29_level_set(_SUB_NB_LEVEL, 255)

    def test_set_nb_level_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            commands.set_nb_level(-1)

    def test_set_nb_level_rejects_over_255(self) -> None:
        with pytest.raises(ValueError):
            commands.set_nb_level(256)

    def test_parse_nb_level_response(self) -> None:
        frame = _level_response_frame(_SUB_NB_LEVEL, 55)
        value = parse_level_response(frame, sub=_SUB_NB_LEVEL)
        assert value == 55

    def test_parse_nb_level_response_zero(self) -> None:
        frame = _level_response_frame(_SUB_NB_LEVEL, 0)
        value = parse_level_response(frame, sub=_SUB_NB_LEVEL)
        assert value == 0

    def test_parse_nb_level_response_max(self) -> None:
        frame = _level_response_frame(_SUB_NB_LEVEL, 255)
        value = parse_level_response(frame, sub=_SUB_NB_LEVEL)
        assert value == 255

    def test_nb_level_sub_distinct_from_nr_level(self) -> None:
        assert commands.get_nb_level() != commands.get_nr_level()
