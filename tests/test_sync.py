"""Tests for synchronous API wrapper."""

from unittest.mock import AsyncMock

import pytest

from icom_lan.sync import IcomRadio
from icom_lan.types import AudioCodec


class TestSyncInit:
    def test_creates_radio(self) -> None:
        r = IcomRadio("192.168.1.100")
        assert r._radio is not None
        assert r._loop is not None
        r._loop.close()

    def test_custom_params(self) -> None:
        r = IcomRadio(
            "192.168.1.100",
            port=50002,
            username="u",
            password="p",
            radio_addr=0xA4,
            timeout=10.0,
            audio_codec=AudioCodec.OPUS_1CH,
            audio_sample_rate=16000,
        )
        assert r._radio._host == "192.168.1.100"
        assert r._radio._port == 50002
        assert r._radio._radio_addr == 0xA4
        assert r.audio_codec == AudioCodec.OPUS_1CH
        assert r.audio_sample_rate == 16000
        r._loop.close()

    def test_not_connected(self) -> None:
        r = IcomRadio("192.168.1.100")
        assert r.connected is False
        r._loop.close()


class TestSyncContextManager:
    def test_exit_closes_loop(self) -> None:
        r = IcomRadio("192.168.1.100")
        # Can't actually connect without a radio, but test the mechanism
        r._loop.close()  # just verify it's closeable


class TestSyncAudioNaming:
    def test_start_audio_rx_alias_warns_and_calls_opus(self) -> None:
        r = IcomRadio("192.168.1.100")
        r._radio.start_audio_rx_opus = AsyncMock()

        with pytest.warns(DeprecationWarning, match="start_audio_rx_opus"):
            r.start_audio_rx(lambda pkt: None)

        r._radio.start_audio_rx_opus.assert_awaited_once()
        r._loop.close()

    def test_new_opus_method_calls_async_impl(self) -> None:
        r = IcomRadio("192.168.1.100")
        r._radio.push_audio_tx_opus = AsyncMock()

        r.push_audio_tx_opus(b"\x01\x02")

        r._radio.push_audio_tx_opus.assert_awaited_once_with(b"\x01\x02")
        r._loop.close()

    def test_audio_capabilities(self) -> None:
        caps = IcomRadio.audio_capabilities()
        assert caps.default_codec.name == "PCM_1CH_16BIT"
        assert caps.default_sample_rate_hz == 48000
        assert caps.default_channels == 1
