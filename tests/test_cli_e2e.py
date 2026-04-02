"""End-to-end tests for the CLI audio sub-commands.

These tests invoke the real async CLI handler functions (_cmd_audio_rx,
_cmd_audio_tx, _cmd_audio_loopback, _cmd_audio_caps) with a fully
mocked IcomRadio, verifying file I/O, JSON output, and error handling.
"""

from __future__ import annotations

import json
import wave
from argparse import Namespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from _caps import FULL_ICOM_CAPS
from icom_lan.cli import (
    _cmd_audio_caps,
    _cmd_audio_loopback,
    _cmd_audio_rx,
    _cmd_audio_tx,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _add_audio_capable(radio: MagicMock) -> MagicMock:
    """Make mock satisfy isinstance(..., AudioCapable) in CLI.

    All attrs must be explicitly set; Python 3.12+ runtime_checkable Protocol uses
    inspect.getattr_static which bypasses MagicMock.__getattr__.
    """
    radio.audio_bus = MagicMock()
    radio.start_audio_rx_opus = AsyncMock()
    radio.stop_audio_rx_opus = AsyncMock()
    radio.push_audio_tx_opus = AsyncMock()
    radio.start_audio_tx_opus = AsyncMock()
    radio.stop_audio_tx = AsyncMock()
    return radio


@pytest.fixture
def mock_radio():
    """Fully-mocked Radio (AudioCapable) for CLI handler tests."""
    radio = AsyncMock()
    radio.capabilities = set(FULL_ICOM_CAPS)
    radio.start_audio_rx_pcm = AsyncMock()
    radio.stop_audio_rx_pcm = AsyncMock()
    radio.start_audio_tx_pcm = AsyncMock()
    radio.stop_audio_tx_pcm = AsyncMock()
    radio.push_audio_tx_pcm = AsyncMock()
    radio.get_audio_stats = MagicMock(
        return_value={
            "active": True,
            "state": "receiving",
            "rx_packets_received": 10,
            "rx_packets_delivered": 9,
            "tx_packets_sent": 0,
            "packets_lost": 1,
            "packet_loss_percent": 10.0,
            "jitter_ms": 2.5,
            "jitter_max_ms": 20.0,
            "underrun_count": 0,
            "overrun_count": 0,
            "estimated_latency_ms": 100.0,
            "jitter_buffer_depth_packets": 5,
            "jitter_buffer_pending_packets": 1,
            "duplicates_dropped": 0,
            "stale_packets_dropped": 0,
            "out_of_order_packets": 0,
        }
    )
    _add_audio_capable(radio)
    return radio


def _make_wav(path, *, sample_rate=48000, channels=1, n_samples=960):
    """Create a small valid WAV file for testing."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x10\x00" * n_samples * channels)
    return path


# ---------------------------------------------------------------------------
# audio rx
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestCliAudioRxE2E:
    @pytest.mark.asyncio
    async def test_rx_creates_wav_with_correct_header(
        self,
        mock_radio,
        tmp_path,
        capsys,
    ) -> None:
        """RX should create a valid WAV file with correct sample rate/channels."""
        frame = b"\x01\x02" * 960  # 1920 bytes, one mono 48kHz 20ms frame

        async def _start_rx(cb, **_kw) -> None:
            cb(frame)
            cb(frame)

        mock_radio.start_audio_rx_pcm = AsyncMock(side_effect=_start_rx)
        out_file = tmp_path / "rx_test.wav"

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
        assert data["rx_frames"] == 2

    @pytest.mark.asyncio
    async def test_rx_handles_gaps_as_silence(
        self,
        mock_radio,
        tmp_path,
        capsys,
    ) -> None:
        """Gap (None) frames should be written as silence."""
        frame = b"\xff\x7f" * 960

        async def _start_rx(cb, **_kw) -> None:
            cb(frame)
            cb(None)  # gap → silence
            cb(frame)

        mock_radio.start_audio_rx_pcm = AsyncMock(side_effect=_start_rx)
        out_file = tmp_path / "rx_gaps.wav"

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
        data = json.loads(capsys.readouterr().out)
        assert data["rx_frames"] == 2
        assert data["gap_frames"] == 1
        # Total bytes: 3 frames × 1920 bytes
        assert data["bytes_written"] == 3 * 1920

    @pytest.mark.asyncio
    async def test_rx_stereo(self, mock_radio, tmp_path, capsys) -> None:
        """RX with 2 channels should produce a stereo WAV."""
        stereo_frame = b"\x01\x02" * 1920  # 3840 bytes for stereo 20ms

        async def _start_rx(cb, **_kw) -> None:
            cb(stereo_frame)

        mock_radio.start_audio_rx_pcm = AsyncMock(side_effect=_start_rx)
        out_file = tmp_path / "rx_stereo.wav"

        args = Namespace(
            output_file=str(out_file),
            seconds=0.01,
            sample_rate=48000,
            channels=2,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_rx(mock_radio, args)

        assert rc == 0
        with wave.open(str(out_file), "rb") as wf:
            assert wf.getnchannels() == 2

    @pytest.mark.asyncio
    async def test_rx_text_output(self, mock_radio, tmp_path, capsys) -> None:
        """Text mode should print a human-readable message."""

        async def _start_rx(cb, **_kw) -> None:
            cb(b"\x00" * 1920)

        mock_radio.start_audio_rx_pcm = AsyncMock(side_effect=_start_rx)
        out_file = tmp_path / "rx_text.wav"

        args = Namespace(
            output_file=str(out_file),
            seconds=0.01,
            sample_rate=48000,
            channels=1,
            json=False,
            stats=False,
        )
        rc = await _cmd_audio_rx(mock_radio, args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "Saved RX audio" in out


# ---------------------------------------------------------------------------
# audio tx
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestCliAudioTxE2E:
    @pytest.mark.asyncio
    async def test_tx_sends_frames(self, mock_radio, tmp_path, capsys) -> None:
        """TX should read WAV and push PCM frames to the radio."""
        in_file = _make_wav(tmp_path / "tx.wav", n_samples=960)

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
    async def test_tx_multiple_frames(self, mock_radio, tmp_path, capsys) -> None:
        """A WAV with 3 frames worth of data should push 3 frames."""
        in_file = _make_wav(tmp_path / "tx_multi.wav", n_samples=960 * 3)

        args = Namespace(
            input_file=str(in_file),
            sample_rate=48000,
            channels=1,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_tx(mock_radio, args)

        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["tx_frames"] == 3

    @pytest.mark.asyncio
    async def test_tx_file_not_found(self, mock_radio, tmp_path, capsys) -> None:
        """TX with nonexistent file should return error."""
        args = Namespace(
            input_file=str(tmp_path / "nonexistent.wav"),
            sample_rate=48000,
            channels=1,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_tx(mock_radio, args)

        assert rc == 1
        err = capsys.readouterr().err
        assert "not found" in err

    @pytest.mark.asyncio
    async def test_tx_text_output(self, mock_radio, tmp_path, capsys) -> None:
        """Text mode should print a human-readable message."""
        in_file = _make_wav(tmp_path / "tx_text.wav")

        args = Namespace(
            input_file=str(in_file),
            sample_rate=48000,
            channels=1,
            json=False,
            stats=False,
        )
        rc = await _cmd_audio_tx(mock_radio, args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "Transmitted WAV audio" in out

    @pytest.mark.asyncio
    async def test_tx_sample_rate_mismatch(
        self,
        mock_radio,
        tmp_path,
        capsys,
    ) -> None:
        """TX should fail if WAV sample rate differs from --sample-rate."""
        in_file = _make_wav(tmp_path / "tx_mismatch.wav", sample_rate=8000)

        args = Namespace(
            input_file=str(in_file),
            sample_rate=48000,
            channels=1,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_tx(mock_radio, args)

        assert rc == 1
        err = capsys.readouterr().err
        assert "sample rate" in err.lower()

    @pytest.mark.asyncio
    async def test_tx_channel_mismatch(
        self,
        mock_radio,
        tmp_path,
        capsys,
    ) -> None:
        """TX should fail if WAV channels differ from --channels."""
        in_file = _make_wav(tmp_path / "tx_ch.wav", channels=2)

        args = Namespace(
            input_file=str(in_file),
            sample_rate=48000,
            channels=1,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_tx(mock_radio, args)

        assert rc == 1
        err = capsys.readouterr().err
        assert "channel" in err.lower()


# ---------------------------------------------------------------------------
# audio loopback
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestCliAudioLoopbackE2E:
    @pytest.mark.asyncio
    async def test_loopback_runs_and_exits(self, mock_radio, capsys) -> None:
        """Loopback should start RX+TX, feed frames, and exit cleanly."""
        frame = b"\x03\x04" * 960

        async def _start_rx(cb, **_kw) -> None:
            cb(frame)
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

        data = json.loads(capsys.readouterr().out)
        assert data["command"] == "audio-loopback"
        assert data["tx_frames"] >= 1

    @pytest.mark.asyncio
    async def test_loopback_text_output(self, mock_radio, capsys) -> None:
        """Text mode should print a human-readable summary."""

        async def _start_rx(cb, **_kw) -> None:
            cb(b"\x00" * 1920)

        mock_radio.start_audio_rx_pcm = AsyncMock(side_effect=_start_rx)

        args = Namespace(
            seconds=0.05,
            sample_rate=48000,
            channels=1,
            json=False,
            stats=False,
        )
        rc = await _cmd_audio_loopback(mock_radio, args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "loopback" in out.lower() or "Loopback" in out


# ---------------------------------------------------------------------------
# audio caps
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestCliAudioCapsE2E:
    @pytest.mark.asyncio
    async def test_caps_json_format(self, capsys) -> None:
        """JSON output should include codec list and defaults."""
        args = Namespace(json=True)
        rc = await _cmd_audio_caps(args)

        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert "supported_codecs" in data
        assert data["default_sample_rate_hz"] == 48000
        assert data["default_channels"] == 1

    @pytest.mark.asyncio
    async def test_caps_text_format(self, capsys) -> None:
        """Text output should include recognizable labels."""
        args = Namespace(json=False)
        rc = await _cmd_audio_caps(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "Supported codecs:" in out
        assert "48000" in out

    @pytest.mark.asyncio
    async def test_caps_with_stats_json(self, capsys) -> None:
        """Caps with --stats should include runtime_stats in JSON."""
        runtime_stats = {
            "active": True,
            "state": "receiving",
            "rx_packets_received": 50,
            "rx_packets_delivered": 48,
            "tx_packets_sent": 0,
            "packets_lost": 2,
            "packet_loss_percent": 4.0,
            "jitter_ms": 5.0,
            "jitter_max_ms": 25.0,
            "underrun_count": 0,
            "overrun_count": 0,
            "estimated_latency_ms": 100.0,
            "jitter_buffer_depth_packets": 5,
            "jitter_buffer_pending_packets": 3,
            "duplicates_dropped": 0,
            "stale_packets_dropped": 0,
            "out_of_order_packets": 1,
        }
        args = Namespace(json=True, stats=True)
        rc = await _cmd_audio_caps(args, runtime_stats=runtime_stats)

        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert "runtime_stats" in data
        assert data["runtime_stats"]["rx_packets_received"] == 50
        assert data["runtime_stats"]["packet_loss_percent"] == 4.0

    @pytest.mark.asyncio
    async def test_caps_with_stats_text(self, capsys) -> None:
        """Caps with --stats in text mode should show stats section."""
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
        args = Namespace(json=False, stats=True)
        rc = await _cmd_audio_caps(args, runtime_stats=runtime_stats)

        assert rc == 0
        out = capsys.readouterr().out
        assert "Runtime stats:" in out


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestCliAudioErrorCasesE2E:
    @pytest.mark.asyncio
    async def test_rx_invalid_sample_rate(
        self,
        mock_radio,
        tmp_path,
        capsys,
    ) -> None:
        """RX with unsupported sample rate should fail."""
        args = Namespace(
            output_file=str(tmp_path / "bad.wav"),
            seconds=1.0,
            sample_rate=44100,
            channels=1,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_rx(mock_radio, args)
        assert rc == 1
        assert "sample" in capsys.readouterr().err.lower()

    @pytest.mark.asyncio
    async def test_rx_invalid_channels(
        self,
        mock_radio,
        tmp_path,
        capsys,
    ) -> None:
        """RX with invalid channel count should fail."""
        args = Namespace(
            output_file=str(tmp_path / "bad.wav"),
            seconds=1.0,
            sample_rate=48000,
            channels=5,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_rx(mock_radio, args)
        assert rc == 1
        assert "channel" in capsys.readouterr().err.lower()

    @pytest.mark.asyncio
    async def test_rx_invalid_seconds(
        self,
        mock_radio,
        tmp_path,
        capsys,
    ) -> None:
        """RX with zero/negative seconds should fail."""
        args = Namespace(
            output_file=str(tmp_path / "bad.wav"),
            seconds=0,
            sample_rate=48000,
            channels=1,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_rx(mock_radio, args)
        assert rc == 1
        err = capsys.readouterr().err
        assert "seconds" in err.lower() or "positive" in err.lower()

    @pytest.mark.asyncio
    async def test_loopback_invalid_sample_rate(
        self,
        mock_radio,
        capsys,
    ) -> None:
        """Loopback with unsupported sample rate should fail."""
        args = Namespace(
            seconds=1.0,
            sample_rate=44100,
            channels=1,
            json=True,
            stats=False,
        )
        rc = await _cmd_audio_loopback(mock_radio, args)
        assert rc == 1
        assert "sample" in capsys.readouterr().err.lower()
