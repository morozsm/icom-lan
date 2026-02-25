"""Tests for CI-V command encoding and decoding."""

import pytest

from icom_lan.commands import (
    IC_7610_ADDR,
    CONTROLLER_ADDR,
    build_civ_frame,
    parse_civ_frame,
    get_frequency,
    set_frequency,
    get_mode,
    set_mode,
    get_power,
    set_power,
    get_s_meter,
    get_swr,
    get_alc,
    ptt_on,
    ptt_off,
    parse_frequency_response,
    parse_mode_response,
    parse_meter_response,
    parse_ack_nak,
)
from icom_lan.types import CivFrame, Mode


class TestConstants:
    """Test CI-V address constants."""

    def test_ic7610_addr(self) -> None:
        assert IC_7610_ADDR == 0x98

    def test_controller_addr(self) -> None:
        assert CONTROLLER_ADDR == 0xE0


class TestBuildCivFrame:
    """Test CIV frame construction."""

    def test_minimal_frame(self) -> None:
        frame = build_civ_frame(0x98, 0xE0, 0x03)
        assert frame == b"\xfe\xfe\x98\xe0\x03\xfd"

    def test_with_sub_command(self) -> None:
        frame = build_civ_frame(0x98, 0xE0, 0x15, sub=0x02)
        assert frame == b"\xfe\xfe\x98\xe0\x15\x02\xfd"

    def test_with_data(self) -> None:
        frame = build_civ_frame(0x98, 0xE0, 0x05, data=b"\x00\x40\x07\x14\x00")
        assert frame == b"\xfe\xfe\x98\xe0\x05\x00\x40\x07\x14\x00\xfd"

    def test_with_sub_and_data(self) -> None:
        frame = build_civ_frame(0x98, 0xE0, 0x14, sub=0x0A, data=b"\x01\x28")
        assert frame == b"\xfe\xfe\x98\xe0\x14\x0a\x01\x28\xfd"


class TestParseCivFrame:
    """Test CIV frame parsing."""

    def test_parse_minimal(self) -> None:
        result = parse_civ_frame(b"\xfe\xfe\x98\xe0\x03\xfd")
        assert result == CivFrame(
            to_addr=0x98, from_addr=0xE0, command=0x03, sub=None, data=b""
        )

    def test_parse_with_data(self) -> None:
        result = parse_civ_frame(b"\xfe\xfe\xe0\x98\x03\x00\x40\x07\x14\x00\xfd")
        assert result == CivFrame(
            to_addr=0xE0,
            from_addr=0x98,
            command=0x03,
            sub=None,
            data=b"\x00\x40\x07\x14\x00",
        )

    def test_parse_ack(self) -> None:
        result = parse_civ_frame(b"\xfe\xfe\xe0\x98\xfb\xfd")
        assert result.command == 0xFB
        assert result.data == b""

    def test_parse_nak(self) -> None:
        result = parse_civ_frame(b"\xfe\xfe\xe0\x98\xfa\xfd")
        assert result.command == 0xFA

    def test_roundtrip(self) -> None:
        original = build_civ_frame(0x98, 0xE0, 0x14, sub=0x0A, data=b"\x01\x28")
        parsed = parse_civ_frame(original)
        assert parsed.to_addr == 0x98
        assert parsed.from_addr == 0xE0
        assert parsed.command == 0x14
        assert parsed.sub == 0x0A
        assert parsed.data == b"\x01\x28"

    def test_invalid_preamble(self) -> None:
        with pytest.raises(ValueError, match="preamble"):
            parse_civ_frame(b"\xfe\xff\x98\xe0\x03\xfd")

    def test_missing_terminator(self) -> None:
        with pytest.raises(ValueError, match="terminator"):
            parse_civ_frame(b"\xfe\xfe\x98\xe0\x03\xfe")

    def test_too_short(self) -> None:
        with pytest.raises(ValueError):
            parse_civ_frame(b"\xfe\xfe\x98\xe0")


class TestFrequencyCommands:
    """Test frequency get/set commands."""

    def test_get_frequency(self) -> None:
        frame = get_frequency()
        assert frame == b"\xfe\xfe\x98\xe0\x03\xfd"

    def test_set_frequency_14mhz(self) -> None:
        frame = set_frequency(14_074_000)
        expected_bcd = b"\x00\x40\x07\x14\x00"
        assert frame == b"\xfe\xfe\x98\xe0\x05" + expected_bcd + b"\xfd"

    def test_set_frequency_7mhz(self) -> None:
        frame = set_frequency(7_074_000)
        expected_bcd = b"\x00\x40\x07\x07\x00"
        assert frame == b"\xfe\xfe\x98\xe0\x05" + expected_bcd + b"\xfd"

    def test_set_frequency_custom_addr(self) -> None:
        frame = set_frequency(14_074_000, to_addr=0xA4, from_addr=0xE1)
        assert frame[2] == 0xA4
        assert frame[3] == 0xE1

    def test_parse_frequency_response(self) -> None:
        # Radio responds with cmd 0x03 + 5 bytes BCD
        resp = parse_civ_frame(b"\xfe\xfe\xe0\x98\x03\x00\x40\x07\x14\x00\xfd")
        freq = parse_frequency_response(resp)
        assert freq == 14_074_000

    def test_parse_frequency_response_wrong_cmd(self) -> None:
        resp = CivFrame(
            to_addr=0xE0, from_addr=0x98, command=0x04, sub=None, data=b"\x00" * 5
        )
        with pytest.raises(ValueError, match="frequency"):
            parse_frequency_response(resp)


class TestModeCommands:
    """Test mode get/set commands."""

    def test_get_mode(self) -> None:
        frame = get_mode()
        assert frame == b"\xfe\xfe\x98\xe0\x04\xfd"

    def test_set_mode_usb(self) -> None:
        frame = set_mode(Mode.USB)
        assert frame == b"\xfe\xfe\x98\xe0\x06\x01\xfd"

    def test_set_mode_with_filter(self) -> None:
        frame = set_mode(Mode.CW, filter_width=2)
        assert frame == b"\xfe\xfe\x98\xe0\x06\x03\x02\xfd"

    def test_parse_mode_response(self) -> None:
        resp = CivFrame(
            to_addr=0xE0, from_addr=0x98, command=0x04, sub=None, data=b"\x01"
        )
        mode, filt = parse_mode_response(resp)
        assert mode == Mode.USB
        assert filt is None

    def test_parse_mode_response_with_filter(self) -> None:
        resp = CivFrame(
            to_addr=0xE0, from_addr=0x98, command=0x04, sub=None, data=b"\x03\x02"
        )
        mode, filt = parse_mode_response(resp)
        assert mode == Mode.CW
        assert filt == 2

    def test_parse_mode_response_wrong_cmd(self) -> None:
        resp = CivFrame(
            to_addr=0xE0, from_addr=0x98, command=0x03, sub=None, data=b"\x01"
        )
        with pytest.raises(ValueError, match="mode"):
            parse_mode_response(resp)


class TestPowerCommands:
    """Test RF power get/set commands."""

    def test_get_power(self) -> None:
        frame = get_power()
        assert frame == b"\xfe\xfe\x98\xe0\x14\x0a\xfd"

    def test_set_power(self) -> None:
        # Power level is 0-255 encoded as 2-byte BCD (00-02 55)
        frame = set_power(128)
        assert frame == b"\xfe\xfe\x98\xe0\x14\x0a\x01\x28\xfd"

    def test_set_power_zero(self) -> None:
        frame = set_power(0)
        assert frame == b"\xfe\xfe\x98\xe0\x14\x0a\x00\x00\xfd"

    def test_set_power_max(self) -> None:
        frame = set_power(255)
        assert frame == b"\xfe\xfe\x98\xe0\x14\x0a\x02\x55\xfd"

    def test_set_power_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            set_power(256)
        with pytest.raises(ValueError):
            set_power(-1)


class TestMeterCommands:
    """Test meter reading commands."""

    def test_get_s_meter(self) -> None:
        frame = get_s_meter()
        assert frame == b"\xfe\xfe\x98\xe0\x15\x02\xfd"

    def test_get_swr(self) -> None:
        frame = get_swr()
        assert frame == b"\xfe\xfe\x98\xe0\x15\x12\xfd"

    def test_get_alc(self) -> None:
        frame = get_alc()
        assert frame == b"\xfe\xfe\x98\xe0\x15\x13\xfd"

    def test_parse_meter_response(self) -> None:
        # Meter values are 2-byte BCD: 0x01 0x20 = 120
        resp = CivFrame(
            to_addr=0xE0, from_addr=0x98, command=0x15, sub=0x02, data=b"\x01\x20"
        )
        value = parse_meter_response(resp)
        assert value == 120

    def test_parse_meter_response_zero(self) -> None:
        resp = CivFrame(
            to_addr=0xE0, from_addr=0x98, command=0x15, sub=0x02, data=b"\x00\x00"
        )
        value = parse_meter_response(resp)
        assert value == 0

    def test_parse_meter_response_max(self) -> None:
        resp = CivFrame(
            to_addr=0xE0, from_addr=0x98, command=0x15, sub=0x02, data=b"\x02\x55"
        )
        value = parse_meter_response(resp)
        assert value == 255


class TestPttCommands:
    """Test PTT on/off commands."""

    def test_ptt_on(self) -> None:
        frame = ptt_on()
        assert frame == b"\xfe\xfe\x98\xe0\x1c\x00\x01\xfd"

    def test_ptt_off(self) -> None:
        frame = ptt_off()
        assert frame == b"\xfe\xfe\x98\xe0\x1c\x00\x00\xfd"


class TestAckNak:
    """Test ACK/NAK response detection."""

    def test_ack(self) -> None:
        resp = CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")
        assert parse_ack_nak(resp) is True

    def test_nak(self) -> None:
        resp = CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFA, sub=None, data=b"")
        assert parse_ack_nak(resp) is False

    def test_not_ack_nak(self) -> None:
        resp = CivFrame(
            to_addr=0xE0, from_addr=0x98, command=0x03, sub=None, data=b"\x00" * 5
        )
        assert parse_ack_nak(resp) is None


class TestEdgeCases:
    """Test edge cases."""

    def test_parse_empty_data_frame(self) -> None:
        frame = build_civ_frame(0x98, 0xE0, 0x03)
        parsed = parse_civ_frame(frame)
        assert parsed.data == b""
        assert parsed.sub is None

    def test_unknown_command_roundtrip(self) -> None:
        frame = build_civ_frame(0x98, 0xE0, 0xFF, data=b"\x01\x02\x03")
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0xFF
        assert parsed.data == b"\x01\x02\x03"

    def test_civframe_equality(self) -> None:
        a = CivFrame(to_addr=0x98, from_addr=0xE0, command=0x03, sub=None, data=b"")
        b = CivFrame(to_addr=0x98, from_addr=0xE0, command=0x03, sub=None, data=b"")
        assert a == b

    def test_civframe_with_sub(self) -> None:
        f = CivFrame(
            to_addr=0x98, from_addr=0xE0, command=0x15, sub=0x02, data=b"\x01\x20"
        )
        assert f.sub == 0x02


class TestCommand29:
    """Test Command29 framing for dual-receiver radios (IC-7610)."""

    def test_build_cmd29_frame_basic(self) -> None:
        from icom_lan.commands import build_cmd29_frame, RECEIVER_MAIN
        frame = build_cmd29_frame(0x98, 0xE0, 0x16, sub=0x02, receiver=RECEIVER_MAIN)
        # FE FE 98 E0 29 00 16 02 FD
        assert frame == bytes.fromhex("fefe98e0 29 00 16 02 fd".replace(" ", ""))

    def test_cmd29_with_data(self) -> None:
        from icom_lan.commands import build_cmd29_frame, RECEIVER_MAIN
        frame = build_cmd29_frame(0x98, 0xE0, 0x16, sub=0x02, data=b"\x01", receiver=RECEIVER_MAIN)
        assert frame == bytes.fromhex("fefe98e0 29 00 16 02 01 fd".replace(" ", ""))

    def test_cmd29_sub_receiver(self) -> None:
        from icom_lan.commands import build_cmd29_frame, RECEIVER_SUB
        frame = build_cmd29_frame(0x98, 0xE0, 0x16, sub=0x02, data=b"\x02", receiver=RECEIVER_SUB)
        assert frame == bytes.fromhex("fefe98e0 29 01 16 02 02 fd".replace(" ", ""))

    def test_cmd29_no_sub(self) -> None:
        from icom_lan.commands import build_cmd29_frame, RECEIVER_MAIN
        # ATT command has no sub-byte
        frame = build_cmd29_frame(0x98, 0xE0, 0x11, receiver=RECEIVER_MAIN)
        assert frame == bytes.fromhex("fefe98e0 29 00 11 fd".replace(" ", ""))

    def test_cmd29_att_with_data(self) -> None:
        from icom_lan.commands import build_cmd29_frame, RECEIVER_MAIN
        frame = build_cmd29_frame(0x98, 0xE0, 0x11, data=b"\x18", receiver=RECEIVER_MAIN)
        assert frame == bytes.fromhex("fefe98e0 29 00 11 18 fd".replace(" ", ""))

    def test_parse_cmd29_response_preamp(self) -> None:
        # Radio response: FE FE E0 98 29 00 16 02 01 FD
        data = bytes.fromhex("fefee098 29 00 16 02 01 fd".replace(" ", ""))
        parsed = parse_civ_frame(data)
        assert parsed.command == 0x16  # Unwrapped to real command
        assert parsed.sub == 0x02
        assert parsed.data == b"\x01"  # Preamp level 1

    def test_parse_cmd29_response_att(self) -> None:
        # Radio response: FE FE E0 98 29 00 11 18 FD
        data = bytes.fromhex("fefee098 29 00 11 18 fd".replace(" ", ""))
        parsed = parse_civ_frame(data)
        assert parsed.command == 0x11
        assert parsed.sub is None
        assert parsed.data == b"\x18"

    def test_get_preamp_uses_cmd29(self) -> None:
        from icom_lan.commands import get_preamp
        frame = get_preamp()
        assert frame[4] == 0x29  # Command byte is 0x29
        assert frame[5] == 0x00  # MAIN receiver
        assert frame[6] == 0x16  # Original preamp command
        assert frame[7] == 0x02  # Preamp status sub

    def test_set_preamp_uses_cmd29(self) -> None:
        from icom_lan.commands import set_preamp
        frame = set_preamp(1)
        assert frame[4] == 0x29
        assert frame[5] == 0x00
        assert frame[6] == 0x16
        assert frame[7] == 0x02
        assert frame[8] == 0x01  # Level 1 in BCD

    def test_get_attenuator_uses_cmd29(self) -> None:
        from icom_lan.commands import get_attenuator
        frame = get_attenuator()
        assert frame[4] == 0x29
        assert frame[5] == 0x00
        assert frame[6] == 0x11

    def test_set_attenuator_level_uses_cmd29(self) -> None:
        from icom_lan.commands import set_attenuator_level
        frame = set_attenuator_level(18)
        assert frame[4] == 0x29
        assert frame[5] == 0x00
        assert frame[6] == 0x11
        assert frame[7] == 0x18  # 18 in BCD
