"""Extra coverage tests for rigctld/poller.py.

Covers:
- hold_for() with <= 0 and positive values (lines 110-114)
- _run() skips cycle while in hold window (lines 122-123)
- _poll_once() early-exit when write_busy set mid-poll (line 164)
- _poll_once() get_data_mode timeout handling (line 178)
- _maybe_log_stats() periodic emit (lines 198-210)
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from icom_lan.exceptions import (
    TimeoutError as IcomTimeoutError,
)
from icom_lan.rigctld.contract import RigctldConfig
from icom_lan.rigctld.poller import RadioPoller
from icom_lan.rigctld.state_cache import StateCache
from icom_lan.types import Mode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> RigctldConfig:
    return RigctldConfig(poll_interval=0.01)


@pytest.fixture
def cache() -> StateCache:
    return StateCache()


@pytest.fixture
def mock_radio() -> AsyncMock:
    radio = AsyncMock()
    radio.get_freq.return_value = 14_074_000
    radio.get_mode_info.return_value = (Mode.USB, 1)
    radio.get_data_mode.return_value = False
    return radio


@pytest.fixture
def poller(
    mock_radio: AsyncMock, cache: StateCache, config: RigctldConfig
) -> RadioPoller:
    return RadioPoller(mock_radio, cache, config)


# ---------------------------------------------------------------------------
# hold_for() — lines 108-114
# ---------------------------------------------------------------------------


def test_hold_for_zero_does_nothing(poller: RadioPoller) -> None:
    """hold_for(0) must not set _hold_until in the future."""
    before = poller._hold_until
    poller.hold_for(0)
    assert poller._hold_until == before


def test_hold_for_negative_does_nothing(poller: RadioPoller) -> None:
    """hold_for(-1) must not extend _hold_until."""
    before = poller._hold_until
    poller.hold_for(-5.0)
    assert poller._hold_until == before


def test_hold_for_positive_extends_hold_until(poller: RadioPoller) -> None:
    """hold_for(2.0) should set _hold_until approximately 2 s from now."""
    before = time.monotonic()
    poller.hold_for(2.0)
    assert poller._hold_until >= before + 1.9


def test_hold_for_second_call_only_extends_if_longer(poller: RadioPoller) -> None:
    """Shorter hold does not override a longer one already in effect."""
    poller.hold_for(10.0)
    first = poller._hold_until
    poller.hold_for(1.0)
    assert poller._hold_until == first  # unchanged


# ---------------------------------------------------------------------------
# _run() skips cycle during hold window — lines 122-123
# ---------------------------------------------------------------------------


async def test_run_skips_poll_during_hold_window(
    poller: RadioPoller,
    mock_radio: AsyncMock,
) -> None:
    """While in a hold window, poller must not call the radio."""
    poller.hold_for(10.0)  # hold for 10 s
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()
    mock_radio.get_freq.assert_not_awaited()


async def test_run_resumes_polling_after_hold_expires(
    poller: RadioPoller,
    cache: StateCache,
    mock_radio: AsyncMock,
) -> None:
    """Once hold window expires, polling should resume normally."""
    # hold_for with a very short window
    poller._hold_until = time.monotonic() - 0.001  # already expired
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()
    assert cache.is_fresh("freq", 1.0) is True


# ---------------------------------------------------------------------------
# _poll_once() early-exit when write_busy fires mid-poll — line 164
# ---------------------------------------------------------------------------


async def test_poll_once_exits_early_if_write_busy_set_after_freq(
    poller: RadioPoller,
    cache: StateCache,
    mock_radio: AsyncMock,
) -> None:
    """write_busy set between freq and mode polls should skip mode."""

    async def get_freq_and_set_busy() -> int:
        poller.write_busy = True
        return 14_074_000

    mock_radio.get_freq.side_effect = get_freq_and_set_busy
    await poller._poll_once()
    # Mode should not be polled because write_busy was set mid-poll
    mock_radio.get_mode_info.assert_not_awaited()


# ---------------------------------------------------------------------------
# _poll_once() get_data_mode timeout — line 178
# ---------------------------------------------------------------------------


async def test_poll_once_data_mode_timeout_does_not_crash(
    poller: RadioPoller,
    mock_radio: AsyncMock,
) -> None:
    """get_data_mode timeout in poll cycle should be logged and not crash."""
    mock_radio.get_data_mode.side_effect = IcomTimeoutError("timeout")
    # Should not raise
    await poller._poll_once()
    # get_mode_info should have been called (timeout only on get_data_mode)
    mock_radio.get_mode_info.assert_awaited()


async def test_poll_once_data_mode_connection_error_does_not_crash(
    poller: RadioPoller,
    mock_radio: AsyncMock,
) -> None:
    """ConnectionError on get_data_mode should be logged and not crash."""
    from icom_lan.exceptions import ConnectionError as IcomConnectionError

    mock_radio.get_data_mode.side_effect = IcomConnectionError("lost")
    await poller._poll_once()
    mock_radio.get_mode_info.assert_awaited()


# ---------------------------------------------------------------------------
# _maybe_log_stats() — lines 198-210
# ---------------------------------------------------------------------------


async def test_maybe_log_stats_emits_after_interval(
    poller: RadioPoller,
    mock_radio: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """_maybe_log_stats() should log when interval has elapsed."""
    import logging

    # Back-date the last stats log so the interval has elapsed
    poller._last_stats_log = time.monotonic() - 100.0
    mock_radio.civ_stats = MagicMock(return_value={"active_waiters": 0})

    with caplog.at_level(logging.INFO, logger="icom_lan.rigctld.poller"):
        poller._maybe_log_stats()

    assert any("RadioPoller stats" in r.message for r in caplog.records)


def test_maybe_log_stats_does_not_emit_before_interval(
    poller: RadioPoller,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """_maybe_log_stats() must be silent when interval has NOT elapsed."""
    import logging

    # Set last log to now so interval has NOT elapsed
    poller._last_stats_log = time.monotonic()

    with caplog.at_level(logging.INFO, logger="icom_lan.rigctld.poller"):
        poller._maybe_log_stats()

    assert not any("RadioPoller stats" in r.message for r in caplog.records)


async def test_maybe_log_stats_with_civ_stats(
    poller: RadioPoller,
    mock_radio: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """_maybe_log_stats() should include civ_stats if available."""
    import logging

    mock_radio.civ_stats = MagicMock(
        return_value={"active_waiters": 0, "stale_cleaned": 0}
    )
    poller._last_stats_log = time.monotonic() - 100.0

    with caplog.at_level(logging.INFO, logger="icom_lan.rigctld.poller"):
        poller._maybe_log_stats()

    assert any("RadioPoller stats" in r.message for r in caplog.records)


async def test_maybe_log_stats_with_circuit_breaker(
    cache: StateCache,
    config: RigctldConfig,
    mock_radio: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """_maybe_log_stats() should include circuit breaker state."""
    import logging
    from icom_lan.rigctld.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker()
    p = RadioPoller(mock_radio, cache, config, circuit_breaker=cb)
    p._last_stats_log = time.monotonic() - 100.0
    mock_radio.civ_stats = MagicMock(return_value={"active_waiters": 0})

    with caplog.at_level(logging.INFO, logger="icom_lan.rigctld.poller"):
        p._maybe_log_stats()

    assert any("RadioPoller stats" in r.message for r in caplog.records)
