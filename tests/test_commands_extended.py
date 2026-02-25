"""Extended tests for commands module — VFO, split, att, preamp, CW, power."""

from icom_lan.commands import (
    IC_7610_ADDR,
    CONTROLLER_ADDR,
    build_civ_frame,
    parse_civ_frame,
    select_vfo,
    vfo_a_equals_b,
    vfo_swap,
    set_split,
    set_attenuator,
    set_preamp,
    send_cw,
    stop_cw,
    power_on,
    power_off,
    parse_ack_nak,
)


class TestSelectVfo:
    def test_vfo_a(self):
        frame = select_vfo("A")
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x07
        assert parsed.data == bytes([0x00])

    def test_vfo_b(self):
        frame = select_vfo("B")
        parsed = parse_civ_frame(frame)
        assert parsed.data == bytes([0x01])

    def test_vfo_main(self):
        frame = select_vfo("MAIN")
        parsed = parse_civ_frame(frame)
        assert parsed.data == bytes([0xD0])

    def test_vfo_sub(self):
        frame = select_vfo("SUB")
        parsed = parse_civ_frame(frame)
        assert parsed.data == bytes([0xD1])

    def test_vfo_case_insensitive(self):
        frame = select_vfo("main")
        parsed = parse_civ_frame(frame)
        assert parsed.data == bytes([0xD0])


class TestVfoCommands:
    def test_vfo_a_equals_b(self):
        frame = vfo_a_equals_b()
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x07
        assert parsed.data == b"\xa0"

    def test_vfo_swap(self):
        frame = vfo_swap()
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x07
        assert parsed.data == b"\xb0"


class TestSplit:
    def test_split_on(self):
        frame = set_split(True)
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x0F
        assert parsed.data == b"\x01"

    def test_split_off(self):
        frame = set_split(False)
        parsed = parse_civ_frame(frame)
        assert parsed.data == b"\x00"


class TestAttenuator:
    def test_att_on(self):
        frame = set_attenuator(True)
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x11
        assert parsed.data == b"\x20"

    def test_att_off(self):
        frame = set_attenuator(False)
        parsed = parse_civ_frame(frame)
        assert parsed.data == b"\x00"


class TestPreamp:
    def test_preamp_off(self):
        frame = set_preamp(0)
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x16
        assert parsed.data == bytes([0])

    def test_preamp_1(self):
        frame = set_preamp(1)
        parsed = parse_civ_frame(frame)
        assert parsed.data == bytes([1])

    def test_preamp_2(self):
        frame = set_preamp(2)
        parsed = parse_civ_frame(frame)
        assert parsed.data == bytes([2])


class TestCw:
    def test_send_short(self):
        frames = send_cw("CQ CQ")
        assert len(frames) == 1
        parsed = parse_civ_frame(frames[0])
        assert parsed.command == 0x17
        assert parsed.data == b"CQ CQ"

    def test_send_long_splits(self):
        text = "A" * 65
        frames = send_cw(text)
        assert len(frames) == 3
        # First chunk 30, second 30, third 5
        assert len(parse_civ_frame(frames[0]).data) == 30
        assert len(parse_civ_frame(frames[1]).data) == 30
        assert len(parse_civ_frame(frames[2]).data) == 5

    def test_send_uppercased(self):
        frames = send_cw("cq cq")
        parsed = parse_civ_frame(frames[0])
        assert parsed.data == b"CQ CQ"

    def test_stop_cw(self):
        frame = stop_cw()
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x17
        assert parsed.data == b"\xff"


class TestPowerOnOff:
    def test_power_on(self):
        frame = power_on()
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x18
        assert parsed.data == b"\x01"

    def test_power_off(self):
        frame = power_off()
        parsed = parse_civ_frame(frame)
        assert parsed.command == 0x18
        assert parsed.data == b"\x00"


class TestParseAckNak:
    def test_ack(self):
        civ = build_civ_frame(CONTROLLER_ADDR, IC_7610_ADDR, 0xFB)
        frame = parse_civ_frame(civ)
        assert parse_ack_nak(frame) is True

    def test_nak(self):
        civ = build_civ_frame(CONTROLLER_ADDR, IC_7610_ADDR, 0xFA)
        frame = parse_civ_frame(civ)
        assert parse_ack_nak(frame) is False

    def test_other(self):
        civ = build_civ_frame(CONTROLLER_ADDR, IC_7610_ADDR, 0x03)
        frame = parse_civ_frame(civ)
        assert parse_ack_nak(frame) is None
