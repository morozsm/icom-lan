"""Single CI-V serialiser — all radio reads and writes go through here.

RadioPoller runs one asyncio task that:
1. Drains the command queue (set_freq, ptt, etc.) — writes first.
2. Polls the next parameter in round-robin order — reads second.

This guarantees that only ONE CI-V exchange is in flight at a time,
preventing the half-duplex protocol from getting confused.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from ..rigctld.state_cache import StateCache
from .protocol import METER_ALC, METER_POWER, METER_SMETER_MAIN, METER_SWR

if TYPE_CHECKING:
    from ..radio import IcomRadio

__all__ = ["RadioPoller", "CommandQueue"]

logger = logging.getLogger(__name__)

# Inter-command gap (seconds).  Small enough to keep latency low,
# large enough to let the radio digest the previous command.
_GAP: float = 0.012

# Parameters polled in round-robin order.
_POLL_PARAMS: list[str] = [
    "freq",
    "mode_info",
    "s_meter",
    "power",
    "swr",
    "alc",
    "rf_gain",
    "af_level",
    "attenuator",
    "preamp",
    "data_mode",
]


# ------------------------------------------------------------------
# Command types
# ------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SetFreq:
    freq: int

@dataclass(frozen=True, slots=True)
class SetMode:
    mode: str
    filter_width: int | None = None

@dataclass(frozen=True, slots=True)
class SetFilter:
    filter_num: int

@dataclass(frozen=True, slots=True)
class SetPower:
    level: int

@dataclass(frozen=True, slots=True)
class SetRfGain:
    level: int

@dataclass(frozen=True, slots=True)
class SetAfLevel:
    level: int

@dataclass(frozen=True, slots=True)
class SetAttenuator:
    db: int

@dataclass(frozen=True, slots=True)
class SetPreamp:
    level: int

@dataclass(frozen=True, slots=True)
class PttOn:
    pass

@dataclass(frozen=True, slots=True)
class PttOff:
    pass

@dataclass(frozen=True, slots=True)
class SelectVfo:
    vfo: str

@dataclass(frozen=True, slots=True)
class VfoSwap:
    pass

@dataclass(frozen=True, slots=True)
class VfoEqualize:
    pass

# Commands that are deduplicated (last-write-wins)
_DEDUP_TYPES = (
    SetFreq, SetMode, SetFilter, SetPower, SetRfGain, SetAfLevel,
    SetAttenuator, SetPreamp, SelectVfo, VfoSwap, VfoEqualize,
)

# Union type for all commands
Command = (
    SetFreq | SetMode | SetFilter | SetPower | SetRfGain | SetAfLevel
    | SetAttenuator | SetPreamp | PttOn | PttOff | SelectVfo
    | VfoSwap | VfoEqualize
)


# ------------------------------------------------------------------
# CommandQueue: dedup + ordered drain
# ------------------------------------------------------------------

class CommandQueue:
    """Thread-safe command queue with last-write-wins dedup.

    PTT commands are never deduped — every PttOn/PttOff must execute.
    All other command types keep only the latest value.
    """

    def __init__(self) -> None:
        self._dedup: dict[type, Command] = {}
        self._ptt: list[PttOn | PttOff] = []
        self._notify: asyncio.Event = asyncio.Event()

    def put(self, cmd: Command) -> None:
        """Enqueue a command."""
        if isinstance(cmd, (PttOn, PttOff)):
            self._ptt.append(cmd)
        else:
            self._dedup[type(cmd)] = cmd
        self._notify.set()

    def drain(self) -> list[Command]:
        """Return all queued commands in order: PTT first, then deduped."""
        self._notify.clear()
        cmds: list[Command] = []
        cmds.extend(self._ptt)
        self._ptt.clear()
        cmds.extend(self._dedup.values())
        self._dedup.clear()
        return cmds

    @property
    def has_commands(self) -> bool:
        return bool(self._ptt or self._dedup)

    async def wait(self, timeout: float | None = None) -> None:
        """Wait until at least one command is available or timeout expires."""
        try:
            await asyncio.wait_for(self._notify.wait(), timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError):
            pass


# ------------------------------------------------------------------
# RadioPoller
# ------------------------------------------------------------------

class RadioPoller:
    """Single-task CI-V serialiser.

    Args:
        radio: Connected IcomRadio instance.
        state_cache: Shared state cache to update with poll results.
        command_queue: Queue of outbound commands.
        on_state_event: Callback ``(event_name, data_dict)`` called when
            a polled value changes.
        on_meter_readings: Callback ``(readings)`` called when meter
            values are polled.  ``readings`` is ``list[tuple[int, int]]``.
    """

    def __init__(
        self,
        radio: "IcomRadio",
        state_cache: StateCache,
        command_queue: CommandQueue,
        *,
        on_state_event: Callable[[str, dict[str, Any]], None] | None = None,
        on_meter_readings: Callable[[list[tuple[int, int]]], None] | None = None,
    ) -> None:
        self._radio = radio
        self._cache = state_cache
        self._queue = command_queue
        self._on_state_event = on_state_event
        self._on_meter_readings = on_meter_readings
        self._poll_index: int = 0
        self._task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the poller loop.  Idempotent."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.get_running_loop().create_task(
            self._run(), name="radio-poller"
        )
        logger.info("radio-poller: started")

    def stop(self) -> None:
        """Cancel the poller task."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
            logger.info("radio-poller: stopped")

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        try:
            while True:
                # 1. Drain command queue
                if self._queue.has_commands:
                    for cmd in self._queue.drain():
                        try:
                            await self._execute(cmd)
                        except Exception:
                            logger.debug("radio-poller: cmd error", exc_info=True)
                        await asyncio.sleep(_GAP)

                # 2. Poll next parameter
                try:
                    await self._poll_next()
                except Exception:
                    logger.debug("radio-poller: poll error", exc_info=True)

                # 3. Wait for next cycle — either a command arrives or timeout
                await self._queue.wait(timeout=_GAP)
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    async def _execute(self, cmd: Command) -> None:
        radio = self._radio
        match cmd:
            case SetFreq(freq=freq):
                await radio.set_frequency(freq)
                self._cache.update_freq(freq)
                self._emit("freq_changed", {"freq": freq, "vfo": "A"})
            case SetMode(mode=mode, filter_width=fw):
                await radio.set_mode(mode, fw)
                self._cache.update_mode(mode, fw)
                filt = f"FIL{fw}" if fw else ""
                self._emit("mode_changed", {"mode": mode, "filter": filt})
            case SetFilter(filter_num=fn):
                await radio.set_filter(fn)
                self._cache.update_mode(self._cache.mode, fn)
                self._emit("mode_changed", {
                    "mode": self._cache.mode,
                    "filter": f"FIL{fn}",
                })
            case PttOn():
                await radio.set_ptt(True)
                self._cache.update_ptt(True)
                self._emit("ptt", {"state": True})
            case PttOff():
                await radio.set_ptt(False)
                self._cache.update_ptt(False)
                self._emit("ptt", {"state": False})
            case SetPower(level=level):
                await radio.set_power(level)
            case SetRfGain(level=level):
                await radio.set_rf_gain(level)
                self._cache.update_rf_gain(float(level))
            case SetAfLevel(level=level):
                await radio.set_af_level(level)
                self._cache.update_af_level(float(level))
            case SetAttenuator(db=db):
                await radio.set_attenuator_level(db)
                self._cache.update_attenuator(db)
                self._emit("att_changed", {"db": db})
            case SetPreamp(level=level):
                await radio.set_preamp(level)
                self._cache.update_preamp(level)
                self._emit("preamp_changed", {"level": level})
            case SelectVfo(vfo=vfo):
                await radio.select_vfo(vfo)
            case VfoSwap():
                await radio.vfo_swap()
            case VfoEqualize():
                await radio.vfo_a_equals_b()

    # ------------------------------------------------------------------
    # Round-robin polling
    # ------------------------------------------------------------------

    async def _poll_next(self) -> None:
        param = _POLL_PARAMS[self._poll_index]
        self._poll_index = (self._poll_index + 1) % len(_POLL_PARAMS)

        radio = self._radio
        cache = self._cache

        match param:
            case "freq":
                val = await radio.get_frequency()
                if val != cache.freq:
                    cache.update_freq(val)
                    self._emit("freq_changed", {"freq": val, "vfo": "A"})

            case "mode_info":
                mode_obj, fw = await radio.get_mode_info()
                mode_name = mode_obj.name
                filt = f"FIL{fw}" if fw else ""
                if mode_name != cache.mode or fw != cache.filter_width:
                    cache.update_mode(mode_name, fw)
                    self._emit("mode_changed", {"mode": mode_name, "filter": filt})

            case "s_meter":
                val = await radio.get_s_meter()
                cache.update_s_meter(val)
                self._emit_meters(METER_SMETER_MAIN, val)

            case "power":
                val = await radio.get_power()
                cache.update_rf_power(val / 255.0)
                self._emit_meters(METER_POWER, val)

            case "swr":
                val = await radio.get_swr()
                cache.update_swr(float(val))
                self._emit_meters(METER_SWR, val)

            case "alc":
                val = await radio.get_alc()
                cache.update_alc(float(val))
                self._emit_meters(METER_ALC, val)

            case "rf_gain":
                val = await radio.get_rf_gain()
                if cache.rf_gain is None or val != int(cache.rf_gain):
                    cache.update_rf_gain(float(val))

            case "af_level":
                val = await radio.get_af_level()
                if cache.af_level is None or val != int(cache.af_level):
                    cache.update_af_level(float(val))

            case "attenuator":
                val = await radio.get_attenuator_level()
                if val != cache.attenuator:
                    cache.update_attenuator(val)
                    self._emit("att_changed", {"db": val})

            case "preamp":
                val = await radio.get_preamp()
                if val != cache.preamp:
                    cache.update_preamp(val)
                    self._emit("preamp_changed", {"level": val})

            case "data_mode":
                val = await radio.get_data_mode()
                if val != cache.data_mode:
                    cache.update_data_mode(val)
                    self._emit("data_mode_changed", {"on": val})

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _emit(self, name: str, data: dict[str, Any]) -> None:
        if self._on_state_event is not None:
            self._on_state_event(name, data)

    def _emit_meters(self, meter_id: int, value: int) -> None:
        """Accumulate meter readings; emit after all meter polls in a cycle."""
        if self._on_meter_readings is not None:
            self._on_meter_readings([(meter_id, int(value))])
