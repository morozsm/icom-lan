from __future__ import annotations

import asyncio
import time

import pytest

from icom_lan.civ import (
    CivEvent,
    CivEventType,
    CivRequestKey,
    CivRequestTracker,
)
from icom_lan.types import CivFrame


def _ack_frame() -> CivFrame:
    return CivFrame(
        to_addr=0xE0,
        from_addr=0x98,
        command=0xFB,
        sub=None,
        data=b"",
    )


@pytest.mark.asyncio
async def test_tracker_cleanup_stale_waiters() -> None:
    tracker = CivRequestTracker(stale_ttl=10.0)

    ack_future = tracker.register_ack(wait=True)
    token_or_future = tracker.register_ack(wait=False)
    assert isinstance(token_or_future, int)
    resp_future = tracker.register_response(CivRequestKey(command=0x03, sub=None))
    created = time.monotonic()

    cleaned = tracker.cleanup_stale(now_monotonic=created + 11.0)
    assert cleaned == 3
    assert tracker.pending_count == 0
    assert tracker.stale_cleaned_total == 3
    assert ack_future.done()
    assert isinstance(ack_future.exception(), asyncio.TimeoutError)
    assert resp_future.done()
    assert isinstance(resp_future.exception(), asyncio.TimeoutError)


@pytest.mark.asyncio
async def test_tracker_generation_rejects_old_epoch_responses() -> None:
    tracker = CivRequestTracker()

    pending = tracker.register_ack(wait=True)
    old_gen = tracker.generation
    new_gen = tracker.advance_generation(RuntimeError("reconnect"))
    assert new_gen == old_gen + 1
    assert pending.done()

    event = CivEvent(type=CivEventType.ACK, frame=_ack_frame())
    assert tracker.resolve(event, generation=old_gen) is False

    fresh = tracker.register_ack(wait=True)
    assert tracker.resolve(event, generation=new_gen) is True
    assert fresh.done()
