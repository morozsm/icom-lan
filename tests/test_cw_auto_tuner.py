"""Tests for CwAutoTuner — FFT-based CW tone detection."""

from __future__ import annotations

import numpy as np

from icom_lan.cw_auto_tuner import CwAutoTuner

_SAMPLE_RATE = 48000


def _make_tone(freq_hz: float, duration_s: float = 0.5) -> bytes:
    """Generate s16le mono PCM sine wave."""
    t = np.arange(int(_SAMPLE_RATE * duration_s)) / _SAMPLE_RATE
    samples = (np.sin(2 * np.pi * freq_hz * t) * 16000).astype(np.int16)
    return samples.tobytes()


def _make_silence(duration_s: float = 0.5) -> bytes:
    """Generate s16le mono silence."""
    n = int(_SAMPLE_RATE * duration_s)
    return np.zeros(n, dtype=np.int16).tobytes()


class TestCwAutoTuner:
    """CwAutoTuner unit tests."""

    def test_detect_700hz_tone(self) -> None:
        """700 Hz sine → callback fires with ~700."""
        tuner = CwAutoTuner()
        result: list[int | None] = []
        tuner.start_collection(result.append)
        tuner.feed_audio(_make_tone(700.0))
        assert len(result) == 1
        assert result[0] is not None
        assert abs(result[0] - 700) <= 6

    def test_silence_returns_none(self) -> None:
        """Silence → callback fires with None."""
        tuner = CwAutoTuner()
        result: list[int | None] = []
        tuner.start_collection(result.append)
        tuner.feed_audio(_make_silence())
        assert len(result) == 1
        assert result[0] is None

    def test_inactive_before_start(self) -> None:
        """Not active until start_collection called."""
        tuner = CwAutoTuner()
        assert tuner.active is False

    def test_disarms_after_callback(self) -> None:
        """Active becomes False after callback fires."""
        tuner = CwAutoTuner()
        tuner.start_collection(lambda _: None)
        assert tuner.active is True
        tuner.feed_audio(_make_tone(700.0))
        assert tuner.active is False

    def test_cancel_aborts(self) -> None:
        """Cancel disarms and does not fire callback."""
        tuner = CwAutoTuner()
        result: list[int | None] = []
        tuner.start_collection(result.append)
        # Feed partial audio (less than 24000 samples)
        tuner.feed_audio(_make_tone(700.0, duration_s=0.1))
        tuner.cancel()
        assert tuner.active is False
        # Feed remaining — should be ignored
        tuner.feed_audio(_make_tone(700.0, duration_s=0.4))
        assert len(result) == 0

    def test_feed_ignored_when_not_armed(self) -> None:
        """feed_audio does nothing when not armed — no error."""
        tuner = CwAutoTuner()
        tuner.feed_audio(_make_tone(700.0))  # should not raise

    def test_detect_1000hz_tone(self) -> None:
        """1000 Hz sine → callback fires with ~1000."""
        tuner = CwAutoTuner()
        result: list[int | None] = []
        tuner.start_collection(result.append)
        tuner.feed_audio(_make_tone(1000.0))
        assert len(result) == 1
        assert result[0] is not None
        assert abs(result[0] - 1000) <= 6

    def test_incremental_feeding(self) -> None:
        """Audio fed in small chunks still triggers detection."""
        tuner = CwAutoTuner()
        result: list[int | None] = []
        tuner.start_collection(result.append)
        pcm = _make_tone(800.0)
        chunk_size = 1920  # 20ms frames (960 samples * 2 bytes)
        for i in range(0, len(pcm), chunk_size):
            tuner.feed_audio(pcm[i : i + chunk_size])
        assert len(result) == 1
        assert result[0] is not None
        assert abs(result[0] - 800) <= 6
