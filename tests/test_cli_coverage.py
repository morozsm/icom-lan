"""Additional coverage tests for icom_lan.cli."""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import struct
import types
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan.backends.config import SerialBackendConfig
from icom_lan.cli import (
    _cmd_att,
    _cmd_audio_loopback,
    _cmd_audio_rx,
    _cmd_audio_tx,
    _cmd_discover,
    _cmd_preamp,
    _cmd_scope,
    _cmd_serve,
    _cmd_tuner,
    _cmd_web,
    _emit_audio_result,
    _run,
    _validate_audio_format_args,
    main,
)
from icom_lan.scope import ScopeFrame


def _run_args(**overrides: object) -> argparse.Namespace:
    base = {
        "host": "127.0.0.1",
        "control_port": 50001,
        "user": "",
        "password": "",
        "timeout": 1.0,
        "json": False,
        "stats": False,
        "command": "status",
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _mock_radio_ctx() -> tuple[MagicMock, AsyncMock]:
    radio_cls = MagicMock()
    radio = AsyncMock()
    radio.__aenter__.return_value = radio
    radio.__aexit__.return_value = None
    radio_cls.return_value = radio
    return radio_cls, radio


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command", "handler_name"),
    [
        ("status", "_cmd_status"),
        ("freq", "_cmd_freq"),
        ("mode", "_cmd_mode"),
        ("power", "_cmd_power"),
        ("meter", "_cmd_meter"),
        ("ptt", "_cmd_ptt"),
        ("cw", "_cmd_cw"),
        ("att", "_cmd_att"),
        ("preamp", "_cmd_preamp"),
        ("web", "_cmd_web"),
        ("scope", "_cmd_scope"),
        ("serve", "_cmd_serve"),
    ],
)
async def test_run_dispatches_non_audio_commands(command: str, handler_name: str) -> None:
    args = _run_args(command=command)
    if command == "ptt":
        args.state = "on"
    if command == "cw":
        args.text = "CQ"
    if command in {"freq", "mode", "power", "att", "preamp"}:
        args.value = None
    if command == "web":
        args.web_host = "127.0.0.1"
        args.web_port = 8080
        args.web_static_dir = None
    if command == "scope":
        args.frames = 1
        args.width = 800
        args.capture_timeout = 1.0
        args.spectrum_only = True
        args.output = "x.png"
        args.theme = "classic"
    if command == "serve":
        args.serve_host = "127.0.0.1"
        args.serve_port = 4532
        args.read_only = False
        args.max_clients = 1
        args.cache_ttl = 0.1
        args.wsjtx_compat = False
        args.log_level = "INFO"
        args.audit_log = None
        args.rate_limit = None

    _, radio = _mock_radio_ctx()
    with (
        patch("icom_lan.cli.create_radio", return_value=radio),
        patch(f"icom_lan.cli.{handler_name}", new_callable=AsyncMock) as handler,
    ):
        handler.return_value = 7
        rc = await _run(args)

    assert rc == 7
    handler.assert_awaited_once_with(radio, args)


@pytest.mark.asyncio
async def test_run_web_uses_serial_backend_factory_config() -> None:
    args = _run_args(
        command="web",
        backend="serial",
        serial_port="/dev/tty.usbmodem-IC7610",
        serial_baud=115200,
        serial_ptt_mode="civ",
        rx_device=None,
        tx_device=None,
        web_host="127.0.0.1",
        web_port=8080,
        web_static_dir=None,
        web_bridge=None,
        web_bridge_tx_device=None,
        web_bridge_rx_only=False,
        web_rigctld=False,
        dx_cluster=None,
        callsign=None,
    )
    _, radio = _mock_radio_ctx()
    with (
        patch("icom_lan.cli.create_radio", return_value=radio) as create_radio,
        patch("icom_lan.cli._cmd_web", new_callable=AsyncMock) as cmd_web,
    ):
        cmd_web.return_value = 0
        rc = await _run(args)

    assert rc == 0
    create_radio.assert_called_once_with(
        SerialBackendConfig(
            device="/dev/tty.usbmodem-IC7610",
            baudrate=115200,
            timeout=1.0,
            rx_device=None,
            tx_device=None,
            ptt_mode="civ",
        )
    )
    cmd_web.assert_awaited_once_with(radio, args)


@pytest.mark.asyncio
async def test_run_serve_uses_serial_backend_factory_config() -> None:
    args = _run_args(
        command="serve",
        backend="serial",
        serial_port="/dev/tty.usbmodem-IC7610",
        serial_baud=115200,
        serial_ptt_mode="civ",
        rx_device="IC-7610 USB Audio RX",
        tx_device="IC-7610 USB Audio TX",
        serve_host="127.0.0.1",
        serve_port=4532,
        read_only=False,
        max_clients=4,
        cache_ttl=0.1,
        wsjtx_compat=False,
        log_level="INFO",
        audit_log=None,
        rate_limit=None,
    )
    _, radio = _mock_radio_ctx()
    with (
        patch("icom_lan.cli.create_radio", return_value=radio) as create_radio,
        patch("icom_lan.cli._cmd_serve", new_callable=AsyncMock) as cmd_serve,
    ):
        cmd_serve.return_value = 0
        rc = await _run(args)

    assert rc == 0
    create_radio.assert_called_once_with(
        SerialBackendConfig(
            device="/dev/tty.usbmodem-IC7610",
            baudrate=115200,
            timeout=1.0,
            rx_device="IC-7610 USB Audio RX",
            tx_device="IC-7610 USB Audio TX",
            ptt_mode="civ",
        )
    )
    cmd_serve.assert_awaited_once_with(radio, args)


@pytest.mark.asyncio
async def test_run_dispatches_power_on_off_and_unknown_paths(capsys: pytest.CaptureFixture[str]) -> None:
    _, radio = _mock_radio_ctx()
    with patch("icom_lan.cli.create_radio", return_value=radio):
        rc_on = await _run(_run_args(command="power-on"))
        rc_off = await _run(_run_args(command="power-off"))
    assert rc_on == 0
    assert rc_off == 0
    radio.power_control.assert_any_await(True)
    radio.power_control.assert_any_await(False)

    bad_audio = _run_args(command="audio", audio_command="invalid")
    with patch("icom_lan.cli.create_radio", return_value=radio):
        rc_bad = await _run(bad_audio)
    assert rc_bad == 1
    assert "unknown audio command" in capsys.readouterr().err.lower()

    with (
        patch("icom_lan.cli.create_radio", return_value=radio),
        patch("icom_lan.cli._cmd_status", new_callable=AsyncMock) as status_cmd,
    ):
        status_cmd.return_value = 9
        rc_fallback = await _run(_run_args(command="something-else"))
    assert rc_fallback == 9
    status_cmd.assert_awaited()


def test_validate_audio_format_negative_values() -> None:
    assert _validate_audio_format_args(0, 1) == "--sample-rate must be > 0."
    assert _validate_audio_format_args(48000, 0) == "--channels must be > 0."


def test_emit_audio_result_text_stats(capsys: pytest.CaptureFixture[str]) -> None:
    args = argparse.Namespace(json=False, stats=True)
    _emit_audio_result(args, message="done", payload={"tx_frames": 3, "bytes": 100})
    out = capsys.readouterr().out
    assert "done" in out
    assert "tx_frames: 3" in out
    assert "bytes: 100" in out


@pytest.mark.asyncio
async def test_cmd_audio_rx_stop_failure_and_write_failure(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    radio = AsyncMock()

    async def start_rx(cb, **_kwargs):
        cb(b"\x01\x02" * 960)

    radio.start_audio_rx_pcm = AsyncMock(side_effect=start_rx)
    radio.stop_audio_rx_pcm = AsyncMock(side_effect=RuntimeError("stop failed"))
    args_ok = argparse.Namespace(
        output_file=str(tmp_path / "rx.wav"),
        seconds=0.001,
        sample_rate=48000,
        channels=1,
        json=False,
        stats=False,
    )
    with patch("icom_lan.cli.logger.debug") as log_debug:
        rc = await _cmd_audio_rx(radio, args_ok)
    assert rc == 0
    assert "Saved RX audio" in capsys.readouterr().out
    assert log_debug.called

    args_bad = argparse.Namespace(
        output_file=str(tmp_path / "bad.wav"),
        seconds=0.001,
        sample_rate=48000,
        channels=1,
        json=False,
        stats=False,
    )
    with patch("icom_lan.cli.wave.open", side_effect=OSError("nope")):
        rc_bad = await _cmd_audio_rx(radio, args_bad)
    assert rc_bad == 1
    assert "failed to write wav file" in capsys.readouterr().err.lower()


@pytest.mark.asyncio
async def test_cmd_audio_tx_error_branches_and_padding(capsys: pytest.CaptureFixture[str]) -> None:
    radio = AsyncMock()
    radio.start_audio_tx_pcm = AsyncMock()
    radio.stop_audio_tx_pcm = AsyncMock()
    radio.push_audio_tx_pcm = AsyncMock()

    bad_fmt = argparse.Namespace(
        input_file="x.wav",
        sample_rate=0,
        channels=1,
        json=False,
        stats=False,
    )
    assert await _cmd_audio_tx(radio, bad_fmt) == 1

    args = argparse.Namespace(
        input_file="x.wav",
        sample_rate=48000,
        channels=1,
        json=False,
        stats=False,
    )
    with patch("icom_lan.cli._load_wav_pcm", side_effect=wave.Error("bad wav")):
        assert await _cmd_audio_tx(radio, args) == 1
    with patch("icom_lan.cli._load_wav_pcm", side_effect=RuntimeError("boom")):
        assert await _cmd_audio_tx(radio, args) == 1
    with patch("icom_lan.cli._load_wav_pcm", return_value=(48000, 1, 1, b"\x00")):
        assert await _cmd_audio_tx(radio, args) == 1
    with patch("icom_lan.cli._load_wav_pcm", return_value=(48000, 1, 2, b"")):
        assert await _cmd_audio_tx(radio, args) == 1

    short_pcm = b"\x01\x02" * 100
    with (
        patch("icom_lan.cli._load_wav_pcm", return_value=(48000, 1, 2, short_pcm)),
        patch("icom_lan.cli.asyncio.sleep", new=AsyncMock()),
    ):
        rc_ok = await _cmd_audio_tx(radio, args)
    assert rc_ok == 0
    sent_frame = radio.push_audio_tx_pcm.await_args.args[0]
    assert len(sent_frame) == 1920  # padded to one full 20ms frame

    radio.stop_audio_tx_pcm = AsyncMock(side_effect=RuntimeError("stop"))
    with (
        patch("icom_lan.cli._load_wav_pcm", return_value=(48000, 1, 2, short_pcm)),
        patch("icom_lan.cli.asyncio.sleep", new=AsyncMock()),
        patch("icom_lan.cli.logger.debug") as log_debug,
    ):
        rc_stop_err = await _cmd_audio_tx(radio, args)
    assert rc_stop_err == 0
    assert log_debug.called
    assert "transmitted wav audio" in capsys.readouterr().out.lower()


@pytest.mark.asyncio
async def test_cmd_audio_loopback_queue_full_and_worker_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    radio = AsyncMock()
    frame = b"\x01\x02" * 960

    async def start_rx(cb, **_kwargs):
        for _ in range(600):
            cb(frame)

    radio.start_audio_rx_pcm = AsyncMock(side_effect=start_rx)
    radio.stop_audio_rx_pcm = AsyncMock()
    radio.start_audio_tx_pcm = AsyncMock()
    radio.stop_audio_tx_pcm = AsyncMock()
    radio.push_audio_tx_pcm = AsyncMock()
    args = argparse.Namespace(
        seconds=0.01,
        sample_rate=48000,
        channels=1,
        json=True,
        stats=False,
    )
    rc = await _cmd_audio_loopback(radio, args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dropped_frames"] > 0

    args_bad = argparse.Namespace(
        seconds=0.0,
        sample_rate=48000,
        channels=1,
        json=False,
        stats=False,
    )
    assert await _cmd_audio_loopback(radio, args_bad) == 1

    async def start_rx_one(cb, **_kwargs):
        cb(frame)

    radio.start_audio_rx_pcm = AsyncMock(side_effect=start_rx_one)
    radio.push_audio_tx_pcm = AsyncMock(side_effect=RuntimeError("tx failed"))
    radio.stop_audio_rx_pcm = AsyncMock(side_effect=RuntimeError("rx stop failed"))
    radio.stop_audio_tx_pcm = AsyncMock(side_effect=RuntimeError("tx stop failed"))
    with patch("icom_lan.cli.logger.debug") as log_debug:
        with pytest.raises(RuntimeError, match="tx failed"):
            await _cmd_audio_loopback(radio, args)
    assert log_debug.call_count >= 2


@pytest.mark.asyncio
async def test_cmd_att_and_preamp_all_paths(capsys: pytest.CaptureFixture[str]) -> None:
    radio = AsyncMock()
    radio.get_attenuator_level = AsyncMock(return_value=0)
    radio.get_preamp = AsyncMock(return_value=2)

    assert await _cmd_att(radio, argparse.Namespace(value="on", json=False)) == 0
    assert await _cmd_att(radio, argparse.Namespace(value="off", json=False)) == 0
    assert await _cmd_att(radio, argparse.Namespace(value="12", json=False)) == 0
    assert await _cmd_att(radio, argparse.Namespace(value=None, json=False)) == 0

    radio.get_attenuator_level = AsyncMock(return_value=6)
    assert await _cmd_att(radio, argparse.Namespace(value=None, json=True)) == 0

    assert await _cmd_preamp(radio, argparse.Namespace(value="off", json=False)) == 0
    assert await _cmd_preamp(radio, argparse.Namespace(value="1", json=False)) == 0
    assert await _cmd_preamp(radio, argparse.Namespace(value=None, json=False)) == 0
    assert await _cmd_preamp(radio, argparse.Namespace(value=None, json=True)) == 0
    output = capsys.readouterr().out
    assert "Attenuator" in output
    assert "Preamp" in output


@pytest.mark.asyncio
async def test_cmd_scope_json_image_and_error_paths(monkeypatch, capsys: pytest.CaptureFixture[str]) -> None:
    radio = AsyncMock()
    frame = ScopeFrame(0, 1, 14_000_000, 14_350_000, b"\x01\x02", False)
    radio.capture_scope_frame = AsyncMock(return_value=frame)
    radio.capture_scope_frames = AsyncMock(return_value=[frame, frame])
    radio.disable_scope = AsyncMock()

    json_spectrum = argparse.Namespace(
        frames=1,
        width=800,
        capture_timeout=None,
        json=True,
        spectrum_only=True,
        output="scope.png",
        theme="classic",
    )
    assert await _cmd_scope(radio, json_spectrum) == 0
    assert "start_freq_hz" in capsys.readouterr().out

    mod = types.ModuleType("icom_lan.scope_render")
    img = MagicMock()
    mod.render_spectrum = MagicMock(return_value=img)
    mod.render_scope_image = MagicMock()
    monkeypatch.setitem(__import__("sys").modules, "icom_lan.scope_render", mod)
    image_spectrum = argparse.Namespace(
        frames=1,
        width=800,
        capture_timeout=0.5,
        json=False,
        spectrum_only=True,
        output="out.png",
        theme="classic",
    )
    assert await _cmd_scope(radio, image_spectrum) == 0
    img.save.assert_called_once_with("out.png", "PNG")

    json_waterfall = argparse.Namespace(
        frames=2,
        width=800,
        capture_timeout=0.5,
        json=True,
        spectrum_only=False,
        output="out.png",
        theme="classic",
    )
    assert await _cmd_scope(radio, json_waterfall) == 0
    waterfall_out = capsys.readouterr().out.strip().splitlines()[-1]
    assert waterfall_out.startswith("[")

    image_waterfall = argparse.Namespace(
        frames=2,
        width=800,
        capture_timeout=0.5,
        json=False,
        spectrum_only=False,
        output="wf.png",
        theme="grayscale",
    )
    assert await _cmd_scope(radio, image_waterfall) == 0
    mod.render_scope_image.assert_called_once()

    bad = argparse.Namespace(
        frames=1,
        width=800,
        capture_timeout=0.5,
        json=True,
        spectrum_only=True,
        output="x.png",
        theme="classic",
    )
    radio.capture_scope_frame = AsyncMock(side_effect=RuntimeError("capture failed"))
    radio.disable_scope = AsyncMock(side_effect=RuntimeError("disable failed"))
    with patch("icom_lan.cli.logger.debug") as log_debug:
        assert await _cmd_scope(radio, bad) == 1
    assert log_debug.called


@pytest.mark.asyncio
async def test_cmd_scope_validation_and_import_error(monkeypatch, capsys: pytest.CaptureFixture[str]) -> None:
    radio = AsyncMock()
    radio.disable_scope = AsyncMock()

    assert await _cmd_scope(
        radio,
        argparse.Namespace(
            frames=0, width=800, capture_timeout=None, json=True,
            spectrum_only=True, output="x.png", theme="classic",
        ),
    ) == 1
    assert await _cmd_scope(
        radio,
        argparse.Namespace(
            frames=1, width=10, capture_timeout=None, json=True,
            spectrum_only=True, output="x.png", theme="classic",
        ),
    ) == 1
    assert await _cmd_scope(
        radio,
        argparse.Namespace(
            frames=1, width=800, capture_timeout=0, json=True,
            spectrum_only=True, output="x.png", theme="classic",
        ),
    ) == 1

    real_import = __import__

    def bad_import(name, *args, **kwargs):
        if name.endswith("scope_render"):
            raise ImportError("missing pillow")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", bad_import)
    rc = await _cmd_scope(
        radio,
        argparse.Namespace(
            frames=1, width=800, capture_timeout=0.5, json=False,
            spectrum_only=True, output="x.png", theme="classic",
        ),
    )
    assert rc == 1
    assert "missing pillow" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_cmd_serve_and_cmd_web_paths(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    radio = AsyncMock()

    class FakeRigctldServer:
        def __init__(self, _radio, _cfg):
            self.radio = _radio
            self.cfg = _cfg

        async def serve_forever(self):
            raise asyncio.CancelledError

    audit_logger = MagicMock()
    icom_logger = MagicMock()
    with (
        patch("icom_lan.rigctld.server.RigctldServer", FakeRigctldServer),
        patch("logging.FileHandler", return_value=MagicMock()),
        patch("logging.getLogger", side_effect=[icom_logger, audit_logger]),
    ):
        args = argparse.Namespace(
            serve_host="127.0.0.1",
            serve_port=5555,
            read_only=True,
            max_clients=5,
            cache_ttl=0.2,
            wsjtx_compat=True,
            log_level="DEBUG",
            audit_log=str(tmp_path / "audit.jsonl"),
            rate_limit=10.0,
        )
        assert await _cmd_serve(radio, args) == 0
    assert audit_logger.addHandler.called
    assert "Listening on 127.0.0.1:5555" in capsys.readouterr().out

    class FakeWebServer:
        def __init__(self, _radio, cfg):
            self.radio = _radio
            self.cfg = cfg

        async def serve_forever(self):
            raise asyncio.CancelledError

    with patch("icom_lan.web.server.WebServer", FakeWebServer):
        args = argparse.Namespace(web_host="127.0.0.1", web_port=9090, web_static_dir=None)
        assert await _cmd_web(radio, args) == 0
        args2 = argparse.Namespace(
            web_host="127.0.0.1",
            web_port=9091,
            web_static_dir=str(tmp_path),
        )
        assert await _cmd_web(radio, args2) == 0


@pytest.mark.asyncio
async def test_cmd_discover_found_and_not_found(capsys: pytest.CaptureFixture[str]) -> None:
    class FakeLoop:
        def __init__(self):
            self.t = 0.0

        def time(self):
            self.t += 0.7
            return self.t

    class FakeSocket:
        def __init__(self, responses):
            self.responses = list(responses)
            self.sent = []
            self.closed = False

        def setsockopt(self, *_args):
            return None

        def settimeout(self, *_args):
            return None

        def sendto(self, data, addr):
            self.sent.append((data, addr))

        def recvfrom(self, _n):
            if self.responses:
                result = self.responses.pop(0)
                if isinstance(result, Exception):
                    raise result
                return result
            raise socket.timeout

        def close(self):
            self.closed = True

    pkt = bytearray(0x10)
    struct.pack_into("<H", pkt, 4, 0x04)
    struct.pack_into("<I", pkt, 8, 0x1234ABCD)
    found_sock = FakeSocket([(bytes(pkt), ("192.168.1.9", 50001)), socket.timeout()])
    with (
        patch("asyncio.get_event_loop", return_value=FakeLoop()),
        patch("socket.socket", return_value=found_sock),
    ):
        rc_found = await _cmd_discover(None, None)
    assert rc_found == 0
    out = capsys.readouterr().out
    assert "Found: 192.168.1.9:50001" in out
    assert "1 radio(s) found" in out

    none_sock = FakeSocket([socket.timeout(), socket.timeout()])
    with (
        patch("asyncio.get_event_loop", return_value=FakeLoop()),
        patch("socket.socket", return_value=none_sock),
    ):
        rc_none = await _cmd_discover(None, None)
    assert rc_none == 0
    assert "No radios found." in capsys.readouterr().out


def test_main_branches(monkeypatch, capsys: pytest.CaptureFixture[str]) -> None:
    class DummyParser:
        def __init__(self, args):
            self._args = args
            self.help_called = False

        def parse_args(self):
            return self._args

        def print_help(self):
            self.help_called = True

    def fake_run(coro):
        coro.close()
        return 3

    parser_help = DummyParser(SimpleNamespace(command=None))
    with (
        patch("icom_lan.cli._build_parser", return_value=parser_help),
        patch("icom_lan.cli.logging.basicConfig") as basic_cfg,
        patch("icom_lan.cli.sys.exit", side_effect=SystemExit) as sys_exit,
    ):
        monkeypatch.setenv("ICOM_DEBUG", "1")
        with pytest.raises(SystemExit):
            main()
    assert parser_help.help_called
    assert basic_cfg.call_args.kwargs["level"] == __import__("logging").DEBUG
    sys_exit.assert_called_once_with(0)

    parser_discover = DummyParser(SimpleNamespace(command="discover"))
    with (
        patch("icom_lan.cli._build_parser", return_value=parser_discover),
        patch("icom_lan.cli.asyncio.run", side_effect=fake_run),
        patch("icom_lan.cli.sys.exit", side_effect=SystemExit) as sys_exit,
    ):
        with pytest.raises(SystemExit):
            main()
    sys_exit.assert_called_once_with(3)

    parser_proxy = DummyParser(
        SimpleNamespace(command="proxy", radio="1.2.3.4", listen="0.0.0.0", port=50001),
    )
    with (
        patch("icom_lan.cli._build_parser", return_value=parser_proxy),
        patch("icom_lan.proxy.run_proxy", new_callable=AsyncMock),
        patch("icom_lan.cli.asyncio.run", side_effect=fake_run),
        patch("icom_lan.cli.sys.exit", side_effect=SystemExit) as sys_exit,
    ):
        with pytest.raises(SystemExit):
            main()
    sys_exit.assert_called_once_with(0)

    def fake_interrupt(coro):
        coro.close()
        raise KeyboardInterrupt

    parser_run = DummyParser(SimpleNamespace(command="status"))
    with (
        patch("icom_lan.cli._build_parser", return_value=parser_run),
        patch("icom_lan.cli.asyncio.run", side_effect=fake_interrupt),
        patch("icom_lan.cli.sys.exit", side_effect=SystemExit) as sys_exit,
    ):
        with pytest.raises(SystemExit):
            main()
    sys_exit.assert_called_once_with(130)
    assert "Interrupted, shutting down..." in capsys.readouterr().err


@pytest.mark.asyncio
async def test_cmd_tuner_get(capsys: pytest.CaptureFixture[str]) -> None:
    radio = AsyncMock()
    radio.get_tuner_status = AsyncMock(return_value=1)
    assert await _cmd_tuner(radio, argparse.Namespace(action=None, json=False)) == 0
    assert "ON" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_cmd_tuner_set_on_off_tune(capsys: pytest.CaptureFixture[str]) -> None:
    radio = AsyncMock()
    radio.set_tuner_status = AsyncMock()

    assert await _cmd_tuner(radio, argparse.Namespace(action="on", json=False)) == 0
    assert await _cmd_tuner(radio, argparse.Namespace(action="off", json=False)) == 0
    assert await _cmd_tuner(radio, argparse.Namespace(action="tune", json=False)) == 0
    out = capsys.readouterr().out
    assert "ON" in out
    assert "OFF" in out
    assert "TUNING" in out


@pytest.mark.asyncio
async def test_cmd_tuner_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    radio = AsyncMock()
    radio.get_tuner_status = AsyncMock(return_value=0)
    radio.set_tuner_status = AsyncMock()

    assert await _cmd_tuner(radio, argparse.Namespace(action=None, json=True)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data == {"tuner_status": 0, "label": "OFF"}

    assert await _cmd_tuner(radio, argparse.Namespace(action="on", json=True)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data == {"tuner_status": 1, "label": "ON"}

    assert await _cmd_tuner(radio, argparse.Namespace(action="tune", json=True)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data == {"tuner_status": 2, "label": "TUNING"}
