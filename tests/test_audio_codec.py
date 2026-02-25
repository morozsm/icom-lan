"""Tests for AudioCodec enum and audio config in IcomRadio."""

import pytest

from icom_lan.types import AudioCodec
from icom_lan.radio import IcomRadio


class TestAudioCodecEnum:
    def test_values(self) -> None:
        assert AudioCodec.ULAW_1CH == 0x01
        assert AudioCodec.PCM_1CH_8BIT == 0x02
        assert AudioCodec.PCM_1CH_16BIT == 0x04
        assert AudioCodec.PCM_2CH_8BIT == 0x08
        assert AudioCodec.PCM_2CH_16BIT == 0x10
        assert AudioCodec.ULAW_2CH == 0x20
        assert AudioCodec.OPUS_1CH == 0x40
        assert AudioCodec.OPUS_2CH == 0x41

    def test_from_int(self) -> None:
        assert AudioCodec(0x04) == AudioCodec.PCM_1CH_16BIT
        assert AudioCodec(0x40) == AudioCodec.OPUS_1CH

    def test_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            AudioCodec(0xFF)

    def test_int_conversion(self) -> None:
        assert int(AudioCodec.PCM_1CH_16BIT) == 0x04


class TestRadioAudioConfig:
    def test_default_codec(self) -> None:
        r = IcomRadio("192.168.1.100")
        assert r.audio_codec == AudioCodec.PCM_1CH_16BIT
        assert r.audio_sample_rate == 48000

    def test_custom_codec(self) -> None:
        r = IcomRadio(
            "192.168.1.100",
            audio_codec=AudioCodec.OPUS_1CH,
            audio_sample_rate=16000,
        )
        assert r.audio_codec == AudioCodec.OPUS_1CH
        assert r.audio_sample_rate == 16000

    def test_codec_from_int(self) -> None:
        r = IcomRadio("192.168.1.100", audio_codec=0x40)
        assert r.audio_codec == AudioCodec.OPUS_1CH

    def test_codec_ulaw(self) -> None:
        r = IcomRadio("192.168.1.100", audio_codec=AudioCodec.ULAW_1CH)
        assert r.audio_codec == AudioCodec.ULAW_1CH
