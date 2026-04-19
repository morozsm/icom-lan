"""Tests for NRScipyNode and resample_if_needed utility."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np

from icom_lan.dsp.exceptions import DSPBackendUnavailable

try:
    import scipy  # noqa: F401

    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


@unittest.skipUnless(_HAS_SCIPY, "scipy not installed")
class TestNRScipyNode(unittest.TestCase):
    """Tests for NRScipyNode spectral subtraction noise reduction."""

    def _make_node(self, **kwargs):
        from icom_lan.dsp.nodes.nr_scipy import NRScipyNode

        return NRScipyNode(**kwargs)

    def test_reduces_noise(self):
        """NR node reduces noise on a noisy signal.

        Feed pure noise first to build the noise estimate, then feed
        signal+noise and verify that RMS error vs clean signal decreases.
        """
        sr = 48000
        frame_size = 1024
        rng = np.random.default_rng(42)

        node = self._make_node(strength=0.8)

        # Phase 1: feed pure-noise frames to build the noise estimate.
        for _ in range(8):
            noise_only = 0.1 * rng.standard_normal(frame_size).astype(np.float32)
            node.process(noise_only, sr)

        # Phase 2: feed signal + noise frames and collect output.
        n_test_frames = 8
        t = np.linspace(
            0,
            frame_size * n_test_frames / sr,
            frame_size * n_test_frames,
            endpoint=False,
            dtype=np.float32,
        )
        clean = 0.5 * np.sin(2 * np.pi * 1000 * t).astype(np.float32)
        noise = 0.1 * rng.standard_normal(len(t)).astype(np.float32)
        noisy = clean + noise

        frames = [noisy[i : i + frame_size] for i in range(0, len(noisy), frame_size)]
        processed = np.concatenate([node.process(f, sr) for f in frames])

        # RMS error vs clean reference should be lower after NR.
        rms_before = np.sqrt(np.mean((noisy - clean) ** 2))
        rms_after = np.sqrt(np.mean((processed - clean) ** 2))
        self.assertLess(rms_after, rms_before)

    def test_passes_clean_signal(self):
        """NR node passes clean sine wave mostly unchanged (correlation > 0.9)."""
        sr = 48000
        duration = 0.5
        t = np.linspace(
            0, duration, int(sr * duration), endpoint=False, dtype=np.float32
        )
        clean = 0.5 * np.sin(2 * np.pi * 1000 * t).astype(np.float32)

        node = self._make_node(strength=0.6)
        frame_size = 1024

        frames = [
            clean[i : i + frame_size]
            for i in range(0, len(clean) - frame_size + 1, frame_size)
        ]
        processed_frames = []
        for frame in frames:
            out = node.process(frame, sr)
            processed_frames.append(out)

        if len(processed_frames) > 4:
            later_input = np.concatenate(frames[4:])
            later_output = np.concatenate(processed_frames[4:])
            corr = np.corrcoef(later_input, later_output)[0, 1]
            self.assertGreater(corr, 0.9)

    def test_reset_clears_noise_estimate(self):
        """reset() clears the noise estimate, forcing re-estimation."""
        sr = 48000
        node = self._make_node(strength=0.6)
        rng = np.random.default_rng(42)
        noise = 0.1 * rng.standard_normal(1024).astype(np.float32)

        # Feed frames to build estimate
        for _ in range(5):
            node.process(noise, sr)

        node.reset()

        # After reset, internal state should be cleared
        # The node should be in initial state (no noise estimate)
        self.assertTrue(node._noise_estimate is None)

    def test_get_set_params(self):
        """get_params/set_params roundtrip."""
        node = self._make_node(strength=0.4)
        params = node.get_params()
        self.assertEqual(params, {"strength": 0.4})

        node.set_params(strength=0.9)
        params = node.get_params()
        self.assertEqual(params, {"strength": 0.9})

    def test_missing_scipy_raises(self):
        """Missing scipy raises DSPBackendUnavailable."""
        import sys

        # Temporarily remove scipy from modules
        with patch.dict(sys.modules, {"scipy": None, "scipy.fft": None}):
            # Need to reimport the module to trigger the guard
            import icom_lan.dsp.nodes.nr_scipy as mod

            with self.assertRaises(DSPBackendUnavailable):
                # Force re-import logic by calling the constructor
                # which lazy-imports scipy
                mod.NRScipyNode(strength=0.5)


class TestResampleIfNeeded(unittest.TestCase):
    """Tests for resample_if_needed utility."""

    def test_same_rate_noop(self):
        """Same rate returns input unchanged."""
        from icom_lan.dsp.resample import resample_if_needed

        samples = np.ones(100, dtype=np.float32)
        result, rate = resample_if_needed(samples, 48000, 48000)
        self.assertIs(result, samples)  # identity, not copy
        self.assertEqual(rate, 48000)

    def test_downsample_reduces_length(self):
        """48000->16000 reduces array length by 3x."""
        from icom_lan.dsp.resample import resample_if_needed

        n = 4800  # 0.1s at 48kHz
        samples = np.zeros(n, dtype=np.float32)
        result, rate = resample_if_needed(samples, 48000, 16000)
        self.assertEqual(rate, 16000)
        expected_len = n * 16000 // 48000  # 1600
        self.assertEqual(len(result), expected_len)

    def test_preserves_tone_frequency(self):
        """Resampled sine wave preserves dominant frequency."""
        from icom_lan.dsp.resample import resample_if_needed

        from_rate = 48000
        to_rate = 16000
        tone_freq = 1000  # Hz
        duration = 0.1  # seconds
        n = int(from_rate * duration)
        t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
        samples = np.sin(2 * np.pi * tone_freq * t).astype(np.float32)

        result, rate = resample_if_needed(samples, from_rate, to_rate)
        self.assertEqual(rate, to_rate)

        # Check FFT peak is at tone_freq
        fft_mag = np.abs(np.fft.rfft(result))
        freqs = np.fft.rfftfreq(len(result), 1.0 / to_rate)
        peak_freq = freqs[np.argmax(fft_mag)]
        self.assertAlmostEqual(peak_freq, tone_freq, delta=to_rate / len(result) + 1)


if __name__ == "__main__":
    unittest.main()
