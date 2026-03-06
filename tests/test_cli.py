"""Tests for CLI module — parser, frequency parsing, main entry."""

import argparse
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan.cli import _build_backend_config, _build_parser, _parse_frequency, main
from icom_lan.backends.config import LanBackendConfig, SerialBackendConfig


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

    def test_audio_caps(self):
        p = _build_parser()
        args = p.parse_args(["audio", "caps"])
        assert args.command == "audio"
        assert args.audio_command == "caps"

    def test_audio_caps_json(self):
        p = _build_parser()
        args = p.parse_args(["audio", "caps", "--json"])
        assert args.command == "audio"
        assert args.audio_command == "caps"
        assert args.json is True

    def test_audio_caps_stats(self):
        p = _build_parser()
        args = p.parse_args(["audio", "caps", "--stats"])
        assert args.command == "audio"
        assert args.audio_command == "caps"
        assert args.stats is True

    def test_audio_rx(self):
        p = _build_parser()
        args = p.parse_args(["audio", "rx", "--out", "rx.wav", "--seconds", "10"])
        assert args.command == "audio"
        assert args.audio_command == "rx"
        assert args.output_file == "rx.wav"
        assert args.seconds == 10.0

    def test_audio_rx_common_flags(self):
        p = _build_parser()
        args = p.parse_args(
            [
                "audio",
                "rx",
                "--out",
                "rx.wav",
                "--sample-rate",
                "24000",
                "--channels",
                "2",
                "--json",
                "--stats",
            ]
        )
        assert args.sample_rate == 24000
        assert args.channels == 2
        assert args.json is True
        assert args.stats is True

    def test_audio_tx(self):
        p = _build_parser()
        args = p.parse_args(["audio", "tx", "--in", "tx.wav"])
        assert args.command == "audio"
        assert args.audio_command == "tx"
        assert args.input_file == "tx.wav"

    def test_audio_loopback(self):
        p = _build_parser()
        args = p.parse_args(["audio", "loopback", "--seconds", "3"])
        assert args.command == "audio"
        assert args.audio_command == "loopback"
        assert args.seconds == 3.0

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

    def test_control_port_default(self):
        p = _build_parser()
        args = p.parse_args(["status"])
        assert args.control_port == 50001

    def test_control_port_override(self):
        p = _build_parser()
        args = p.parse_args(["--control-port", "50002", "status"])
        assert args.control_port == 50002

    def test_deprecated_port_sets_control_port(self):
        p = _build_parser()
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            args = p.parse_args(["--port", "9999", "status"])
        assert args.control_port == 9999
        assert "deprecated" in mock_stderr.getvalue().lower()

    def test_deprecated_port_prints_warning(self):
        p = _build_parser()
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            p.parse_args(["--port", "9999", "status"])
        assert "--control-port" in mock_stderr.getvalue()

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


class TestServeSubcommand:
    def test_serve_registered(self):
        p = _build_parser()
        args = p.parse_args(["serve"])
        assert args.command == "serve"

    def test_serve_default_host(self):
        p = _build_parser()
        args = p.parse_args(["serve"])
        assert args.serve_host == "0.0.0.0"

    def test_serve_default_port(self):
        p = _build_parser()
        args = p.parse_args(["serve"])
        assert args.serve_port == 4532

    def test_serve_host_override(self):
        p = _build_parser()
        args = p.parse_args(["serve", "--host", "127.0.0.1"])
        assert args.serve_host == "127.0.0.1"

    def test_serve_port_override(self):
        p = _build_parser()
        args = p.parse_args(["serve", "--port", "14532"])
        assert args.serve_port == 14532

    def test_serve_read_only_default(self):
        p = _build_parser()
        args = p.parse_args(["serve"])
        assert args.read_only is False

    def test_serve_read_only_flag(self):
        p = _build_parser()
        args = p.parse_args(["serve", "--read-only"])
        assert args.read_only is True

    def test_serve_max_clients(self):
        p = _build_parser()
        args = p.parse_args(["serve", "--max-clients", "5"])
        assert args.max_clients == 5

    def test_serve_max_clients_default(self):
        p = _build_parser()
        args = p.parse_args(["serve"])
        assert args.max_clients == 10

    def test_serve_cache_ttl(self):
        p = _build_parser()
        args = p.parse_args(["serve", "--cache-ttl", "1.0"])
        assert args.cache_ttl == 1.0

    def test_serve_cache_ttl_default(self):
        p = _build_parser()
        args = p.parse_args(["serve"])
        assert args.cache_ttl == 0.2

    def test_serve_radio_host_unaffected(self):
        """Radio --host is independent of serve --host."""
        p = _build_parser()
        args = p.parse_args(["--host", "192.168.1.200", "serve"])
        assert args.host == "192.168.1.200"
        assert args.serve_host == "0.0.0.0"


class TestMainEntryPoint:
    def test_no_args_prints_help(self):
        with patch("sys.argv", ["icom-lan"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestBackendArgs:
    def test_backend_default_is_lan(self):
        p = _build_parser()
        args = p.parse_args(["status"])
        assert args.backend == "lan"

    def test_backend_lan_explicit(self):
        p = _build_parser()
        args = p.parse_args(["--backend", "lan", "status"])
        assert args.backend == "lan"

    def test_backend_serial(self):
        p = _build_parser()
        args = p.parse_args(["--backend", "serial", "--serial-port", "/dev/tty.test", "status"])
        assert args.backend == "serial"
        assert args.serial_port == "/dev/tty.test"

    def test_serial_port_flag(self):
        p = _build_parser()
        args = p.parse_args(["--serial-port", "/dev/tty.usbmodem1", "status"])
        assert args.serial_port == "/dev/tty.usbmodem1"

    def test_serial_baud_default(self):
        p = _build_parser()
        args = p.parse_args(["status"])
        assert args.serial_baud == 115200

    def test_serial_baud_override(self):
        p = _build_parser()
        args = p.parse_args(["--serial-baud", "57600", "status"])
        assert args.serial_baud == 57600

    def test_serial_ptt_mode_default(self):
        p = _build_parser()
        args = p.parse_args(["status"])
        assert args.serial_ptt_mode == "civ"

    def test_serial_ptt_mode_override(self):
        p = _build_parser()
        args = p.parse_args(
            ["--serial-ptt-mode", "civ", "--backend", "serial", "status"]
        )
        assert args.serial_ptt_mode == "civ"

    def test_rx_device_default_none(self):
        p = _build_parser()
        args = p.parse_args(["status"])
        assert args.rx_device is None

    def test_rx_device_override(self):
        p = _build_parser()
        args = p.parse_args(["--rx-device", "IC-7610 USB Audio", "status"])
        assert args.rx_device == "IC-7610 USB Audio"

    def test_tx_device_default_none(self):
        p = _build_parser()
        args = p.parse_args(["status"])
        assert args.tx_device is None

    def test_tx_device_override(self):
        p = _build_parser()
        args = p.parse_args(["--tx-device", "BlackHole 2ch", "status"])
        assert args.tx_device == "BlackHole 2ch"

    def test_list_audio_devices_flag(self):
        p = _build_parser()
        args = p.parse_args(["--list-audio-devices"])
        assert args.list_audio_devices is True

    def test_list_audio_devices_default_false(self):
        p = _build_parser()
        args = p.parse_args(["status"])
        assert args.list_audio_devices is False

    def test_backend_invalid_rejected(self):
        p = _build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(["--backend", "zigbee", "status"])


class TestBuildBackendConfig:
    def test_lan_default(self):
        p = _build_parser()
        args = p.parse_args(["--host", "192.168.1.1", "status"])
        config = _build_backend_config(args)
        assert isinstance(config, LanBackendConfig)
        assert config.backend == "lan"
        assert config.host == "192.168.1.1"
        assert config.port == 50001

    def test_lan_preserves_user_pass(self):
        p = _build_parser()
        args = p.parse_args(["--host", "10.0.0.1", "--user", "admin", "--pass", "secret", "status"])
        config = _build_backend_config(args)
        assert isinstance(config, LanBackendConfig)
        assert config.username == "admin"
        assert config.password == "secret"

    def test_lan_custom_port(self):
        p = _build_parser()
        args = p.parse_args(["--host", "10.0.0.1", "--control-port", "50010", "status"])
        config = _build_backend_config(args)
        assert isinstance(config, LanBackendConfig)
        assert config.port == 50010

    def test_serial_config_built(self):
        p = _build_parser()
        args = p.parse_args(["--backend", "serial", "--serial-port", "/dev/tty.usb0", "status"])
        config = _build_backend_config(args)
        assert isinstance(config, SerialBackendConfig)
        assert config.backend == "serial"
        assert config.device == "/dev/tty.usb0"
        assert config.baudrate == 115200

    def test_serial_baud_passed(self):
        p = _build_parser()
        args = p.parse_args([
            "--backend", "serial",
            "--serial-port", "/dev/tty.usb0",
            "--serial-baud", "9600",
            "status",
        ])
        config = _build_backend_config(args)
        assert isinstance(config, SerialBackendConfig)
        assert config.baudrate == 9600

    def test_serial_rx_tx_device(self):
        p = _build_parser()
        args = p.parse_args([
            "--backend", "serial",
            "--serial-port", "/dev/tty.usb0",
            "--rx-device", "IC-7610 RX",
            "--tx-device", "IC-7610 TX",
            "status",
        ])
        config = _build_backend_config(args)
        assert isinstance(config, SerialBackendConfig)
        assert config.rx_device == "IC-7610 RX"
        assert config.tx_device == "IC-7610 TX"

    def test_serial_ptt_mode_passed(self):
        p = _build_parser()
        args = p.parse_args([
            "--backend", "serial",
            "--serial-port", "/dev/tty.usb0",
            "--serial-ptt-mode", "civ",
            "status",
        ])
        config = _build_backend_config(args)
        assert isinstance(config, SerialBackendConfig)
        assert config.ptt_mode == "civ"

    def test_serial_missing_port_raises_value_error(self):
        p = _build_parser()
        args = p.parse_args(["--backend", "serial", "status"])
        with pytest.raises(ValueError, match="--serial-port"):
            _build_backend_config(args)

    def test_serial_missing_port_error_mentions_env_var(self):
        p = _build_parser()
        args = p.parse_args(["--backend", "serial", "status"])
        with pytest.raises(ValueError, match="ICOM_SERIAL_DEVICE"):
            _build_backend_config(args)

    def test_serial_missing_port_error_shows_example(self):
        p = _build_parser()
        args = p.parse_args(["--backend", "serial", "status"])
        with pytest.raises(ValueError, match="Example"):
            _build_backend_config(args)


class TestBackendAwareDiscover:
    def test_discover_serial_exits_with_error(self, capsys):
        with patch("sys.argv", ["icom-lan", "--backend", "serial", "discover"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "serial" in captured.err.lower()
        assert "not supported" in captured.err.lower()

    def test_discover_serial_error_mentions_lan(self, capsys):
        with patch("sys.argv", ["icom-lan", "--backend", "serial", "discover"]):
            with pytest.raises(SystemExit):
                main()
        captured = capsys.readouterr()
        assert "lan" in captured.err.lower()


class TestListAudioDevices:
    def test_list_audio_devices_missing_sounddevice(self, capsys):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "sounddevice":
                raise ImportError("No module named 'sounddevice'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with patch("sys.argv", ["icom-lan", "--list-audio-devices"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "sounddevice" in captured.err

    def test_list_audio_devices_plain_output(self, capsys):
        async def fake_list_cmd(args):
            print("2 audio device(s):")
            print("  [0] IC-7610 USB Audio  (in=1, out=1)")
            print("  [1] Built-in Mic  (in=1, out=0)")
            return 0

        with patch("icom_lan.cli._cmd_list_audio_devices", side_effect=fake_list_cmd):
            with patch("sys.argv", ["icom-lan", "--list-audio-devices"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "IC-7610 USB Audio" in captured.out

    def test_list_audio_devices_json_flag_is_parser_reachable(self):
        captured: dict[str, object] = {}

        async def fake_list_cmd(args):
            captured["json"] = getattr(args, "json", False)
            return 0

        with patch("icom_lan.cli._cmd_list_audio_devices", side_effect=fake_list_cmd):
            with patch("sys.argv", ["icom-lan", "--list-audio-devices", "--json"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
        assert exc_info.value.code == 0
        assert captured["json"] is True

    def test_list_audio_devices_json_output(self, capsys):
        import asyncio
        import argparse as _ap
        import json as json_module
        from icom_lan.cli import _cmd_list_audio_devices

        mock_sd = MagicMock()
        mock_sd.query_devices.return_value = [
            {
                "index": 0,
                "name": "IC-7610 USB Audio",
                "max_input_channels": 1,
                "max_output_channels": 1,
                "default_samplerate": 48000,
            },
        ]
        mock_sd.default = MagicMock()
        mock_sd.default.device = [-1, -1]

        test_args = _ap.Namespace(json=True)

        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            result = asyncio.run(_cmd_list_audio_devices(test_args))

        assert result == 0
        captured = capsys.readouterr()
        data = json_module.loads(captured.out.strip())
        assert data[0]["name"] == "IC-7610 USB Audio"
        assert data[0]["index"] == 0
