"""IC-7610 TOML profile tests — verify TOML produces correct RadioProfile.

All profile data comes from TOML; there are no hardcoded constants to
compare against.  Tests verify expected values directly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from icom_lan.profiles import RadioProfile
from icom_lan.rig_loader import load_rig

RIGS_DIR = Path(__file__).resolve().parent.parent / "rigs"
IC7610_PATH = RIGS_DIR / "ic7610.toml"


@pytest.fixture()
def rig():
    return load_rig(IC7610_PATH)


@pytest.fixture()
def profile(rig):
    return rig.to_profile()


@pytest.fixture()
def cmdmap(rig):
    return rig.to_command_map()


# ── Profile parity ──────────────────────────────────────────────


class TestProfileParity:
    """ic7610.toml profile must match hardcoded RadioProfile exactly."""

    def test_loads_without_error(self, rig):
        assert rig is not None

    def test_profile_id(self, profile):
        assert profile.id == "icom_ic7610"

    def test_model(self, profile):
        assert profile.model == "IC-7610"

    def test_civ_addr(self, profile):
        assert profile.civ_addr == 0x98

    def test_receiver_count(self, profile):
        assert profile.receiver_count == 2

    def test_capabilities_exact(self, profile):
        expected = frozenset({
            # Receiver
            "audio", "dual_rx", "dual_watch", "af_level", "rf_gain", "squelch",
            # RF front end
            "attenuator", "preamp", "digisel", "ip_plus",
            # Antenna
            "antenna", "rx_antenna",
            # DSP / Noise
            "nb", "nr", "notch", "apf", "twin_peak",
            # Filter
            "pbt", "filter_width", "filter_shape",
            # TX
            "tx", "split", "vox", "compressor", "monitor", "drive_gain", "ssb_tx_bw",
            # CW
            "cw", "break_in",
            # RIT / XIT
            "rit", "xit",
            # Tuner
            "tuner",
            # Metering / Scope
            "meters", "scope",
            # Tone
            "repeater_tone", "tsql",
            # Data / System
            "data_mode", "power_control", "dial_lock", "scan", "bsr",
            "main_sub_tracking",
        })
        assert profile.capabilities == expected

    def test_capabilities_count(self, profile):
        assert len(profile.capabilities) == 42

    def test_cmd29_routes_exact(self, profile):
        expected = frozenset({
            (0x11, None), (0x12, None),
            (0x14, 0x01), (0x14, 0x02), (0x14, 0x03),
            (0x14, 0x05), (0x14, 0x06), (0x14, 0x07), (0x14, 0x08),
            (0x14, 0x0D), (0x14, 0x12), (0x14, 0x13),
            (0x15, 0x01), (0x15, 0x02), (0x15, 0x05),
            (0x16, 0x02), (0x16, 0x22), (0x16, 0x32),
            (0x16, 0x40), (0x16, 0x41), (0x16, 0x42), (0x16, 0x43),
            (0x16, 0x48), (0x16, 0x4E), (0x16, 0x4F),
            (0x16, 0x53), (0x16, 0x56), (0x16, 0x65),
            (0x1A, 0x03), (0x1A, 0x04), (0x1A, 0x09),
            (0x1B, 0x00), (0x1B, 0x01),
        })
        assert profile.cmd29_routes == expected

    def test_cmd29_routes_count(self, profile):
        assert len(profile.cmd29_routes) == 33

    def test_vfo_main_code(self, profile):
        assert profile.vfo_main_code == 0xD0

    def test_vfo_sub_code(self, profile):
        assert profile.vfo_sub_code == 0xD1

    def test_vfo_swap_code(self, profile):
        assert profile.vfo_swap_code == 0xB0

    def test_freq_ranges_count(self, profile):
        assert len(profile.freq_ranges) == 2

    def test_freq_range_hf(self, profile):
        hf = profile.freq_ranges[0]
        assert hf.start == 30_000
        assert hf.end == 60_000_000
        assert hf.label == "HF"

    def test_freq_range_6m(self, profile):
        sixm = profile.freq_ranges[1]
        assert sixm.start == 50_000_000
        assert sixm.end == 54_000_000
        assert sixm.label == "6m"

    def test_hf_bands_count(self, profile):
        hf = profile.freq_ranges[0]
        assert len(hf.bands) == 10

    def test_modes(self, profile):
        assert profile.modes == ("USB", "LSB", "CW", "CW-R", "AM", "FM", "RTTY", "RTTY-R", "PSK", "PSK-R")

    def test_filters(self, profile):
        assert profile.filters == ("FIL1", "FIL2", "FIL3")


# ── CommandMap parity ───────────────────────────────────────────


class TestCommandMapParity:
    """ic7610.toml commands must have correct wire bytes."""

    def test_get_freq(self, cmdmap):
        assert cmdmap.get("get_freq") == (0x03,)

    def test_set_freq(self, cmdmap):
        assert cmdmap.get("set_freq") == (0x05,)

    def test_get_af_level(self, cmdmap):
        assert cmdmap.get("get_af_level") == (0x14, 0x01)

    def test_get_s_meter(self, cmdmap):
        assert cmdmap.get("get_s_meter") == (0x15, 0x02)

    def test_get_power_meter(self, cmdmap):
        assert cmdmap.get("get_power_meter") == (0x15, 0x11)

    def test_get_swr(self, cmdmap):
        assert cmdmap.get("get_swr") == (0x15, 0x12)

    def test_ptt_on(self, cmdmap):
        assert cmdmap.get("ptt_on") == (0x1C, 0x00)

    def test_scope_on(self, cmdmap):
        assert cmdmap.get("scope_on") == (0x27, 0x10)

    def test_send_cw(self, cmdmap):
        assert cmdmap.get("send_cw") == (0x17,)

    def test_command_count_minimum(self, cmdmap):
        assert len(cmdmap) >= 90


# ── cmd29 route detail checks ──────────────────────────────────


class TestCmd29Detail:
    """Verify specific cmd29 route entries."""

    def test_att_cmd_only(self, profile):
        assert (0x11, None) in profile.cmd29_routes

    def test_af_gain(self, profile):
        assert (0x14, 0x01) in profile.cmd29_routes

    def test_rf_gain(self, profile):
        assert (0x14, 0x02) in profile.cmd29_routes

    def test_preamp(self, profile):
        assert (0x16, 0x02) in profile.cmd29_routes

    def test_ip_plus(self, profile):
        assert (0x16, 0x65) in profile.cmd29_routes

    def test_agc_time_constant(self, profile):
        assert (0x1A, 0x04) in profile.cmd29_routes

    def test_af_mute(self, profile):
        assert (0x1A, 0x09) in profile.cmd29_routes
