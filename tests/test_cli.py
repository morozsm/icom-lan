"""Tests for CLI module — parser, frequency parsing, main entry."""

import argparse
from unittest.mock import patch

import pytest

from icom_lan.cli import _build_parser, _parse_frequency, main


class TestParseFrequency:
    def test_hz(self):
        assert _parse_frequency("14074000") == 14_074_000

    def test_khz(self):
        assert _parse_frequency("14074k") == 14_074_000

    def test_khz_suffix(self):
        assert _parse_frequency("14074khz") == 14_074_000

    def test_mhz(self):
        assert _parse_frequency("14.074m") == 14_074_000

    def test_mhz_suffix(self):
        assert _parse_frequency("14.074mhz") == 14_074_000

    def test_float_hz(self):
        assert _parse_frequency("7074000.0") == 7_074_000

    def test_whitespace(self):
        assert _parse_frequency("  14074000  ") == 14_074_000


class TestBuildParser:
    def test_parser_created(self):
        p = _build_parser()
        assert isinstance(p, argparse.ArgumentParser)

    def test_status_command(self):
        p = _build_parser()
        args = p.parse_args(["status"])
        assert args.command == "status"

    def test_freq_get(self):
        p = _build_parser()
        args = p.parse_args(["freq"])
        assert args.command == "freq"
        assert args.value is None

    def test_freq_set(self):
        p = _build_parser()
        args = p.parse_args(["freq", "14074000"])
        assert args.command == "freq"
        assert args.value == "14074000"

    def test_mode_get(self):
        p = _build_parser()
        args = p.parse_args(["mode"])
        assert args.command == "mode"
        assert args.value is None

    def test_mode_set(self):
        p = _build_parser()
        args = p.parse_args(["mode", "USB"])
        assert args.command == "mode"
        assert args.value == "USB"

    def test_power_get(self):
        p = _build_parser()
        args = p.parse_args(["power"])
        assert args.command == "power"
        assert args.value is None

    def test_power_set(self):
        p = _build_parser()
        args = p.parse_args(["power", "100"])
        assert args.command == "power"
        assert args.value == 100

    def test_meter(self):
        p = _build_parser()
        args = p.parse_args(["meter"])
        assert args.command == "meter"

    def test_ptt_on(self):
        p = _build_parser()
        args = p.parse_args(["ptt", "on"])
        assert args.command == "ptt"
        assert args.state == "on"

    def test_ptt_off(self):
        p = _build_parser()
        args = p.parse_args(["ptt", "off"])
        assert args.state == "off"

    def test_cw(self):
        p = _build_parser()
        args = p.parse_args(["cw", "CQ CQ DE KN4KYD"])
        assert args.command == "cw"
        assert args.text == "CQ CQ DE KN4KYD"

    def test_power_on(self):
        p = _build_parser()
        args = p.parse_args(["power-on"])
        assert args.command == "power-on"

    def test_power_off(self):
        p = _build_parser()
        args = p.parse_args(["power-off"])
        assert args.command == "power-off"

    def test_discover(self):
        p = _build_parser()
        args = p.parse_args(["discover"])
        assert args.command == "discover"

    def test_json_flag(self):
        p = _build_parser()
        args = p.parse_args(["status", "--json"])
        assert args.json is True

    def test_host_override(self):
        p = _build_parser()
        args = p.parse_args(["--host", "10.0.0.1", "status"])
        assert args.host == "10.0.0.1"

    def test_timeout_override(self):
        p = _build_parser()
        args = p.parse_args(["--timeout", "10", "status"])
        assert args.timeout == 10.0

    def test_no_command_prints_help(self):
        p = _build_parser()
        args = p.parse_args([])
        assert args.command is None


class TestMainEntryPoint:
    def test_no_args_prints_help(self):
        with patch("sys.argv", ["icom-lan"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
