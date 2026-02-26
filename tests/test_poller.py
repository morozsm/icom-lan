"""Tests for RadioPoller — lifecycle, cache updates, error resilience."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from icom_lan.exceptions import (
    ConnectionError as IcomConnectionError,
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
    # Very short poll interval so tests run quickly.
    return RigctldConfig(poll_interval=0.01)


@pytest.fixture
def cache() -> StateCache:
    return StateCache()


@pytest.fixture
def mock_radio() -> AsyncMock:
    radio = AsyncMock()
    radio.get_frequency.return_value = 14_074_000
    radio.get_mode_info.return_value = (Mode.USB, 1)
    return radio


@pytest.fixture
def poller(mock_radio: AsyncMock, cache: StateCache, config: RigctldConfig) -> RadioPoller:
    return RadioPoller(mock_radio, cache, config)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

async def test_start_creates_task(poller: RadioPoller) -> None:
    await poller.start()
    assert poller._task is not None
    await poller.stop()


async def test_stop_clears_task(poller: RadioPoller) -> None:
    await poller.start()
    await poller.stop()
    assert poller._task is None


async def test_start_is_idempotent(poller: RadioPoller) -> None:
    await poller.start()
    task_first = poller._task
    await poller.start()  # second call should be a no-op
    assert poller._task is task_first
    await poller.stop()


async def test_stop_before_start_is_safe(poller: RadioPoller) -> None:
    # Calling stop() before start() must not raise.
    await poller.stop()
    assert poller._task is None


async def test_double_stop_is_safe(poller: RadioPoller) -> None:
    await poller.start()
    await poller.stop()
    await poller.stop()  # second stop must not raise


# ---------------------------------------------------------------------------
# Cache updates
# ---------------------------------------------------------------------------

async def test_poll_updates_freq_in_cache(
    poller: RadioPoller,
    cache: StateCache,
    mock_radio: AsyncMock,
) -> None:
    mock_radio.get_frequency.return_value = 7_050_000
    await poller.start()
    # Wait long enough for at least one poll cycle.
    await asyncio.sleep(0.05)
    await poller.stop()
    assert cache.freq == 7_050_000
    assert cache.is_fresh("freq", 1.0) is True


async def test_poll_updates_mode_in_cache(
    poller: RadioPoller,
    cache: StateCache,
    mock_radio: AsyncMock,
) -> None:
    mock_radio.get_mode_info.return_value = (Mode.CW, 3)
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()
    assert cache.mode == "CW"
    assert cache.filter_width == 3
    assert cache.is_fresh("mode", 1.0) is True


async def test_poll_converts_mode_enum_to_hamlib_string(
    poller: RadioPoller,
    cache: StateCache,
    mock_radio: AsyncMock,
) -> None:
    mock_radio.get_mode_info.return_value = (Mode.LSB, None)
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()
    assert cache.mode == "LSB"
    assert cache.filter_width is None


async def test_poll_calls_radio_multiple_times(
    poller: RadioPoller,
    mock_radio: AsyncMock,
) -> None:
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()
    # With interval=0.01s and sleep=0.05s, expect at least 3 cycles.
    assert mock_radio.get_frequency.await_count >= 3


# ---------------------------------------------------------------------------
# write_busy — skip cycle
# ---------------------------------------------------------------------------

async def test_write_busy_skips_poll(
    poller: RadioPoller,
    mock_radio: AsyncMock,
) -> None:
    poller.write_busy = True
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()
    # Poller should not have called the radio at all while busy.
    mock_radio.get_frequency.assert_not_awaited()


async def test_write_busy_released_resumes_polling(
    poller: RadioPoller,
    cache: StateCache,
    mock_radio: AsyncMock,
) -> None:
    mock_radio.get_frequency.return_value = 14_074_000
    poller.write_busy = True
    await poller.start()
    await asyncio.sleep(0.03)

    # Release the write lock; polling should resume.
    poller.write_busy = False
    await asyncio.sleep(0.05)
    await poller.stop()

    assert cache.is_fresh("freq", 1.0) is True


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------

async def test_timeout_on_get_frequency_does_not_crash(
    poller: RadioPoller,
    mock_radio: AsyncMock,
) -> None:
    mock_radio.get_frequency.side_effect = IcomTimeoutError("timeout")
    await poller.start()
    await asyncio.sleep(0.05)
    # Poller must still be running after timeout errors.
    assert poller._task is not None
    assert not poller._task.done()
    await poller.stop()


async def test_connection_error_on_get_frequency_does_not_crash(
    poller: RadioPoller,
    mock_radio: AsyncMock,
) -> None:
    mock_radio.get_frequency.side_effect = IcomConnectionError("lost")
    await poller.start()
    await asyncio.sleep(0.05)
    assert poller._task is not None
    assert not poller._task.done()
    await poller.stop()


async def test_timeout_on_get_mode_info_does_not_crash(
    poller: RadioPoller,
    mock_radio: AsyncMock,
) -> None:
    mock_radio.get_mode_info.side_effect = IcomTimeoutError("timeout")
    await poller.start()
    await asyncio.sleep(0.05)
    assert poller._task is not None
    assert not poller._task.done()
    await poller.stop()


async def test_connection_error_on_get_mode_info_does_not_crash(
    poller: RadioPoller,
    mock_radio: AsyncMock,
) -> None:
    mock_radio.get_mode_info.side_effect = IcomConnectionError("lost")
    await poller.start()
    await asyncio.sleep(0.05)
    assert poller._task is not None
    assert not poller._task.done()
    await poller.stop()


async def test_freq_error_does_not_prevent_mode_poll(
    poller: RadioPoller,
    cache: StateCache,
    mock_radio: AsyncMock,
) -> None:
    """Even if get_frequency fails, get_mode_info should still be called."""
    mock_radio.get_frequency.side_effect = IcomTimeoutError("timeout")
    mock_radio.get_mode_info.return_value = (Mode.AM, 2)
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()
    assert cache.mode == "AM"
    assert cache.is_fresh("mode", 1.0) is True


async def test_timeout_logs_warning(
    poller: RadioPoller,
    mock_radio: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_radio.get_frequency.side_effect = IcomTimeoutError("timed out")
    import logging
    with caplog.at_level(logging.WARNING, logger="icom_lan.rigctld.poller"):
        await poller.start()
        await asyncio.sleep(0.05)
        await poller.stop()
    assert any("get_frequency" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Stop cancels the background task
# ---------------------------------------------------------------------------

async def test_stop_cancels_running_task(
    poller: RadioPoller,
) -> None:
    await poller.start()
    task = poller._task
    assert task is not None
    await poller.stop()
    assert task.cancelled() or task.done()


async def test_no_more_polls_after_stop(
    poller: RadioPoller,
    mock_radio: AsyncMock,
) -> None:
    await poller.start()
    await asyncio.sleep(0.03)
    await poller.stop()
    count_after_stop = mock_radio.get_frequency.await_count
    # Give a couple more intervals; count must not increase.
    await asyncio.sleep(0.05)
    assert mock_radio.get_frequency.await_count == count_after_stop


# ---------------------------------------------------------------------------
# poll_interval respected
# ---------------------------------------------------------------------------

async def test_poll_interval_is_respected(
    mock_radio: AsyncMock,
    cache: StateCache,
) -> None:
    # Use a longer interval so we can assert exact call count.
    config = RigctldConfig(poll_interval=0.05)
    p = RadioPoller(mock_radio, cache, config)
    await p.start()
    await asyncio.sleep(0.12)  # ~2 cycles at 0.05s
    await p.stop()
    # Expect 2 or 3 calls (timing-dependent but bounded).
    count = mock_radio.get_frequency.await_count
    assert 1 <= count <= 4, f"unexpected call count: {count}"
