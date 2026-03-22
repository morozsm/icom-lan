"""Tests for --model and --radio-addr CLI flags (#260)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from icom_lan.cli import _build_backend_config, _build_parser


@pytest.fixture()
def parser() -> argparse.ArgumentParser:
    return _build_parser()


def _parse(parser: argparse.ArgumentParser, args: list[str]) -> argparse.Namespace:
    return parser.parse_args(args)


RIGS_DIR = Path(__file__).resolve().parents[1] / "rigs"


class TestModelResolution:
    """--model resolves radio_addr from rig TOML profiles."""

    def test_model_ic7300_resolves_radio_addr(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(parser, ["--model", "IC-7300", "status"])
        cfg = _build_backend_config(ns)
        assert cfg.radio_addr == 0x94
        assert cfg.model == "IC-7300"

    def test_model_ic7610_resolves_radio_addr(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(parser, ["--model", "IC-7610", "status"])
        cfg = _build_backend_config(ns)
        assert cfg.radio_addr == 0x98
        assert cfg.model == "IC-7610"

    def test_model_case_insensitive(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(parser, ["--model", "ic-7300", "status"])
        cfg = _build_backend_config(ns)
        assert cfg.radio_addr == 0x94
        assert cfg.model == "IC-7300"

    def test_model_unknown_raises(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(parser, ["--model", "IC-FAKE", "status"])
        with pytest.raises(ValueError, match="Unknown model 'IC-FAKE'"):
            _build_backend_config(ns)

    def test_model_unknown_lists_available(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(parser, ["--model", "IC-FAKE", "status"])
        with pytest.raises(ValueError, match="IC-7300"):
            _build_backend_config(ns)


class TestRadioAddrOverride:
    """--radio-addr overrides profile civ_addr."""

    def test_radio_addr_standalone(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(parser, ["--radio-addr", "0xA0", "status"])
        cfg = _build_backend_config(ns)
        assert cfg.radio_addr == 0xA0

    def test_radio_addr_overrides_model(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(parser, ["--model", "IC-7300", "--radio-addr", "0xA0", "status"])
        cfg = _build_backend_config(ns)
        assert cfg.radio_addr == 0xA0
        assert cfg.model == "IC-7300"

    def test_radio_addr_decimal(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(parser, ["--radio-addr", "148", "status"])
        cfg = _build_backend_config(ns)
        assert cfg.radio_addr == 148


class TestDefaults:
    """No --model, no --radio-addr → backward compatible defaults."""

    def test_no_flags_radio_addr_none(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(parser, ["status"])
        cfg = _build_backend_config(ns)
        assert cfg.radio_addr is None
        assert cfg.model is None

    def test_no_flags_model_none(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(parser, ["status"])
        cfg = _build_backend_config(ns)
        assert cfg.model is None


class TestSerialBackend:
    """--model and --radio-addr work with serial backend."""

    def test_model_with_serial(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(
            parser,
            ["--backend", "serial", "--serial-port", "/dev/ttyUSB0",
             "--model", "IC-7300", "status"],
        )
        cfg = _build_backend_config(ns)
        assert cfg.radio_addr == 0x94
        assert cfg.model == "IC-7300"
        assert cfg.backend == "serial"

    def test_radio_addr_with_serial(self, parser: argparse.ArgumentParser) -> None:
        ns = _parse(
            parser,
            ["--backend", "serial", "--serial-port", "/dev/ttyUSB0",
             "--radio-addr", "0x94", "status"],
        )
        cfg = _build_backend_config(ns)
        assert cfg.radio_addr == 0x94
