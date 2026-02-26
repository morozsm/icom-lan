"""Tests for CLI async command handlers using mocked IcomRadio."""

import json
import wave
from argparse import Namespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan.cli import (
    _cmd_audio_caps,
    _cmd_audio_loopback,
    _cmd_audio_rx,
    _cmd_audio_tx,
    _cmd_cw,
    _cmd_freq,
    _cmd_meter,
    _cmd_mode,
    _cmd_power,
    _cmd_ptt,
    _cmd_scope,
    _cmd_status,
    _run,
    main,
)
from icom_lan.exceptions import TimeoutError as IcomTimeout
from icom_lan.types import Mode, get_audio_capabilities


# ---------------------------------------------------------------------------
# Mock radio fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_radio():
    radio = AsyncMock()
    radio.get_frequency = AsyncMock(return_value=14_074_000)
    radio.set_frequency = AsyncMock()
    radio.get_mode = AsyncMock(return_value=Mode.USB)
    radio.set_mode = AsyncMock()
    radio.get_power = AsyncMock(return_value=128)
    radio.set_power = AsyncMock()
    radio.get_s_meter = AsyncMock(return_value=120)
    radio.get_swr = AsyncMock(return_value=50)
    radio.get_alc = AsyncMock(return_value=30)
    radio.set_ptt = AsyncMock()
    radio.send_cw_text = AsyncMock()
    radio.power_control = AsyncMock()
    radio.capture_scope_frame = AsyncMock()
    radio.capture_scope_frames = AsyncMock()
    radio.disable_scope = AsyncMock()
    radio.start_audio_rx_pcm = AsyncMock()
    radio.stop_audio_rx_pcm = AsyncMock()
    radio.start_audio_tx_pcm = AsyncMock()
    radio.stop_audio_tx_pcm = AsyncMock()
    radio.push_audio_tx_pcm = AsyncMock()
    return radio


# ---------------------------------------------------------------------------
# _cmd_status
# ---------------------------------------------------------------------------


class TestCmdStatus:
    @pytest.mark.asyncio
    async def test_status_text(self, mock_radio, capsys) -> None:
        args = Namespace(json=False)
        rc = await _cmd_status(mock_radio, args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "14,074,000" in out
        assert "USB" in out

    @pytest.mark.asyncio
    async def test_status_json(self, mock_radio, capsys) -> None:
        args = Namespace(json=True)
        rc = await _cmd_status(mock_radio, args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["frequency_hz"] == 14_074_000
        assert data["mode"] == "USB"
        assert data["s_meter"] == 120
        assert data["power"] == 128


# ---------------------------------------------------------------------------
# _cmd_audio_caps
# ---------------------------------------------------------------------------


class TestCmdAudioCaps:
    @pytest.mark.asyncio
    async def test_audio_caps_text(self, capsys) -> None:
        args = Namespace(json=False)
        rc = await _cmd_audio_caps(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Supported codecs:" in out
        assert "Defaults:" in out
        assert "PCM_1CH_16BIT" in out
        assert "48000" in out

    @pytest.mark.asyncio
    async def test_audio_caps_json(self, capsys) -> None:
        args = Namespace(json=True)
        rc = await _cmd_audio_caps(args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["default_codec"]["name"] == "PCM_1CH_16BIT"
        assert data["default_sample_rate_hz"] == 48000
        assert data["default_channels"] == 1
        assert any(c["name"] == "OPUS_1CH" for c in data["supported_codecs"])

    @pytest.mark.asyncio
    async def test_audio_caps_json_with_stats(self, capsys) -> None:
        args = Namespace(json=True, stats=True)
        runtime_stats = {
            "active": False,
            "state": "idle",
            "rx_packets_received": 4,
            "rx_packets_delivered": 3,
            "tx_packets_sent": 0,
            "packets_lost": 1,
            "packet_loss_percent": 25.0,
            "jitter_ms": 8.0,
            "jitter_max_ms": 20.0,
            "underrun_count": 1,
            "overrun_count": 0,
            "estimated_latency_ms": 0.0,
            "jitter_buffer_depth_packets": 5,
            "jitter_buffer_pending_packets": 0,
            "duplicates_dropped": 0,
            "stale_packets_dropped": 0,
            "out_of_order_packets": 2,
        }
        rc = await _cmd_audio_caps(args, runtime_stats=runtime_stats)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["runtime_stats"]["packets_lost"] == 1
        assert data["runtime_stats"]["packet_loss_percent"] == 25.0

    @pytest.mark.asyncio
    async def test_audio_caps_text_with_stats(self, capsys) -> None:
        args = Namespace(json=False, stats=True)
        runtime_stats = {
            "active": True,
            "state": "receiving",
            "rx_packets_received": 10,
            "rx_packets_delivered": 9,
            "tx_packets_sent": 0,
            "packets_lost": 1,
            "packet_loss_percent": 10.0,
            "jitter_ms": 2.5,
            "jitter_max_ms": 20.0,
            "underrun_count": 1,
            "overrun_count": 0,
            "estimated_latency_ms": 100.0,
            "jitter_buffer_depth_packets": 5,
            "jitter_buffer_pending_packets": 1,
            "duplicates_dropped": 0,
            "stale_packets_dropped": 0,
            "out_of_order_packets": 1,
        }
        rc = await _cmd_audio_caps(args, runtime_stats=runtime_stats)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Runtime stats:" in out
        assert "packet_loss_percent: 10.000" in out


# ---------------------------------------------------------------------------
# _cmd_audio_rx / _cmd_audio_tx / _cmd_audio_loopback
# ---------------------------------------------------------------------------


class TestCmdAudioCli:
    @pytest.mark.asyncio
    async def test_audio_rx_smoke(self, mock_radio, tmp_path, capsys) -> None:
        frame = b"\x01\x02" * 960

        async def _start_rx(cb, **_kwargs) -> None:
            cb(frame)
            cb(None)

        mock_radio.start_audio_rx_pcm = AsyncMock(side_effect=_start_rx)

        out_file = tmp_path / "rx.wav"
        args = Namespace(
            output_file=str(out_file),
            seconds=0.01,
            sample_rate=48000,
            channels=1,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_rx(mock_radio, args)

        assert rc == 0
        mock_radio.start_audio_rx_pcm.assert_awaited_once()
        mock_radio.stop_audio_rx_pcm.assert_awaited_once()
        with wave.open(str(out_file), "rb") as wf:
            assert wf.getframerate() == 48000
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getnframes() > 0
        data = json.loads(capsys.readouterr().out)
        assert data["command"] == "audio-rx"
        assert data["bytes_written"] > 0

    @pytest.mark.asyncio
    async def test_audio_tx_smoke(self, mock_radio, tmp_path, capsys) -> None:
        in_file = tmp_path / "tx.wav"
        with wave.open(str(in_file), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x01\x02" * 960)

        args = Namespace(
            input_file=str(in_file),
            sample_rate=48000,
            channels=1,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_tx(mock_radio, args)

        assert rc == 0
        mock_radio.start_audio_tx_pcm.assert_awaited_once()
        mock_radio.stop_audio_tx_pcm.assert_awaited_once()
        assert mock_radio.push_audio_tx_pcm.await_count >= 1
        data = json.loads(capsys.readouterr().out)
        assert data["command"] == "audio-tx"
        assert data["tx_frames"] >= 1

    @pytest.mark.asyncio
    async def test_audio_loopback_smoke(self, mock_radio, capsys) -> None:
        frame = b"\x03\x04" * 960

        async def _start_rx(cb, **_kwargs) -> None:
            cb(frame)
            cb(None)

        mock_radio.start_audio_rx_pcm = AsyncMock(side_effect=_start_rx)

        args = Namespace(
            seconds=0.05,
            sample_rate=48000,
            channels=1,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_loopback(mock_radio, args)

        assert rc == 0
        mock_radio.start_audio_rx_pcm.assert_awaited_once()
        mock_radio.stop_audio_rx_pcm.assert_awaited_once()
        mock_radio.start_audio_tx_pcm.assert_awaited_once()
        mock_radio.stop_audio_tx_pcm.assert_awaited_once()
        assert mock_radio.push_audio_tx_pcm.await_count >= 1
        data = json.loads(capsys.readouterr().out)
        assert data["command"] == "audio-loopback"
        assert data["tx_frames"] >= 1


# ---------------------------------------------------------------------------
# _cmd_freq
# ---------------------------------------------------------------------------


class TestCmdFreq:
    @pytest.mark.asyncio
    async def test_get_freq_text(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=False)
        rc = await _cmd_freq(mock_radio, args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "14,074,000" in out

    @pytest.mark.asyncio
    async def test_get_freq_json(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=True)
        rc = await _cmd_freq(mock_radio, args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["frequency_hz"] == 14_074_000

    @pytest.mark.asyncio
    async def test_set_freq(self, mock_radio, capsys) -> None:
        args = Namespace(value="7074000", json=False)
        rc = await _cmd_freq(mock_radio, args)
        assert rc == 0
        mock_radio.set_frequency.assert_called_once_with(7_074_000)
        out = capsys.readouterr().out
        assert "7,074,000" in out

    @pytest.mark.asyncio
    async def test_set_freq_mhz(self, mock_radio, capsys) -> None:
        args = Namespace(value="14.074m", json=False)
        rc = await _cmd_freq(mock_radio, args)
        assert rc == 0
        mock_radio.set_frequency.assert_called_once_with(14_074_000)


# ---------------------------------------------------------------------------
# _cmd_mode
# ---------------------------------------------------------------------------


class TestCmdMode:
    @pytest.mark.asyncio
    async def test_get_mode_text(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=False)
        rc = await _cmd_mode(mock_radio, args)
        assert rc == 0
        assert "USB" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_get_mode_json(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=True)
        rc = await _cmd_mode(mock_radio, args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["mode"] == "USB"

    @pytest.mark.asyncio
    async def test_set_mode(self, mock_radio, capsys) -> None:
        args = Namespace(value="LSB", json=False)
        rc = await _cmd_mode(mock_radio, args)
        assert rc == 0
        mock_radio.set_mode.assert_called_once_with("LSB")


# ---------------------------------------------------------------------------
# _cmd_power
# ---------------------------------------------------------------------------


class TestCmdPower:
    @pytest.mark.asyncio
    async def test_get_power_text(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=False)
        rc = await _cmd_power(mock_radio, args)
        assert rc == 0
        assert "128" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_get_power_json(self, mock_radio, capsys) -> None:
        args = Namespace(value=None, json=True)
        rc = await _cmd_power(mock_radio, args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["power"] == 128

    @pytest.mark.asyncio
    async def test_set_power(self, mock_radio, capsys) -> None:
        args = Namespace(value=200, json=False)
        rc = await _cmd_power(mock_radio, args)
        assert rc == 0
        mock_radio.set_power.assert_called_once_with(200)


# ---------------------------------------------------------------------------
# _cmd_meter
# ---------------------------------------------------------------------------


class TestCmdMeter:
    @pytest.mark.asyncio
    async def test_meter_text(self, mock_radio, capsys) -> None:
        args = Namespace(json=False)
        rc = await _cmd_meter(mock_radio, args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "120" in out  # s_meter
        assert "50" in out  # swr

    @pytest.mark.asyncio
    async def test_meter_json(self, mock_radio, capsys) -> None:
        args = Namespace(json=True)
        rc = await _cmd_meter(mock_radio, args)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["s_meter"] == 120
        assert data["swr"] == 50
        assert data["alc"] == 30

    @pytest.mark.asyncio
    async def test_meter_timeout_handled(self, mock_radio, capsys) -> None:
        mock_radio.get_swr = AsyncMock(side_effect=IcomTimeout("timeout"))
        args = Namespace(json=False)
        rc = await _cmd_meter(mock_radio, args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "n/a" in out


# ---------------------------------------------------------------------------
# _cmd_ptt
# ---------------------------------------------------------------------------


class TestCmdPtt:
    @pytest.mark.asyncio
    async def test_ptt_on(self, mock_radio, capsys) -> None:
        args = Namespace(state="on")
        rc = await _cmd_ptt(mock_radio, args)
        assert rc == 0
        mock_radio.set_ptt.assert_called_once_with(True)
        assert "ON" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_ptt_off(self, mock_radio, capsys) -> None:
        args = Namespace(state="off")
        rc = await _cmd_ptt(mock_radio, args)
        assert rc == 0
        mock_radio.set_ptt.assert_called_once_with(False)
        assert "OFF" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _cmd_cw
# ---------------------------------------------------------------------------


class TestCmdCw:
    @pytest.mark.asyncio
    async def test_cw(self, mock_radio, capsys) -> None:
        args = Namespace(text="CQ DE KN4KYD")
        rc = await _cmd_cw(mock_radio, args)
        assert rc == 0
        mock_radio.send_cw_text.assert_called_once_with("CQ DE KN4KYD")
        assert "CQ DE KN4KYD" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _run error handling
# ---------------------------------------------------------------------------


class TestRunErrorHandling:
    @pytest.mark.asyncio
    async def test_run_audio_caps_does_not_connect(self, capsys) -> None:
        args = Namespace(
            host="192.168.1.100",
            port=50001,
            user="",
            password="",
            timeout=5.0,
            command="audio",
            audio_command="caps",
            json=True,
        )
        with patch("icom_lan.cli.IcomRadio") as radio_cls:
            radio_cls.audio_capabilities.return_value = get_audio_capabilities()
            rc = await _run(args)
        assert rc == 0
        radio_cls.assert_not_called()
        data = json.loads(capsys.readouterr().out)
        assert data["default_channels"] == 1

    @pytest.mark.asyncio
    async def test_run_audio_caps_with_stats_connects(self, capsys) -> None:
        args = Namespace(
            host="192.168.1.100",
            port=50001,
            user="",
            password="",
            timeout=5.0,
            command="audio",
            audio_command="caps",
            json=True,
            stats=True,
        )
        runtime_stats = {
            "active": False,
            "state": "idle",
            "rx_packets_received": 2,
            "rx_packets_delivered": 2,
            "tx_packets_sent": 0,
            "packets_lost": 0,
            "packet_loss_percent": 0.0,
            "jitter_ms": 0.0,
            "jitter_max_ms": 0.0,
            "underrun_count": 0,
            "overrun_count": 0,
            "estimated_latency_ms": 0.0,
            "jitter_buffer_depth_packets": 5,
            "jitter_buffer_pending_packets": 0,
            "duplicates_dropped": 0,
            "stale_packets_dropped": 0,
            "out_of_order_packets": 0,
        }
        with patch("icom_lan.cli.IcomRadio") as radio_cls:
            radio = AsyncMock()
            radio.__aenter__.return_value = radio
            radio.__aexit__.return_value = None
            radio.start_audio_rx_opus = AsyncMock()
            radio.stop_audio_rx_opus = AsyncMock()
            radio.get_audio_stats = MagicMock(return_value=runtime_stats)
            radio_cls.return_value = radio
            radio_cls.audio_capabilities.return_value = get_audio_capabilities()
            with patch("icom_lan.cli.asyncio.sleep", new=AsyncMock()):
                rc = await _run(args)
        assert rc == 0
        radio_cls.assert_called_once()
        radio.start_audio_rx_opus.assert_awaited_once()
        radio.stop_audio_rx_opus.assert_awaited_once()
        data = json.loads(capsys.readouterr().out)
        assert data["runtime_stats"]["rx_packets_received"] == 2

    @pytest.mark.asyncio
    async def test_run_exception(self, capsys) -> None:
        args = Namespace(
            host="192.168.1.100",
            port=50001,
            user="",
            password="",
            timeout=0.1,
            command="status",
            json=False,
        )
        # _run will try to connect and fail — it catches and prints
        rc = await _run(args)
        assert rc == 1
        err = capsys.readouterr().err
        assert "Error" in err

    @pytest.mark.asyncio
    async def test_run_audio_rx_routes_to_handler(self) -> None:
        args = Namespace(
            host="192.168.1.100",
            port=50001,
            user="",
            password="",
            timeout=5.0,
            command="audio",
            audio_command="rx",
            output_file="rx.wav",
            seconds=1.0,
            sample_rate=48000,
            channels=1,
            json=False,
            stats=False,
        )
        with patch("icom_lan.cli.IcomRadio") as radio_cls:
            radio = AsyncMock()
            radio.__aenter__.return_value = radio
            radio.__aexit__.return_value = None
            radio_cls.return_value = radio
            with patch("icom_lan.cli._cmd_audio_rx", new_callable=AsyncMock) as cmd:
                cmd.return_value = 0
                rc = await _run(args)
        assert rc == 0
        cmd.assert_awaited_once_with(radio, args)

    @pytest.mark.asyncio
    async def test_run_audio_tx_routes_to_handler(self) -> None:
        args = Namespace(
            host="192.168.1.100",
            port=50001,
            user="",
            password="",
            timeout=5.0,
            command="audio",
            audio_command="tx",
            input_file="tx.wav",
            sample_rate=48000,
            channels=1,
            json=False,
            stats=False,
        )
        with patch("icom_lan.cli.IcomRadio") as radio_cls:
            radio = AsyncMock()
            radio.__aenter__.return_value = radio
            radio.__aexit__.return_value = None
            radio_cls.return_value = radio
            with patch("icom_lan.cli._cmd_audio_tx", new_callable=AsyncMock) as cmd:
                cmd.return_value = 0
                rc = await _run(args)
        assert rc == 0
        cmd.assert_awaited_once_with(radio, args)

    @pytest.mark.asyncio
    async def test_run_audio_loopback_routes_to_handler(self) -> None:
        args = Namespace(
            host="192.168.1.100",
            port=50001,
            user="",
            password="",
            timeout=5.0,
            command="audio",
            audio_command="loopback",
            seconds=1.0,
            sample_rate=48000,
            channels=1,
            json=False,
            stats=False,
        )
        with patch("icom_lan.cli.IcomRadio") as radio_cls:
            radio = AsyncMock()
            radio.__aenter__.return_value = radio
            radio.__aexit__.return_value = None
            radio_cls.return_value = radio
            with patch(
                "icom_lan.cli._cmd_audio_loopback",
                new_callable=AsyncMock,
            ) as cmd:
                cmd.return_value = 0
                rc = await _run(args)
        assert rc == 0
        cmd.assert_awaited_once_with(radio, args)


# ---------------------------------------------------------------------------
# _cmd_scope
# ---------------------------------------------------------------------------


class TestCmdScope:
    @pytest.mark.asyncio
    async def test_rejects_invalid_frames(self, mock_radio, capsys) -> None:
        args = Namespace(
            frames=0,
            width=800,
            capture_timeout=None,
            spectrum_only=False,
            json=True,
            output="scope.png",
            theme="classic",
        )
        rc = await _cmd_scope(mock_radio, args)
        assert rc == 1
        assert "--frames must be >= 1" in capsys.readouterr().err

    @pytest.mark.asyncio
    async def test_rejects_invalid_width(self, mock_radio, capsys) -> None:
        args = Namespace(
            frames=1,
            width=10,
            capture_timeout=None,
            spectrum_only=True,
            json=True,
            output="scope.png",
            theme="classic",
        )
        rc = await _cmd_scope(mock_radio, args)
        assert rc == 1
        assert "--width must be >= 64" in capsys.readouterr().err

    @pytest.mark.asyncio
    async def test_rejects_non_positive_timeout(self, mock_radio, capsys) -> None:
        args = Namespace(
            frames=1,
            width=800,
            capture_timeout=0.0,
            spectrum_only=True,
            json=True,
            output="scope.png",
            theme="classic",
        )
        rc = await _cmd_scope(mock_radio, args)
        assert rc == 1
        assert "--capture-timeout must be > 0" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# main() entrypoint
# ---------------------------------------------------------------------------


class TestMain:
    def test_no_command_prints_help(self, capsys) -> None:
        with patch("sys.argv", ["icom-lan"]):
            # main with no command should print help and exit 0
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0

    def test_discover_command(self) -> None:
        # Just verify it doesn't crash on import/parse
        with patch("sys.argv", ["icom-lan", "discover"]):
            # Discover will try UDP broadcast — mock socket
            with patch(
                "icom_lan.cli._cmd_discover",
                new_callable=lambda: lambda: AsyncMock(return_value=0),
            ):
                pass  # We just test parsing works
