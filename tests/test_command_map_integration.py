"""CommandMap integration tests — verify cmd_map parity with hardcoded commands.

For IC-7610, calling any command function with cmd_map from the TOML must
produce identical output to calling without (hardcoded bytes).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from icom_lan import commands
from icom_lan.command_map import CommandMap
from icom_lan.rig_loader import load_rig

RIG_DIR = Path(__file__).resolve().parents[1] / "rigs"


@pytest.fixture()
def cmd_map():
    rig = load_rig(RIG_DIR / "ic7610.toml")
    return rig.to_command_map()


# ── Profile parity: getters (no data) ──────────────────────────


class TestGetterParity:
    """Calling getters with IC-7610 cmd_map must match hardcoded output."""

    def test_get_frequency(self, cmd_map):
        assert commands.get_freq(cmd_map=cmd_map) == commands.get_freq()

    def test_get_mode(self, cmd_map):
        assert commands.get_mode(cmd_map=cmd_map) == commands.get_mode()

    def test_get_af_level(self, cmd_map):
        assert commands.get_af_level(cmd_map=cmd_map) == commands.get_af_level()

    def test_get_rf_gain(self, cmd_map):
        assert commands.get_rf_gain(cmd_map=cmd_map) == commands.get_rf_gain()

    def test_get_power(self, cmd_map):
        assert commands.get_rf_power(cmd_map=cmd_map) == commands.get_rf_power()

    def test_get_s_meter(self, cmd_map):
        assert commands.get_s_meter(cmd_map=cmd_map) == commands.get_s_meter()

    def test_get_swr(self, cmd_map):
        assert commands.get_swr(cmd_map=cmd_map) == commands.get_swr()

    def test_get_alc(self, cmd_map):
        assert commands.get_alc(cmd_map=cmd_map) == commands.get_alc()

    def test_get_tuning_step(self, cmd_map):
        assert commands.get_tuning_step(cmd_map=cmd_map) == commands.get_tuning_step()

    def test_get_nb(self, cmd_map):
        assert commands.get_nb(cmd_map=cmd_map) == commands.get_nb()

    def test_get_nr(self, cmd_map):
        assert commands.get_nr(cmd_map=cmd_map) == commands.get_nr()

    def test_get_ip_plus(self, cmd_map):
        assert commands.get_ip_plus(cmd_map=cmd_map) == commands.get_ip_plus()

    def test_get_power_meter(self, cmd_map):
        assert commands.get_power_meter(cmd_map=cmd_map) == commands.get_power_meter()

    def test_get_transceiver_id(self, cmd_map):
        assert commands.get_transceiver_id(cmd_map=cmd_map) == commands.get_transceiver_id()

    def test_get_band_edge_freq(self, cmd_map):
        assert commands.get_band_edge_freq(cmd_map=cmd_map) == commands.get_band_edge_freq()

    def test_scope_on(self, cmd_map):
        assert commands.scope_on(cmd_map=cmd_map) == commands.scope_on()

    def test_scope_off(self, cmd_map):
        assert commands.scope_off(cmd_map=cmd_map) == commands.scope_off()


# ── Profile parity: setters (with data) ────────────────────────


class TestSetterParity:
    """Calling setters with IC-7610 cmd_map must match hardcoded output."""

    def test_set_frequency(self, cmd_map):
        assert commands.set_freq(14_200_000, cmd_map=cmd_map) == commands.set_freq(14_200_000)

    def test_set_power(self, cmd_map):
        assert commands.set_rf_power(128, cmd_map=cmd_map) == commands.set_rf_power(128)

    def test_set_af_level(self, cmd_map):
        assert commands.set_af_level(200, cmd_map=cmd_map) == commands.set_af_level(200)

    def test_set_rf_gain(self, cmd_map):
        assert commands.set_rf_gain(128, cmd_map=cmd_map) == commands.set_rf_gain(128)

    def test_set_squelch(self, cmd_map):
        assert commands.set_squelch(64, cmd_map=cmd_map) == commands.set_squelch(64)

    def test_set_tuning_step(self, cmd_map):
        assert commands.set_tuning_step(3, cmd_map=cmd_map) == commands.set_tuning_step(3)

    def test_ptt_on(self, cmd_map):
        assert commands.ptt_on(cmd_map=cmd_map) == commands.ptt_on()

    def test_ptt_off(self, cmd_map):
        assert commands.ptt_off(cmd_map=cmd_map) == commands.ptt_off()

    def test_power_on(self, cmd_map):
        assert commands.power_on(cmd_map=cmd_map) == commands.power_on()

    def test_power_off(self, cmd_map):
        assert commands.power_off(cmd_map=cmd_map) == commands.power_off()

    def test_stop_cw(self, cmd_map):
        assert commands.stop_cw(cmd_map=cmd_map) == commands.stop_cw()

    def test_start_scan(self, cmd_map):
        assert commands.scan_start(cmd_map=cmd_map) == commands.scan_start()

    def test_stop_scan(self, cmd_map):
        assert commands.scan_stop(cmd_map=cmd_map) == commands.scan_stop()


# ── Helper-delegating functions ─────────────────────────────────


class TestHelperCallerParity:
    """Functions delegating to _build_* helpers must match with cmd_map."""

    def test_get_apf_type_level(self, cmd_map):
        assert commands.get_apf_type_level(cmd_map=cmd_map) == commands.get_apf_type_level()

    def test_get_nr_level(self, cmd_map):
        assert commands.get_nr_level(cmd_map=cmd_map) == commands.get_nr_level()

    def test_get_nb_level(self, cmd_map):
        assert commands.get_nb_level(cmd_map=cmd_map) == commands.get_nb_level()

    def test_get_agc(self, cmd_map):
        assert commands.get_agc(cmd_map=cmd_map) == commands.get_agc()

    def test_get_compressor(self, cmd_map):
        assert commands.get_compressor(cmd_map=cmd_map) == commands.get_compressor()

    def test_get_monitor(self, cmd_map):
        assert commands.get_monitor(cmd_map=cmd_map) == commands.get_monitor()

    def test_get_vox(self, cmd_map):
        assert commands.get_vox(cmd_map=cmd_map) == commands.get_vox()

    def test_get_break_in(self, cmd_map):
        assert commands.get_break_in(cmd_map=cmd_map) == commands.get_break_in()

    def test_get_dial_lock(self, cmd_map):
        assert commands.get_dial_lock(cmd_map=cmd_map) == commands.get_dial_lock()

    def test_get_filter_shape(self, cmd_map):
        assert commands.get_filter_shape(cmd_map=cmd_map) == commands.get_filter_shape()

    def test_get_ref_adjust(self, cmd_map):
        assert commands.get_ref_adjust(cmd_map=cmd_map) == commands.get_ref_adjust()

    def test_get_s_meter_sql_status(self, cmd_map):
        assert commands.get_s_meter_sql_status(cmd_map=cmd_map) == commands.get_s_meter_sql_status()

    def test_get_agc_time_constant(self, cmd_map):
        assert commands.get_agc_time_constant(cmd_map=cmd_map) == commands.get_agc_time_constant()


# ── cmd29-aware functions ───────────────────────────────────────


class TestCmd29Parity:
    """Functions using cmd29 framing must match with cmd_map."""

    def test_get_attenuator(self, cmd_map):
        assert commands.get_attenuator(cmd_map=cmd_map) == commands.get_attenuator()

    def test_get_preamp(self, cmd_map):
        assert commands.get_preamp(cmd_map=cmd_map) == commands.get_preamp()

    def test_get_digisel(self, cmd_map):
        assert commands.get_digisel(cmd_map=cmd_map) == commands.get_digisel()

    def test_get_af_mute(self, cmd_map):
        assert commands.get_af_mute(cmd_map=cmd_map) == commands.get_af_mute()

    def test_get_audio_peak_filter(self, cmd_map):
        assert commands.get_audio_peak_filter(cmd_map=cmd_map) == commands.get_audio_peak_filter()

    def test_get_auto_notch(self, cmd_map):
        assert commands.get_auto_notch(cmd_map=cmd_map) == commands.get_auto_notch()

    def test_get_manual_notch(self, cmd_map):
        assert commands.get_manual_notch(cmd_map=cmd_map) == commands.get_manual_notch()

    def test_get_twin_peak_filter(self, cmd_map):
        assert commands.get_twin_peak_filter(cmd_map=cmd_map) == commands.get_twin_peak_filter()

    def test_get_various_squelch(self, cmd_map):
        assert commands.get_various_squelch(cmd_map=cmd_map) == commands.get_various_squelch()


# ── Custom CommandMap (different wire bytes) ────────────────────


class TestCommandMapOverride:
    """Custom CommandMap with different wire bytes produces different output."""

    def test_different_wire_bytes_produce_different_frame(self):
        custom = CommandMap({"get_af_level": (0x16, 0x43)})
        result = commands.get_af_level(cmd_map=custom)
        hardcoded = commands.get_af_level()
        assert result != hardcoded
        assert b"\x16\x43" in result

    def test_custom_single_byte_command(self):
        custom = CommandMap({"get_freq": (0xFF,)})
        result = commands.get_freq(cmd_map=custom)
        assert b"\xff" in result
        assert result != commands.get_freq()

    def test_custom_setter(self):
        custom = CommandMap({"set_rf_power": (0x14, 0xFF)})
        result = commands.set_rf_power(128, cmd_map=custom)
        hardcoded = commands.set_rf_power(128)
        assert result != hardcoded
        assert b"\x14\xff" in result

    def test_four_byte_wire_extended_sub(self):
        """IC-7300 style: 4-byte wire like [0x1A, 0x05, 0x00, 0x64].

        Bytes 0-1 are command+sub, bytes 2+ are prepended to data payload.
        """
        custom = CommandMap({"get_acc1_mod_level": (0x1A, 0x05, 0x00, 0x64)})
        result = commands.get_acc1_mod_level(cmd_map=custom)
        # Frame: FE FE <to> <from> 1A 05 00 64 FD
        assert b"\x1a\x05\x00\x64" in result
        assert result.startswith(b"\xfe\xfe")
        assert result.endswith(b"\xfd")

    def test_four_byte_wire_with_set_data(self):
        """4-byte wire + data: extra wire bytes prepend to data."""
        custom = CommandMap({"set_acc1_mod_level": (0x1A, 0x05, 0x00, 0x64)})
        result = commands.set_acc1_mod_level(128, cmd_map=custom)
        # Frame: FE FE <to> <from> 1A 05 00 64 <level_bcd> FD
        assert b"\x1a\x05\x00\x64" in result
        # The level data should follow the extended sub-command bytes
        idx = result.index(b"\x00\x64")
        assert idx + 2 < len(result) - 1  # there's data after 00 64 before FD
