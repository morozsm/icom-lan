"""IC-7610 TOML parity tests — verify TOML matches hardcoded Python exactly.

TDD: these tests were written FIRST, then the TOML was fixed to pass them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from icom_lan.profiles import RadioProfile, _CMD29_7610, _DUAL_CAPS
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
        assert profile.capabilities == _DUAL_CAPS

    def test_capabilities_count(self, profile):
        assert len(profile.capabilities) == 15

    def test_cmd29_routes_exact(self, profile):
        assert profile.cmd29_routes == _CMD29_7610

    def test_cmd29_routes_count(self, profile):
        assert len(profile.cmd29_routes) == 24

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
        assert profile.modes == ("USB", "LSB", "CW", "CW-R", "AM", "FM", "RTTY", "RTTY-R")

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
