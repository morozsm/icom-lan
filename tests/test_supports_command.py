"""Tests for Radio.supports_command() — Phase 3 of unified capability gating."""

from __future__ import annotations

from pathlib import Path

import pytest

from icom_lan.backends.yaesu_cat.radio import YaesuCatRadio
from icom_lan.radio import CoreRadio
from icom_lan.rig_loader import load_rig

_RIGS_DIR = Path(__file__).parents[1] / "rigs"


# ---------------------------------------------------------------------------
# CoreRadio (base for all Icom LAN + serial backends)
# ---------------------------------------------------------------------------


class TestIcomSupportsCommand:
    """CoreRadio.supports_command checks _KNOWN_COMMANDS."""

    def test_known_commands_return_true(self):
        known = [
            "get_freq",
            "set_freq",
            "get_mode",
            "set_mode",
            "set_ptt",
            "get_s_meter",
            "set_nb",
            "set_nr",
            "set_agc",
            "set_attenuator",
            "set_preamp",
            "set_filter",
            "send_cw_text",
            "set_key_speed",
            "get_key_speed",
            "enable_scope",
            "disable_scope",
            "get_powerstat",
            "set_powerstat",
            "send_civ",
        ]
        for cmd in known:
            assert CoreRadio.supports_command(
                CoreRadio,
                cmd,  # type: ignore[arg-type]
            ), f"{cmd} should be supported"

    def test_unknown_commands_return_false(self):
        unknown = [
            "do_magic",
            "fly_to_moon",
            "get_coffee",
            "set_hyperdrive",
            "",
            "GET_FREQ",
        ]
        for cmd in unknown:
            assert not CoreRadio.supports_command(
                CoreRadio,
                cmd,  # type: ignore[arg-type]
            ), f"{cmd!r} should NOT be supported"

    def test_known_commands_match_public_async_methods(self):
        """Every entry in _KNOWN_COMMANDS must correspond to an actual method."""
        for cmd in CoreRadio._KNOWN_COMMANDS:
            assert hasattr(CoreRadio, cmd), (
                f"_KNOWN_COMMANDS lists {cmd!r} but no such method exists"
            )


# ---------------------------------------------------------------------------
# YaesuCatRadio
# ---------------------------------------------------------------------------


@pytest.fixture()
def ftx1_config():
    return load_rig(_RIGS_DIR / "ftx1.toml")


@pytest.fixture()
def yaesu_radio(ftx1_config):
    return YaesuCatRadio("/dev/null", profile=ftx1_config)


class TestYaesuSupportsCommand:
    """YaesuCatRadio.supports_command delegates to _has_command."""

    def test_defined_commands_return_true(self, yaesu_radio):
        for cmd in (
            "get_freq",
            "set_freq",
            "get_mode",
            "set_mode",
            "set_ptt",
            "get_s_meter",
            "get_af_level",
            "set_af_level",
        ):
            assert yaesu_radio.supports_command(cmd), (
                f"{cmd} should be supported on FTX-1"
            )

    def test_undefined_commands_return_false(self, yaesu_radio):
        for cmd in ("do_magic", "fly_to_moon", "get_coffee", ""):
            assert not yaesu_radio.supports_command(cmd), (
                f"{cmd!r} should NOT be supported on FTX-1"
            )

    def test_matches_has_command(self, yaesu_radio, ftx1_config):
        """supports_command must agree with _has_command for every TOML key."""
        for name in ftx1_config.commands:
            assert yaesu_radio.supports_command(name) == yaesu_radio._has_command(name)


# ---------------------------------------------------------------------------
# Serial Icom backends (all inherit CoreRadio)
# ---------------------------------------------------------------------------


class TestSerialBackendsSupportsCommand:
    """Serial backends inherit supports_command from CoreRadio."""

    def test_ic7300_serial(self):
        from icom_lan.backends.ic7300.serial import Ic7300SerialRadio

        assert hasattr(Ic7300SerialRadio, "supports_command")
        assert Ic7300SerialRadio.supports_command is CoreRadio.supports_command

    def test_ic705_serial(self):
        from icom_lan.backends.ic705.serial import Ic705SerialRadio

        assert hasattr(Ic705SerialRadio, "supports_command")
        assert Ic705SerialRadio.supports_command is CoreRadio.supports_command

    def test_ic9700_serial(self):
        from icom_lan.backends.ic9700.serial import Ic9700SerialRadio

        assert hasattr(Ic9700SerialRadio, "supports_command")
        assert Ic9700SerialRadio.supports_command is CoreRadio.supports_command

    def test_icom7610_serial(self):
        from icom_lan.backends.icom7610.serial import Icom7610SerialRadio

        assert hasattr(Icom7610SerialRadio, "supports_command")
        assert Icom7610SerialRadio.supports_command is CoreRadio.supports_command
