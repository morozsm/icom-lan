from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import TypeVar

from .exceptions import ConnectionError
from .types import CivFrame


class Priority(IntEnum):
    IMMEDIATE = 0
    NORMAL = 10
    BACKGROUND = 20


T = TypeVar("T")


@dataclass(slots=True)
class _QueueItem:
    priority: int
    seq: int
    payload: bytes
    future: asyncio.Future[CivFrame]
    key: str | None = None


class IcomCommander:
    """wfview-style serialized command executor with priorities.

    Features:
    - strict in-order execution within priority levels
    - configurable pacing between commands
    - optional dedup for background polling keys
    - transaction helper (snapshot/restore)
    """

    def __init__(
        self,
        execute: Callable[[bytes], Awaitable[CivFrame]],
        *,
        min_interval: float = 0.035,
    ) -> None:
        self._execute = execute
        self._min_interval = min_interval
        self._queue: asyncio.PriorityQueue[tuple[int, int, _QueueItem]] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._seq = 0
        self._last_send = 0.0
        self._pending_by_key: dict[str, asyncio.Future[CivFrame]] = {}

    def start(self) -> None:
        if self._worker is None or self._worker.done():
            self._queue = asyncio.PriorityQueue()
            self._worker = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._queue is not None:
            while True:
                try:
                    _, _, item = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if item.key is not None:
                    self._pending_by_key.pop(item.key, None)
                if not item.future.done():
                    item.future.set_exception(ConnectionError("Commander stopped"))
                self._queue.task_done()

        if self._worker is not None and not self._worker.done():
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass

        self._worker = None
        self._queue = None
        self._pending_by_key.clear()

    async def send(
        self,
        payload: bytes,
        *,
        priority: Priority = Priority.NORMAL,
        key: str | None = None,
        dedupe: bool = False,
        timeout: float | None = None,
    ) -> CivFrame:
        if self._queue is None or self._worker is None:
            raise ConnectionError("Commander is not started")

        if dedupe and key is not None:
            existing = self._pending_by_key.get(key)
            if existing is not None and not existing.done():
                if timeout is not None:
                    return await asyncio.wait_for(existing, timeout=timeout)
                return await existing

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[CivFrame] = loop.create_future()
        self._seq += 1
        item = _QueueItem(int(priority), self._seq, payload, fut, key=key)

        if key is not None:
            self._pending_by_key[key] = fut

        await self._queue.put((item.priority, item.seq, item))

        if timeout is not None:
            return await asyncio.wait_for(fut, timeout=timeout)
        return await fut

    async def transaction(
        self,
        *,
        snapshot: Callable[[], Awaitable[T]],
        restore: Callable[[T], Awaitable[None]],
        body: Callable[[], Awaitable[T]],
    ) -> T:
        state = await snapshot()
        try:
            return await body()
        finally:
            await restore(state)

    async def _loop(self) -> None:
        assert self._queue is not None
        try:
            while True:
                _, _, item = await self._queue.get()
                try:
                    now = asyncio.get_running_loop().time()
                    delta = now - self._last_send
                    if delta < self._min_interval:
                        await asyncio.sleep(self._min_interval - delta)

                    resp = await self._execute(item.payload)
                    self._last_send = asyncio.get_running_loop().time()
                    if not item.future.done():
                        item.future.set_result(resp)
                except Exception as exc:
                    if not item.future.done():
                        item.future.set_exception(exc)
                finally:
                    if item.key is not None and self._pending_by_key.get(item.key) is item.future:
                        self._pending_by_key.pop(item.key, None)
                    self._queue.task_done()
        except asyncio.CancelledError:
            pass
