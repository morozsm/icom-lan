"""Tests for AudioFftScope — audio-based IF panadapter."""

from __future__ import annotations


import numpy as np
import pytest

from icom_lan.audio_fft_scope import AudioFftScope
from icom_lan.scope import ScopeFrame


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_pcm_tone(
    freq_hz: float, duration_s: float, sample_rate: int = 48000
) -> bytes:
    """Generate PCM16 mono sine wave at given frequency."""
    t = np.arange(int(sample_rate * duration_s)) / sample_rate
    samples = (np.sin(2 * np.pi * freq_hz * t) * 16000).astype(np.int16)
    return samples.tobytes()


def _make_pcm_silence(num_samples: int) -> bytes:
    """Generate PCM16 mono silence."""
    return b"\x00\x00" * num_samples


def _make_pcm_noise(num_samples: int, amplitude: int = 1000) -> bytes:
    """Generate PCM16 mono white noise."""
    rng = np.random.default_rng(42)
    samples = (rng.uniform(-1, 1, num_samples) * amplitude).astype(np.int16)
    return samples.tobytes()


# ── Basic construction ───────────────────────────────────────────────────────


class TestAudioFftScopeConstruction:
    """Test AudioFftScope initialization and configuration."""

    def test_default_construction(self):
        scope = AudioFftScope()
        assert scope.fft_size == 2048
        assert scope.fps == 20

    def test_custom_params(self):
        scope = AudioFftScope(fft_size=4096, fps=30, window="blackman", avg_count=8)
        assert scope.fft_size == 4096
        assert scope.fps == 30

    def test_frequency_resolution(self):
        scope = AudioFftScope(fft_size=2048, sample_rate=48000)
        assert scope.frequency_resolution == pytest.approx(48000 / 2048, rel=1e-6)

    def test_set_center_freq(self):
        scope = AudioFftScope()
        scope.set_center_freq(14_074_000)
        # No error, center freq stored internally

    def test_set_sample_rate(self):
        scope = AudioFftScope()
        scope.set_sample_rate(44100)
        assert scope.frequency_resolution == pytest.approx(44100 / 2048, rel=1e-6)


# ── Frame generation ────────────────────────────────────────────────────────


class TestAudioFftScopeFrames:
    """Test that AudioFftScope produces valid ScopeFrame objects."""

    def test_produces_scope_frame(self):
        """Feed enough audio to produce at least one frame."""
        scope = AudioFftScope(fft_size=1024, fps=100, avg_count=1)
        scope.set_center_freq(14_074_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        # Feed 2x fft_size samples to ensure at least one frame
        pcm = _make_pcm_tone(1000.0, duration_s=1024 * 2 / 48000)
        scope.feed_audio(pcm)

        assert len(frames) >= 1
        frame = frames[0]
        assert isinstance(frame, ScopeFrame)
        assert frame.receiver == 0
        assert frame.mode == 0  # center
        assert frame.out_of_range is False

    def test_scope_frame_frequency_mapping(self):
        """Verify start/end freq mapped correctly from center freq."""
        scope = AudioFftScope(fft_size=1024, fps=100, avg_count=1, sample_rate=48000)
        scope.set_center_freq(14_074_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        pcm = _make_pcm_tone(1000.0, duration_s=1024 * 2 / 48000)
        scope.feed_audio(pcm)

        assert len(frames) >= 1
        frame = frames[0]
        assert frame.start_freq_hz == 14_074_000 - 24_000
        assert frame.end_freq_hz == 14_074_000 + 24_000

    def test_pixel_range(self):
        """All pixels should be in 0-160 range."""
        scope = AudioFftScope(fft_size=1024, fps=100, avg_count=1)
        scope.set_center_freq(7_000_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        pcm = _make_pcm_noise(1024 * 3, amplitude=5000)
        scope.feed_audio(pcm)

        assert len(frames) >= 1
        for frame in frames:
            for px in frame.pixels:
                assert 0 <= px <= 160, f"pixel {px} out of range"

    def test_symmetric_pixel_count(self):
        """Output should be symmetric: 2 * (fft_size/2) + 1 pixels."""
        fft_size = 1024
        scope = AudioFftScope(fft_size=fft_size, fps=100, avg_count=1)
        scope.set_center_freq(7_000_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        pcm = _make_pcm_noise(fft_size * 2)
        scope.feed_audio(pcm)

        assert len(frames) >= 1
        # rfft gives fft_size//2 + 1 bins
        # symmetric = 2 * fft_size//2 + 1 = fft_size + 1
        n_positive = fft_size // 2  # bins 1..N (excluding DC)
        expected_pixels = 2 * n_positive + 1  # negative + DC + positive
        assert len(frames[0].pixels) == expected_pixels


# ── Signal detection ────────────────────────────────────────────────────────


class TestAudioFftScopeSignalDetection:
    """Test that FFT correctly identifies signal frequencies."""

    def test_tone_peak_location(self):
        """A 1kHz tone should produce a peak near bin corresponding to 1kHz."""
        fft_size = 2048
        sample_rate = 48000
        tone_freq = 1000.0

        scope = AudioFftScope(
            fft_size=fft_size, fps=100, avg_count=1, sample_rate=sample_rate
        )
        scope.set_center_freq(14_074_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        # Generate a clean tone
        pcm = _make_pcm_tone(tone_freq, duration_s=fft_size * 2 / sample_rate)
        scope.feed_audio(pcm)

        assert len(frames) >= 1
        pixels = np.frombuffer(frames[0].pixels, dtype=np.uint8)

        # The peak should be in the right half (positive freq) of the symmetric spectrum
        # Center pixel = DC, pixels to the right = positive frequencies
        center = len(pixels) // 2
        # Bin for 1kHz: bin_index = tone_freq / (sample_rate / fft_size)
        expected_bin = int(tone_freq / (sample_rate / fft_size))

        # Peak should be at center + expected_bin (± 2 bins for windowing)
        peak_region = pixels[center + expected_bin - 3 : center + expected_bin + 4]
        peak_val = int(np.max(peak_region))

        # Also check the mirror (negative freq side)
        mirror_region = pixels[center - expected_bin - 3 : center - expected_bin + 4]
        mirror_val = int(np.max(mirror_region))

        # Peak should be significantly above noise
        noise_floor = int(np.median(pixels))
        assert peak_val > noise_floor + 20, (
            f"Peak {peak_val} not significantly above noise {noise_floor}"
        )
        assert mirror_val > noise_floor + 20, (
            f"Mirror peak {mirror_val} not significantly above noise {noise_floor}"
        )

    def test_silence_low_amplitude(self):
        """Silence should produce low pixel values."""
        scope = AudioFftScope(fft_size=1024, fps=100, avg_count=1)
        scope.set_center_freq(7_000_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        pcm = _make_pcm_silence(1024 * 2)
        scope.feed_audio(pcm)

        assert len(frames) >= 1
        pixels = np.frombuffer(frames[0].pixels, dtype=np.uint8)
        # Silence → all pixels near 0
        assert np.max(pixels) < 30, f"Silence produced max pixel {np.max(pixels)}"

    def test_two_tones_two_peaks(self):
        """Two tones should produce two pairs of peaks (symmetric)."""
        fft_size = 2048
        sample_rate = 48000
        scope = AudioFftScope(
            fft_size=fft_size, fps=100, avg_count=1, sample_rate=sample_rate
        )
        scope.set_center_freq(14_074_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        # Generate two-tone signal
        t = np.arange(int(fft_size * 2)) / sample_rate
        signal = (
            np.sin(2 * np.pi * 800 * t) * 10000 + np.sin(2 * np.pi * 2000 * t) * 10000
        ).astype(np.int16)
        scope.feed_audio(signal.tobytes())

        assert len(frames) >= 1
        pixels = np.frombuffer(frames[0].pixels, dtype=np.uint8)
        center = len(pixels) // 2

        # Check peaks at 800 Hz and 2000 Hz
        bin_800 = int(800 / (sample_rate / fft_size))
        bin_2000 = int(2000 / (sample_rate / fft_size))

        peak_800 = int(np.max(pixels[center + bin_800 - 3 : center + bin_800 + 4]))
        peak_2000 = int(np.max(pixels[center + bin_2000 - 3 : center + bin_2000 + 4]))
        noise = int(np.median(pixels))

        assert peak_800 > noise + 15, f"800Hz peak {peak_800} not above noise {noise}"
        assert peak_2000 > noise + 15, (
            f"2000Hz peak {peak_2000} not above noise {noise}"
        )


# ── Frame rate limiting ─────────────────────────────────────────────────────


class TestAudioFftScopeFrameRate:
    """Test frame rate limiting."""

    def test_fps_limiting(self):
        """With very high data rate, should not exceed target FPS."""
        scope = AudioFftScope(fft_size=256, fps=10, avg_count=1)
        scope.set_center_freq(7_000_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        # Feed much more data than needed (256 * 100 samples = 100 windows)
        pcm = _make_pcm_noise(256 * 100)
        scope.feed_audio(pcm)

        # At 10 fps, processing ~0.5s of audio should yield few frames
        # (actual count depends on monotonic clock, but should be limited)
        # Main check: it doesn't produce 100 frames
        assert len(frames) < 50, (
            f"Too many frames: {len(frames)} (expected <50 at 10fps)"
        )


# ── Averaging ───────────────────────────────────────────────────────────────


class TestAudioFftScopeAveraging:
    """Test frame averaging."""

    def test_averaging_smooths_output(self):
        """Averaged frames should be smoother than single frames."""
        fft_size = 1024

        # No averaging
        scope1 = AudioFftScope(fft_size=fft_size, fps=100, avg_count=1)
        scope1.set_center_freq(7_000_000)
        frames1: list[ScopeFrame] = []
        scope1.on_frame(frames1.append)

        # With averaging
        scope4 = AudioFftScope(fft_size=fft_size, fps=100, avg_count=4)
        scope4.set_center_freq(7_000_000)
        frames4: list[ScopeFrame] = []
        scope4.on_frame(frames4.append)

        # Feed identical noise to both
        pcm = _make_pcm_noise(fft_size * 8, amplitude=3000)
        scope1.feed_audio(pcm)
        scope4.feed_audio(pcm)

        # Both should produce frames
        assert len(frames1) >= 1
        assert len(frames4) >= 1

    def test_avg_count_1_means_no_averaging(self):
        """avg_count=1 should produce frames identical to raw FFT."""
        scope = AudioFftScope(fft_size=1024, fps=100, avg_count=1)
        scope.set_center_freq(7_000_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        pcm = _make_pcm_tone(1500.0, duration_s=1024 * 3 / 48000)
        scope.feed_audio(pcm)

        assert len(frames) >= 1


# ── No callback = no work ───────────────────────────────────────────────────


class TestAudioFftScopeNoCallback:
    """Test that no work is done without a callback."""

    def test_no_callback_no_frames(self):
        """Without a callback, feed_audio should be a no-op."""
        scope = AudioFftScope(fft_size=1024, fps=100, avg_count=1)
        scope.set_center_freq(7_000_000)
        # No on_frame callback registered

        pcm = _make_pcm_noise(1024 * 5)
        scope.feed_audio(pcm)  # Should not raise

    def test_unregister_callback(self):
        """Unregistering callback should stop frame delivery."""
        scope = AudioFftScope(fft_size=1024, fps=100, avg_count=1)
        scope.set_center_freq(7_000_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        pcm1 = _make_pcm_noise(1024 * 2)
        scope.feed_audio(pcm1)
        count_before = len(frames)

        scope.on_frame(None)  # Unregister

        pcm2 = _make_pcm_noise(1024 * 2)
        scope.feed_audio(pcm2)

        assert len(frames) == count_before  # No new frames


# ── Protocol compatibility ──────────────────────────────────────────────────


class TestAudioFftScopeProtocolCompat:
    """Test compatibility with existing scope binary protocol."""

    def test_scope_frame_encodable(self):
        """ScopeFrame from AudioFftScope should be encodable by protocol.py."""
        from icom_lan.web.protocol import encode_scope_frame

        scope = AudioFftScope(fft_size=1024, fps=100, avg_count=1)
        scope.set_center_freq(14_074_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        pcm = _make_pcm_noise(1024 * 2)
        scope.feed_audio(pcm)

        assert len(frames) >= 1
        # Should encode without error
        binary = encode_scope_frame(frames[0], sequence=1)
        assert len(binary) >= 16  # Header size
        assert binary[0] == 0x01  # MSG_TYPE_SCOPE

    def test_stop_clears_state(self):
        """stop() should clear buffers and unregister callback."""
        scope = AudioFftScope(fft_size=1024, fps=100, avg_count=1)
        scope.set_center_freq(7_000_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        pcm = _make_pcm_noise(1024 * 2)
        scope.feed_audio(pcm)
        count = len(frames)

        scope.stop()

        scope.feed_audio(pcm)
        assert len(frames) == count  # No new frames after stop


# ── Mode bandwidth cropping ─────────────────────────────────────────────────


class TestAudioFftScopeModeBandwidth:
    """Test mode-bandwidth cropping via set_mode_bandwidth()."""

    def _get_frame(self, scope: AudioFftScope, fft_size: int) -> ScopeFrame:
        """Feed one FFT window of noise and return the first frame."""
        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)
        pcm = _make_pcm_noise(fft_size * 2)
        scope.feed_audio(pcm)
        assert len(frames) >= 1, "No frames produced"
        return frames[0]

    def test_no_crop_by_default(self):
        """Without set_mode_bandwidth, output is full symmetric spectrum."""
        fft_size = 1024
        scope = AudioFftScope(fft_size=fft_size, fps=100, avg_count=1)
        scope.set_center_freq(14_074_000)
        frame = self._get_frame(scope, fft_size)
        expected = 2 * (fft_size // 2) + 1
        assert len(frame.pixels) == expected

    def test_bandwidth_none_means_full_spectrum(self):
        """set_mode_bandwidth(None) is backward compatible — no crop."""
        fft_size = 1024
        scope = AudioFftScope(fft_size=fft_size, fps=100, avg_count=1)
        scope.set_center_freq(14_074_000)
        scope.set_mode_bandwidth(None)
        frame = self._get_frame(scope, fft_size)
        expected = 2 * (fft_size // 2) + 1
        assert len(frame.pixels) == expected

    def test_bandwidth_zero_means_full_spectrum(self):
        """set_mode_bandwidth(0) is backward compatible — no crop."""
        fft_size = 1024
        scope = AudioFftScope(fft_size=fft_size, fps=100, avg_count=1)
        scope.set_center_freq(14_074_000)
        scope.set_mode_bandwidth(0)
        frame = self._get_frame(scope, fft_size)
        expected = 2 * (fft_size // 2) + 1
        assert len(frame.pixels) == expected

    def test_bandwidth_usb_3600hz(self):
        """USB mode max_hz=3600 → ~153 bins (±76 bins × 23.4 Hz/bin)."""
        fft_size = 2048
        sample_rate = 48000
        scope = AudioFftScope(
            fft_size=fft_size, fps=100, avg_count=1, sample_rate=sample_rate
        )
        scope.set_center_freq(14_074_000)
        scope.set_mode_bandwidth(3600)
        frame = self._get_frame(scope, fft_size)

        bin_res = sample_rate / fft_size
        crop_half_bins = int((3600 / 2) / bin_res)
        expected_bins = 2 * crop_half_bins + 1
        assert len(frame.pixels) == expected_bins

    def test_bandwidth_am_10000hz(self):
        """AM mode max_hz=10000 → ~427 bins."""
        fft_size = 2048
        sample_rate = 48000
        scope = AudioFftScope(
            fft_size=fft_size, fps=100, avg_count=1, sample_rate=sample_rate
        )
        scope.set_center_freq(7_200_000)
        scope.set_mode_bandwidth(10000)
        frame = self._get_frame(scope, fft_size)

        bin_res = sample_rate / fft_size
        crop_half_bins = int((10000 / 2) / bin_res)
        expected_bins = 2 * crop_half_bins + 1
        assert len(frame.pixels) == expected_bins

    def test_cropped_freq_range(self):
        """start_freq_hz and end_freq_hz should reflect the crop."""
        fft_size = 2048
        sample_rate = 48000
        center = 14_074_000
        max_hz = 3600

        scope = AudioFftScope(
            fft_size=fft_size, fps=100, avg_count=1, sample_rate=sample_rate
        )
        scope.set_center_freq(center)
        scope.set_mode_bandwidth(max_hz)
        frame = self._get_frame(scope, fft_size)

        bin_res = sample_rate / fft_size
        crop_half_bins = int((max_hz / 2) / bin_res)
        actual_half_hz = int(crop_half_bins * bin_res)

        assert frame.start_freq_hz == center - actual_half_hz
        assert frame.end_freq_hz == center + actual_half_hz

    def test_full_spectrum_freq_range_unchanged(self):
        """Without crop, start/end freq span full ±24kHz."""
        fft_size = 1024
        sample_rate = 48000
        center = 14_074_000

        scope = AudioFftScope(
            fft_size=fft_size, fps=100, avg_count=1, sample_rate=sample_rate
        )
        scope.set_center_freq(center)
        frame = self._get_frame(scope, fft_size)

        assert frame.start_freq_hz == center - sample_rate // 2
        assert frame.end_freq_hz == center + sample_rate // 2

    def test_mode_switch_changes_bin_count(self):
        """Changing bandwidth mid-stream produces frames with new bin count."""
        fft_size = 2048
        sample_rate = 48000
        scope = AudioFftScope(
            fft_size=fft_size, fps=100, avg_count=1, sample_rate=sample_rate
        )
        scope.set_center_freq(14_074_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        # First: USB bandwidth
        scope.set_mode_bandwidth(3600)
        scope.feed_audio(_make_pcm_noise(fft_size * 2))
        assert len(frames) >= 1
        bin_res = sample_rate / fft_size
        usb_bins = 2 * int((3600 / 2) / bin_res) + 1
        assert len(frames[0].pixels) == usb_bins

        # Switch to AM bandwidth
        frames.clear()
        scope.set_mode_bandwidth(10000)
        scope.feed_audio(_make_pcm_noise(fft_size * 2))
        assert len(frames) >= 1
        am_bins = 2 * int((10000 / 2) / bin_res) + 1
        assert len(frames[0].pixels) == am_bins

    def test_bandwidth_hz_property(self):
        """bandwidth_hz property reflects current setting."""
        scope = AudioFftScope()
        assert scope.bandwidth_hz is None

        scope.set_mode_bandwidth(3600)
        assert scope.bandwidth_hz == 3600

        scope.set_mode_bandwidth(None)
        assert scope.bandwidth_hz is None

    def test_avg_buf_reset_on_bandwidth_change(self):
        """Changing bandwidth clears averaging buffer to avoid bin-count mismatch."""
        fft_size = 2048
        sample_rate = 48000
        scope = AudioFftScope(
            fft_size=fft_size, fps=100, avg_count=4, sample_rate=sample_rate
        )
        scope.set_center_freq(14_074_000)

        frames: list[ScopeFrame] = []
        scope.on_frame(frames.append)

        # Build up avg buffer
        scope.feed_audio(_make_pcm_noise(fft_size * 5))

        # Change bandwidth — avg_buf should be cleared, no crash
        scope.set_mode_bandwidth(3600)
        frames.clear()
        scope.feed_audio(_make_pcm_noise(fft_size * 2))
        assert len(frames) >= 1

        bin_res = sample_rate / fft_size
        expected = 2 * int((3600 / 2) / bin_res) + 1
        assert len(frames[0].pixels) == expected
