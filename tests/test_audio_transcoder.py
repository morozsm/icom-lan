"""Tests for internal PCM<->Opus transcoder helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from icom_lan._audio_transcoder import PcmAudioFormat, PcmOpusTranscoder
from icom_lan.audio import AudioPacket
from icom_lan.exceptions import (
    AudioCodecBackendError,
    AudioFormatError,
    AudioTranscodeError,
)
from icom_lan.radio import IcomRadio


class _FakeBackend:
    def __init__(
        self,
        *,
        fail_encode: bool = False,
        fail_decode: bool = False,
        decode_size_mismatch: bool = False,
    ) -> None:
        self.fail_encode = fail_encode
        self.fail_decode = fail_decode
        self.decode_size_mismatch = decode_size_mismatch
        self.last_encode_frame_samples: int | None = None
        self.last_decode_frame_samples: int | None = None
        self.last_decode_channels: int | None = None

    def create_encoder(self, sample_rate: int, channels: int) -> tuple[int, int]:
        return (sample_rate, channels)

    def create_decoder(self, sample_rate: int, channels: int) -> tuple[int, int]:
        return (sample_rate, channels)

    def encode(
        self,
        encoder: tuple[int, int],
        pcm_data: bytes,
        frame_samples: int,
    ) -> bytes:
        _ = encoder
        self.last_encode_frame_samples = frame_samples
        if self.fail_encode:
            raise RuntimeError("encode boom")
        return b"OPUS" + pcm_data[:4]

    def decode(
        self,
        decoder: tuple[int, int],
        opus_data: bytes,
        frame_samples: int,
    ) -> bytes:
        _ = opus_data
        self.last_decode_frame_samples = frame_samples
        self.last_decode_channels = decoder[1]
        if self.fail_decode:
            raise RuntimeError("decode boom")
        if self.decode_size_mismatch:
            return b"\x00"
        return b"\x01" * (frame_samples * decoder[1] * 2)


class TestPcmOpusTranscoder:
    def test_missing_backend_raises_actionable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("icom_lan._audio_transcoder._load_default_backend", lambda: None)
        with pytest.raises(AudioCodecBackendError, match="install icom-lan\\[audio\\]"):
            PcmOpusTranscoder()

    def test_format_validation_error(self) -> None:
        with pytest.raises(AudioFormatError, match="Unsupported sample_rate"):
            PcmOpusTranscoder(PcmAudioFormat(sample_rate=44100), backend=_FakeBackend())

    def test_pcm_opus_roundtrip_happy_path(self) -> None:
        backend = _FakeBackend()
        fmt = PcmAudioFormat(sample_rate=48000, channels=1, frame_ms=20)
        transcoder = PcmOpusTranscoder(fmt, backend=backend)

        pcm = b"\x10\x00" * fmt.frame_samples
        opus = transcoder.pcm_to_opus(pcm)
        decoded = transcoder.opus_to_pcm(opus)

        assert opus.startswith(b"OPUS")
        assert len(decoded) == fmt.frame_bytes
        assert backend.last_encode_frame_samples == fmt.frame_samples
        assert backend.last_decode_frame_samples == fmt.frame_samples

    def test_pcm_frame_size_error(self) -> None:
        transcoder = PcmOpusTranscoder(backend=_FakeBackend())
        with pytest.raises(AudioFormatError, match="PCM frame size mismatch"):
            transcoder.pcm_to_opus(b"\x00" * 16)

    def test_empty_opus_frame_error(self) -> None:
        transcoder = PcmOpusTranscoder(backend=_FakeBackend())
        with pytest.raises(AudioFormatError, match="must not be empty"):
            transcoder.opus_to_pcm(b"")

    def test_encode_failure_wrapped(self) -> None:
        transcoder = PcmOpusTranscoder(backend=_FakeBackend(fail_encode=True))
        pcm = b"\x00\x00" * transcoder.fmt.frame_samples
        with pytest.raises(AudioTranscodeError, match="encode PCM frame"):
            transcoder.pcm_to_opus(pcm)

    def test_decode_failure_wrapped(self) -> None:
        transcoder = PcmOpusTranscoder(backend=_FakeBackend(fail_decode=True))
        with pytest.raises(AudioTranscodeError, match="decode Opus frame"):
            transcoder.opus_to_pcm(b"\xAA")

    def test_decode_size_mismatch_wrapped(self) -> None:
        transcoder = PcmOpusTranscoder(backend=_FakeBackend(decode_size_mismatch=True))
        with pytest.raises(AudioTranscodeError, match="size mismatch"):
            transcoder.opus_to_pcm(b"\xAA")


class TestRadioPcmHooks:
    @pytest.mark.asyncio
    async def test_push_audio_tx_pcm_internal_uses_transcoder(self) -> None:
        radio = IcomRadio("192.168.1.100")
        radio.push_audio_tx = AsyncMock()  # type: ignore[method-assign]

        class _DummyTranscoder:
            def pcm_to_opus(self, pcm: bytes) -> bytes:
                return b"opus:" + pcm[:2]

        radio._pcm_transcoder = _DummyTranscoder()  # type: ignore[assignment]
        radio._pcm_transcoder_fmt = (48000, 1, 20)

        await radio._push_audio_tx_pcm_internal(b"\x01\x02" * 960)
        radio.push_audio_tx.assert_awaited_once_with(b"opus:\x01\x02")

    def test_decode_audio_packet_to_pcm_and_callback_adapter(self) -> None:
        radio = IcomRadio("192.168.1.100")

        class _DummyTranscoder:
            def opus_to_pcm(self, opus: bytes) -> bytes:
                return b"pcm:" + opus

        radio._pcm_transcoder = _DummyTranscoder()  # type: ignore[assignment]
        radio._pcm_transcoder_fmt = (48000, 1, 20)

        packet = AudioPacket(ident=0x0080, send_seq=1, data=b"\xAA\xBB")
        decoded = radio._decode_audio_packet_to_pcm(packet)
        assert decoded == b"pcm:\xAA\xBB"

        received: list[bytes | None] = []
        adapter = radio._build_pcm_rx_callback(lambda frame: received.append(frame))
        adapter(None)
        adapter(packet)

        assert received == [None, b"pcm:\xAA\xBB"]
