"""RadioPoller — fire-and-forget CI-V serialiser.

## ARCHITECTURE PRINCIPLE: FIRE-AND-FORGET ONLY

All CI-V communication MUST be fire-and-forget.  Never await a CI-V response.

Why: The IC-7610 scope streams ~225 CI-V packets/sec on port 50002.  When
a request-response command waits for a specific reply, the response packet
gets lost among scope frames, causing 2-second timeouts that cascade and
freeze the entire poller.

wfview (the reference implementation) works the same way: commands go out,
responses are parsed from the incoming stream — nobody waits for a specific
reply.

How it works:
1. RadioPoller sends fire-and-forget CI-V queries (get_freq, get_mode, etc.)
2. The CI-V RX loop (_civ_rx.py) receives ALL packets and calls
   _update_state_cache_from_frame() for every data frame.
3. StateCache is the single source of truth.
4. Clients read from the cache; broadcast events notify on changes.

DO NOT add request-response (await get_frequency, await get_mode, etc.)
to this module.  If you need new data, add parsing to
_update_state_cache_from_frame() in _civ_rx.py instead.
"""

from __future__ import annotations

import asyncio
import logging

from ..exceptions import ConnectionError as RadioConnectionError
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from ..rigctld.state_cache import StateCache
from .protocol import METER_ALC, METER_POWER, METER_SMETER_MAIN, METER_SWR

if TYPE_CHECKING:
    from ..radio import IcomRadio

__all__ = ["RadioPoller", "CommandQueue", "EnableScope", "DisableScope"]

logger = logging.getLogger(__name__)

_GAP: float = 0.012
_SEND_TIMEOUT: float = 1.0
_FAST_INTERVAL: float = 0.025  # meters — wfview queue interval for LAN (25ms)
_SLOW_INTERVAL: float = 0.25   # levels/settings — rarely change


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
class SetBand:
    band: int  # CI-V band code: 0x00=160m, 0x01=80m, ... 0x09=6m

@dataclass(frozen=True, slots=True)
class SelectVfo:
    vfo: str

@dataclass(frozen=True, slots=True)
class VfoSwap:
    pass

@dataclass(frozen=True, slots=True)
class VfoEqualize:
    pass

@dataclass(frozen=True, slots=True)
class EnableScope:
    policy: str = "fast"

@dataclass(frozen=True, slots=True)
class DisableScope:
    pass


Command = (
    SetFreq | SetMode | SetFilter | SetPower | SetRfGain | SetAfLevel
    | SetAttenuator | SetPreamp | PttOn | PttOff | SetBand | SelectVfo
    | VfoSwap | VfoEqualize
)


# ------------------------------------------------------------------
# CommandQueue
# ------------------------------------------------------------------

class CommandQueue:
    def __init__(self) -> None:
        self._dedup: dict[type, Command] = {}
        self._ptt: list[PttOn | PttOff] = []
        self._notify: asyncio.Event = asyncio.Event()

    def put(self, cmd: Command) -> None:
        if isinstance(cmd, (PttOn, PttOff)):
            self._ptt.append(cmd)
        else:
            self._dedup[type(cmd)] = cmd
        self._notify.set()

    def drain(self) -> list[Command]:
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
        try:
            await asyncio.wait_for(self._notify.wait(), timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError):
            pass


# ------------------------------------------------------------------
# RadioPoller
# ------------------------------------------------------------------

class RadioPoller:
    """Fire-and-forget CI-V poller.

    State is updated from CI-V RX stream (_civ_rx._update_state_cache_from_frame),
    NOT from polling responses.
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

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.get_running_loop().create_task(
            self._run(), name="radio-poller"
        )
        logger.info("radio-poller: started")

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None
            logger.info("radio-poller: stopped")

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def _run(self) -> None:
        _backoff = 0.0
        _MAX_BACKOFF = 5.0  # max pause when radio is disconnected
        try:
            while True:
                # 1. Drain command queue (fire-and-forget writes)
                if self._queue.has_commands:
                    for cmd in self._queue.drain():
                        try:
                            await self._execute(cmd)
                            _backoff = 0.0
                        except (ConnectionError, RadioConnectionError):
                            _backoff = min(_backoff + 0.5, _MAX_BACKOFF)
                        except Exception:
                            logger.debug("radio-poller: cmd error: %s",
                                         type(cmd).__name__, exc_info=True)
                        await asyncio.sleep(_GAP)

                # If disconnected, back off to avoid log spam
                if _backoff > 0:
                    await asyncio.sleep(_backoff)
                    # Still try one query to detect reconnection
                    try:
                        await self._send_query()
                        _backoff = 0.0
                        logger.info("radio-poller: connection restored")
                    except (ConnectionError, RadioConnectionError):
                        _backoff = min(_backoff + 0.5, _MAX_BACKOFF)
                        continue
                    except Exception:
                        continue

                # 2. Send fast meter query
                try:
                    await self._send_query()
                except (ConnectionError, RadioConnectionError):
                    _backoff = min(_backoff + 0.5, _MAX_BACKOFF)
                    logger.info("radio-poller: radio disconnected, backing off %.1fs", _backoff)
                    continue
                except Exception:
                    logger.debug("radio-poller: query error", exc_info=True)

                # 3. Every 10th cycle, also send one slow query
                if self._poll_index % 10 == 0:
                    slow_idx = (self._poll_index // 10) % len(self._SLOW_CMDS)
                    cmd_byte, sub_byte = self._SLOW_CMDS[slow_idx]
                    await asyncio.sleep(_GAP)
                    try:
                        await self._radio.send_civ(
                            cmd_byte, sub=sub_byte, data=b"", wait_response=False,
                        )
                    except Exception:
                        pass

                # 4. Wait for next cycle
                await self._queue.wait(timeout=_FAST_INTERVAL)
        except asyncio.CancelledError:
            pass

    async def _execute(self, cmd: Command) -> None:
        radio = self._radio
        match cmd:
            case SetFreq(freq=freq):
                await radio.set_frequency(freq)
            case SetMode(mode=mode, filter_width=fw):
                await radio.set_mode(mode, fw)
            case SetFilter(filter_num=fn):
                await radio.set_filter(fn)
            case PttOn():
                await radio.set_ptt(True)
            case PttOff():
                await radio.set_ptt(False)
            case SetPower(level=level):
                await radio.set_power(level)
            case SetRfGain(level=level):
                await radio.set_rf_gain(level)
            case SetAfLevel(level=level):
                await radio.set_af_level(level)
            case SetAttenuator(db=db):
                await radio.set_attenuator_level(db)
            case SetPreamp(level=level):
                await radio.set_preamp(level)
            case SetBand(band=band):
                await radio.send_civ(0x07, data=bytes([band]), wait_response=False)
            case SelectVfo(vfo=vfo):
                await radio.select_vfo(vfo)
            case VfoSwap():
                await radio.vfo_swap()
            case VfoEqualize():
                await radio.vfo_a_equals_b()
            case EnableScope(policy=policy):
                await radio.enable_scope(policy=policy)
                logger.info("radio-poller: scope enabled")
            case DisableScope():
                await radio.disable_scope()
                logger.info("radio-poller: scope disabled")

    # Fast: meters (polled every 25ms = ~10 updates/sec per meter)
    # wfview: Priority=Highest, queue interval 25ms for LAN (HasFDComms)
    _FAST_CMDS: list[tuple[int, int | None]] = [
        (0x15, 0x02),   # S-meter
        (0x15, 0x11),   # RF power
        (0x15, 0x12),   # SWR
        (0x15, 0x13),   # ALC
        (0x15, 0x15),   # VD (voltage)
        (0x15, 0x16),   # Id (PA drain current)
    ]

    # Slow: levels and settings (freq/mode come unsolicited via CI-V transceive)
    _SLOW_CMDS: list[tuple[int, int | None]] = [
        (0x03, None),   # frequency (backup)
        (0x04, None),   # mode (backup)
        (0x14, 0x0A),   # RF power level (set value)
        (0x14, 0x02),   # RF gain
        (0x14, 0x01),   # AF level
        (0x11, None),   # attenuator
        (0x16, 0x02),   # preamp
    ]

    async def _send_query(self) -> None:
        # Fast meter query every cycle
        fast_idx = self._poll_index % len(self._FAST_CMDS)
        cmd_byte, sub_byte = self._FAST_CMDS[fast_idx]
        await self._radio.send_civ(
            cmd_byte, sub=sub_byte, data=b"", wait_response=False,
        )
        self._poll_index += 1

    def _emit(self, name: str, data: dict[str, Any]) -> None:
        if self._on_state_event is not None:
            self._on_state_event(name, data)

    def _emit_meters(self, meter_id: int, value: int) -> None:
        if self._on_meter_readings is not None:
            self._on_meter_readings([(meter_id, int(value))])
