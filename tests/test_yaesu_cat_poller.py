"""Tests for YaesuCatPoller."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from icom_lan.backends.yaesu_cat.poller import YaesuCatPoller
from icom_lan.radio_state import RadioState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_radio(
    *,
    s_meter_main: int = 100,
    s_meter_sub: int = 50,
    freq_main: int = 14_074_000,
    freq_sub: int = 7_074_000,
    mode_main: tuple = ("USB", None),
    mode_sub: tuple = ("LSB", None),
    ptt: bool = False,
    agc: int = 2,
    af_level: int = 128,
    rf_gain: int = 200,
    squelch: int = 0,
) -> MagicMock:
    """Return a mock YaesuCatRadio with sensible defaults."""
    radio = MagicMock()
    radio.radio_state = RadioState()

    radio.get_s_meter = AsyncMock(side_effect=lambda r=0: s_meter_main if r == 0 else s_meter_sub)
    radio.get_freq = AsyncMock(side_effect=lambda r=0: freq_main if r == 0 else freq_sub)
    radio.get_mode = AsyncMock(side_effect=lambda r=0: mode_main if r == 0 else mode_sub)
    radio.get_ptt = AsyncMock(return_value=ptt)
    radio.get_agc = AsyncMock(return_value=agc)
    radio.get_af_level = AsyncMock(return_value=af_level)
    radio.get_rf_gain = AsyncMock(return_value=rf_gain)
    radio.get_squelch = AsyncMock(return_value=squelch)
    return radio


# ---------------------------------------------------------------------------
# Start / stop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_creates_tasks() -> None:
    radio = make_radio()
    calls: list[RadioState] = []
    poller = YaesuCatPoller(radio, callback=calls.append, fast_interval=0.01)

    await poller.start()
    assert poller.running
    assert len(poller._tasks) == 3

    await poller.stop()
    assert not poller.running
    assert poller._tasks == []


@pytest.mark.asyncio
async def test_start_is_idempotent() -> None:
    radio = make_radio()
    poller = YaesuCatPoller(radio, callback=lambda s: None, fast_interval=0.01)

    await poller.start()
    tasks_first = list(poller._tasks)
    await poller.start()  # second call — no-op
    assert poller._tasks is tasks_first or poller._tasks == tasks_first

    await poller.stop()


@pytest.mark.asyncio
async def test_stop_cancels_tasks() -> None:
    radio = make_radio()
    poller = YaesuCatPoller(radio, callback=lambda s: None, fast_interval=10.0)

    await poller.start()
    await poller.stop()

    assert not poller.running


# ---------------------------------------------------------------------------
# Callback invocation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fast_poll_invokes_callback() -> None:
    radio = make_radio(s_meter_main=120)
    calls: list[RadioState] = []

    poller = YaesuCatPoller(
        radio,
        callback=calls.append,
        fast_interval=0.01,
        medium_interval=10.0,
        slow_interval=10.0,
        ema_alpha=1.0,  # no smoothing so raw == smoothed
    )
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()

    assert len(calls) >= 1
    # Callback receives the RadioState object
    assert isinstance(calls[0], RadioState)


@pytest.mark.asyncio
async def test_medium_poll_invokes_callback() -> None:
    radio = make_radio()
    calls: list[RadioState] = []

    poller = YaesuCatPoller(
        radio,
        callback=calls.append,
        fast_interval=10.0,
        medium_interval=0.01,
        slow_interval=10.0,
    )
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()

    assert len(calls) >= 1


@pytest.mark.asyncio
async def test_slow_poll_invokes_callback() -> None:
    radio = make_radio()
    calls: list[RadioState] = []

    poller = YaesuCatPoller(
        radio,
        callback=calls.append,
        fast_interval=10.0,
        medium_interval=10.0,
        slow_interval=0.01,
    )
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()

    assert len(calls) >= 1


# ---------------------------------------------------------------------------
# State updates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fast_poll_updates_s_meter() -> None:
    radio = make_radio(s_meter_main=150, s_meter_sub=75)

    poller = YaesuCatPoller(
        radio,
        callback=lambda s: None,
        fast_interval=0.01,
        medium_interval=10.0,
        slow_interval=10.0,
        ema_alpha=1.0,  # raw pass-through
    )
    await poller.start()
    await asyncio.sleep(0.03)
    await poller.stop()

    assert radio.radio_state.main.s_meter == 150
    assert radio.radio_state.sub.s_meter == 75


@pytest.mark.asyncio
async def test_medium_poll_updates_freq_mode_ptt() -> None:
    radio = make_radio(freq_main=14_074_000, ptt=True)

    poller = YaesuCatPoller(
        radio,
        callback=lambda s: None,
        fast_interval=10.0,
        medium_interval=0.01,
        slow_interval=10.0,
    )
    await poller.start()
    await asyncio.sleep(0.03)
    await poller.stop()

    radio.get_freq.assert_called()
    radio.get_mode.assert_called()
    radio.get_ptt.assert_called()


@pytest.mark.asyncio
async def test_slow_poll_updates_agc_and_levels() -> None:
    radio = make_radio(agc=3, af_level=200, rf_gain=180, squelch=20)

    poller = YaesuCatPoller(
        radio,
        callback=lambda s: None,
        fast_interval=10.0,
        medium_interval=10.0,
        slow_interval=0.01,
    )
    await poller.start()
    await asyncio.sleep(0.03)
    await poller.stop()

    assert radio.radio_state.main.agc == 3
    assert radio.radio_state.main.af_level == 200
    assert radio.radio_state.main.rf_gain == 180
    assert radio.radio_state.main.squelch == 20


# ---------------------------------------------------------------------------
# EMA smoothing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ema_smoothing_applied() -> None:
    """With alpha=0.5 two identical samples should converge to the value."""
    radio = make_radio(s_meter_main=100)
    states: list[RadioState] = []

    poller = YaesuCatPoller(
        radio,
        callback=states.append,
        fast_interval=0.005,
        medium_interval=10.0,
        slow_interval=10.0,
        ema_alpha=0.5,
    )
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()

    # After several samples of 100, EMA should converge to 100.
    assert states, "No callbacks received"
    final = states[-1].main.s_meter
    assert 90 <= final <= 110, f"EMA didn't converge: {final}"


@pytest.mark.asyncio
async def test_ema_zero_alpha_no_smoothing() -> None:
    """alpha=0 means EMA always returns the first sample."""
    radio = make_radio(s_meter_main=77)
    states: list[RadioState] = []

    poller = YaesuCatPoller(
        radio,
        callback=states.append,
        fast_interval=0.005,
        medium_interval=10.0,
        slow_interval=10.0,
        ema_alpha=0,
    )
    await poller.start()
    await asyncio.sleep(0.03)
    await poller.stop()

    # alpha=0: formula returns float(raw) on first call, then 0*raw + 1*prev = prev
    # but first call always returns float(raw) = 77
    assert states[0].main.s_meter == 77


# ---------------------------------------------------------------------------
# Pause / resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_stops_callbacks() -> None:
    radio = make_radio()
    calls: list[RadioState] = []

    poller = YaesuCatPoller(
        radio,
        callback=calls.append,
        fast_interval=0.01,
        medium_interval=10.0,
        slow_interval=10.0,
    )
    await poller.start()
    await asyncio.sleep(0.03)

    before = len(calls)
    await poller.pause()
    await asyncio.sleep(0.05)
    after = len(calls)

    # At most one in-flight request completes after pause().
    assert after - before <= 1

    await poller.stop()


@pytest.mark.asyncio
async def test_resume_restarts_callbacks() -> None:
    radio = make_radio()
    calls: list[RadioState] = []

    poller = YaesuCatPoller(
        radio,
        callback=calls.append,
        fast_interval=0.01,
        medium_interval=10.0,
        slow_interval=10.0,
    )
    await poller.start()
    await poller.pause()
    await asyncio.sleep(0.03)

    before = len(calls)
    await poller.resume()
    await asyncio.sleep(0.05)
    after = len(calls)

    assert after > before

    await poller.stop()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fast_poll_continues_after_error() -> None:
    """A transient get_s_meter error must not crash the poller."""
    call_count = 0

    async def flaky_s_meter(receiver: int = 0) -> int:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise RuntimeError("timeout")
        return 100

    radio = make_radio()
    radio.get_s_meter = AsyncMock(side_effect=flaky_s_meter)

    calls: list[RadioState] = []
    poller = YaesuCatPoller(
        radio,
        callback=calls.append,
        fast_interval=0.01,
        medium_interval=10.0,
        slow_interval=10.0,
        ema_alpha=1.0,
    )
    await poller.start()
    await asyncio.sleep(0.08)
    await poller.stop()

    # Should have recovered and fired callbacks after early errors.
    assert len(calls) >= 1


@pytest.mark.asyncio
async def test_sub_receiver_unavailable_does_not_crash() -> None:
    """If sub S-meter raises, main polling must still work."""
    radio = make_radio()

    async def s_meter_side_effect(receiver: int = 0) -> int:
        if receiver == 1:
            raise RuntimeError("sub not supported")
        return 80

    radio.get_s_meter = AsyncMock(side_effect=s_meter_side_effect)

    calls: list[RadioState] = []
    poller = YaesuCatPoller(
        radio,
        callback=calls.append,
        fast_interval=0.01,
        medium_interval=10.0,
        slow_interval=10.0,
        ema_alpha=1.0,
    )
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()

    assert len(calls) >= 1
    assert calls[-1].main.s_meter == 80


@pytest.mark.asyncio
async def test_slow_poll_continues_after_partial_error() -> None:
    """Even if get_agc raises, the remaining slow-poll commands run."""
    radio = make_radio(af_level=99)
    radio.get_agc = AsyncMock(side_effect=RuntimeError("agc error"))

    calls: list[RadioState] = []
    poller = YaesuCatPoller(
        radio,
        callback=calls.append,
        fast_interval=10.0,
        medium_interval=10.0,
        slow_interval=0.01,
    )
    await poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()

    # get_af_level should still have run.
    radio.get_af_level.assert_called()
    assert calls[-1].main.af_level == 99


# ---------------------------------------------------------------------------
# Polling rates (rough verification)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fast_polls_more_than_slow() -> None:
    """Fast loop should fire at least 3× more often than slow."""
    radio = make_radio()
    fast_count = 0
    slow_count = 0

    original_fast = radio.get_s_meter

    async def count_fast(receiver: int = 0) -> int:
        nonlocal fast_count
        if receiver == 0:
            fast_count += 1
        return 0

    async def count_slow(receiver: int = 0) -> int:
        nonlocal slow_count
        slow_count += 1
        return 0

    radio.get_s_meter = AsyncMock(side_effect=count_fast)
    radio.get_agc = AsyncMock(side_effect=count_slow)

    poller = YaesuCatPoller(
        radio,
        callback=lambda s: None,
        fast_interval=0.02,
        medium_interval=10.0,
        slow_interval=0.1,
    )
    await poller.start()
    await asyncio.sleep(0.25)
    await poller.stop()

    assert fast_count > 0
    assert slow_count > 0
    assert fast_count >= slow_count * 3, (
        f"fast={fast_count} should be >= 3×slow={slow_count}"
    )
