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

from ..exceptions import CommandError, ConnectionError as RadioConnectionError
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, cast

from ..profiles import RadioProfile, resolve_radio_profile
from ..rigctld.state_cache import CacheField, StateCache
from .._shared_state_runtime import DEFAULT_STATE_CACHE_TTL, is_cache_fresh

if TYPE_CHECKING:
    from ..radio_protocol import Radio

__all__ = [
    "RadioPoller",
    "CommandQueue",
    "EnableScope",
    "DisableScope",
    "SwitchScopeReceiver",
    "SetScopeDuringTx",
    "SetScopeCenterType",
    "SetScopeFixedEdge",
    "SetAntenna1",
    "SetAntenna2",
    "SetRxAntennaAnt1",
    "SetRxAntennaAnt2",
    "SetSystemDate",
    "SetSystemTime",
    "SetAcc1ModLevel",
    "SetUsbModLevel",
    "SetLanModLevel",
    "SetDualWatch",
    "SetCompressor",
]

logger = logging.getLogger(__name__)

_GAP: float = 0.012
_SEND_TIMEOUT: float = 1.0
_FAST_INTERVAL: float = 0.025  # meters — wfview queue interval for LAN (25ms)
_SLOW_INTERVAL: float = 0.25  # levels/settings — rarely change


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


@dataclass(frozen=True, slots=True)
class SetScopeDuringTx:
    on: bool


@dataclass(frozen=True, slots=True)
class SetScopeCenterType:
    center_type: int  # 0-2


@dataclass(frozen=True, slots=True)
class SetScopeFixedEdge:
    edge: int
    start_hz: int
    end_hz: int


@dataclass(frozen=True, slots=True)
class SetPowerstat:
    on: bool


@dataclass(frozen=True, slots=True)
class SetAntenna1:
    on: bool


@dataclass(frozen=True, slots=True)
class SetAntenna2:
    on: bool


@dataclass(frozen=True, slots=True)
class SetRxAntennaAnt1:
    on: bool


@dataclass(frozen=True, slots=True)
class SetRxAntennaAnt2:
    on: bool


@dataclass(frozen=True, slots=True)
class SetSystemDate:
    year: int
    month: int
    day: int


@dataclass(frozen=True, slots=True)
class SetSystemTime:
    hour: int
    minute: int


@dataclass(frozen=True, slots=True)
class SetAcc1ModLevel:
    level: int


@dataclass(frozen=True, slots=True)
class SetUsbModLevel:
    level: int


@dataclass(frozen=True, slots=True)
class SetLanModLevel:
    level: int


@dataclass(frozen=True, slots=True)
class SetDualWatch:
    on: bool


@dataclass(frozen=True, slots=True)
class SetCompressor:
    on: bool


Command = (
    SetFreq
    | SetMode
    | SetFilter
    | SetPower
    | SetRfGain
    | SetAfLevel
    | SetSquelch
    | SetNB
    | SetNR
    | SetDigiSel
    | SetIpPlus
    | SetAttenuator
    | SetPreamp
    | PttOn
    | PttOff
    | SetBand
    | SelectVfo
    | VfoSwap
    | VfoEqualize
    | EnableScope
    | DisableScope
    | SwitchScopeReceiver
    | SetScopeDuringTx
    | SetScopeCenterType
    | SetScopeFixedEdge
    | SetPowerstat
    | SetAntenna1
    | SetAntenna2
    | SetRxAntennaAnt1
    | SetRxAntennaAnt2
    | SetSystemDate
    | SetSystemTime
    | SetAcc1ModLevel
    | SetUsbModLevel
    | SetLanModLevel
    | SetDualWatch
    | SetCompressor
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
        self._revision: int = 0
        self._task: asyncio.Task[None] | None = None
        self._caps: set[str] = self._radio_capabilities()
        self._profile: RadioProfile = self._runtime_profile()
        self._STATE_QUERIES = self._build_state_queries()

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

    @property
    def revision(self) -> int:
        """Monotonic counter incremented on every radio state change."""
        return self._revision

    def bump_revision(self) -> None:
        """Increment the revision counter (called on each state change)."""
        self._revision += 1

    def state_is_fresh(
        self,
        field: CacheField,
        ttl: float = DEFAULT_STATE_CACHE_TTL,
    ) -> bool:
        """Return True if *field* in the shared cache is still fresh.

        Convenience wrapper around :func:`~icom_lan._shared_state_runtime.is_cache_fresh`
        so callers that hold a :class:`RadioPoller` reference do not need to
        import the lower-level helper directly.

        Args:
            field: Cache field name (e.g. ``"freq"``, ``"mode"``).
            ttl: Maximum acceptable age in seconds (defaults to
                :data:`~icom_lan._shared_state_runtime.DEFAULT_STATE_CACHE_TTL`).
        """
        return is_cache_fresh(self._cache, field, ttl)

    def _radio_capabilities(self) -> set[str]:
        raw_caps = getattr(self._radio, "capabilities", None)
        return set(raw_caps) if isinstance(raw_caps, set) else set()

    def _runtime_profile(self) -> RadioProfile:
        raw_profile = getattr(self._radio, "profile", None)
        if isinstance(raw_profile, RadioProfile):
            return raw_profile
        raw_model = getattr(self._radio, "model", None)
        try:
            if isinstance(raw_model, str) and raw_model.strip():
                return resolve_radio_profile(model=raw_model)
        except KeyError:
            pass
        if "dual_rx" in self._caps:
            return resolve_radio_profile(model="IC-7610")
        return resolve_radio_profile(model="IC-7300")

    def _supports_capability(self, capability: str) -> bool:
        return capability in self._caps

    def _ensure_receiver_supported(self, receiver: int, *, operation: str) -> None:
        if self._profile.supports_receiver(receiver):
            return
        raise CommandError(
            f"{operation} does not support receiver={receiver} for profile "
            f"{self._profile.model} (receivers={self._profile.receiver_count})"
        )

    def _build_state_queries(self) -> list[tuple[int, int | None, int | None]]:
        receivers = [0]
        if self._profile.receiver_count > 1:
            receivers.append(1)
        queries: list[tuple[int, int | None, int | None]] = []
        for receiver in receivers:
            queries.append((0x25, None, receiver))
            queries.append((0x26, None, receiver))
            if self._supports_capability("attenuator") and self._profile.supports_cmd29(
                0x11
            ):
                queries.append((0x11, None, receiver))
            if self._supports_capability("af_level") and self._profile.supports_cmd29(
                0x14, 0x01
            ):
                queries.append((0x14, 0x01, receiver))
            if self._supports_capability("rf_gain") and self._profile.supports_cmd29(
                0x14, 0x02
            ):
                queries.append((0x14, 0x02, receiver))
            if self._supports_capability("squelch") and self._profile.supports_cmd29(
                0x14, 0x03
            ):
                queries.append((0x14, 0x03, receiver))
            if self._supports_capability("preamp") and self._profile.supports_cmd29(
                0x16, 0x02
            ):
                queries.append((0x16, 0x02, receiver))
            if self._supports_capability("nb") and self._profile.supports_cmd29(
                0x16, 0x22
            ):
                queries.append((0x16, 0x22, receiver))
            if self._supports_capability("nr") and self._profile.supports_cmd29(
                0x16, 0x40
            ):
                queries.append((0x16, 0x40, receiver))
            if self._supports_capability("digisel") and self._profile.supports_cmd29(
                0x16, 0x4E
            ):
                queries.append((0x16, 0x4E, receiver))
            if self._supports_capability("ip_plus") and self._profile.supports_cmd29(
                0x16, 0x65
            ):
                queries.append((0x16, 0x65, receiver))
            if self._profile.model == "IC-7610":
                for cmd_byte, sub_byte in (
                    (0x15, 0x01),  # S-meter squelch status
                    (0x16, 0x32),  # Audio peak filter
                    (0x16, 0x41),  # Auto notch
                    (0x16, 0x48),  # Manual notch
                    (0x16, 0x4F),  # Twin peak filter
                    (0x16, 0x56),  # Filter shape
                    (0x1A, 0x04),  # AGC time constant
                ):
                    if self._profile.supports_cmd29(cmd_byte, sub_byte):
                        queries.append((cmd_byte, sub_byte, receiver))
        queries.extend(
            [
                (0x1C, 0x00, None),  # PTT (global)
                (0x1C, 0x01, None),  # Tuner/ATU status
                (0x1C, 0x03, None),  # TX frequency monitor
                (0x14, 0x0A, None),  # Power level (global)
                (0x0F, None, None),  # Split (global)
                (0x07, 0xD2, None),  # Active receiver
                (0x07, 0xC2, None),  # Dual Watch status
                (0x21, 0x00, None),  # RIT frequency
                (0x21, 0x01, None),  # RIT status
                (0x21, 0x02, None),  # RIT TX status
            ]
        )
        if self._profile.model == "IC-7610":
            queries.extend(
                [
                    (0x15, 0x07, None),  # Overflow status
                    (0x16, 0x12, None),  # AGC mode
                    (0x16, 0x44, None),  # Compressor status
                    (0x16, 0x45, None),  # Monitor status
                    (0x16, 0x46, None),  # VOX status
                    (0x16, 0x47, None),  # Break-in mode
                    (0x16, 0x50, None),  # Dial lock status
                    (0x16, 0x58, None),  # SSB TX bandwidth
                ]
            )
        return queries

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
                            logger.debug(
                                "radio-poller: cmd error: %s",
                                type(cmd).__name__,
                                exc_info=True,
                            )
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
                    logger.info(
                        "radio-poller: radio disconnected, backing off %.1fs", _backoff
                    )
                    continue
                except Exception:
                    logger.debug("radio-poller: query error", exc_info=True)

                # 3. Wait for next cycle
                await self._queue.wait(timeout=_FAST_INTERVAL)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception(
                "radio-poller: FATAL — task crashed, commands will stop working"
            )

    async def _civ(
        self,
        cmd: int,
        *,
        sub: int | None = None,
        data: bytes = b"",
        wait_response: bool = False,
    ) -> None:
        """Send a raw CI-V command if the backend provides a CI-V transport.

        For non-Icom backends this is a no-op — scope/meter polling simply
        won't happen, which is acceptable.
        """
        from ..radio_protocol import CivCommandCapable

        if isinstance(self._radio, CivCommandCapable):
            await self._radio.send_civ(
                cmd,
                sub=sub,
                data=data,
                wait_response=wait_response,
            )

    def _current_active(self) -> str:
        """Return current active receiver ('MAIN' or 'SUB') from RadioState."""
        rs = getattr(self._radio, "_radio_state", None)
        _active = getattr(rs, "active", None) if rs is not None else None
        return _active if isinstance(_active, str) else "MAIN"

    async def _execute(self, cmd: Command) -> None:
        radio = self._radio
        from ..radio_protocol import (
            AdvancedControlCapable,
            DualReceiverCapable,
            LevelsCapable,
            PowerControlCapable,
            ScopeCapable,
        )

        match cmd:
            case SetFreq(freq=freq, receiver=rx):
                self._ensure_receiver_supported(rx, operation="set_freq")
                current = self._current_active()
                if rx != 0 and self._profile.supports_cmd29(0x05):
                    await radio.set_frequency(freq, receiver=rx)
                elif rx != 0:
                    if (
                        self._profile.vfo_sub_code is None
                        or self._profile.vfo_main_code is None
                    ):
                        raise CommandError(
                            f"set_freq receiver={rx} is unsupported by profile {self._profile.model}: "
                            "no cmd29 route and no VFO switch codes"
                        )
                    if current != "SUB":
                        await self._civ(0x07, data=bytes([self._profile.vfo_sub_code]))
                        await asyncio.sleep(_GAP)
                    await radio.set_frequency(freq)
                    if current != "SUB":
                        await asyncio.sleep(_GAP)
                        await self._civ(0x07, data=bytes([self._profile.vfo_main_code]))
                else:
                    if current != "MAIN" and self._profile.vfo_main_code is not None:
                        await self._civ(0x07, data=bytes([self._profile.vfo_main_code]))
                        await asyncio.sleep(_GAP)
                    await radio.set_frequency(freq)
                    if current != "MAIN" and self._profile.vfo_sub_code is not None:
                        await asyncio.sleep(_GAP)
                        await self._civ(0x07, data=bytes([self._profile.vfo_sub_code]))
            case SetMode(mode=mode, filter_width=fw, receiver=rx):
                self._ensure_receiver_supported(rx, operation="set_mode")
                current = self._current_active()
                if rx != 0 and self._profile.supports_cmd29(0x06):
                    await radio.set_mode(mode, fw, receiver=rx)
                elif rx != 0:
                    if (
                        self._profile.vfo_sub_code is None
                        or self._profile.vfo_main_code is None
                    ):
                        raise CommandError(
                            f"set_mode receiver={rx} is unsupported by profile {self._profile.model}: "
                            "no cmd29 route and no VFO switch codes"
                        )
                    if current != "SUB":
                        await self._civ(0x07, data=bytes([self._profile.vfo_sub_code]))
                        await asyncio.sleep(_GAP)
                    await radio.set_mode(mode, fw)
                    if current != "SUB":
                        await asyncio.sleep(_GAP)
                        await self._civ(0x07, data=bytes([self._profile.vfo_main_code]))
                else:
                    if current != "MAIN" and self._profile.vfo_main_code is not None:
                        await self._civ(0x07, data=bytes([self._profile.vfo_main_code]))
                        await asyncio.sleep(_GAP)
                    await radio.set_mode(mode, fw)
                    if current != "MAIN" and self._profile.vfo_sub_code is not None:
                        await asyncio.sleep(_GAP)
                        await self._civ(0x07, data=bytes([self._profile.vfo_sub_code]))
            case SetFilter(filter_num=fn, receiver=rx):
                if isinstance(radio, AdvancedControlCapable):
                    self._ensure_receiver_supported(rx, operation="set_filter")
                    await radio.set_filter(fn, receiver=rx)
            case PttOn():
                logger.info("poller: PTT ON")
                # Start TX audio stream before PTT (LAN audio requires this)
                from ..radio_protocol import AudioCapable

                if isinstance(radio, AudioCapable):
                    try:
                        await radio.start_audio_tx_opus()
                        logger.info("poller: TX audio stream started")
                    except Exception as e:
                        logger.warning("poller: start TX audio failed: %s", e)
                await radio.set_ptt(True)
            case PttOff():
                logger.info("poller: PTT OFF")
                await radio.set_ptt(False)
                # Stop TX audio stream after PTT, then restart RX
                from ..radio_protocol import AudioCapable

                if isinstance(radio, AudioCapable):
                    try:
                        await radio.stop_audio_tx()
                        logger.info("poller: TX audio stream stopped")
                        # Restart RX audio after TX (IC-7610 doesn't support full duplex)
                        await radio.start_audio_rx_opus()
                        logger.info("poller: RX audio stream restarted")
                    except Exception as e:
                        logger.debug("poller: audio stream transition failed: %s", e)
            case SetPower(level=level):
                if isinstance(radio, PowerControlCapable):
                    await radio.set_power(level)
            case SetRfGain(level=level, receiver=rx):
                if isinstance(radio, LevelsCapable):
                    self._ensure_receiver_supported(rx, operation="set_rf_gain")
                    await radio.set_rf_gain(level, receiver=rx)
            case SetAfLevel(level=level, receiver=rx):
                if isinstance(radio, LevelsCapable):
                    self._ensure_receiver_supported(rx, operation="set_af_level")
                    await radio.set_af_level(level, receiver=rx)
            case SetSquelch(level=level, receiver=rx):
                if isinstance(radio, LevelsCapable):
                    self._ensure_receiver_supported(rx, operation="set_squelch")
                    await radio.set_squelch(level, receiver=rx)
            case SetNB(on=on, receiver=rx):
                if isinstance(radio, AdvancedControlCapable):
                    self._ensure_receiver_supported(rx, operation="set_nb")
                    await radio.set_nb(on, receiver=rx)
                if self._on_state_event:
                    self._on_state_event("nb_changed", {"on": on})
            case SetNR(on=on, receiver=rx):
                if isinstance(radio, AdvancedControlCapable):
                    self._ensure_receiver_supported(rx, operation="set_nr")
                    await radio.set_nr(on, receiver=rx)
                if self._on_state_event:
                    self._on_state_event("nr_changed", {"on": on})
            case SetDigiSel(on=on, receiver=rx):
                if isinstance(radio, AdvancedControlCapable):
                    self._ensure_receiver_supported(rx, operation="set_digisel")
                    await radio.set_digisel(on, receiver=rx)
                if self._on_state_event:
                    self._on_state_event("digisel_changed", {"on": on})
            case SetIpPlus(on=on, receiver=rx):
                if isinstance(radio, AdvancedControlCapable):
                    self._ensure_receiver_supported(rx, operation="set_ipplus")
                    await radio.set_ip_plus(on, receiver=rx)
                if self._on_state_event:
                    self._on_state_event("ipplus_changed", {"on": on})
            case SetAttenuator(db=db, receiver=rx):
                if isinstance(radio, AdvancedControlCapable):
                    self._ensure_receiver_supported(rx, operation="set_attenuator")
                    await radio.set_attenuator_level(db, receiver=rx)
            case SetPreamp(level=level, receiver=rx):
                if isinstance(radio, AdvancedControlCapable):
                    self._ensure_receiver_supported(rx, operation="set_preamp")
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
                if is_sub:
                    self._ensure_receiver_supported(1, operation="select_vfo")
                current = self._current_active()
                need_swap = (is_sub and current == "MAIN") or (
                    not is_sub and current == "SUB"
                )
                if need_swap:
                    if self._profile.vfo_swap_code is None:
                        raise CommandError(
                            f"select_vfo({vfo}) is unsupported by profile {self._profile.model}: "
                            "no VFO swap code"
                        )
                    await self._civ(0x07, data=bytes([self._profile.vfo_swap_code]))
                    logger.info("radio-poller: VFO swap (Main<>Sub)")
                    rs = getattr(self._radio, "_radio_state", None)
                    if rs is not None and hasattr(rs, "active"):
                        rs.active = "SUB" if current == "MAIN" else "MAIN"
                if self._on_state_event:
                    self._on_state_event("vfo_changed", {"vfo": vfo})
            case VfoSwap():
                if isinstance(radio, DualReceiverCapable):
                    await cast(DualReceiverCapable, radio).vfo_exchange()
                # After swap, active VFO stays same but freqs are exchanged
                if self._on_state_event:
                    self._on_state_event("vfo_swapped", {})
            case VfoEqualize():
                if isinstance(radio, DualReceiverCapable):
                    await cast(DualReceiverCapable, radio).vfo_equalize()
            case EnableScope(policy=policy):
                if isinstance(radio, ScopeCapable):
                    await cast(ScopeCapable, radio).enable_scope(policy=policy)
                    logger.info("radio-poller: scope enabled")
            case DisableScope():
                if isinstance(radio, ScopeCapable):
                    await cast(ScopeCapable, radio).disable_scope()
                    logger.info("radio-poller: scope disabled")
            case SwitchScopeReceiver(receiver=receiver):
                # Fire-and-forget scope receiver select (0x27 0x12)
                self._ensure_receiver_supported(
                    receiver,
                    operation="switch_scope_receiver",
                )
                await self._civ(0x27, sub=0x12, data=bytes([receiver]))
                logger.info(
                    "radio-poller: scope receiver → %s",
                    "SUB" if receiver else "MAIN",
                )
            case SetScopeDuringTx(on=on):
                if isinstance(radio, ScopeCapable):
                    await radio.set_scope_during_tx(on)
            case SetScopeCenterType(center_type=center_type):
                if isinstance(radio, ScopeCapable):
                    await radio.set_scope_center_type(center_type)
            case SetScopeFixedEdge(edge=edge, start_hz=start_hz, end_hz=end_hz):
                if isinstance(radio, ScopeCapable):
                    await radio.set_scope_fixed_edge(
                        edge=edge,
                        start_hz=start_hz,
                        end_hz=end_hz,
                    )
            case SetPowerstat(on=on):
                if isinstance(radio, PowerControlCapable):
                    await radio.set_powerstat(on)
                    logger.info("radio-poller: power %s", "ON" if on else "OFF")
            case SetAntenna1(on=on):
                await radio.set_antenna_1(on)
            case SetAntenna2(on=on):
                await radio.set_antenna_2(on)
            case SetRxAntennaAnt1(on=on):
                await radio.set_rx_antenna_ant1(on)
            case SetRxAntennaAnt2(on=on):
                await radio.set_rx_antenna_ant2(on)
            case SetSystemDate(year=year, month=month, day=day):
                await radio.set_system_date(year, month, day)
            case SetSystemTime(hour=hour, minute=minute):
                await radio.set_system_time(hour, minute)
            case SetAcc1ModLevel(level=level):
                await radio.set_acc1_mod_level(level)
            case SetUsbModLevel(level=level):
                await radio.set_usb_mod_level(level)
            case SetLanModLevel(level=level):
                await radio.set_lan_mod_level(level)
            case SetDualWatch(on=on):
                await radio.set_dual_watch(on)
            case SetCompressor(on=on):
                await radio.set_compressor(on)

    # Fast: meters (polled on even cycles)
    # wfview: Priority=Highest, queue interval 25ms for LAN (HasFDComms)
    _FAST_CMDS: list[tuple[int, int | None]] = [
        (0x15, 0x02),  # S-meter
        (0x15, 0x11),  # RF power
        (0x15, 0x12),  # SWR
        (0x15, 0x13),  # ALC
        (0x15, 0x14),  # Compressor meter
        (0x15, 0x15),  # VD (voltage)
        (0x15, 0x16),  # Id (PA drain current)
    ]

    # State queries interleaved on odd cycles.
    # Tuple: (cmd, sub, receiver) where receiver=None means global query.
    # Populated per instance from runtime profile/capabilities.
    _STATE_QUERIES: list[tuple[int, int | None, int | None]] = []

    async def _send_query(self) -> None:
        # Even cycles → meter query; odd cycles → state query.
        if self._poll_index % 2 == 0:
            fast_idx = (self._poll_index // 2) % len(self._FAST_CMDS)
            cmd_byte, sub_byte = self._FAST_CMDS[fast_idx]
            await self._civ(cmd_byte, sub=sub_byte, data=b"")
        else:
            if not self._STATE_QUERIES:
                self._poll_index += 1
                return
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
