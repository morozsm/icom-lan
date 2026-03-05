from __future__ import annotations

import asyncio

import pytest

from icom_lan.commander import IcomCommander, Priority
from icom_lan.exceptions import ConnectionError
from icom_lan.types import CivFrame


@pytest.mark.asyncio
async def test_priority_ordering() -> None:
    order: list[bytes] = []

    async def execute(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
        await asyncio.sleep(0)
        order.append(cmd)
        return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

    c = IcomCommander(execute, min_interval=0.0)
    c.start()
    try:
        t1 = asyncio.create_task(c.send(b"normal-1", priority=Priority.NORMAL))
        t2 = asyncio.create_task(c.send(b"bg-1", priority=Priority.BACKGROUND))
        t3 = asyncio.create_task(c.send(b"immediate-1", priority=Priority.IMMEDIATE))
        await asyncio.gather(t1, t2, t3)
    finally:
        await c.stop()

    assert order == [b"immediate-1", b"normal-1", b"bg-1"]


@pytest.mark.asyncio
async def test_transaction_restores_on_error() -> None:
    async def execute(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
        return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

    c = IcomCommander(execute, min_interval=0.0)
    c.start()

    calls: list[str] = []

    async def snapshot() -> dict[str, int]:
        calls.append("snapshot")
        return {"x": 1}

    async def restore(state: dict[str, int]) -> None:
        assert state == {"x": 1}
        calls.append("restore")

    async def body() -> None:
        calls.append("body")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await c.transaction(snapshot=snapshot, restore=restore, body=body)

    await c.stop()
    assert calls == ["snapshot", "body", "restore"]


@pytest.mark.asyncio
async def test_min_interval_throttling() -> None:
    times: list[float] = []

    async def execute(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
        times.append(asyncio.get_running_loop().time())
        return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

    c = IcomCommander(execute, min_interval=0.03)
    c.start()
    try:
        await c.send(b"a")
        await c.send(b"b")
    finally:
        await c.stop()

    assert len(times) == 2
    assert times[1] - times[0] >= 0.02


@pytest.mark.asyncio
async def test_dedupe_returns_existing_future() -> None:
    count = 0

    async def execute(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
        nonlocal count
        count += 1
        await asyncio.sleep(0.02)
        return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

    c = IcomCommander(execute, min_interval=0.0)
    c.start()
    try:
        t1 = asyncio.create_task(
            c.send(b"poll", priority=Priority.BACKGROUND, key="meter", dedupe=True)
        )
        t2 = asyncio.create_task(
            c.send(b"poll", priority=Priority.BACKGROUND, key="meter", dedupe=True)
        )
        await asyncio.gather(t1, t2)
    finally:
        await c.stop()

    assert count == 1


@pytest.mark.asyncio
async def test_stop_fails_pending() -> None:
    async def execute(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
        await asyncio.sleep(0.5)
        return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

    c = IcomCommander(execute, min_interval=0.0)
    c.start()
    task = asyncio.create_task(c.send(b"long"))
    await asyncio.sleep(0.01)
    await c.stop()
    with pytest.raises(ConnectionError):
        await asyncio.wait_for(task, timeout=0.1)


@pytest.mark.asyncio
async def test_stop_fails_inflight_command() -> None:
    started = asyncio.Event()

    async def execute(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
        started.set()
        await asyncio.sleep(10)
        return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

    c = IcomCommander(execute, min_interval=0.0)
    c.start()
    task = asyncio.create_task(c.send(b"slow"))
    await asyncio.wait_for(started.wait(), timeout=1.0)
    await c.stop()

    with pytest.raises(ConnectionError):
        await asyncio.wait_for(task, timeout=0.2)


@pytest.mark.asyncio
async def test_cancelled_queued_request_is_not_executed() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    seen: list[bytes] = []

    async def execute(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
        seen.append(cmd)
        if cmd == b"block":
            started.set()
            await release.wait()
        return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

    c = IcomCommander(execute, min_interval=0.0)
    c.start()
    try:
        t1 = asyncio.create_task(c.send(b"block"))
        await asyncio.wait_for(started.wait(), timeout=1.0)

        t2 = asyncio.create_task(c.send(b"abandoned"))
        await asyncio.sleep(0.01)  # let request enqueue
        t2.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t2

        release.set()
        await asyncio.wait_for(t1, timeout=0.5)

        # Worker must skip cancelled queued request.
        await asyncio.sleep(0.05)
        assert seen == [b"block"]
    finally:
        await c.stop()
