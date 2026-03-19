"""Stress tests for audio pipeline: high-frequency RX with slow consumer, clean teardown.

- Feed many RX audio frames with a slow consumer (blocking delay in callback).
- Run for a bounded duration; assert jitter buffer / queue does not grow without bound.
- After stop_rx(), assert background task is cancelled and no lingering work.
Uses mock transport and controlled frame source; no real hardware.
"""

from __future__ import annotations

import asyncio
import struct
import time
from unittest.mock import AsyncMock

import pytest

from icom_lan.audio import (
    AUDIO_HEADER_SIZE,
    AudioStream,
    AudioState,
)
from icom_lan.types import PacketType

# Match test_audio.py
SENDER_ID = 0xAABBCCDD
RECEIVER_ID = 0x11223344


def _make_audio_bytes(
    opus_data: bytes,
    *,
    ident: int = 0x9781,
    send_seq: int = 0,
    sender_id: int = SENDER_ID,
    receiver_id: int = RECEIVER_ID,
    pkt_type: int = PacketType.DATA,
) -> bytes:
    total = AUDIO_HEADER_SIZE + len(opus_data)
    pkt = bytearray(total)
    struct.pack_into("<I", pkt, 0x00, total)
    struct.pack_into("<H", pkt, 0x04, pkt_type)
    struct.pack_into("<H", pkt, 0x06, 0)
    struct.pack_into("<I", pkt, 0x08, sender_id)
    struct.pack_into("<I", pkt, 0x0C, receiver_id)
    struct.pack_into("<H", pkt, 0x10, ident)
    struct.pack_into(">H", pkt, 0x12, send_seq)
    struct.pack_into(">H", pkt, 0x16, len(opus_data))
    pkt[AUDIO_HEADER_SIZE:] = opus_data
    return bytes(pkt)


def _make_audio_packet_queue(count: int) -> list[bytes]:
    """Build `count` raw UDP audio packets (seq 0..count-1)."""
    return [_make_audio_bytes(bytes([i % 256] * 160), send_seq=i) for i in range(count)]


class QueuedAudioTransport:
    """Mock transport that returns queued audio packets from receive_packet, then timeouts."""

    def __init__(self, packets: list[bytes]) -> None:
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        for p in packets:
            self._queue.put_nowait(p)
        self.my_id = SENDER_ID
        self.remote_id = RECEIVER_ID
        self.send_tracked = AsyncMock()

    async def receive_packet(self, timeout: float = 5.0) -> bytes:
        return await asyncio.wait_for(self._queue.get(), timeout=timeout)

    async def connect(self, host: str, port: int) -> None:
        pass

    async def disconnect(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Audio RX stress: high packet rate, slow consumer, jitter buffer bounded
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.asyncio
async def test_audio_stress_slow_consumer_jitter_bounded() -> None:
    """High-frequency RX packets with slow consumer; jitter buffer pending must not grow unbounded."""
    num_packets = 400
    slow_delay_s = 0.02
    run_duration_s = 3.0
    jitter_depth = 5
    # JitterBuffer caps at depth * 4
    max_pending_cap = jitter_depth * 4

    packets = _make_audio_packet_queue(num_packets)
    transport = QueuedAudioTransport(packets)
    stream = AudioStream(transport, jitter_depth=jitter_depth)

    received: list = []
    max_pending_seen = 0

    def slow_callback(pkt: object) -> None:
        nonlocal max_pending_seen
        received.append(pkt)
        stats = stream.get_audio_stats()
        pending = stats.get("jitter_buffer_pending_packets", 0)
        if pending > max_pending_seen:
            max_pending_seen = pending
        time.sleep(slow_delay_s)

    await stream.start_rx(slow_callback)
    try:
        await asyncio.sleep(run_duration_s)
    finally:
        await stream.stop_rx()

    assert max_pending_seen <= max_pending_cap, (
        f"Jitter buffer pending grew beyond cap: max_seen={max_pending_seen}, cap={max_pending_cap}"
    )
    assert len(received) >= 1


@pytest.mark.asyncio
async def test_audio_stress_clean_teardown_no_lingering_tasks() -> None:
    """After stop_rx(), RX task is cancelled and no lingering background work."""
    packets = _make_audio_packet_queue(200)
    transport = QueuedAudioTransport(packets)
    stream = AudioStream(transport, jitter_depth=5)

    received: list = []
    await stream.start_rx(lambda pkt: received.append(pkt))

    await asyncio.sleep(0.5)
    await stream.stop_rx()
    await asyncio.sleep(0.2)

    assert stream._rx_task is None
    assert stream.state == AudioState.IDLE
