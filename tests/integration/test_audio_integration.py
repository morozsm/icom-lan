"""Integration tests for audio streaming with real Icom radio.

Audio RX tests are safe (no transmission).
Audio TX tests are skipped by default (require antenna/dummy load).

Run with: pytest -m integration tests/integration/test_audio_integration.py

By default, RX tests require at least one audio packet to prove the stream works.
Override with ICOM_AUDIO_REQUIRE_PACKETS=0 if you only want start/stop smoke.
"""

from __future__ import annotations

import asyncio
import os
from typing import List

import pytest

from icom_lan import IcomRadio
from icom_lan.audio import AudioPacket


pytestmark = pytest.mark.integration


class TestAudioRx:
    """Audio receive tests (safe, no transmission)."""

    @staticmethod
    async def _run_rx_window(radio: IcomRadio, seconds: float = 2.0) -> list[AudioPacket]:
        packets: List[AudioPacket] = []

        def on_audio(pkt: AudioPacket) -> None:
            # Jitter buffer can emit None placeholders for gaps.
            if pkt is not None:
                packets.append(pkt)

        await radio.start_audio_rx(on_audio)
        await asyncio.sleep(seconds)
        await radio.stop_audio_rx()
        return packets

    @staticmethod
    def _require_packets() -> bool:
        return os.environ.get("ICOM_AUDIO_REQUIRE_PACKETS", "1") != "0"

    async def test_start_stop_audio_rx(self, radio: IcomRadio) -> None:
        """Start/stop RX and verify packet sanity."""
        packets = await self._run_rx_window(radio, seconds=2.0)

        print(f"Received {len(packets)} audio packets")

        if self._require_packets():
            assert packets, (
                "No audio packets received. "
                "Check radio audio settings/monitor and LAN audio availability. "
                "Set ICOM_AUDIO_REQUIRE_PACKETS=0 to run smoke-only."
            )

        # If packets exist, validate basic structure.
        if packets:
            first = packets[0]
            assert isinstance(first.ident, int)
            assert isinstance(first.send_seq, int)
            assert isinstance(first.data, bytes)
            assert len(first.data) > 0

    async def test_audio_rx_restart_cycle(self, radio: IcomRadio) -> None:
        """RX can be started/stopped repeatedly on one connection."""
        first = await self._run_rx_window(radio, seconds=1.5)
        second = await self._run_rx_window(radio, seconds=1.5)

        print(f"Cycle #1 packets: {len(first)}, cycle #2 packets: {len(second)}")

        if self._require_packets():
            assert first, "First RX cycle produced no audio packets"
            assert second, "Second RX cycle produced no audio packets"


class TestAudioTx:
    """Audio TX tests (requires antenna/dummy load)."""

    async def test_push_audio_tx(self, radio: IcomRadio) -> None:
        """Push several TX audio payload frames."""
        await radio.start_audio_tx()
        try:
            payloads = [
                b"\xf8\xff\xfe",  # tiny synthetic opus-like payload
                b"\xf8\x11\x22\x33\x44",
                b"\xf8" + bytes(range(1, 20)),
            ]
            sent = 0
            for p in payloads:
                await radio.push_audio_tx(p)
                sent += 1
                await asyncio.sleep(0.03)

            print(f"Audio TX payloads sent: {sent} ✓")
        finally:
            await radio.stop_audio_tx()

    async def test_start_stop_audio_full_duplex(self, radio: IcomRadio) -> None:
        """Start/stop full-duplex audio orchestration API."""
        packets: List[AudioPacket] = []

        def on_audio(pkt: AudioPacket) -> None:
            if pkt is not None:
                packets.append(pkt)

        await radio.start_audio(on_audio, tx_enabled=True)
        try:
            # Push a few TX frames while RX is active.
            for p in (b"\xf8\x01\x02", b"\xf8\x03\x04\x05", b"\xf8\x06"):
                await radio.push_audio_tx(p)
                await asyncio.sleep(0.05)
            await asyncio.sleep(1.0)
        finally:
            await radio.stop_audio()

        print(f"Full-duplex audio ✓ (rx_packets={len(packets)})")


class TestAudioSampleRate:
    """Sample rate configuration tests."""

    async def test_default_sample_rate(self, radio: IcomRadio) -> None:
        """Default sample rate should be 48000."""
        assert radio.audio_sample_rate == 48000
        print(f"Sample rate: {radio.audio_sample_rate} Hz ✓")

    async def test_custom_sample_rate(self, radio_config: dict) -> None:
        """Custom sample rate configuration."""
        radio = IcomRadio(**radio_config, audio_sample_rate=24000)
        await radio.connect()

        try:
            assert radio.audio_sample_rate == 24000
            print(f"Custom sample rate: {radio.audio_sample_rate} Hz ✓")
        finally:
            await radio.disconnect()
