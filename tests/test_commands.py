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

    def test_parse_mode_response_empty_payload_raises(self) -> None:
        resp = CivFrame(
            to_addr=0xE0, from_addr=0x98, command=0x04, sub=None, data=b""
        )
        with pytest.raises(ValueError, match="payload too short"):
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

    def test_parse_meter_response_short_payload_raises(self) -> None:
        resp = CivFrame(
            to_addr=0xE0, from_addr=0x98, command=0x15, sub=0x02, data=b"\x01"
        )
        with pytest.raises(ValueError, match="payload too short"):
            parse_meter_response(resp)


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

        frame = build_cmd29_frame(
            0x98, 0xE0, 0x16, sub=0x02, data=b"\x01", receiver=RECEIVER_MAIN
        )
        assert frame == bytes.fromhex("fefe98e0 29 00 16 02 01 fd".replace(" ", ""))

    def test_cmd29_sub_receiver(self) -> None:
        from icom_lan.commands import build_cmd29_frame, RECEIVER_SUB

        frame = build_cmd29_frame(
            0x98, 0xE0, 0x16, sub=0x02, data=b"\x02", receiver=RECEIVER_SUB
        )
        assert frame == bytes.fromhex("fefe98e0 29 01 16 02 02 fd".replace(" ", ""))

    def test_cmd29_no_sub(self) -> None:
        from icom_lan.commands import build_cmd29_frame, RECEIVER_MAIN

        # ATT command has no sub-byte
        frame = build_cmd29_frame(0x98, 0xE0, 0x11, receiver=RECEIVER_MAIN)
        assert frame == bytes.fromhex("fefe98e0 29 00 11 fd".replace(" ", ""))

    def test_cmd29_att_with_data(self) -> None:
        from icom_lan.commands import build_cmd29_frame, RECEIVER_MAIN

        frame = build_cmd29_frame(
            0x98, 0xE0, 0x11, data=b"\x18", receiver=RECEIVER_MAIN
        )
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


class TestCmd29ReceiverRouting:
    """Test that per-receiver SET commands use cmd29 when receiver=SUB."""

    def test_set_frequency_main_no_cmd29(self) -> None:
        from icom_lan.commands import set_frequency, RECEIVER_MAIN

        frame = set_frequency(14_074_000, receiver=RECEIVER_MAIN)
        assert frame[4] == 0x05  # Direct freq set, no cmd29 prefix

    def test_set_frequency_sub_uses_cmd29(self) -> None:
        from icom_lan.commands import set_frequency, RECEIVER_SUB

        frame = set_frequency(14_074_000, receiver=RECEIVER_SUB)
        assert frame[4] == 0x29
        assert frame[5] == 0x01  # SUB receiver
        assert frame[6] == 0x05  # Freq set command

    def test_set_mode_main_no_cmd29(self) -> None:
        from icom_lan.commands import set_mode, RECEIVER_MAIN
        from icom_lan.types import Mode

        frame = set_mode(Mode.USB, receiver=RECEIVER_MAIN)
        assert frame[4] == 0x06  # Direct mode set, no cmd29 prefix

    def test_set_mode_sub_uses_cmd29(self) -> None:
        from icom_lan.commands import set_mode, RECEIVER_SUB
        from icom_lan.types import Mode

        frame = set_mode(Mode.USB, receiver=RECEIVER_SUB)
        assert frame[4] == 0x29
        assert frame[5] == 0x01  # SUB receiver
        assert frame[6] == 0x06  # Mode set command

    def test_set_rf_gain_main_no_cmd29(self) -> None:
        from icom_lan.commands import set_rf_gain, RECEIVER_MAIN

        frame = set_rf_gain(128, receiver=RECEIVER_MAIN)
        assert frame[4] == 0x14  # Direct level cmd, no cmd29 prefix
        assert frame[5] == 0x02  # RF gain sub

    def test_set_rf_gain_sub_uses_cmd29(self) -> None:
        from icom_lan.commands import set_rf_gain, RECEIVER_SUB

        frame = set_rf_gain(128, receiver=RECEIVER_SUB)
        assert frame[4] == 0x29
        assert frame[5] == 0x01  # SUB receiver
        assert frame[6] == 0x14  # Level command
        assert frame[7] == 0x02  # RF gain sub

    def test_set_af_level_main_no_cmd29(self) -> None:
        from icom_lan.commands import set_af_level, RECEIVER_MAIN

        frame = set_af_level(200, receiver=RECEIVER_MAIN)
        assert frame[4] == 0x14
        assert frame[5] == 0x01  # AF level sub

    def test_set_af_level_sub_uses_cmd29(self) -> None:
        from icom_lan.commands import set_af_level, RECEIVER_SUB

        frame = set_af_level(200, receiver=RECEIVER_SUB)
        assert frame[4] == 0x29
        assert frame[5] == 0x01
        assert frame[6] == 0x14
        assert frame[7] == 0x01  # AF level sub

    def test_set_squelch_main_no_cmd29(self) -> None:
        from icom_lan.commands import set_squelch, RECEIVER_MAIN

        frame = set_squelch(100, receiver=RECEIVER_MAIN)
        assert frame[4] == 0x14
        assert frame[5] == 0x03  # SQL sub

    def test_set_squelch_sub_uses_cmd29(self) -> None:
        from icom_lan.commands import set_squelch, RECEIVER_SUB

        frame = set_squelch(100, receiver=RECEIVER_SUB)
        assert frame[4] == 0x29
        assert frame[5] == 0x01
        assert frame[6] == 0x14
        assert frame[7] == 0x03  # SQL sub

    def test_set_nb_main_no_cmd29(self) -> None:
        from icom_lan.commands import set_nb, RECEIVER_MAIN

        frame = set_nb(True, receiver=RECEIVER_MAIN)
        assert frame[4] == 0x16  # Direct cmd, no cmd29
        assert frame[5] == 0x22  # NB sub

    def test_set_nb_sub_uses_cmd29(self) -> None:
        from icom_lan.commands import set_nb, RECEIVER_SUB

        frame = set_nb(True, receiver=RECEIVER_SUB)
        assert frame[4] == 0x29
        assert frame[5] == 0x01
        assert frame[6] == 0x16
        assert frame[7] == 0x22  # NB sub
        assert frame[8] == 0x01  # on=True

    def test_set_nr_main_no_cmd29(self) -> None:
        from icom_lan.commands import set_nr, RECEIVER_MAIN

        frame = set_nr(False, receiver=RECEIVER_MAIN)
        assert frame[4] == 0x16
        assert frame[5] == 0x40  # NR sub

    def test_set_nr_sub_uses_cmd29(self) -> None:
        from icom_lan.commands import set_nr, RECEIVER_SUB

        frame = set_nr(False, receiver=RECEIVER_SUB)
        assert frame[4] == 0x29
        assert frame[5] == 0x01
        assert frame[6] == 0x16
        assert frame[7] == 0x40  # NR sub
        assert frame[8] == 0x00  # on=False

    def test_set_ip_plus_main_no_cmd29(self) -> None:
        from icom_lan.commands import set_ip_plus, RECEIVER_MAIN

        frame = set_ip_plus(True, receiver=RECEIVER_MAIN)
        assert frame[4] == 0x16
        assert frame[5] == 0x65  # IP+ sub

    def test_set_ip_plus_sub_uses_cmd29(self) -> None:
        from icom_lan.commands import set_ip_plus, RECEIVER_SUB

        frame = set_ip_plus(True, receiver=RECEIVER_SUB)
        assert frame[4] == 0x29
        assert frame[5] == 0x01
        assert frame[6] == 0x16
        assert frame[7] == 0x65  # IP+ sub
        assert frame[8] == 0x01  # on=True

    def test_set_digisel_sub_uses_cmd29(self) -> None:
        from icom_lan.commands import set_digisel, RECEIVER_SUB

        frame = set_digisel(True, receiver=RECEIVER_SUB)
        assert frame[4] == 0x29
        assert frame[5] == 0x01
        assert frame[6] == 0x16
        assert frame[7] == 0x4E  # DIGI-SEL sub

    def test_backward_compat_no_receiver_arg(self) -> None:
        """All functions remain backward-compatible (no receiver arg = MAIN)."""
        from icom_lan.commands import (
            set_frequency, set_mode, set_rf_gain, set_af_level,
            set_squelch, set_nb, set_nr, set_ip_plus,
        )
        from icom_lan.types import Mode

        # None of these should use cmd29 when called without receiver
        assert set_frequency(14_000_000)[4] == 0x05
        assert set_mode(Mode.USB)[4] == 0x06
        assert set_rf_gain(128)[4] == 0x14
        assert set_af_level(200)[4] == 0x14
        assert set_squelch(50)[4] == 0x14
        assert set_nb(True)[4] == 0x16
        assert set_nr(True)[4] == 0x16
        assert set_ip_plus(True)[4] == 0x16


class TestDspLevelParityCommands:
    """Test IC-7610 DSP/level parity command builders and parsers."""

    @pytest.mark.parametrize(
        ("getter_name", "setter_name", "sub", "receiver"),
        [
            ("get_apf_type_level", "set_apf_type_level", 0x05, 1),
            ("get_nr_level", "set_nr_level", 0x06, 1),
            ("get_pbt_inner", "set_pbt_inner", 0x07, 1),
            ("get_pbt_outer", "set_pbt_outer", 0x08, 1),
            ("get_nb_level", "set_nb_level", 0x12, 1),
            ("get_digisel_shift", "set_digisel_shift", 0x13, 1),
        ],
    )
    def test_cmd29_level_builders(
        self,
        getter_name: str,
        setter_name: str,
        sub: int,
        receiver: int,
    ) -> None:
        import icom_lan.commands as commands

        getter = getattr(commands, getter_name)
        setter = getattr(commands, setter_name)
        expected = bytes([0xFE, 0xFE, 0x98, 0xE0, 0x29, receiver, 0x14, sub])

        assert getter(receiver=receiver) == expected + b"\xFD"
        assert setter(128, receiver=receiver) == expected + b"\x01\x28\xFD"

    @pytest.mark.parametrize(
        ("getter_name", "setter_name", "sub", "value"),
        [
            ("get_cw_pitch", "set_cw_pitch", 0x09, 600),
            ("get_mic_gain", "set_mic_gain", 0x0B, 128),
            ("get_key_speed", "set_key_speed", 0x0C, 30),
            ("get_notch_filter", "set_notch_filter", 0x0D, 128),
            ("get_compressor_level", "set_compressor_level", 0x0E, 128),
            ("get_break_in_delay", "set_break_in_delay", 0x0F, 128),
            ("get_drive_gain", "set_drive_gain", 0x14, 128),
            ("get_monitor_gain", "set_monitor_gain", 0x15, 128),
            ("get_vox_gain", "set_vox_gain", 0x16, 128),
            ("get_anti_vox_gain", "set_anti_vox_gain", 0x17, 128),
        ],
    )
    def test_level_builders(
        self,
        getter_name: str,
        setter_name: str,
        sub: int,
        value: int,
    ) -> None:
        import icom_lan.commands as commands

        getter = getattr(commands, getter_name)
        setter = getattr(commands, setter_name)

        assert getter() == bytes([0xFE, 0xFE, 0x98, 0xE0, 0x14, sub, 0xFD])
        assert setter(value).startswith(bytes([0xFE, 0xFE, 0x98, 0xE0, 0x14, sub]))
        assert setter(value).endswith(b"\xFD")

    @pytest.mark.parametrize(
        ("getter_name", "setter_name", "prefix", "value", "expected_payload"),
        [
            ("get_ref_adjust", "set_ref_adjust", b"\x00\x70", 511, b"\x05\x11"),
            ("get_dash_ratio", "set_dash_ratio", b"\x02\x28", 45, b"\x45"),
            ("get_nb_depth", "set_nb_depth", b"\x02\x90", 9, b"\x09"),
            ("get_nb_width", "set_nb_width", b"\x02\x91", 255, b"\x02\x55"),
        ],
    )
    def test_ctl_mem_level_builders(
        self,
        getter_name: str,
        setter_name: str,
        prefix: bytes,
        value: int,
        expected_payload: bytes,
    ) -> None:
        import icom_lan.commands as commands

        getter = getattr(commands, getter_name)
        setter = getattr(commands, setter_name)

        assert getter() == b"\xFE\xFE\x98\xE0\x1A\x05" + prefix + b"\xFD"
        assert setter(value) == b"\xFE\xFE\x98\xE0\x1A\x05" + prefix + expected_payload + b"\xFD"

    def test_af_mute_builders(self) -> None:
        from icom_lan.commands import get_af_mute, set_af_mute, RECEIVER_SUB

        assert get_af_mute() == b"\xFE\xFE\x98\xE0\x29\x00\x1A\x09\xFD"
        assert get_af_mute(receiver=RECEIVER_SUB) == b"\xFE\xFE\x98\xE0\x29\x01\x1A\x09\xFD"
        assert set_af_mute(True) == b"\xFE\xFE\x98\xE0\x29\x00\x1A\x09\x01\xFD"
        assert set_af_mute(False, receiver=RECEIVER_SUB) == b"\xFE\xFE\x98\xE0\x29\x01\x1A\x09\x00\xFD"

    def test_parse_level_response_direct_level(self) -> None:
        from icom_lan.commands import parse_level_response

        frame = CivFrame(
            to_addr=0xE0,
            from_addr=0x98,
            command=0x14,
            sub=0x13,
            data=b"\x01\x99",
        )
        assert parse_level_response(frame, sub=0x13) == 199

    def test_parse_level_response_with_ctl_mem_prefix(self) -> None:
        from icom_lan.commands import parse_level_response

        frame = CivFrame(
            to_addr=0xE0,
            from_addr=0x98,
            command=0x1A,
            sub=0x05,
            data=b"\x00\x70\x05\x11",
        )
        assert parse_level_response(frame, command=0x1A, sub=0x05, prefix=b"\x00\x70") == 511

    def test_parse_bool_response(self) -> None:
        from icom_lan.commands import parse_bool_response

        frame = CivFrame(
            to_addr=0xE0,
            from_addr=0x98,
            command=0x1A,
            sub=0x09,
            data=b"\x01",
        )
        assert parse_bool_response(frame, command=0x1A, sub=0x09) is True

    def test_parse_level_response_rejects_wrong_prefix(self) -> None:
        from icom_lan.commands import parse_level_response

        frame = CivFrame(
            to_addr=0xE0,
            from_addr=0x98,
            command=0x1A,
            sub=0x05,
            data=b"\x02\x90\x00",
        )
        with pytest.raises(ValueError, match="prefix"):
            parse_level_response(frame, command=0x1A, sub=0x05, prefix=b"\x00\x70")

    def test_set_nb_width_rejects_out_of_range(self) -> None:
        from icom_lan.commands import set_nb_width

        with pytest.raises(ValueError, match="0-255"):
            set_nb_width(256)
