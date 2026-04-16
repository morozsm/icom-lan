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
    """Context manager that patches slow handshake steps for mock integration tests.

    - 0.3s handshake sleeps in _control_phase → skipped.
    - wait_for_radio_startup_ready → AsyncMock (avoids 5s fallback on flaky mock timing).
    - CoreRadio._fetch_initial_state → AsyncMock. Otherwise connect issues ~290 CI-V GET
      queries with 12ms gaps (~3.5s per connect); tests read state via direct GETs or
      preset mock fields, so the pre-fetch adds no value.
    """
    with patch("asyncio.sleep", _fast_sleep), \
         patch("icom_lan._control_phase.wait_for_radio_startup_ready", new=AsyncMock()), \
         patch("icom_lan.radio.CoreRadio._fetch_initial_state", new=AsyncMock()):
        yield
