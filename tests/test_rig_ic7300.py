"""IC-7300 TOML tests — verify ic7300.toml loads correctly and overrides are accurate.

TDD: these tests were written FIRST, then the TOML was created to pass them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from icom_lan.rig_loader import load_rig

RIGS_DIR = Path(__file__).resolve().parent.parent / "rigs"
IC7300_PATH = RIGS_DIR / "ic7300.toml"


@pytest.fixture()
def rig():
    return load_rig(IC7300_PATH)


@pytest.fixture()
def profile(rig):
    return rig.to_profile()


@pytest.fixture()
def cmdmap(rig):
    return rig.to_command_map()


# ── Profile basics ─────────────────────────────────────────────


class TestProfileBasics:
    """ic7300.toml profile must have correct metadata."""

    def test_loads_without_error(self, rig):
        assert rig is not None

    def test_profile_id(self, profile):
        assert profile.id == "icom_ic7300"

    def test_model(self, profile):
        assert profile.model == "IC-7300"

    def test_civ_addr(self, profile):
        assert profile.civ_addr == 0x94

    def test_receiver_count(self, profile):
        assert profile.receiver_count == 1

    def test_no_cmd29_routes(self, profile):
        assert len(profile.cmd29_routes) == 0

    def test_modes(self, profile):
        assert profile.modes == ("USB", "LSB", "CW", "CW-R", "AM", "FM", "RTTY", "RTTY-R")

    def test_filters(self, profile):
        assert profile.filters == ("FIL1", "FIL2", "FIL3")


# ── VFO scheme ─────────────────────────────────────────────────


class TestVFOScheme:
    """IC-7300 uses A/B VFO scheme, not main/sub."""

    def test_vfo_main_code_is_a(self, profile):
        # In ab scheme, "main" maps to VFO-A
        assert profile.vfo_main_code == 0x00

    def test_vfo_sub_code_is_b(self, profile):
        # In ab scheme, "sub" maps to VFO-B
        assert profile.vfo_sub_code == 0x01

    def test_vfo_swap_code(self, profile):
        assert profile.vfo_swap_code == 0xB0


# ── Capabilities ───────────────────────────────────────────────


class TestCapabilities:
    """IC-7300 capabilities: no dual_rx, digisel, ip_plus."""

    def test_has_audio(self, profile):
        assert "audio" in profile.capabilities

    def test_has_scope(self, profile):
        assert "scope" in profile.capabilities

    def test_has_meters(self, profile):
        assert "meters" in profile.capabilities

    def test_has_tx(self, profile):
        assert "tx" in profile.capabilities

    def test_has_nb(self, profile):
        assert "nb" in profile.capabilities

    def test_has_nr(self, profile):
        assert "nr" in profile.capabilities

    def test_has_attenuator(self, profile):
        assert "attenuator" in profile.capabilities

    def test_has_preamp(self, profile):
        assert "preamp" in profile.capabilities

    def test_no_dual_rx(self, profile):
        assert "dual_rx" not in profile.capabilities

    def test_no_digisel(self, profile):
        assert "digisel" not in profile.capabilities

    def test_no_ip_plus(self, profile):
        assert "ip_plus" not in profile.capabilities

    def test_capabilities_count(self, profile):
        assert len(profile.capabilities) == 12


# ── Command overrides ──────────────────────────────────────────


class TestCommandOverrides:
    """14 commands differ from IC-7610; verify IC-7300-specific wire bytes."""

    def test_acc1_mod_level(self, cmdmap):
        assert cmdmap.get("acc1_mod_level") == (0x1A, 0x05, 0x00, 0x64)

    def test_usb_mod_level(self, cmdmap):
        assert cmdmap.get("usb_mod_level") == (0x1A, 0x05, 0x00, 0x65)

    def test_data_off_mod_input(self, cmdmap):
        assert cmdmap.get("data_off_mod_input") == (0x1A, 0x05, 0x00, 0x66)

    def test_data1_mod_input(self, cmdmap):
        assert cmdmap.get("data1_mod_input") == (0x1A, 0x05, 0x00, 0x67)

    def test_civ_transceive(self, cmdmap):
        assert cmdmap.get("civ_transceive") == (0x1A, 0x05, 0x00, 0x71)

    def test_system_date(self, cmdmap):
        assert cmdmap.get("system_date") == (0x1A, 0x05, 0x00, 0x94)

    def test_system_time(self, cmdmap):
        assert cmdmap.get("system_time") == (0x1A, 0x05, 0x00, 0x95)

    def test_utc_offset(self, cmdmap):
        assert cmdmap.get("utc_offset") == (0x1A, 0x05, 0x00, 0x96)

    def test_quick_split(self, cmdmap):
        assert cmdmap.get("quick_split") == (0x1A, 0x05, 0x00, 0x30)

    def test_nb_depth(self, cmdmap):
        assert cmdmap.get("nb_depth") == (0x1A, 0x05, 0x01, 0x89)

    def test_nb_width(self, cmdmap):
        assert cmdmap.get("nb_width") == (0x1A, 0x05, 0x01, 0x90)

    def test_get_s_meter_sql_status(self, cmdmap):
        assert cmdmap.get("get_s_meter_sql_status") == (0x16, 0x43)

    def test_civ_output_ant(self, cmdmap):
        assert cmdmap.get("civ_output_ant") == (0x1A, 0x05, 0x00, 0x61)

    def test_agc_time_constant(self, cmdmap):
        assert cmdmap.get("agc_time_constant") == (0x1A, 0x04)


# ── Shared commands (same wire bytes as IC-7610) ───────────────


class TestSharedCommands:
    """Commands not overridden must match IC-7610 wire bytes."""

    def test_get_freq(self, cmdmap):
        assert cmdmap.get("get_freq") == (0x03,)

    def test_get_s_meter(self, cmdmap):
        assert cmdmap.get("get_s_meter") == (0x15, 0x02)

    def test_get_mode(self, cmdmap):
        assert cmdmap.get("get_mode") == (0x04,)

    def test_ptt_on(self, cmdmap):
        assert cmdmap.get("ptt_on") == (0x1C, 0x00)

    def test_scope_on(self, cmdmap):
        assert cmdmap.get("scope_on") == (0x27, 0x10)


# ── Removed commands (not available on IC-7300) ────────────────


class TestRemovedCommands:
    """Commands that should NOT be in the IC-7300 command map."""

    def test_no_digisel(self, cmdmap):
        assert not cmdmap.has("get_digisel")
        assert not cmdmap.has("set_digisel")

    def test_no_ip_plus(self, cmdmap):
        assert not cmdmap.has("get_ip_plus")
        assert not cmdmap.has("set_ip_plus")

    def test_no_digisel_shift(self, cmdmap):
        assert not cmdmap.has("get_digisel_shift")
        assert not cmdmap.has("set_digisel_shift")

    def test_no_drive_gain(self, cmdmap):
        assert not cmdmap.has("get_drive_gain")
        assert not cmdmap.has("set_drive_gain")

    def test_no_scope_main_sub(self, cmdmap):
        assert not cmdmap.has("get_scope_main_sub")


# ── Spectrum params ────────────────────────────────────────────


class TestSpectrumParams:
    """IC-7300 spectrum parameters (same as IC-7610 for these values)."""

    def test_seq_max(self, rig):
        assert rig.spectrum["seq_max"] == 11

    def test_amp_max(self, rig):
        assert rig.spectrum["amp_max"] == 160

    def test_data_len_max(self, rig):
        assert rig.spectrum["data_len_max"] == 475
