"""Tests for AudioAnalyzer — realtime SNR estimation from PCM stream."""

from __future__ import annotations

import array
import math

import pytest

from icom_lan.audio_analyzer import AudioAnalyzer


def _make_pcm_silence(n_samples: int = 480) -> bytes:
    """Generate s16le mono silence."""
    return b"\x00\x00" * n_samples


def _make_pcm_tone(
    amplitude: int = 16384,
    n_samples: int = 480,
    freq_hz: float = 1000.0,
    sample_rate: int = 48000,
) -> bytes:
    """Generate s16le mono sine tone."""
    buf = array.array("h", [0] * n_samples)
    for i in range(n_samples):
        val = int(amplitude * math.sin(2.0 * math.pi * freq_hz * i / sample_rate))
        buf[i] = max(-32768, min(32767, val))
    return buf.tobytes()


def _make_pcm_noise(amplitude: int = 100, n_samples: int = 480) -> bytes:
    """Generate low-level pseudo-noise (deterministic)."""
    buf = array.array("h", [0] * n_samples)
    # Simple PRNG for determinism
    seed = 42
    for i in range(n_samples):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        val = (seed % (2 * amplitude + 1)) - amplitude
        buf[i] = max(-32768, min(32767, val))
    return buf.tobytes()


class TestAudioAnalyzer:
    def test_feed_silence_rms_near_minus96(self) -> None:
        az = AudioAnalyzer()
        az.feed_audio(_make_pcm_silence())
        assert az.rms_db == pytest.approx(-96.0, abs=1.0)

    def test_feed_silence_snr_near_zero(self) -> None:
        az = AudioAnalyzer()
        az.feed_audio(_make_pcm_silence())
        assert az.snr_db == pytest.approx(0.0, abs=1.0)

    def test_feed_loud_signal_rms_increases(self) -> None:
        az = AudioAnalyzer()
        az.feed_audio(_make_pcm_silence())
        rms_silent = az.rms_db
        # Feed loud tone — multiple frames to overcome smoothing
        for _ in range(10):
            az.feed_audio(_make_pcm_tone(amplitude=16384))
        assert az.rms_db > rms_silent + 20

    def test_noise_then_signal_snr_positive(self) -> None:
        az = AudioAnalyzer(window_seconds=1.0, smoothing=0.5)
        # Feed noise first to establish a noise floor
        for _ in range(100):
            az.feed_audio(_make_pcm_noise(amplitude=100))
        # Now feed loud tone
        for _ in range(20):
            az.feed_audio(_make_pcm_tone(amplitude=16384))
        assert az.snr_db > 10.0

    def test_noise_floor_tracks_minimum(self) -> None:
        az = AudioAnalyzer(window_seconds=2.0, smoothing=0.8)
        # Feed quiet noise to establish a low floor
        for _ in range(100):
            az.feed_audio(_make_pcm_noise(amplitude=50))
        floor_after_noise = az.noise_floor_db
        # Feed a few loud tone frames (fewer than the window so noise entries remain)
        for _ in range(20):
            az.feed_audio(_make_pcm_tone(amplitude=16384))
        # Noise floor should still be near the noise level (entries still in window)
        assert az.noise_floor_db < floor_after_noise + 5

    def test_reset_clears_state(self) -> None:
        az = AudioAnalyzer()
        for _ in range(10):
            az.feed_audio(_make_pcm_tone(amplitude=16384))
        assert az.rms_db > -50
        az.reset()
        assert az.rms_db == -96.0
        assert az.noise_floor_db == -96.0
        assert az.snr_db == 0.0

    def test_to_dict_keys(self) -> None:
        az = AudioAnalyzer()
        az.feed_audio(_make_pcm_tone(amplitude=8000))
        d = az.to_dict()
        assert set(d.keys()) == {"rms_db", "noise_floor_db", "snr_db"}
        assert all(isinstance(v, float) for v in d.values())

    def test_to_dict_values_rounded(self) -> None:
        az = AudioAnalyzer()
        az.feed_audio(_make_pcm_tone(amplitude=8000))
        d = az.to_dict()
        for v in d.values():
            # Values should be rounded to 1 decimal
            assert v == round(v, 1)

    def test_handles_empty_bytes(self) -> None:
        az = AudioAnalyzer()
        az.feed_audio(b"")
        # Should not crash, state remains at defaults
        assert az.rms_db == -96.0

    def test_handles_single_byte(self) -> None:
        """Odd byte count — should not crash."""
        az = AudioAnalyzer()
        az.feed_audio(b"\x00")
        assert az.rms_db == -96.0
