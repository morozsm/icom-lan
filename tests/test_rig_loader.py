"""Tests for rig_loader and command_map modules.

TDD: these tests were written FIRST, then the implementation.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from icom_lan.command_map import CommandMap
from icom_lan.profiles import BandInfo, FreqRangeInfo, RadioProfile
from icom_lan.rig_loader import RigConfig, RigLoadError, discover_rigs, load_rig

RIGS_DIR = Path(__file__).resolve().parent.parent / "rigs"
TEMPLATE_PATH = RIGS_DIR / "ic7610.toml"


# ── Helpers ──────────────────────────────────────────────────────


def _write_toml(tmp_path: Path, content: str, name: str = "test.toml") -> Path:
    """Write a TOML string to a temp file and return the path."""
    p = tmp_path / name
    p.write_text(textwrap.dedent(content))
    return p


_MINIMAL_TOML = """\
[radio]
id = "icom_ic7300"
model = "IC-7300"
civ_addr = 0x94
receiver_count = 1
has_lan = true
has_wifi = false

[spectrum]
seq_max = 11
amp_max = 160
data_len_max = 475

[capabilities]
features = ["audio", "scope", "meters", "tx"]

[modes]
list = ["USB", "LSB", "CW"]

[filters]
list = ["FIL1", "FIL2"]

[vfo]
scheme = "ab"

[[freq_ranges.ranges]]
label = "HF"
start_hz = 30000
end_hz = 60000000

[commands]
get_freq = [0x03]
set_freq = [0x05]

[commands.overrides]
"""


# ── RigConfig loading ────────────────────────────────────────────


class TestLoadRig:
    """load_rig() parsing and validation."""

    def test_load_template(self):
        rig = load_rig(TEMPLATE_PATH)
        assert isinstance(rig, RigConfig)
        assert rig.model == "IC-7610"
        assert rig.id == "icom_ic7610"
        assert rig.civ_addr == 0x98
        assert rig.receiver_count == 2

    def test_load_minimal(self, tmp_path):
        p = _write_toml(tmp_path, _MINIMAL_TOML)
        rig = load_rig(p)
        assert rig.model == "IC-7300"

    def test_missing_radio_section(self, tmp_path):
        p = _write_toml(tmp_path, """\
            [spectrum]
            seq_max = 1
            amp_max = 1
            data_len_max = 1
        """)
        with pytest.raises(RigLoadError, match="radio"):
            load_rig(p)

    def test_missing_required_field(self, tmp_path):
        toml = _MINIMAL_TOML.replace('id = "icom_ic7300"\n', "")
        p = _write_toml(tmp_path, toml)
        with pytest.raises(RigLoadError, match="id"):
            load_rig(p)

    def test_civ_addr_out_of_range(self, tmp_path):
        toml = _MINIMAL_TOML.replace("civ_addr = 0x94", "civ_addr = 256")
        p = _write_toml(tmp_path, toml)
        with pytest.raises(RigLoadError, match="civ_addr"):
            load_rig(p)

    def test_empty_capabilities(self, tmp_path):
        toml = _MINIMAL_TOML.replace(
            'features = ["audio", "scope", "meters", "tx"]',
            "features = []",
        )
        p = _write_toml(tmp_path, toml)
        with pytest.raises(RigLoadError, match="capabilities"):
            load_rig(p)

    def test_unknown_capability(self, tmp_path):
        toml = _MINIMAL_TOML.replace(
            'features = ["audio", "scope", "meters", "tx"]',
            'features = ["audio", "teleportation"]',
        )
        p = _write_toml(tmp_path, toml)
        with pytest.raises(RigLoadError, match="teleportation"):
            load_rig(p)

    def test_invalid_vfo_scheme(self, tmp_path):
        toml = _MINIMAL_TOML.replace('scheme = "ab"', 'scheme = "xyz"')
        p = _write_toml(tmp_path, toml)
        with pytest.raises(RigLoadError, match="vfo.*scheme"):
            load_rig(p)

    def test_file_not_found(self, tmp_path):
        with pytest.raises(RigLoadError, match="not found"):
            load_rig(tmp_path / "nonexistent.toml")

    def test_invalid_toml_syntax(self, tmp_path):
        p = _write_toml(tmp_path, "this is not [valid toml")
        with pytest.raises(RigLoadError):
            load_rig(p)


# ── RadioProfile building ───────────────────────────────────────


class TestToProfile:
    """RigConfig.to_profile() produces correct RadioProfile."""

    def test_returns_radio_profile(self):
        rig = load_rig(TEMPLATE_PATH)
        profile = rig.to_profile()
        assert isinstance(profile, RadioProfile)

    def test_civ_addr(self):
        profile = load_rig(TEMPLATE_PATH).to_profile()
        assert profile.civ_addr == 0x98

    def test_receiver_count(self):
        profile = load_rig(TEMPLATE_PATH).to_profile()
        assert profile.receiver_count == 2

    def test_capabilities_frozenset(self):
        profile = load_rig(TEMPLATE_PATH).to_profile()
        assert isinstance(profile.capabilities, frozenset)
        assert "audio" in profile.capabilities
        assert "dual_rx" in profile.capabilities

    def test_vfo_main_sub_codes(self):
        profile = load_rig(TEMPLATE_PATH).to_profile()
        assert profile.vfo_main_code == 0xD0
        assert profile.vfo_sub_code == 0xD1
        assert profile.vfo_swap_code == 0xB0

    def test_vfo_ab_codes(self, tmp_path):
        p = _write_toml(tmp_path, _MINIMAL_TOML)
        profile = load_rig(p).to_profile()
        # ab scheme with no explicit codes → None
        assert profile.vfo_main_code is None
        assert profile.vfo_sub_code is None

    def test_freq_ranges(self):
        profile = load_rig(TEMPLATE_PATH).to_profile()
        assert isinstance(profile.freq_ranges, tuple)
        assert len(profile.freq_ranges) == 2
        hf = profile.freq_ranges[0]
        assert isinstance(hf, FreqRangeInfo)
        assert hf.start == 30_000
        assert hf.end == 60_000_000
        assert hf.label == "HF"

    def test_freq_range_bands(self):
        profile = load_rig(TEMPLATE_PATH).to_profile()
        hf = profile.freq_ranges[0]
        assert len(hf.bands) == 10
        band_160 = hf.bands[0]
        assert isinstance(band_160, BandInfo)
        assert band_160.name == "160m"
        assert band_160.start == 1_800_000
        assert band_160.end == 2_000_000
        assert band_160.default == 1_825_000

    def test_modes(self):
        profile = load_rig(TEMPLATE_PATH).to_profile()
        assert profile.modes == ("USB", "LSB", "CW", "CW-R", "AM", "FM", "RTTY", "RTTY-R", "PSK", "PSK-R")

    def test_filters(self):
        profile = load_rig(TEMPLATE_PATH).to_profile()
        assert profile.filters == ("FIL1", "FIL2", "FIL3")

    def test_model_and_id(self):
        profile = load_rig(TEMPLATE_PATH).to_profile()
        assert profile.model == "IC-7610"
        assert profile.id == "icom_ic7610"


# ── CommandMap ───────────────────────────────────────────────────


class TestCommandMap:
    """CommandMap basic API."""

    def test_get_returns_wire_bytes(self):
        cm = CommandMap({"af_gain": (0x14, 0x01)})
        assert cm.get("af_gain") == (0x14, 0x01)

    def test_get_missing_raises_key_error(self):
        cm = CommandMap({"af_gain": (0x14, 0x01)})
        with pytest.raises(KeyError, match="nonexistent"):
            cm.get("nonexistent")

    def test_has_existing(self):
        cm = CommandMap({"af_gain": (0x14, 0x01)})
        assert cm.has("af_gain") is True

    def test_has_missing(self):
        cm = CommandMap({"af_gain": (0x14, 0x01)})
        assert cm.has("nonexistent") is False

    def test_len(self):
        cm = CommandMap({"a": (0x01,), "b": (0x02,)})
        assert len(cm) == 2

    def test_iter(self):
        cm = CommandMap({"a": (0x01,), "b": (0x02,)})
        assert sorted(cm) == ["a", "b"]

    def test_repr(self):
        cm = CommandMap({"a": (0x01,)})
        assert "CommandMap" in repr(cm)
        assert "1" in repr(cm)


class TestToCommandMap:
    """RigConfig.to_command_map() integration."""

    def test_returns_command_map(self):
        rig = load_rig(TEMPLATE_PATH)
        cm = rig.to_command_map()
        assert isinstance(cm, CommandMap)

    def test_has_expected_commands(self):
        cm = load_rig(TEMPLATE_PATH).to_command_map()
        assert cm.has("get_freq")
        assert cm.has("set_freq")
        assert cm.has("get_af_level")
        assert cm.has("ptt_on")
        assert cm.has("scope_on")

    def test_wire_bytes_correct(self):
        cm = load_rig(TEMPLATE_PATH).to_command_map()
        assert cm.get("get_freq") == (0x03,)
        assert cm.get("get_af_level") == (0x14, 0x01)
        assert cm.get("ptt_on") == (0x1C, 0x00)

    def test_command_count(self):
        cm = load_rig(TEMPLATE_PATH).to_command_map()
        assert len(cm) > 50  # template has ~100 commands


# ── discover_rigs ────────────────────────────────────────────────


class TestDiscoverRigs:
    """discover_rigs() directory scanning."""

    def test_finds_rig_files(self, tmp_path):
        (tmp_path / "ic7300.toml").write_text(_MINIMAL_TOML)
        rigs = discover_rigs(tmp_path)
        assert "IC-7300" in rigs
        assert isinstance(rigs["IC-7300"], RigConfig)

    def test_discovers_ic7610(self):
        # rigs/ has ic7610.toml — should be discovered
        rigs = discover_rigs(RIGS_DIR)
        assert "IC-7610" in rigs

    def test_ignores_underscore_prefix(self, tmp_path):
        # Create a proper rig file and an underscore-prefixed file
        (tmp_path / "ic7300.toml").write_text(_MINIMAL_TOML)
        (tmp_path / "_defaults.toml").write_text(_MINIMAL_TOML)
        rigs = discover_rigs(tmp_path)
        assert "IC-7300" in rigs
        assert len(rigs) == 1  # _defaults.toml was ignored

    def test_returns_dict_keyed_by_model(self, tmp_path):
        (tmp_path / "ic7300.toml").write_text(_MINIMAL_TOML)
        rigs = discover_rigs(tmp_path)
        for model, rig in rigs.items():
            assert rig.model == model

    def test_empty_directory(self, tmp_path):
        rigs = discover_rigs(tmp_path)
        assert rigs == {}
