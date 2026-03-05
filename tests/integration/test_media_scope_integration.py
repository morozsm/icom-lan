"""Media and scope integration tests (backlog items 10-11)."""

from __future__ import annotations

import asyncio
import os
from typing import List

import pytest

from icom_lan import IcomRadio
from icom_lan.exceptions import AudioCodecBackendError
pytestmark = pytest.mark.integration


def _flag_enabled(name: str) -> bool:
    return os.environ.get(name, "0") == "1"


def _pcm_require_frames() -> bool:
    return os.environ.get("ICOM_PCM_REQUIRE_FRAMES", "1") != "0"


class TestAudioPcm:
    """Integration coverage for high-level PCM APIs."""

    async def test_start_stop_audio_rx_pcm(self, radio: IcomRadio) -> None:
        """Receive decoded PCM frames from radio audio stream."""
        frames: List[bytes] = []

        def on_pcm(frame: bytes | None) -> None:
            if frame is not None:
                frames.append(frame)

        try:
            await radio.start_audio_rx_pcm(
                on_pcm,
                sample_rate=48000,
                channels=1,
                frame_ms=20,
                jitter_depth=5,
            )
        except AudioCodecBackendError as e:
            pytest.skip(str(e))
        try:
            await asyncio.sleep(2.0)
        finally:
            await radio.stop_audio_rx_pcm()

        print(f"PCM RX frames: {len(frames)}")

        if _pcm_require_frames():
            assert frames, (
                "No PCM frames received. "
                "Check audio monitor/LAN audio settings. "
                "Set ICOM_PCM_REQUIRE_FRAMES=0 for smoke-only."
            )

        if frames:
            first = frames[0]
            assert isinstance(first, (bytes, bytearray))
            assert len(first) > 0
            assert len(first) % 2 == 0

    async def test_push_audio_tx_pcm(self, radio: IcomRadio) -> None:
        """Push PCM frames into TX pipeline (gated)."""
        if not _flag_enabled("ICOM_ALLOW_AUDIO_TX"):
            pytest.skip("Set ICOM_ALLOW_AUDIO_TX=1 to run PCM TX integration tests")

        try:
            await radio.start_audio_tx_pcm(sample_rate=48000, channels=1, frame_ms=20)
        except AudioCodecBackendError as e:
            pytest.skip(str(e))
        try:
            # 48k * 20ms = 960 samples, mono s16le => 1920 bytes.
            frame = b"\x00\x00" * 960
            for _ in range(4):
                await radio.push_audio_tx_pcm(frame)
                await asyncio.sleep(0.03)
            print("PCM TX frames sent: 4 ✓")
        finally:
            await radio.stop_audio_tx_pcm()


class TestScopeIntegration:
    """Integration coverage for scope lifecycle APIs."""

    async def test_scope_enable_capture_disable(self, radio: IcomRadio) -> None:
        """Enable scope, capture frames, then disable output."""
        if not _flag_enabled("ICOM_ALLOW_SCOPE"):
            pytest.skip("Set ICOM_ALLOW_SCOPE=1 to run scope integration tests")

        try:
            await radio.enable_scope(policy="verify", timeout=8.0)
            frames = await radio.capture_scope_frames(count=2, timeout=10.0)
            assert len(frames) == 2

            f0 = frames[0]
            assert f0.start_freq_hz > 0
            assert f0.end_freq_hz > 0
            assert f0.end_freq_hz >= f0.start_freq_hz

            # Out-of-range scope frames may have no pixels.
            if not f0.out_of_range:
                assert len(f0.pixels) > 0

            print(
                "Scope capture ✓ "
                f"(frames={len(frames)}, pixels0={len(f0.pixels)}, oor={f0.out_of_range})"
            )
        finally:
            try:
                await radio.disable_scope(policy="fast")
            except Exception:
                pass
