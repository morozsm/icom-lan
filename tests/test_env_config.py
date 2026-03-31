"""Tests for env_config — environment variable configuration helpers."""

import logging
from unittest.mock import MagicMock

import pytest


def _reload_env_config(monkeypatch, env: dict[str, str]):
    """Import env_config with the given environment variables set."""
    import icom_lan.env_config as mod

    for key, val in env.items():
        monkeypatch.setenv(key, val)
    # Force re-evaluation of module-level helpers (functions read env at call time)
    return mod


class TestGetAudioSampleRate:
    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("ICOM_AUDIO_SAMPLE_RATE", raising=False)
        from icom_lan.env_config import get_audio_sample_rate

        assert get_audio_sample_rate() == 48000

    @pytest.mark.parametrize("rate", [8000, 16000, 24000, 48000])
    def test_valid_values(self, monkeypatch, rate):
        monkeypatch.setenv("ICOM_AUDIO_SAMPLE_RATE", str(rate))
        from icom_lan.env_config import get_audio_sample_rate

        assert get_audio_sample_rate() == rate

    def test_invalid_string_falls_back_to_default(self, monkeypatch, caplog):
        monkeypatch.setenv("ICOM_AUDIO_SAMPLE_RATE", "not_a_number")
        from icom_lan.env_config import get_audio_sample_rate

        with caplog.at_level(logging.WARNING, logger="icom_lan.env_config"):
            result = get_audio_sample_rate()
        assert result == 48000
        assert "ICOM_AUDIO_SAMPLE_RATE" in caplog.text

    def test_unsupported_rate_falls_back_to_default(self, monkeypatch, caplog):
        monkeypatch.setenv("ICOM_AUDIO_SAMPLE_RATE", "22050")
        from icom_lan.env_config import get_audio_sample_rate

        with caplog.at_level(logging.WARNING, logger="icom_lan.env_config"):
            result = get_audio_sample_rate()
        assert result == 48000
        assert "ICOM_AUDIO_SAMPLE_RATE" in caplog.text


class TestGetAudioBufferPoolSize:
    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("ICOM_AUDIO_BUFFER_POOL_SIZE", raising=False)
        from icom_lan.env_config import get_audio_buffer_pool_size

        assert get_audio_buffer_pool_size() == 5

    def test_valid_override(self, monkeypatch):
        monkeypatch.setenv("ICOM_AUDIO_BUFFER_POOL_SIZE", "15")
        from icom_lan.env_config import get_audio_buffer_pool_size

        assert get_audio_buffer_pool_size() == 15

    def test_invalid_string_falls_back(self, monkeypatch, caplog):
        monkeypatch.setenv("ICOM_AUDIO_BUFFER_POOL_SIZE", "bad")
        from icom_lan.env_config import get_audio_buffer_pool_size

        with caplog.at_level(logging.WARNING, logger="icom_lan.env_config"):
            result = get_audio_buffer_pool_size()
        assert result == 5
        assert "ICOM_AUDIO_BUFFER_POOL_SIZE" in caplog.text

    def test_zero_falls_back(self, monkeypatch, caplog):
        monkeypatch.setenv("ICOM_AUDIO_BUFFER_POOL_SIZE", "0")
        from icom_lan.env_config import get_audio_buffer_pool_size

        with caplog.at_level(logging.WARNING, logger="icom_lan.env_config"):
            result = get_audio_buffer_pool_size()
        assert result == 5

    def test_negative_falls_back(self, monkeypatch, caplog):
        monkeypatch.setenv("ICOM_AUDIO_BUFFER_POOL_SIZE", "-3")
        from icom_lan.env_config import get_audio_buffer_pool_size

        with caplog.at_level(logging.WARNING, logger="icom_lan.env_config"):
            result = get_audio_buffer_pool_size()
        assert result == 5


class TestGetAudioBroadcasterHighWatermark:
    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("ICOM_AUDIO_BROADCASTER_HIGH_WATERMARK", raising=False)
        from icom_lan.env_config import get_audio_broadcaster_high_watermark

        assert get_audio_broadcaster_high_watermark() == 10

    def test_valid_override(self, monkeypatch):
        monkeypatch.setenv("ICOM_AUDIO_BROADCASTER_HIGH_WATERMARK", "25")
        from icom_lan.env_config import get_audio_broadcaster_high_watermark

        assert get_audio_broadcaster_high_watermark() == 25

    def test_invalid_falls_back(self, monkeypatch, caplog):
        monkeypatch.setenv("ICOM_AUDIO_BROADCASTER_HIGH_WATERMARK", "nope")
        from icom_lan.env_config import get_audio_broadcaster_high_watermark

        with caplog.at_level(logging.WARNING, logger="icom_lan.env_config"):
            result = get_audio_broadcaster_high_watermark()
        assert result == 10
        assert "ICOM_AUDIO_BROADCASTER_HIGH_WATERMARK" in caplog.text

    def test_zero_falls_back(self, monkeypatch, caplog):
        monkeypatch.setenv("ICOM_AUDIO_BROADCASTER_HIGH_WATERMARK", "0")
        from icom_lan.env_config import get_audio_broadcaster_high_watermark

        with caplog.at_level(logging.WARNING, logger="icom_lan.env_config"):
            result = get_audio_broadcaster_high_watermark()
        assert result == 10


class TestGetAudioClientHighWatermark:
    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("ICOM_AUDIO_CLIENT_HIGH_WATERMARK", raising=False)
        from icom_lan.env_config import get_audio_client_high_watermark

        assert get_audio_client_high_watermark() == 10

    def test_valid_override(self, monkeypatch):
        monkeypatch.setenv("ICOM_AUDIO_CLIENT_HIGH_WATERMARK", "25")
        from icom_lan.env_config import get_audio_client_high_watermark

        assert get_audio_client_high_watermark() == 25

    def test_invalid_falls_back(self, monkeypatch, caplog):
        monkeypatch.setenv("ICOM_AUDIO_CLIENT_HIGH_WATERMARK", "??")
        from icom_lan.env_config import get_audio_client_high_watermark

        with caplog.at_level(logging.WARNING, logger="icom_lan.env_config"):
            result = get_audio_client_high_watermark()
        assert result == 10
        assert "ICOM_AUDIO_CLIENT_HIGH_WATERMARK" in caplog.text

    def test_zero_falls_back(self, monkeypatch, caplog):
        monkeypatch.setenv("ICOM_AUDIO_CLIENT_HIGH_WATERMARK", "0")
        from icom_lan.env_config import get_audio_client_high_watermark

        with caplog.at_level(logging.WARNING, logger="icom_lan.env_config"):
            result = get_audio_client_high_watermark()
        assert result == 10


class TestHandlerIntegration:
    """Verify that env vars are picked up when handlers are instantiated."""

    def test_audio_broadcaster_uses_env_watermark(self, monkeypatch):
        monkeypatch.setenv("ICOM_AUDIO_BROADCASTER_HIGH_WATERMARK", "25")
        from icom_lan.web.handlers import AudioBroadcaster

        broadcaster = AudioBroadcaster(radio=None)
        assert broadcaster.HIGH_WATERMARK == 25

    def test_audio_broadcaster_default_watermark(self, monkeypatch):
        monkeypatch.delenv("ICOM_AUDIO_BROADCASTER_HIGH_WATERMARK", raising=False)
        from icom_lan.web.handlers import AudioBroadcaster

        broadcaster = AudioBroadcaster(radio=None)
        assert broadcaster.HIGH_WATERMARK == 10

    def test_audio_handler_uses_env_watermark(self, monkeypatch):
        monkeypatch.setenv("ICOM_AUDIO_CLIENT_HIGH_WATERMARK", "30")
        from icom_lan.web.handlers import AudioHandler
        from icom_lan.web.websocket import WebSocketConnection

        mock_ws = MagicMock(spec=WebSocketConnection)
        handler = AudioHandler(mock_ws, radio=None)
        assert handler.HIGH_WATERMARK == 30

    def test_audio_handler_default_watermark(self, monkeypatch):
        monkeypatch.delenv("ICOM_AUDIO_CLIENT_HIGH_WATERMARK", raising=False)
        from icom_lan.web.handlers import AudioHandler
        from icom_lan.web.websocket import WebSocketConnection

        mock_ws = MagicMock(spec=WebSocketConnection)
        handler = AudioHandler(mock_ws, radio=None)
        assert handler.HIGH_WATERMARK == 10
