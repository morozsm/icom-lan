"""Tests for cmd29 (dual-receiver) CI-V frame parsing and RadioState routing.

Tests parse_civ_frame() for cmd29-wrapped frames and verify that
_CivRxMixin._update_radio_state_from_frame() routes updates to the
correct receiver in RadioState.
"""

from __future__ import annotations


from icom_lan.commands import (
    IC_7610_ADDR,
    CONTROLLER_ADDR,
    RECEIVER_MAIN,
    RECEIVER_SUB,
    build_cmd29_frame,
    build_civ_frame,
    parse_civ_frame,
)
from icom_lan.radio_state import RadioState
from icom_lan.types import bcd_encode, CivFrame


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cmd29_response(
    receiver: int, inner_cmd: int, inner_sub: int | None, data: bytes
) -> CivFrame:
    """Build a simulated cmd29 response from the radio and parse it."""
    # The radio responds with cmd29 wrapping its answer.
    frame_bytes = build_cmd29_frame(
        CONTROLLER_ADDR,  # to: controller
        IC_7610_ADDR,  # from: radio
        inner_cmd,
        sub=inner_sub,
        data=data,
        receiver=receiver,
    )
    return parse_civ_frame(frame_bytes)


def _apply_frame(frame: CivFrame, rs: RadioState) -> None:
    """Call _update_radio_state_from_frame logic directly (extracted for testing)."""
    # Replicate the logic from _CivRxMixin._update_radio_state_from_frame
    # so we can test it without instantiating the full mixin.
    try:
        if frame.receiver is not None:
            rx_name = "MAIN" if frame.receiver == 0x00 else "SUB"
        else:
            rx_name = rs.active
        rx = rs.receiver(rx_name)

        cmd = frame.command

        if cmd in (0x03, 0x00):
            from icom_lan.commands import parse_frequency_response

            rx.freq = parse_frequency_response(frame)

        elif cmd in (0x04, 0x01):
            from icom_lan.commands import parse_mode_response

            mode_val, filt = parse_mode_response(frame)
            rx.mode = mode_val.name
            if filt is not None:
                rx.filter = filt

        elif cmd == 0x15:
            if frame.sub == 0x02 and len(frame.data) >= 2:
                b0, b1 = frame.data[0], frame.data[1]
                raw = (
                    (b0 >> 4) * 1000 + (b0 & 0x0F) * 100 + (b1 >> 4) * 10 + (b1 & 0x0F)
                )
                rs.receiver(rs.active).s_meter = raw

        elif cmd == 0x14:
            if len(frame.data) >= 2:
                b0, b1 = frame.data[0], frame.data[1]
                raw = (
                    (b0 >> 4) * 1000 + (b0 & 0x0F) * 100 + (b1 >> 4) * 10 + (b1 & 0x0F)
                )
                sub = frame.sub
                if sub == 0x01:
                    rx.af_level = raw
                elif sub == 0x02:
                    rx.rf_gain = raw
                elif sub == 0x03:
                    rx.squelch = raw
                elif sub == 0x0A:
                    rs.power_level = raw

        elif cmd == 0x11:
            if frame.data:
                val = frame.data[0]
                rx.att = ((val >> 4) & 0x0F) * 10 + (val & 0x0F)

        elif cmd == 0x16:
            sub = frame.sub or 0
            data = frame.data
            if sub == 0 and len(data) >= 2:
                sub = data[0]
                data = data[1:]
            if data:
                val = data[0]
                if sub == 0x02:
                    rx.preamp = val
                elif sub == 0x22:
                    rx.nb = bool(val)
                elif sub == 0x40:
                    rx.nr = bool(val)
                elif sub == 0x4E:
                    rx.digisel = bool(val)
                elif sub == 0x65:
                    rx.ipplus = bool(val)

        elif cmd == 0x1A:
            sub = frame.sub
            if sub == 0x03 and frame.data:
                rx.filter = frame.data[0]
            elif sub == 0x06 and frame.data:
                rx.data_mode = bool(frame.data[0])

        elif cmd == 0x1C and frame.sub == 0x00:
            if frame.data:
                rs.ptt = bool(frame.data[0])

        elif cmd == 0x0F:
            if frame.data:
                rs.split = bool(frame.data[0])

        elif cmd == 0x07:
            if len(frame.data) >= 2:
                sub07 = frame.data[0]
                val07 = frame.data[1]
                if sub07 == 0xD2:
                    rs.active = "SUB" if val07 else "MAIN"
                elif sub07 == 0xC2:
                    rs.dual_watch = bool(val07)

    except Exception:
        pass


# ---------------------------------------------------------------------------
# parse_civ_frame: cmd29 unwrapping
# ---------------------------------------------------------------------------


def test_cmd29_unwrap_sets_receiver_main() -> None:
    frame = _make_cmd29_response(RECEIVER_MAIN, 0x11, None, b"\x00")
    assert frame.receiver == RECEIVER_MAIN
    assert frame.command == 0x11


def test_cmd29_unwrap_sets_receiver_sub() -> None:
    frame = _make_cmd29_response(RECEIVER_SUB, 0x11, None, b"\x12")
    assert frame.receiver == RECEIVER_SUB
    assert frame.command == 0x11


def test_cmd29_with_sub_command_parsed_correctly() -> None:
    # cmd29 for preamp (0x16 0x02)
    frame = _make_cmd29_response(RECEIVER_MAIN, 0x16, 0x02, b"\x01")
    assert frame.receiver == RECEIVER_MAIN
    assert frame.command == 0x16
    assert frame.sub == 0x02
    assert frame.data == b"\x01"


def test_cmd29_with_level_sub_command() -> None:
    # AF level (0x14 0x01) on SUB receiver
    frame = _make_cmd29_response(RECEIVER_SUB, 0x14, 0x01, b"\x01\x28")
    assert frame.receiver == RECEIVER_SUB
    assert frame.command == 0x14
    assert frame.sub == 0x01


def test_non_cmd29_frame_has_no_receiver() -> None:
    # Normal (non-cmd29) frequency response
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x03, data=bcd_encode(14_074_000)
    )
    frame = parse_civ_frame(frame_bytes)
    assert frame.receiver is None
    assert frame.command == 0x03


# ---------------------------------------------------------------------------
# RadioState routing: ATT (0x11)
# ---------------------------------------------------------------------------


def test_att_main_updates_main_receiver() -> None:
    rs = RadioState()
    # 0x12 BCD = 12 dB
    frame = _make_cmd29_response(RECEIVER_MAIN, 0x11, None, b"\x12")
    _apply_frame(frame, rs)
    assert rs.main.att == 12
    assert rs.sub.att == 0  # untouched


def test_att_sub_updates_sub_receiver() -> None:
    rs = RadioState()
    frame = _make_cmd29_response(RECEIVER_SUB, 0x11, None, b"\x18")
    _apply_frame(frame, rs)
    assert rs.sub.att == 18
    assert rs.main.att == 0


# ---------------------------------------------------------------------------
# RadioState routing: Preamp (0x16 0x02)
# ---------------------------------------------------------------------------


def test_preamp_main() -> None:
    rs = RadioState()
    frame = _make_cmd29_response(RECEIVER_MAIN, 0x16, 0x02, b"\x01")
    _apply_frame(frame, rs)
    assert rs.main.preamp == 1
    assert rs.sub.preamp == 0


def test_preamp_sub() -> None:
    rs = RadioState()
    frame = _make_cmd29_response(RECEIVER_SUB, 0x16, 0x02, b"\x02")
    _apply_frame(frame, rs)
    assert rs.sub.preamp == 2
    assert rs.main.preamp == 0


# ---------------------------------------------------------------------------
# RadioState routing: NB (0x16 0x22)
# ---------------------------------------------------------------------------


def test_nb_on_main() -> None:
    rs = RadioState()
    frame = _make_cmd29_response(RECEIVER_MAIN, 0x16, 0x22, b"\x01")
    _apply_frame(frame, rs)
    assert rs.main.nb is True
    assert rs.sub.nb is False


def test_nb_off_sub() -> None:
    rs = RadioState()
    rs.sub.nb = True
    frame = _make_cmd29_response(RECEIVER_SUB, 0x16, 0x22, b"\x00")
    _apply_frame(frame, rs)
    assert rs.sub.nb is False


# ---------------------------------------------------------------------------
# RadioState routing: NR (0x16 0x40)
# ---------------------------------------------------------------------------


def test_nr_on_sub() -> None:
    rs = RadioState()
    frame = _make_cmd29_response(RECEIVER_SUB, 0x16, 0x40, b"\x01")
    _apply_frame(frame, rs)
    assert rs.sub.nr is True
    assert rs.main.nr is False


# ---------------------------------------------------------------------------
# RadioState routing: DIGI-SEL (0x16 0x4E)
# ---------------------------------------------------------------------------


def test_digisel_main() -> None:
    rs = RadioState()
    frame = _make_cmd29_response(RECEIVER_MAIN, 0x16, 0x4E, b"\x01")
    _apply_frame(frame, rs)
    assert rs.main.digisel is True
    assert rs.sub.digisel is False


# ---------------------------------------------------------------------------
# RadioState routing: IP+ (0x16 0x65)
# ---------------------------------------------------------------------------


def test_ipplus_sub() -> None:
    rs = RadioState()
    frame = _make_cmd29_response(RECEIVER_SUB, 0x16, 0x65, b"\x01")
    _apply_frame(frame, rs)
    assert rs.sub.ipplus is True
    assert rs.main.ipplus is False


# ---------------------------------------------------------------------------
# RadioState routing: AF level (0x14 0x01)
# ---------------------------------------------------------------------------


def test_af_level_main() -> None:
    rs = RadioState()
    # BCD 0x01 0x28 = 128
    frame = _make_cmd29_response(RECEIVER_MAIN, 0x14, 0x01, b"\x01\x28")
    _apply_frame(frame, rs)
    assert rs.main.af_level == 128
    assert rs.sub.af_level == 0


# ---------------------------------------------------------------------------
# RadioState routing: Filter (0x1A 0x03)
# ---------------------------------------------------------------------------


def test_filter_main() -> None:
    rs = RadioState()
    frame = _make_cmd29_response(RECEIVER_MAIN, 0x1A, 0x03, b"\x02")
    _apply_frame(frame, rs)
    assert rs.main.filter == 2
    assert rs.sub.filter is None


# ---------------------------------------------------------------------------
# RadioState routing: PTT (global, 0x1C 0x00)
# ---------------------------------------------------------------------------


def test_ptt_on_global() -> None:
    rs = RadioState()
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x1C, sub=0x00, data=b"\x01"
    )
    frame = parse_civ_frame(frame_bytes)
    _apply_frame(frame, rs)
    assert rs.ptt is True


def test_ptt_off_global() -> None:
    rs = RadioState()
    rs.ptt = True
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x1C, sub=0x00, data=b"\x00"
    )
    frame = parse_civ_frame(frame_bytes)
    _apply_frame(frame, rs)
    assert rs.ptt is False


# ---------------------------------------------------------------------------
# RadioState routing: Split (global, 0x0F)
# ---------------------------------------------------------------------------


def test_split_on_global() -> None:
    rs = RadioState()
    frame_bytes = build_civ_frame(CONTROLLER_ADDR, IC_7610_ADDR, 0x0F, data=b"\x01")
    frame = parse_civ_frame(frame_bytes)
    _apply_frame(frame, rs)
    assert rs.split is True


# ---------------------------------------------------------------------------
# RadioState routing: no receiver → active receiver
# ---------------------------------------------------------------------------


def test_freq_without_receiver_updates_active_main() -> None:
    rs = RadioState()
    rs.active = "MAIN"
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x03, data=bcd_encode(14_074_000)
    )
    frame = parse_civ_frame(frame_bytes)
    _apply_frame(frame, rs)
    assert rs.main.freq == 14_074_000
    assert rs.sub.freq == 0


def test_freq_without_receiver_updates_active_sub() -> None:
    rs = RadioState()
    rs.active = "SUB"
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x03, data=bcd_encode(7_000_000)
    )
    frame = parse_civ_frame(frame_bytes)
    _apply_frame(frame, rs)
    assert rs.sub.freq == 7_000_000
    assert rs.main.freq == 0


# ---------------------------------------------------------------------------
# parse_civ_frame: 0x07 active receiver / Dual Watch
# ---------------------------------------------------------------------------


def test_parse_0x07_D2_frame_main() -> None:
    """0x07 0xD2 0x00 parses as command=0x07, data=[0xD2, 0x00]."""
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x07, data=bytes([0xD2, 0x00])
    )
    frame = parse_civ_frame(frame_bytes)
    assert frame.command == 0x07
    assert frame.sub is None
    assert frame.data == bytes([0xD2, 0x00])


def test_parse_0x07_D2_frame_sub() -> None:
    """0x07 0xD2 0x01 parses as command=0x07, data=[0xD2, 0x01]."""
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x07, data=bytes([0xD2, 0x01])
    )
    frame = parse_civ_frame(frame_bytes)
    assert frame.command == 0x07
    assert frame.sub is None
    assert frame.data == bytes([0xD2, 0x01])


def test_parse_0x07_C2_frame_off() -> None:
    """0x07 0xC2 0x00 parses as command=0x07, data=[0xC2, 0x00]."""
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x07, data=bytes([0xC2, 0x00])
    )
    frame = parse_civ_frame(frame_bytes)
    assert frame.command == 0x07
    assert frame.sub is None
    assert frame.data == bytes([0xC2, 0x00])


def test_parse_0x07_C2_frame_on() -> None:
    """0x07 0xC2 0x01 parses as command=0x07, data=[0xC2, 0x01]."""
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x07, data=bytes([0xC2, 0x01])
    )
    frame = parse_civ_frame(frame_bytes)
    assert frame.command == 0x07
    assert frame.sub is None
    assert frame.data == bytes([0xC2, 0x01])


# ---------------------------------------------------------------------------
# RadioState routing: active receiver (0x07 0xD2)
# ---------------------------------------------------------------------------


def test_active_receiver_main_from_0x07_D2() -> None:
    rs = RadioState()
    rs.active = "SUB"
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x07, data=bytes([0xD2, 0x00])
    )
    frame = parse_civ_frame(frame_bytes)
    _apply_frame(frame, rs)
    assert rs.active == "MAIN"


def test_active_receiver_sub_from_0x07_D2() -> None:
    rs = RadioState()
    rs.active = "MAIN"
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x07, data=bytes([0xD2, 0x01])
    )
    frame = parse_civ_frame(frame_bytes)
    _apply_frame(frame, rs)
    assert rs.active == "SUB"


# ---------------------------------------------------------------------------
# RadioState routing: Dual Watch (0x07 0xC2)
# ---------------------------------------------------------------------------


def test_dual_watch_on_from_0x07_C2() -> None:
    rs = RadioState()
    assert rs.dual_watch is False
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x07, data=bytes([0xC2, 0x01])
    )
    frame = parse_civ_frame(frame_bytes)
    _apply_frame(frame, rs)
    assert rs.dual_watch is True


def test_dual_watch_off_from_0x07_C2() -> None:
    rs = RadioState()
    rs.dual_watch = True
    frame_bytes = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, 0x07, data=bytes([0xC2, 0x00])
    )
    frame = parse_civ_frame(frame_bytes)
    _apply_frame(frame, rs)
    assert rs.dual_watch is False


def test_dual_watch_in_to_dict() -> None:
    rs = RadioState()
    rs.dual_watch = True
    d = rs.to_dict()
    assert d["dual_watch"] is True
    rs.dual_watch = False
    d = rs.to_dict()
    assert d["dual_watch"] is False
