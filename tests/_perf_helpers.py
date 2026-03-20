"""Shared test performance helpers — speed up radio handshake sleeps."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

_real_sleep = asyncio.sleep


async def _fast_sleep(delay: float, *args, **kwargs):  # type: ignore[no-untyped-def]
    """Replace asyncio.sleep, skipping the 0.3s handshake pauses in _control_phase."""
    if delay == 0.3:
        return
    return await _real_sleep(delay, *args, **kwargs)


def fast_connect():  # noqa: D103
    """Context manager that patches out 0.3s handshake sleeps for faster connect()."""
    return patch("asyncio.sleep", _fast_sleep)
