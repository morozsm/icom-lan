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

if TYPE_CHECKING:
    from ..radio_protocol import Radio

__all__ = ["RadioPoller", "CommandQueue", "EnableScope", "DisableScope", "SwitchScopeReceiver"]

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
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetMode:
    mode: str
    filter_width: int | None = None
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetFilter:
    filter_num: int
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetPower:
    level: int

@dataclass(frozen=True, slots=True)
class SetRfGain:
    level: int
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetAfLevel:
    level: int
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetSquelch:
    level: int
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetNB:
    on: bool
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetNR:
    on: bool
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetDigiSel:
    on: bool
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetIpPlus:
    on: bool
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetAttenuator:
    db: int
    receiver: int = 0

@dataclass(frozen=True, slots=True)
class SetPreamp:
    level: int
    receiver: int = 0

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

@dataclass(frozen=True, slots=True)
class SwitchScopeReceiver:
    receiver: int  # 0=MAIN, 1=SUB


Command = (
    SetFreq | SetMode | SetFilter | SetPower | SetRfGain | SetAfLevel | SetSquelch | SetNB | SetNR | SetDigiSel | SetIpPlus
    | SetAttenuator | SetPreamp | PttOn | PttOff | SetBand | SelectVfo
    | VfoSwap | VfoEqualize | SwitchScopeReceiver
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
        radio: "Radio",
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

                # 3. Wait for next cycle
                await self._queue.wait(timeout=_FAST_INTERVAL)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("radio-poller: FATAL — task crashed, commands will stop working")

    async def _civ(
        self,
        cmd: int,
        *,
        sub: int | None = None,
        data: bytes = b"",
        wait_response: bool = False,
    ) -> None:
        """Send a raw CI-V command if the radio supports it (IcomRadio-specific).

        For non-Icom backends this is a no-op — scope/meter polling simply
        won't happen, which is acceptable.
        """
        _send_civ = getattr(self._radio, "send_civ", None)
        if _send_civ is not None:
            await _send_civ(cmd, sub=sub, data=data, wait_response=wait_response)

    def _current_active(self) -> str:
        """Return current active receiver ('MAIN' or 'SUB') from RadioState."""
        rs = getattr(self._radio, "_radio_state", None)
        _active = getattr(rs, "active", None) if rs is not None else None
        return _active if isinstance(_active, str) else "MAIN"

    async def _execute(self, cmd: Command) -> None:
        radio = self._radio
        match cmd:
            case SetFreq(freq=freq, receiver=rx):
                # 0x05 does NOT support cmd29 on IC-7610.
                # If targeting SUB, temporarily switch active VFO, send, switch back.
                current = self._current_active()
                if rx != 0:
                    if current != "SUB":
                        await self._civ(0x07, data=bytes([0xD1]))
                        await asyncio.sleep(_GAP)
                    await radio.set_frequency(freq)
                    if current != "SUB":
                        await asyncio.sleep(_GAP)
                        await self._civ(0x07, data=bytes([0xD0]))
                else:
                    if current != "MAIN":
                        await self._civ(0x07, data=bytes([0xD0]))
                        await asyncio.sleep(_GAP)
                    await radio.set_frequency(freq)
                    if current != "MAIN":
                        await asyncio.sleep(_GAP)
                        await self._civ(0x07, data=bytes([0xD1]))
            case SetMode(mode=mode, filter_width=fw, receiver=rx):
                # 0x06 does NOT support cmd29 on IC-7610. Same VFO-switch pattern.
                current = self._current_active()
                if rx != 0:
                    if current != "SUB":
                        await self._civ(0x07, data=bytes([0xD1]))
                        await asyncio.sleep(_GAP)
                    await radio.set_mode(mode, fw)
                    if current != "SUB":
                        await asyncio.sleep(_GAP)
                        await self._civ(0x07, data=bytes([0xD0]))
                else:
                    await radio.set_mode(mode, fw)
            case SetFilter(filter_num=fn, receiver=rx):
                await radio.set_filter(fn)
            case PttOn():
                logger.info("poller: PTT ON")
                await radio.set_ptt(True)
            case PttOff():
                logger.info("poller: PTT OFF")
                await radio.set_ptt(False)
            case SetPower(level=level):
                await radio.set_power(level)
            case SetRfGain(level=level, receiver=rx):
                await radio.set_rf_gain(level, receiver=rx)
            case SetAfLevel(level=level, receiver=rx):
                await radio.set_af_level(level, receiver=rx)
            case SetSquelch(level=level, receiver=rx):
                await radio.set_squelch(level, receiver=rx)
            case SetNB(on=on, receiver=rx):
                await radio.set_nb(on, receiver=rx)
                if self._on_state_event:
                    self._on_state_event("nb_changed", {"on": on})
            case SetNR(on=on, receiver=rx):
                await radio.set_nr(on, receiver=rx)
                if self._on_state_event:
                    self._on_state_event("nr_changed", {"on": on})
            case SetDigiSel(on=on, receiver=rx):
                await radio.set_digisel(on, receiver=rx)
                if self._on_state_event:
                    self._on_state_event("digisel_changed", {"on": on})
            case SetIpPlus(on=on, receiver=rx):
                await radio.set_ip_plus(on, receiver=rx)
                if self._on_state_event:
                    self._on_state_event("ipplus_changed", {"on": on})
            case SetAttenuator(db=db, receiver=rx):
                await radio.set_attenuator_level(db, receiver=rx)
            case SetPreamp(level=level, receiver=rx):
                await radio.set_preamp(level, receiver=rx)
            case SetBand(band=band):
                await self._civ(0x07, data=bytes([band]))
            case SelectVfo(vfo=vfo):
                # IC-7610 LAN audio is always from MAIN receiver (mono).
                # To "switch" audio to SUB, we SWAP MAIN↔SUB (0x07 0xB0).
                # This exchanges frequencies, modes, and all params between
                # MAIN and SUB — audio, scope, everything follows MAIN.
                vfo_upper = vfo.upper()
                is_sub = vfo_upper in ("SUB", "B")
                current = self._current_active()
                need_swap = (is_sub and current == "MAIN") or (not is_sub and current == "SUB")
                if need_swap:
                    await self._civ(0x07, data=bytes([0xB0]))
                    logger.info("radio-poller: VFO swap (Main<>Sub)")
                    rs = getattr(self._radio, "_radio_state", None)
                    if rs is not None and hasattr(rs, "active"):
                        rs.active = "SUB" if current == "MAIN" else "MAIN"
                if self._on_state_event:
                    self._on_state_event("vfo_changed", {"vfo": vfo})
            case VfoSwap():
                await radio.vfo_exchange()
                # After swap, active VFO stays same but freqs are exchanged
                if self._on_state_event:
                    self._on_state_event("vfo_swapped", {})
            case VfoEqualize():
                await radio.vfo_equalize()
            case EnableScope(policy=policy):
                await radio.enable_scope(policy=policy)
                logger.info("radio-poller: scope enabled")
            case DisableScope():
                await radio.disable_scope()
                logger.info("radio-poller: scope disabled")
            case SwitchScopeReceiver(receiver=receiver):
                # Fire-and-forget scope receiver select (0x27 0x12)
                await self._civ(0x27, sub=0x12, data=bytes([receiver & 0x01]))
                logger.info("radio-poller: scope receiver → %s", "SUB" if receiver else "MAIN")

    # Fast: meters (polled on even cycles)
    # wfview: Priority=Highest, queue interval 25ms for LAN (HasFDComms)
    _FAST_CMDS: list[tuple[int, int | None]] = [
        (0x15, 0x02),   # S-meter
        (0x15, 0x11),   # RF power
        (0x15, 0x12),   # SWR
        (0x15, 0x13),   # ALC
        (0x15, 0x15),   # VD (voltage)
        (0x15, 0x16),   # Id (PA drain current)
    ]

    # State queries interleaved on odd cycles.
    # Tuple: (cmd, sub, receiver) where receiver=None means global (no cmd29).
    # Per-receiver queries use cmd29 framing (0x29 prefix).
    # receiver: 0x00=MAIN, 0x01=SUB, None=global
    # For 0x25/0x26: receiver byte goes in data payload (not cmd29 prefix)
    _STATE_QUERIES: list[tuple[int, int | None, int | None]] = [
        (0x25, None, 0x00),   # RX Freq MAIN (built-in receiver byte)
        (0x25, None, 0x01),   # RX Freq SUB
        (0x26, None, 0x00),   # RX Mode MAIN (built-in receiver byte)
        (0x26, None, 0x01),   # RX Mode SUB
        (0x11, None, 0x00),   # ATT MAIN
        (0x11, None, 0x01),   # ATT SUB
        (0x14, 0x01, 0x00),   # AF MAIN
        (0x14, 0x01, 0x01),   # AF SUB
        (0x14, 0x02, 0x00),   # RF gain MAIN
        (0x14, 0x02, 0x01),   # RF gain SUB
        (0x14, 0x03, 0x00),   # Squelch MAIN
        (0x14, 0x03, 0x01),   # Squelch SUB
        (0x16, 0x02, 0x00),   # Preamp MAIN
        (0x16, 0x02, 0x01),   # Preamp SUB
        (0x16, 0x22, 0x00),   # NB MAIN
        (0x16, 0x22, 0x01),   # NB SUB
        (0x16, 0x40, 0x00),   # NR MAIN
        (0x16, 0x40, 0x01),   # NR SUB
        (0x16, 0x4E, 0x00),   # DIGI-SEL MAIN
        (0x16, 0x4E, 0x01),   # DIGI-SEL SUB
        (0x16, 0x65, 0x00),   # IP+ MAIN
        (0x16, 0x65, 0x01),   # IP+ SUB
        # NOTE: 0x1A 0x03 returns IF filter width code on IC-7610, not
        # filter selector (1/2/3). Filter comes from mode response (0x26).
        # Polling 0x1A 0x03 removed to avoid misparsing and UI flicker.
        (0x1C, 0x00, None),   # PTT (global)
        (0x14, 0x0A, None),   # Power level (global)
        (0x0F, None, None),   # Split (global)
        (0x07, 0xD2, None),   # Active receiver: 0x00=MAIN, 0x01=SUB
        (0x07, 0xC2, None),   # Dual Watch status: 0x00=off, 0x01=on
    ]

    async def _send_query(self) -> None:
        # Even cycles → meter query; odd cycles → state query.
        if self._poll_index % 2 == 0:
            fast_idx = (self._poll_index // 2) % len(self._FAST_CMDS)
            cmd_byte, sub_byte = self._FAST_CMDS[fast_idx]
            await self._civ(cmd_byte, sub=sub_byte, data=b"")
        else:
            state_idx = (self._poll_index // 2) % len(self._STATE_QUERIES)
            cmd_byte, sub_byte, receiver = self._STATE_QUERIES[state_idx]
            if receiver is not None:
                if cmd_byte in (0x25, 0x26):
                    # RX Freq / RX Mode: receiver byte in data payload
                    await self._civ(cmd_byte, data=bytes([receiver]))
                else:
                    # cmd29 framing: FE FE to from 29 rcvr cmd [sub] FD
                    inner = bytes([receiver, cmd_byte])
                    if sub_byte is not None:
                        inner += bytes([sub_byte])
                    await self._civ(0x29, data=inner)
            else:
                # Global: plain CI-V query
                await self._civ(cmd_byte, sub=sub_byte, data=b"")
        self._poll_index += 1

    def _emit(self, name: str, data: dict[str, Any]) -> None:
        if self._on_state_event is not None:
            self._on_state_event(name, data)

    def _emit_meters(self, meter_id: int, value: int) -> None:
        if self._on_meter_readings is not None:
            self._on_meter_readings([(meter_id, int(value))])
