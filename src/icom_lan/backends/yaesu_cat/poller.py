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
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ...radio_state import RadioState
    from ...web.radio_poller import CommandQueue
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
        command_queue: "CommandQueue | None" = None,
        fast_interval: float = _FAST_INTERVAL,
        medium_interval: float = _MEDIUM_INTERVAL,
        slow_interval: float = _SLOW_INTERVAL,
        ema_alpha: float = _EMA_ALPHA,
    ) -> None:
        self._radio = radio
        self._callback = callback
        self._command_queue = command_queue
        self._fast_interval = fast_interval
        self._medium_interval = medium_interval
        self._slow_interval = slow_interval
        self._ema_alpha = ema_alpha

        # Shared serial access lock — one request in flight at a time.
        self._lock: asyncio.Lock = asyncio.Lock()
        # Clear = paused, set = running.
        self._paused: asyncio.Event = asyncio.Event()
        self._paused.set()
        self._reconnecting = False

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

    async def _try_reconnect(self) -> None:
        """Attempt serial reconnect if transport reports too many errors.

        Only one reconnect runs at a time.  Other loops sleep while
        reconnect is in progress.
        """
        transport = getattr(self._radio, "_transport", None)
        if transport is None:
            return
        if not getattr(transport, "_maybe_reconnect_needed", lambda: False)():
            return
        if self._reconnecting:
            return  # Another loop is already reconnecting

        self._reconnecting = True
        try:
            logger.warning("YaesuCatPoller: triggering auto-reconnect")
            await transport.reconnect()
            logger.info("YaesuCatPoller: reconnected successfully")
        except Exception:
            logger.error("YaesuCatPoller: reconnect failed", exc_info=True)
        finally:
            self._reconnecting = False

    async def _run_poll_cycle(
        self,
        name: str,
        coro_fn: Callable[[], Awaitable[None]],
        interval: float,
    ) -> None:
        """Generic poll loop with auto-reconnect on persistent errors."""
        while True:
            await self._paused.wait()
            if self._reconnecting:
                await asyncio.sleep(interval)
                continue
            try:
                async with self._lock:
                    await coro_fn()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("YaesuCatPoller: %s poll error", name, exc_info=True)
                await self._try_reconnect()
            await asyncio.sleep(interval)

    async def _fast_loop(self) -> None:
        await self._run_poll_cycle("fast", self._poll_fast, self._fast_interval)

    async def _medium_loop(self) -> None:
        async def _medium() -> None:
            await self._drain_commands()
            await self._poll_medium()

        await self._run_poll_cycle("medium", _medium, self._medium_interval)

    async def _slow_loop(self) -> None:
        await self._run_poll_cycle("slow", self._poll_slow, self._slow_interval)

    # ------------------------------------------------------------------
    # Command queue drain
    # ------------------------------------------------------------------

    async def _drain_commands(self) -> None:
        """Process all pending commands from the web UI command queue."""
        if self._command_queue is None or not self._command_queue.has_commands:
            return

        commands = self._command_queue.drain()
        for cmd in commands:
            try:
                await self._execute_command(cmd)
            except Exception:
                logger.warning(
                    "YaesuCatPoller: command %s failed",
                    type(cmd).__name__,
                    exc_info=True,
                )

    # CI-V band codes → Yaesu BS band codes
    _CIV_TO_YAESU_BAND: dict[int, int] = {
        0x00: 0,   # 160m → 1.8M
        0x01: 1,   # 80m  → 3.5M
        0x02: 2,   # 60m  → 5M
        0x03: 3,   # 40m  → 7M
        0x04: 4,   # 30m  → 10M
        0x05: 5,   # 20m  → 14M
        0x06: 6,   # 17m  → 18M
        0x07: 7,   # 15m  → 21M
        0x08: 8,   # 12m  → 24M
        0x09: 9,   # 10m  → 28M
        0x0A: 10,  # 6m   → 50M
    }

    async def _execute_command(self, cmd: Any) -> None:
        """Dispatch a single command to the radio.

        Commands come from the web UI CommandQueue.  The dispatcher handles
        all command types; unsupported commands for this radio are silently
        dropped.
        """
        from ...web.radio_poller import (
            PttOff,
            PttOn,
            SelectVfo,
            SetAfLevel,
            SetAgc,
            SetApf,
            SetAttenuator,
            SetAutoNotch,
            SetBand,
            SetBreakIn,
            SetCompressor,
            SetCompressorLevel,
            SetCwPitch,
            SetDataMode,
            SetDialLock,
            SetDigiSel,
            SetDriveGain,
            SetDualWatch,
            SetFilter,
            SetFilterShape,
            SetFilterWidth,
            SetFreq,
            SetIpPlus,
            SetKeySpeed,
            SetManualNotch,
            SetMicGain,
            SetMode,
            SetMonitor,
            SetMonitorGain,
            SetNB,
            SetNBLevel,
            SetNR,
            SetNRLevel,
            SetNotchFilter,
            SetPbtInner,
            SetPbtOuter,
            SetPower,
            SetPreamp,
            SetRfGain,
            SetRitFrequency,
            SetRitStatus,
            SetRitTxStatus,
            SetSplit,
            SetSquelch,
            SetTwinPeak,
            SetVox,
            VfoSwap,
        )

        radio = self._radio
        name = type(cmd).__name__

        try:
            match cmd:
                # ── Core: Frequency / Mode / Band ──
                case SetFreq(freq=freq, receiver=rx):
                    await radio.set_freq(freq, receiver=rx)
                case SetMode(mode=mode, receiver=rx):
                    await radio.set_mode(mode, receiver=rx)
                case SetBand(band=band):
                    yaesu_band = self._CIV_TO_YAESU_BAND.get(band, band)
                    await radio.set_band(yaesu_band)
                case SelectVfo(vfo=vfo):
                    code = 0 if vfo.upper() in ("A", "MAIN") else 1
                    await radio.set_vfo_select(code)
                case VfoSwap():
                    await radio.vfo_a_to_b()

                # ── PTT ──
                case PttOn():
                    await radio.set_ptt(True)
                case PttOff():
                    await radio.set_ptt(False)

                # ── Audio / RF Levels ──
                case SetAfLevel(level=level):
                    await radio.set_af_level(level)
                case SetRfGain(level=level):
                    await radio.set_rf_gain(level)
                case SetSquelch(level=level):
                    await radio.set_squelch(level)
                case SetMicGain(level=level):
                    await radio.set_mic_gain(level)
                case SetPower(level=level):
                    await radio.set_power(level)
                case SetDriveGain(level=level):
                    await radio.set_drive_gain(level)

                # ── RF Front End ──
                case SetAttenuator(state=state):
                    await radio.set_attenuator(state)
                case SetPreamp(band=band, value=value):
                    await radio.set_preamp(band, value)

                # ── DSP / Noise ──
                case SetAgc(mode=mode):
                    await radio.set_agc(mode)
                case SetNB(on=on):
                    await radio.set_nb(on)
                case SetNR(on=on):
                    await radio.set_nr(on)
                case SetNBLevel(level=level):
                    await radio.set_nb_level(level)
                case SetNRLevel(level=level):
                    await radio.set_nr_level(level)
                case SetAutoNotch(on=on):
                    await radio.set_auto_notch(on)
                case SetManualNotch(on=on):
                    await radio.set_manual_notch(on)
                case SetNotchFilter(level=level):
                    await radio.set_manual_notch_freq(level)

                # ── Filters ──
                case SetFilter(filter_num=num):
                    pass  # FTX-1 uses filter_width, not discrete filter numbers
                case SetFilterWidth(width=width):
                    await radio.set_filter_width(width)
                case SetFilterShape(shape=shape):
                    pass  # Not available on FTX-1
                case SetPbtInner() | SetPbtOuter():
                    pass  # Not available on FTX-1

                # ── CW ──
                case SetKeySpeed(speed=speed):
                    await radio.set_keyer_speed(speed)
                case SetCwPitch(value=value):
                    await radio.set_key_pitch(value)
                case SetBreakIn(break_in_mode=mode):
                    await radio.set_break_in(bool(mode))

                # ── TX Controls ──
                case SetCompressor(on=on):
                    await radio.set_processor(on)
                case SetCompressorLevel(level=level):
                    await radio.set_processor_level(level)
                case SetVox(on=on):
                    await radio.set_vox(on)
                case SetMonitor(on=on):
                    await radio.set_monitor_on(on)
                case SetMonitorGain(level=level):
                    await radio.set_monitor_level(level)
                case SetSplit(on=on):
                    await radio.set_split(on)

                # ── RIT / Clarifier ──
                case SetRitStatus(on=on):
                    # RX clarifier only; TX clarifier left unchanged
                    await radio.set_clarifier(rx_clar=on, tx_clar=False)
                case SetRitTxStatus(on=on):
                    # TX clarifier only; RX clarifier left unchanged
                    await radio.set_clarifier(rx_clar=False, tx_clar=on)
                case SetRitFrequency(freq=freq):
                    await radio.set_clarifier_freq(freq)

                # ── Data Mode ──
                case SetDataMode(mode=mode):
                    await radio.set_data_mode(mode)

                # ── Dial Lock ──
                case SetDialLock(on=on):
                    await radio.set_lock(on)

                # ── Dual Watch ──
                case SetDualWatch(on=on):
                    await radio.set_dual_watch(on)

                # ── IC-7610-specific (not applicable) ──
                case SetIpPlus() | SetApf() | SetTwinPeak() | SetDigiSel():
                    pass  # Icom-only DSP features

                case _:
                    logger.debug("CMD: unhandled %s — ignoring", name)
                    return

            logger.info("CMD: %s", name)

        except Exception:
            logger.warning("CMD: %s failed", name, exc_info=True)

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
        """Slow group: AGC, levels, DSP, TX settings."""
        state = self._radio.radio_state
        radio = self._radio

        # -- Levels --
        try:
            state.main.agc = await radio.get_agc(0)
        except Exception:
            logger.debug("YaesuCatPoller: get_agc failed", exc_info=True)

        try:
            state.main.af_level = await radio.get_af_level(0)
        except Exception:
            logger.debug("YaesuCatPoller: get_af_level failed", exc_info=True)

        try:
            state.main.rf_gain = await radio.get_rf_gain(0)
        except Exception:
            logger.debug("YaesuCatPoller: get_rf_gain failed", exc_info=True)

        try:
            state.main.squelch = await radio.get_squelch(0)
        except Exception:
            logger.debug("YaesuCatPoller: get_squelch failed", exc_info=True)

        # -- DSP: NB/NR levels, auto notch --
        try:
            state.main.nb_level = await radio.get_nb_level(0)
        except Exception:
            logger.debug("YaesuCatPoller: get_nb_level failed", exc_info=True)

        try:
            state.main.nr_level = await radio.get_nr_level(0)
        except Exception:
            logger.debug("YaesuCatPoller: get_nr_level failed", exc_info=True)

        try:
            state.main.auto_notch = await radio.get_auto_notch(0)
        except Exception:
            logger.debug("YaesuCatPoller: get_auto_notch failed", exc_info=True)

        # -- Filter width --
        try:
            state.main.filter_width = await radio.get_filter_width(0)
        except Exception:
            logger.debug("YaesuCatPoller: get_filter_width failed", exc_info=True)

        # -- TX power --
        try:
            _, watts = await radio.get_power()
            state.power_level = watts
        except Exception:
            logger.debug("YaesuCatPoller: get_power failed", exc_info=True)

        # -- Mic gain --
        try:
            state.mic_gain = await radio.get_mic_gain()
        except Exception:
            logger.debug("YaesuCatPoller: get_mic_gain failed", exc_info=True)

        # -- Split --
        try:
            state.split = await radio.get_split()
        except Exception:
            logger.debug("YaesuCatPoller: get_split failed", exc_info=True)

        # -- VOX --
        try:
            state.vox = await radio.get_vox()
        except Exception:
            logger.debug("YaesuCatPoller: get_vox failed", exc_info=True)

        # -- Dial lock --
        try:
            state.dial_lock = await radio.get_lock()
        except Exception:
            logger.debug("YaesuCatPoller: get_lock failed", exc_info=True)

        self._callback(state)
