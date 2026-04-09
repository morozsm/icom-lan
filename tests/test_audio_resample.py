"""Tests for audio sample-rate negotiation and resampling."""

from __future__ import annotations

import numpy as np
import pytest

from icom_lan.audio.backend import AudioDeviceId, AudioDeviceInfo, FakeAudioBackend
from icom_lan.audio.resample import PcmResampler, SampleRateNegotiation, negotiate_sample_rate


# ---------------------------------------------------------------------------
# PcmResampler
# ---------------------------------------------------------------------------


def test_resampler_identity_passthrough():
    """When from_rate == to_rate, input is returned unchanged."""
    r = PcmResampler(48000, 48000)
    assert r.identity is True
    data = b"\x01\x02" * 960
    assert r.process(data) is data  # same object


def test_resampler_downsample_48k_to_44100():
    """48kHz → 44.1kHz produces fewer samples."""
    r = PcmResampler(48000, 44100)
    assert r.identity is False
    # 960 samples at 48kHz, 20ms frame
    n_in = 960
    pcm_in = np.zeros(n_in, dtype=np.int16).tobytes()
    pcm_out = r.process(pcm_in)
    n_out = len(pcm_out) // 2  # s16le = 2 bytes per sample
    expected = round(n_in * 44100 / 48000)
    assert n_out == expected


def test_resampler_upsample_44100_to_48k():
    """44.1kHz → 48kHz produces more samples."""
    r = PcmResampler(44100, 48000)
    n_in = 882  # ~20ms at 44.1kHz
    pcm_in = np.zeros(n_in, dtype=np.int16).tobytes()
    pcm_out = r.process(pcm_in)
    n_out = len(pcm_out) // 2
    expected = round(n_in * 48000 / 44100)
    assert n_out == expected


def test_resampler_preserves_signal():
    """A 1kHz sine wave survives resampling without gross distortion."""
    from_rate = 48000
    to_rate = 44100
    n_in = 960
    t = np.arange(n_in) / from_rate
    sine = (np.sin(2 * np.pi * 1000 * t) * 16000).astype(np.int16)
    pcm_in = sine.tobytes()

    r = PcmResampler(from_rate, to_rate)
    pcm_out = r.process(pcm_in)
    out = np.frombuffer(pcm_out, dtype=np.int16)

    # Output should have reasonable amplitude
    assert np.max(np.abs(out)) > 10000


def test_resampler_multichannel():
    """Stereo resampling produces correct output shape."""
    r = PcmResampler(48000, 24000, channels=2)
    n_in = 960
    pcm_in = np.zeros(n_in * 2, dtype=np.int16).tobytes()  # 960 frames * 2 channels
    pcm_out = r.process(pcm_in)
    n_out_samples = len(pcm_out) // 2
    expected_frames = round(n_in * 24000 / 48000)
    assert n_out_samples == expected_frames * 2


def test_resampler_clipping():
    """Values at int16 boundaries are not clipped incorrectly."""
    r = PcmResampler(48000, 96000)
    n_in = 100
    loud = np.full(n_in, 32767, dtype=np.int16)
    pcm_out = r.process(loud.tobytes())
    out = np.frombuffer(pcm_out, dtype=np.int16)
    assert np.max(out) == 32767


def test_resampler_anti_aliasing_attenuates_high_freq():
    """Downsampling applies anti-aliasing filter to reduce aliasing."""
    from_rate = 48000
    to_rate = 16000  # 3:1 decimation — aliasing would be severe without filter
    n_in = 960

    # Generate a tone at 10kHz (above Nyquist of 8kHz for 16kHz output)
    t = np.arange(n_in) / from_rate
    high_tone = (np.sin(2 * np.pi * 10000 * t) * 16000).astype(np.int16)

    r = PcmResampler(from_rate, to_rate)
    pcm_out = r.process(high_tone.tobytes())
    out = np.frombuffer(pcm_out, dtype=np.int16)

    # The 10kHz tone should be significantly attenuated after AA filter
    # (without the filter, aliasing would fold it into the passband)
    assert np.max(np.abs(out)) < 8000  # >50% attenuation


def test_resampler_invalid_rates():
    with pytest.raises(ValueError, match="positive"):
        PcmResampler(0, 48000)
    with pytest.raises(ValueError, match="positive"):
        PcmResampler(48000, -1)


# ---------------------------------------------------------------------------
# negotiate_sample_rate
# ---------------------------------------------------------------------------


def test_negotiate_preferred_rate_supported():
    """When 48kHz is supported, no resampling needed."""
    backend = FakeAudioBackend(
        [AudioDeviceInfo(id=AudioDeviceId(1), name="Dev", input_channels=2)],
        supported_sample_rates={48_000, 44_100},
    )
    result = negotiate_sample_rate(backend, AudioDeviceId(1), radio_rate=48_000)
    assert result == SampleRateNegotiation(
        device_rate=48_000, radio_rate=48_000, needs_resample=False
    )


def test_negotiate_fallback_to_44100():
    """When 48kHz is NOT supported, negotiate falls back to 44.1kHz."""
    backend = FakeAudioBackend(
        [AudioDeviceInfo(id=AudioDeviceId(1), name="Dev", input_channels=2)],
        supported_sample_rates={44_100, 96_000},
    )
    result = negotiate_sample_rate(backend, AudioDeviceId(1), radio_rate=48_000)
    assert result.device_rate == 44_100
    assert result.radio_rate == 48_000
    assert result.needs_resample is True


def test_negotiate_fallback_priority():
    """Fallback order follows _PREFERRED_RATES: 44100 before 96000."""
    backend = FakeAudioBackend(
        [AudioDeviceInfo(id=AudioDeviceId(1), name="Dev", input_channels=2)],
        supported_sample_rates={96_000, 44_100},
    )
    result = negotiate_sample_rate(backend, AudioDeviceId(1), radio_rate=48_000)
    # 44100 comes before 96000 in priority list
    assert result.device_rate == 44_100


def test_negotiate_no_common_rate():
    """When no rates are supported, falls back to radio_rate without resampling."""
    backend = FakeAudioBackend(
        [AudioDeviceInfo(id=AudioDeviceId(1), name="Dev", input_channels=2)],
        supported_sample_rates=set(),
    )
    result = negotiate_sample_rate(backend, AudioDeviceId(1), radio_rate=48_000)
    assert result.device_rate == 48_000
    assert result.needs_resample is False


def test_negotiate_backend_without_check():
    """Backends without check_sample_rate always succeed at radio_rate."""
    class _MinimalBackend:
        def list_devices(self):
            return []
        def open_rx(self, *a, **kw):
            pass
        def open_tx(self, *a, **kw):
            pass

    result = negotiate_sample_rate(_MinimalBackend(), None, radio_rate=48_000)
    assert result.needs_resample is False
