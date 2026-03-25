"""YaesuCatPoller — polling scheduler for YaesuCatRadio.

Three polling groups with different intervals share a single serial lock:

- **Fast  (75 ms):**  S-meter (main + sub) for smooth UI animation.
- **Medium (200 ms):** Frequency, mode, PTT — changes at human speed.
- **Slow  (1000 ms):** AGC, AF/RF/squelch levels — rarely change.

Each group runs as an independent asyncio task.  The shared lock prevents
concurrent serial requests so the CAT bus is never overwhelmed.

Usage::

    poller = YaesuCatPoller(radio, callback=on_state_update)
    await poller.start()
    ...
    await poller.pause()
    await poller.resume()
    await poller.stop()
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ...radio_state import RadioState
    from .radio import YaesuCatRadio

__all__ = ["YaesuCatPoller"]

logger = logging.getLogger(__name__)

_FAST_INTERVAL: float = 0.075    # 13.3 Hz
_MEDIUM_INTERVAL: float = 0.200  # 5 Hz
_SLOW_INTERVAL: float = 1.000    # 1 Hz
_EMA_ALPHA: float = 0.3


class YaesuCatPoller:
    """Polling scheduler for :class:`~.radio.YaesuCatRadio`.

    Args:
        radio:           Connected :class:`YaesuCatRadio` instance.
        callback:        Called with the current :class:`RadioState` after
                         every successful poll.
        fast_interval:   Seconds between fast (S-meter) polls.
        medium_interval: Seconds between medium (freq/mode/PTT) polls.
        slow_interval:   Seconds between slow (AGC/levels) polls.
        ema_alpha:       EMA smoothing factor for S-meter (0 = disabled,
                         0.3 = moderate smoothing, 1.0 = no smoothing).
    """

    def __init__(
        self,
        radio: "YaesuCatRadio",
        callback: Callable[["RadioState"], None],
        *,
        fast_interval: float = _FAST_INTERVAL,
        medium_interval: float = _MEDIUM_INTERVAL,
        slow_interval: float = _SLOW_INTERVAL,
        ema_alpha: float = _EMA_ALPHA,
    ) -> None:
        self._radio = radio
        self._callback = callback
        self._fast_interval = fast_interval
        self._medium_interval = medium_interval
        self._slow_interval = slow_interval
        self._ema_alpha = ema_alpha

        # Shared serial access lock — one request in flight at a time.
        self._lock: asyncio.Lock = asyncio.Lock()
        # Clear = paused, set = running.
        self._paused: asyncio.Event = asyncio.Event()
        self._paused.set()

        self._tasks: list[asyncio.Task[None]] = []

        # EMA state per receiver (None until first sample).
        self._ema_s_main: float | None = None
        self._ema_s_sub: float | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start all three polling loops."""
        if self._tasks:
            return
        self._paused.set()
        loop = asyncio.get_running_loop()
        self._tasks = [
            loop.create_task(self._fast_loop(), name="yaesu-poller-fast"),
            loop.create_task(self._medium_loop(), name="yaesu-poller-medium"),
            loop.create_task(self._slow_loop(), name="yaesu-poller-slow"),
        ]
        logger.info("YaesuCatPoller: started")

    async def stop(self) -> None:
        """Cancel all polling loops and wait for them to finish."""
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("YaesuCatPoller: stopped")

    async def pause(self) -> None:
        """Suspend polling.  In-flight requests complete; new ones wait."""
        self._paused.clear()
        logger.debug("YaesuCatPoller: paused")

    async def resume(self) -> None:
        """Resume a paused poller."""
        self._paused.set()
        logger.debug("YaesuCatPoller: resumed")

    @property
    def running(self) -> bool:
        """True if any polling task is alive."""
        return bool(self._tasks) and any(not t.done() for t in self._tasks)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_ema(self, raw: int, prev: float | None) -> float:
        """Apply exponential moving average smoothing to a meter sample."""
        if prev is None or self._ema_alpha <= 0:
            return float(raw)
        return self._ema_alpha * raw + (1.0 - self._ema_alpha) * prev

    # ------------------------------------------------------------------
    # Polling loops
    # ------------------------------------------------------------------

    async def _fast_loop(self) -> None:
        while True:
            await self._paused.wait()
            try:
                async with self._lock:
                    await self._poll_fast()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("YaesuCatPoller: fast poll error", exc_info=True)
            await asyncio.sleep(self._fast_interval)

    async def _medium_loop(self) -> None:
        while True:
            await self._paused.wait()
            try:
                async with self._lock:
                    await self._poll_medium()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("YaesuCatPoller: medium poll error", exc_info=True)
            await asyncio.sleep(self._medium_interval)

    async def _slow_loop(self) -> None:
        while True:
            await self._paused.wait()
            try:
                async with self._lock:
                    await self._poll_slow()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("YaesuCatPoller: slow poll error", exc_info=True)
            await asyncio.sleep(self._slow_interval)

    # ------------------------------------------------------------------
    # Poll actions
    # ------------------------------------------------------------------

    async def _poll_fast(self) -> None:
        """Fast group: S-meter for main and sub receivers."""
        state = self._radio.radio_state

        raw_main = await self._radio.get_s_meter(0)
        self._ema_s_main = self._apply_ema(raw_main, self._ema_s_main)
        state.main.s_meter = int(round(self._ema_s_main))

        try:
            raw_sub = await self._radio.get_s_meter(1)
            self._ema_s_sub = self._apply_ema(raw_sub, self._ema_s_sub)
            state.sub.s_meter = int(round(self._ema_s_sub))
        except Exception:
            # Sub receiver S-meter may not be supported on all rigs.
            logger.debug("YaesuCatPoller: sub S-meter unavailable", exc_info=True)

        self._callback(state)

    async def _poll_medium(self) -> None:
        """Medium group: frequency, mode, PTT."""
        await self._radio.get_freq(0)
        await self._radio.get_mode(0)

        try:
            await self._radio.get_freq(1)
            await self._radio.get_mode(1)
        except Exception:
            logger.debug("YaesuCatPoller: sub freq/mode unavailable", exc_info=True)

        await self._radio.get_ptt()

        self._callback(self._radio.radio_state)

    async def _poll_slow(self) -> None:
        """Slow group: AGC, AF level, RF gain, squelch."""
        state = self._radio.radio_state

        try:
            agc = await self._radio.get_agc(0)
            state.main.agc = agc
        except Exception:
            logger.debug("YaesuCatPoller: get_agc failed", exc_info=True)

        try:
            af = await self._radio.get_af_level(0)
            state.main.af_level = af
        except Exception:
            logger.debug("YaesuCatPoller: get_af_level failed", exc_info=True)

        try:
            rf = await self._radio.get_rf_gain(0)
            state.main.rf_gain = rf
        except Exception:
            logger.debug("YaesuCatPoller: get_rf_gain failed", exc_info=True)

        try:
            sq = await self._radio.get_squelch(0)
            state.main.squelch = sq
        except Exception:
            logger.debug("YaesuCatPoller: get_squelch failed", exc_info=True)

        self._callback(state)
