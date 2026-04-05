"""Shared test performance helpers — speed up radio handshake sleeps."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

_real_sleep = asyncio.sleep


async def _fast_sleep(delay: float, *args, **kwargs):  # type: ignore[no-untyped-def]
    """Replace asyncio.sleep, skipping the 0.3s handshake pauses in _control_phase."""
    if delay == 0.3:
        return
    return await _real_sleep(delay, *args, **kwargs)


@contextmanager
def fast_connect():  # noqa: D103
    """Context manager that patches out 0.3s handshake sleeps and startup readiness
    check for mock integration tests.

    MockIcomRadio sends an unsolicited CI-V frame on OpenClose(open) to trigger
    _civ_stream_ready, but the timing is not always reliable under asyncio test
    conditions.  Patching wait_for_radio_startup_ready ensures we never hang 5s
    waiting for radio_ready when the CI-V frame is processed slightly too late.
    """
    with patch("asyncio.sleep", _fast_sleep), \
         patch("icom_lan._control_phase.wait_for_radio_startup_ready", new=AsyncMock()):
        yield
