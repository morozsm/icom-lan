from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


def log_event(
    *,
    test: str,
    step: str,
    cmd: str | None = None,
    attempt: int | None = None,
    timeout: bool | None = None,
    recovered: bool | None = None,
    duration_ms: int | None = None,
    **extra: Any,
) -> None:
    """Emit standardized JSONL integration event.

    Canonical fields:
    - test, step, cmd, attempt, timeout, recovered, duration_ms
    """
    payload: dict[str, Any] = {"test": test, "step": step}
    if cmd is not None:
        payload["cmd"] = cmd
    if attempt is not None:
        payload["attempt"] = attempt
    if timeout is not None:
        payload["timeout"] = timeout
    if recovered is not None:
        payload["recovered"] = recovered
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False))


async def timed_call(name: str, fn: Callable[[], Awaitable[T]]) -> tuple[T, int]:
    """Execute async callable and return (result, duration_ms)."""
    t0 = time.monotonic()
    out = await fn()
    dt = int((time.monotonic() - t0) * 1000)
    return out, dt
