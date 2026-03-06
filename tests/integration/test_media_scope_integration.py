"""Media and scope integration tests (backlog items 10-11)."""

from __future__ import annotations

import asyncio
import os
from typing import List

import pytest

from icom_lan import IcomRadio
from icom_lan.backends.icom7610 import Icom7610SerialRadio
from icom_lan.exceptions import AudioCodecBackendError, CommandError
pytestmark = pytest.mark.integration


_SERIAL_SCOPE_MIN_BAUD = 115200


def _flag_enabled(name: str) -> bool:
    return os.environ.get(name, "0") == "1"


def _pcm_require_frames() -> bool:
    return os.environ.get("ICOM_PCM_REQUIRE_FRAMES", "1") != "0"


def _serial_scope_enabled() -> bool:
    return _flag_enabled("ICOM_ALLOW_SERIAL_SCOPE") or _flag_enabled("ICOM_ALLOW_SCOPE")


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

    @pytest.mark.ic7610_parity
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


@pytest.mark.serial_integration
class TestSerialScopeIntegration:
    """Integration coverage for serial backend scope lifecycle and guardrails."""

    @pytest.mark.ic7610_parity
    async def test_serial_scope_enable_capture_disable(
        self, serial_radio_config: dict
    ) -> None:
        """Connect serial backend, capture a scope frame, then disable and disconnect."""
        if not _serial_scope_enabled():
            pytest.skip(
                "Set ICOM_ALLOW_SERIAL_SCOPE=1 (or ICOM_ALLOW_SCOPE=1) to run serial scope integration tests"
            )
        baudrate = int(serial_radio_config["baudrate"])
        if baudrate < _SERIAL_SCOPE_MIN_BAUD:
            pytest.skip(
                "Set ICOM_SERIAL_BAUDRATE>=115200 for serial scope lifecycle integration run"
            )

        radio = Icom7610SerialRadio(**serial_radio_config)
        connected = False
        try:
            await radio.connect()
            connected = True
            assert radio.connected is True
            await radio.enable_scope(policy="verify", timeout=10.0)
            frame = await radio.capture_scope_frame(timeout=12.0)
            assert frame.start_freq_hz > 0
            assert frame.end_freq_hz >= frame.start_freq_hz
            if not frame.out_of_range:
                assert len(frame.pixels) > 0
        except ImportError as exc:
            pytest.skip(str(exc))
        finally:
            if connected:
                try:
                    await radio.disable_scope(policy="fast")
                except Exception:
                    pass
                await radio.disconnect()

    @pytest.mark.ic7610_parity
    async def test_serial_scope_low_baud_guardrail_rejects(
        self, serial_radio_config: dict
    ) -> None:
        """Validate low-baud guardrail rejection on real serial backend when configured."""
        baudrate = int(serial_radio_config["baudrate"])
        if baudrate >= _SERIAL_SCOPE_MIN_BAUD:
            pytest.skip(
                "Set ICOM_SERIAL_BAUDRATE below 115200 to validate serial low-baud guardrail"
            )
        if _flag_enabled("ICOM_SERIAL_SCOPE_ALLOW_LOW_BAUD"):
            pytest.skip("Unset ICOM_SERIAL_SCOPE_ALLOW_LOW_BAUD to validate guardrail rejection")

        radio = Icom7610SerialRadio(**serial_radio_config)
        connected = False
        try:
            await radio.connect()
            connected = True
            with pytest.raises(CommandError, match="baudrate"):
                await radio.enable_scope(policy="fast")
        except ImportError as exc:
            pytest.skip(str(exc))
        finally:
            if connected:
                await radio.disconnect()
