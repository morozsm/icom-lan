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
@pytest.mark.xfail(
    reason="Flaky under OpenClaw exec (intermittent SIGTERM)", strict=False
)
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
async def test_cancel_pending_send_does_not_break_pipeline() -> None:
    """Cancelling a caller's send() must not kill the commander loop.

    This is the core bug from issue #27: asyncio.wait_for() in the server
    cancels a pending send(), which without shield() would propagate into
    _loop() and kill the CI-V pipeline.
    """
    call_count = 0

    async def execute(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

    c = IcomCommander(execute, min_interval=0.0)
    c.start()
    try:
        # Start a send and cancel it mid-flight (simulates client disconnect)
        task = asyncio.create_task(c.send(b"will-cancel"))
        await asyncio.sleep(0.01)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # The next command must still work — pipeline not broken
        resp = await asyncio.wait_for(c.send(b"after-cancel"), timeout=2.0)
        assert resp is not None
        assert call_count == 2
    finally:
        await c.stop()


@pytest.mark.asyncio
async def test_rapid_cancel_cycles() -> None:
    """Simulate rapid connect/disconnect: cancel multiple sends, then verify recovery."""

    async def execute(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
        await asyncio.sleep(0.02)
        return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

    c = IcomCommander(execute, min_interval=0.0)
    c.start()
    try:
        # 5 rapid cancel cycles
        for _ in range(5):
            task = asyncio.create_task(c.send(b"cancel-me"))
            await asyncio.sleep(0.005)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Pipeline must still work
        resp = await asyncio.wait_for(c.send(b"final"), timeout=2.0)
        assert resp is not None
    finally:
        await c.stop()


@pytest.mark.asyncio
async def test_already_cancelled_future_skipped() -> None:
    """If a future is cancelled before _loop gets to it, skip execution."""
    executed: list[bytes] = []

    async def execute(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
        executed.append(cmd)
        return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

    c = IcomCommander(execute, min_interval=0.0)
    c.start()
    try:
        # Block the loop with a slow command
        async def slow_exec(cmd: bytes, wait_response: bool = True) -> CivFrame | None:
            executed.append(cmd)
            await asyncio.sleep(0.1)
            return CivFrame(to_addr=0xE0, from_addr=0x98, command=0xFB, sub=None, data=b"")

        c._execute = slow_exec  # type: ignore[assignment]

        blocker = asyncio.create_task(c.send(b"blocker"))
        await asyncio.sleep(0.01)

        # Queue a command and cancel before it's processed
        queued = asyncio.create_task(c.send(b"pre-cancelled"))
        await asyncio.sleep(0.001)
        queued.cancel()

        await blocker  # let blocker finish

        # Restore fast executor
        c._execute = execute  # type: ignore[assignment]

        resp = await asyncio.wait_for(c.send(b"after"), timeout=2.0)
        assert resp is not None
        # "pre-cancelled" should have been skipped
        assert b"pre-cancelled" not in executed
    finally:
        await c.stop()
