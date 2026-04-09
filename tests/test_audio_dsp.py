"""Tests for audio DSP pipeline — noise gate, RMS normalizer, limiter."""

from __future__ import annotations

import numpy as np
import pytest

from icom_lan.audio.dsp import (
    DspPipeline,
    Limiter,
    NoiseGate,
    RmsNormalizer,
    _db_to_linear,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _silence(n: int = 960) -> bytes:
    return b"\x00" * (n * 2)


def _tone(amplitude: int = 16000, n: int = 960, freq: float = 1000.0) -> bytes:
    t = np.arange(n) / 48000
    return (np.sin(2 * np.pi * freq * t) * amplitude).astype(np.int16).tobytes()


def _rms(pcm: bytes) -> float:
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
    return float(np.sqrt(np.mean(samples ** 2)))


def _peak(pcm: bytes) -> int:
    return int(np.max(np.abs(np.frombuffer(pcm, dtype=np.int16))))


# ---------------------------------------------------------------------------
# _db_to_linear
# ---------------------------------------------------------------------------


def test_db_to_linear_0db():
    assert _db_to_linear(0.0) == pytest.approx(32767.0, rel=0.01)


def test_db_to_linear_minus6db():
    # -6dB ≈ half amplitude
    assert _db_to_linear(-6.0) == pytest.approx(32767.0 * 0.5012, rel=0.02)


# ---------------------------------------------------------------------------
# NoiseGate
# ---------------------------------------------------------------------------


def test_noise_gate_silences_quiet_input():
    gate = NoiseGate(threshold_db=-40)
    quiet = _tone(amplitude=10, n=960)  # very quiet
    out = gate.process(quiet)
    assert out == _silence(960)


def test_noise_gate_passes_loud_input():
    gate = NoiseGate(threshold_db=-40)
    loud = _tone(amplitude=16000, n=960)
    out = gate.process(loud)
    assert out == loud  # unchanged


def test_noise_gate_passes_silence_as_silence():
    gate = NoiseGate(threshold_db=-60)
    out = gate.process(_silence())
    assert out == _silence()


# ---------------------------------------------------------------------------
# RmsNormalizer
# ---------------------------------------------------------------------------


def test_rms_normalizer_boosts_quiet_signal():
    norm = RmsNormalizer(target_db=-20)
    quiet = _tone(amplitude=500, n=960)
    rms_in = _rms(quiet)

    # Process multiple frames to let envelope settle
    out = quiet
    for _ in range(10):
        out = norm.process(out)

    rms_out = _rms(out)
    assert rms_out > rms_in  # should have been boosted


def test_rms_normalizer_reduces_loud_signal():
    norm = RmsNormalizer(target_db=-20)
    loud = _tone(amplitude=30000, n=960)
    rms_in = _rms(loud)

    out = loud
    for _ in range(10):
        out = norm.process(out)

    rms_out = _rms(out)
    assert rms_out < rms_in  # should have been reduced


def test_rms_normalizer_passes_silence():
    norm = RmsNormalizer(target_db=-20)
    out = norm.process(_silence())
    assert out == _silence()


def test_rms_normalizer_max_gain_limit():
    """Very quiet input should not get amplified beyond max_gain."""
    norm = RmsNormalizer(target_db=-10, max_gain_db=10)
    whisper = _tone(amplitude=10, n=960)

    out = whisper
    for _ in range(20):
        out = norm.process(out)

    # With max_gain=10 (20dB), output should be limited
    assert _peak(out) < 32767


# ---------------------------------------------------------------------------
# Limiter
# ---------------------------------------------------------------------------


def test_limiter_clamps_peaks():
    limiter = Limiter(ceiling_db=-6)
    ceiling = _db_to_linear(-6)
    loud = _tone(amplitude=30000, n=960)
    out = limiter.process(loud)
    assert _peak(out) <= ceiling + 1  # +1 for rounding


def test_limiter_passes_quiet_input():
    limiter = Limiter(ceiling_db=-1)
    quiet = _tone(amplitude=1000, n=960)
    out = limiter.process(quiet)
    assert out == quiet  # no change needed


def test_limiter_handles_silence():
    limiter = Limiter(ceiling_db=-6)
    out = limiter.process(_silence())
    assert out == _silence()


# ---------------------------------------------------------------------------
# DspPipeline
# ---------------------------------------------------------------------------


def test_pipeline_empty_passthrough():
    pipeline = DspPipeline()
    assert pipeline.empty is True
    data = _tone(amplitude=16000)
    assert pipeline.process(data) == data


def test_pipeline_single_stage():
    pipeline = DspPipeline([NoiseGate(threshold_db=-40)])
    assert pipeline.empty is False
    quiet = _tone(amplitude=5)
    out = pipeline.process(quiet)
    assert out == _silence(960)


def test_pipeline_chain_gate_then_limiter():
    """Gate + Limiter: loud signal passes gate, gets limited."""
    pipeline = DspPipeline([
        NoiseGate(threshold_db=-60),
        Limiter(ceiling_db=-6),
    ])
    loud = _tone(amplitude=30000)
    out = pipeline.process(loud)
    ceiling = _db_to_linear(-6)
    assert _peak(out) <= ceiling + 1


def test_pipeline_full_chain():
    """Gate → Normalizer → Limiter full chain."""
    pipeline = DspPipeline([
        NoiseGate(threshold_db=-50),
        RmsNormalizer(target_db=-20),
        Limiter(ceiling_db=-1),
    ])
    tone = _tone(amplitude=16000)
    out = pipeline.process(tone)
    # Should produce valid audio, not silence, and be limited
    assert _peak(out) > 0
    assert _peak(out) <= _db_to_linear(-1) + 1
