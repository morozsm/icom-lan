"""Tests for RadioState and ReceiverState dataclasses."""

from __future__ import annotations

import pytest

from icom_lan.radio_state import RadioState, ReceiverState


# ---------------------------------------------------------------------------
# ReceiverState defaults
# ---------------------------------------------------------------------------


def test_receiver_state_defaults() -> None:
    rx = ReceiverState()
    assert rx.freq == 0
    assert rx.mode == "USB"
    assert rx.filter is None
    assert rx.data_mode is False
    assert rx.att == 0
    assert rx.preamp == 0
    assert rx.nb is False
    assert rx.nr is False
    assert rx.digisel is False
    assert rx.ipplus is False
    assert rx.s_meter_sql_open is False
    assert rx.agc == 0
    assert rx.audio_peak_filter == 0
    assert rx.auto_notch is False
    assert rx.manual_notch is False
    assert rx.twin_peak_filter is False
    assert rx.filter_shape == 0
    assert rx.agc_time_constant == 0
    assert rx.af_level == 0
    assert rx.rf_gain == 0
    assert rx.squelch == 0
    assert rx.s_meter == 0
    assert rx.apf_type_level == 0
    assert rx.nr_level == 0
    assert rx.pbt_inner == 0
    assert rx.pbt_outer == 0
    assert rx.nb_level == 0
    assert rx.digisel_shift == 0
    assert rx.af_mute is False


def test_receiver_state_field_update() -> None:
    rx = ReceiverState()
    rx.freq = 14_074_000
    rx.mode = "USB"
    rx.filter = 2
    rx.att = 18
    rx.preamp = 1
    rx.nb = True
    rx.s_meter = 120
    assert rx.freq == 14_074_000
    assert rx.filter == 2
    assert rx.att == 18
    assert rx.preamp == 1
    assert rx.nb is True
    assert rx.s_meter == 120


# ---------------------------------------------------------------------------
# RadioState defaults
# ---------------------------------------------------------------------------


def test_radio_state_defaults() -> None:
    rs = RadioState()
    assert rs.active == "MAIN"
    assert rs.ptt is False
    assert rs.power_level == 0
    assert rs.split is False
    assert rs.dual_watch is False
    assert rs.overflow is False
    assert rs.cw_pitch == 0
    assert rs.mic_gain == 0
    assert rs.key_speed == 0
    assert rs.notch_filter == 0
    assert rs.compressor_on is False
    assert rs.compressor_level == 0
    assert rs.monitor_on is False
    assert rs.break_in_delay == 0
    assert rs.break_in == 0
    assert rs.dial_lock is False
    assert rs.drive_gain == 0
    assert rs.monitor_gain == 0
    assert rs.vox_on is False
    assert rs.vox_gain == 0
    assert rs.anti_vox_gain == 0
    assert rs.ssb_tx_bandwidth == 0
    assert rs.ref_adjust == 0
    assert rs.dash_ratio == 0
    assert rs.nb_depth == 0
    assert rs.nb_width == 0
    assert isinstance(rs.main, ReceiverState)
    assert isinstance(rs.sub, ReceiverState)


def test_radio_state_main_sub_are_independent() -> None:
    rs = RadioState()
    rs.main.freq = 14_074_000
    rs.sub.freq = 7_000_000
    assert rs.main.freq == 14_074_000
    assert rs.sub.freq == 7_000_000


# ---------------------------------------------------------------------------
# receiver() method
# ---------------------------------------------------------------------------


def test_receiver_main_returns_main() -> None:
    rs = RadioState()
    rs.main.freq = 14_000_000
    assert rs.receiver("MAIN") is rs.main
    assert rs.receiver("MAIN").freq == 14_000_000


def test_receiver_sub_returns_sub() -> None:
    rs = RadioState()
    rs.sub.freq = 7_000_000
    assert rs.receiver("SUB") is rs.sub
    assert rs.receiver("SUB").freq == 7_000_000


def test_receiver_unknown_falls_back_to_sub() -> None:
    # Any non-"MAIN" string returns sub (matches the ternary logic)
    rs = RadioState()
    assert rs.receiver("OTHER") is rs.sub


# ---------------------------------------------------------------------------
# to_dict()
# ---------------------------------------------------------------------------


def test_to_dict_structure() -> None:
    rs = RadioState()
    d = rs.to_dict()
    assert set(d.keys()) == {
        "active",
        "ptt",
        "power_level",
        "split",
        "dual_watch",
        "overflow",
        "tuner_status",
        "tx_freq_monitor",
        "rit_freq",
        "rit_on",
        "rit_tx",
        "comp_meter",
        "vd_meter",
        "id_meter",
        "cw_pitch",
        "mic_gain",
        "key_speed",
        "notch_filter",
        "compressor_on",
        "compressor_level",
        "monitor_on",
        "break_in_delay",
        "break_in",
        "dial_lock",
        "drive_gain",
        "monitor_gain",
        "vox_on",
        "vox_gain",
        "anti_vox_gain",
        "ssb_tx_bandwidth",
        "ref_adjust",
        "dash_ratio",
        "nb_depth",
        "nb_width",
        "main",
        "sub",
    }
    assert d["active"] == "MAIN"
    assert d["ptt"] is False
    assert d["power_level"] == 0
    assert d["split"] is False
    assert d["dual_watch"] is False


def test_to_dict_main_keys() -> None:
    rs = RadioState()
    main = rs.to_dict()["main"]
    expected_keys = {
        "freq", "mode", "filter", "data_mode",
        "att", "preamp", "nb", "nr", "digisel", "ipplus",
        "s_meter_sql_open", "agc", "audio_peak_filter", "auto_notch",
        "manual_notch", "twin_peak_filter", "filter_shape",
        "agc_time_constant",
        "af_level", "rf_gain", "squelch", "s_meter",
        "apf_type_level", "nr_level", "pbt_inner", "pbt_outer",
        "nb_level", "digisel_shift", "af_mute",
    }
    assert set(main.keys()) == expected_keys


def test_to_dict_reflects_field_changes() -> None:
    rs = RadioState()
    rs.main.freq = 14_074_000
    rs.main.mode = "USB"
    rs.main.att = 18
    rs.ptt = True
    rs.split = True
    d = rs.to_dict()
    assert d["ptt"] is True
    assert d["split"] is True
    assert d["main"]["freq"] == 14_074_000
    assert d["main"]["att"] == 18


def test_to_dict_sub_independent() -> None:
    rs = RadioState()
    rs.main.freq = 14_000_000
    rs.sub.freq = 7_000_000
    d = rs.to_dict()
    assert d["main"]["freq"] == 14_000_000
    assert d["sub"]["freq"] == 7_000_000


def test_to_dict_is_json_serialisable() -> None:
    import json
    rs = RadioState()
    rs.main.freq = 14_074_000
    rs.main.nb = True
    rs.ptt = False
    payload = json.dumps(rs.to_dict())
    reloaded = json.loads(payload)
    assert reloaded["main"]["freq"] == 14_074_000
    assert reloaded["main"]["nb"] is True


# --- Transceiver status family (#136) ---

class TestTransceiverStatusState:
    """Test RadioState fields for transceiver_status family."""

    def test_tuner_status_default(self) -> None:
        rs = RadioState()
        assert rs.tuner_status == 0

    def test_tuner_status_set(self) -> None:
        rs = RadioState()
        rs.tuner_status = 2
        assert rs.tuner_status == 2
        d = rs.to_dict()
        assert d["tuner_status"] == 2

    def test_tx_freq_monitor_default(self) -> None:
        rs = RadioState()
        assert rs.tx_freq_monitor is False

    def test_rit_fields_defaults(self) -> None:
        rs = RadioState()
        assert rs.rit_freq == 0
        assert rs.rit_on is False
        assert rs.rit_tx is False

    def test_rit_fields_set(self) -> None:
        rs = RadioState()
        rs.rit_freq = -150
        rs.rit_on = True
        rs.rit_tx = True
        d = rs.to_dict()
        assert d["rit_freq"] == -150
        assert d["rit_on"] is True
        assert d["rit_tx"] is True

    def test_meter_fields_defaults(self) -> None:
        rs = RadioState()
        assert rs.comp_meter == 0
        assert rs.vd_meter == 0
        assert rs.id_meter == 0

    def test_meter_fields_in_dict(self) -> None:
        rs = RadioState()
        rs.comp_meter = 42
        rs.vd_meter = 130
        rs.id_meter = 55
        d = rs.to_dict()
        assert d["comp_meter"] == 42
        assert d["vd_meter"] == 130
        assert d["id_meter"] == 55
