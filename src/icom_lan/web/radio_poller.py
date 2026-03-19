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
2. The CI-V RX loop receives all packets and projects them into RadioState.
3. RadioState is the canonical source of truth for web consumers.
4. Poll freshness stays local to the poller; broadcast events notify on changes.

DO NOT add request-response (await get_frequency, await get_mode, etc.)
to this module. If you need new data, add parsing to the CI-V RX path instead.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, cast

from ..commands import bcd_encode_value, filter_hz_to_index
from ..exceptions import CommandError
from ..exceptions import ConnectionError as RadioConnectionError
from ..profiles import RadioProfile, resolve_radio_profile

if TYPE_CHECKING:
    from ..radio_protocol import Radio
    from ..radio_state import RadioState

__all__ = [
    "RadioPoller",
    "CommandQueue",
    "SetAgcTimeConstant",
    "SetDataMode",
    "SetFilterWidth",
    "SetFilterShape",
    "SetPbtInner",
    "SetPbtOuter",
    "SetRitFrequency",
    "SetRitStatus",
    "SetRitTxStatus",
    "SetSplit",
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
_GAP_SERIAL: float = 0.050  # serial CI-V needs more breathing room
_SEND_TIMEOUT: float = 1.0
_DEFAULT_POLL_FIELD_TTL: float = 0.2
_FAST_INTERVAL: float = 0.025  # meters — wfview queue interval for LAN (25ms)
_FAST_INTERVAL_SERIAL: float = 0.100  # serial: 10 polls/sec for responsive meters
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
class SetFilterWidth:
    width: int
    receiver: int = 0


@dataclass(frozen=True, slots=True)
class SetFilterShape:
    shape: int
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
class SetPbtInner:
    level: int
    receiver: int = 0


@dataclass(frozen=True, slots=True)
class SetPbtOuter:
    level: int
    receiver: int = 0


@dataclass(frozen=True, slots=True)
class SetNRLevel:
    level: int
    receiver: int = 0


@dataclass(frozen=True, slots=True)
class SetNBLevel:
    level: int
    receiver: int = 0


@dataclass(frozen=True, slots=True)
class SetAutoNotch:
    on: bool
    receiver: int = 0


@dataclass(frozen=True, slots=True)
class SetManualNotch:
    on: bool
    receiver: int = 0


@dataclass(frozen=True, slots=True)
class SetNotchFilter:
    level: int


@dataclass(frozen=True, slots=True)
class SetAgcTimeConstant:
    value: int
    receiver: int = 0


@dataclass(frozen=True, slots=True)
class SetCwPitch:
    value: int


@dataclass(frozen=True, slots=True)
class SetDataMode:
    mode: int
    receiver: int = 0


@dataclass(frozen=True, slots=True)
class SetMicGain:
    level: int


@dataclass(frozen=True, slots=True)
class SetVox:
    on: bool


@dataclass(frozen=True, slots=True)
class SetCompressorLevel:
    level: int


@dataclass(frozen=True, slots=True)
class SetMonitor:
    on: bool


@dataclass(frozen=True, slots=True)
class SetMonitorGain:
    level: int


@dataclass(frozen=True, slots=True)
class SetDialLock:
    on: bool


@dataclass(frozen=True, slots=True)
class SetAgc:
    mode: int  # 1=FAST, 2=MID, 3=SLOW
    receiver: int = 0


@dataclass(frozen=True, slots=True)
class SetRitStatus:
    on: bool


@dataclass(frozen=True, slots=True)
class SetRitTxStatus:
    on: bool


@dataclass(frozen=True, slots=True)
class SetRitFrequency:
    freq: int


@dataclass(frozen=True, slots=True)
class SetSplit:
    on: bool


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
    | SetFilterWidth
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
    | SetPbtInner
    | SetPbtOuter
    | SetNRLevel
    | SetNBLevel
    | SetAutoNotch
    | SetManualNotch
    | SetNotchFilter
    | SetAgcTimeConstant
    | SetCwPitch
    | SetDataMode
    | SetMicGain
    | SetVox
    | SetCompressorLevel
    | SetMonitor
    | SetMonitorGain
    | SetDialLock
    | SetAgc
    | SetRitStatus
    | SetRitTxStatus
    | SetRitFrequency
    | SetSplit
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

    State is updated from the CI-V RX stream into RadioState,
    NOT from polling responses.
    """

    def __init__(
        self,
        radio: "Radio",
        command_queue: CommandQueue,
        legacy_queue: CommandQueue | None = None,
        *,
        on_state_event: Callable[[str, dict[str, Any]], None] | None = None,
        radio_state: "RadioState | None" = None,
    ) -> None:
        queue = legacy_queue if legacy_queue is not None else command_queue
        self._radio = radio
        self._radio_state = radio_state
        self._queue = queue
        self._on_state_event = on_state_event
        self._poll_index: int = 0
        self._revision: int = 0
        self._task: asyncio.Task[None] | None = None
        self._last_polled: dict[str, float] = {}
        self._caps: set[str] = self._radio_capabilities()
        self._profile: RadioProfile = self._runtime_profile()
        self._cmd_map: dict[str, tuple[int, ...]] = self._load_command_map()
        # Serial backends need slower polling to avoid flooding the CI-V link
        self._is_serial: bool = not self._profile.has_lan
        self._gap: float = _GAP_SERIAL if self._is_serial else _GAP
        self._fast_interval: float = (
            _FAST_INTERVAL_SERIAL if self._is_serial else _FAST_INTERVAL
        )
        self._FAST_CMDS = (
            self._FAST_CMDS_SERIAL if self._is_serial else self._FAST_CMDS_LAN
        )
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

    def mark_polled(self, field: str) -> None:
        """Record the last successful poll time for a logical field."""
        self._last_polled[field] = time.monotonic()

    def state_is_fresh(self, field: str, ttl: float = _DEFAULT_POLL_FIELD_TTL) -> bool:
        """Return True if *field* was polled recently enough to skip re-query."""
        last = self._last_polled.get(field)
        return last is not None and (time.monotonic() - last) < ttl

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

    def _load_command_map(self) -> dict[str, tuple[int, ...]]:
        """Load command wire bytes from TOML rig profile."""
        try:
            from pathlib import Path

            from ..rig_loader import discover_rigs

            for rig_dir in [
                Path(__file__).resolve().parent.parent.parent.parent / "rigs",
                Path(__file__).resolve().parent.parent / "rigs",
            ]:
                if rig_dir.is_dir():
                    rigs = discover_rigs(rig_dir)
                    for _model, rig_config in rigs.items():
                        if rig_config.model == self._profile.model:
                            return rig_config.commands
        except Exception:
            logger.debug("radio-poller: failed to load command map", exc_info=True)
        return {}

    async def _send_cmd(
        self,
        cmd_name: str,
        data: bytes = b"",
        *,
        receiver: int = 0,
    ) -> bool:
        """Send a command using wire bytes from TOML profile.

        Returns True if command was found and sent, False otherwise.
        """
        wire = self._cmd_map.get(cmd_name)
        if not wire:
            logger.debug("radio-poller: command %s not in profile", cmd_name)
            return False
        cmd = wire[0]
        sub = wire[1] if len(wire) > 1 else None
        extra = bytes(wire[2:]) if len(wire) > 2 else b""
        payload = extra + data
        if receiver != 0 and self._profile.supports_cmd29(cmd, sub):
            inner = bytes([receiver, cmd])
            if sub is not None:
                inner += bytes([sub])
            await self._civ(0x29, data=inner + payload)
        else:
            await self._civ(cmd, sub=sub, data=payload)
        return True

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
            # Freq/mode are needed even on serial — for initial state and
            # to pick up filter/attenuator/preamp that don't come via
            # transceive.  The slow cycle handles them at SLOW_INTERVAL.
            queries.append((0x25, None, receiver))  # frequency
            queries.append((0x26, None, receiver))  # mode
            # Per-receiver state queries.  On dual-receiver radios these use
            # cmd29 wrapping.  On single-receiver radios without cmd29 we send
            # plain CI-V queries (receiver=None).
            _PER_RX_QUERIES: list[tuple[str, int, int | None]] = [
                ("attenuator", 0x11, None),
                ("af_level", 0x14, 0x01),
                ("rf_gain", 0x14, 0x02),
                ("squelch", 0x14, 0x03),
                ("preamp", 0x16, 0x02),
                ("nb", 0x16, 0x22),
                ("nr", 0x16, 0x40),
                ("digisel", 0x16, 0x4E),
                ("ip_plus", 0x16, 0x65),
                ("filter_width", 0x1A, 0x03),
            ]
            for cap, cmd_byte, sub_byte in _PER_RX_QUERIES:
                if not self._supports_capability(cap):
                    continue
                if self._profile.supports_cmd29(cmd_byte, sub_byte):
                    # Dual-receiver: cmd29-wrapped with receiver byte
                    queries.append((cmd_byte, sub_byte, receiver))
                elif receiver == 0:
                    # Single-receiver: plain CI-V query (only once, not per-rx)
                    queries.append((cmd_byte, sub_byte, None))
            if self._profile.model == "IC-7610":
                for cmd_byte, sub_byte in (
                    (0x15, 0x01),  # S-meter squelch status
                    (0x16, 0x12),  # AGC mode
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
        # Common feature queries (data-driven: if radio has the command, poll it)
        _COMMON_FEATURE_QUERIES = [
            (0x16, 0x44),  # Compressor status
            (0x16, 0x45),  # Monitor status
            (0x16, 0x46),  # VOX status
            (0x16, 0x47),  # Break-in mode
            (0x16, 0x50),  # Dial lock status
        ]
        if not self._profile.supports_cmd29(0x16, 0x12):
            _COMMON_FEATURE_QUERIES.insert(0, (0x16, 0x12))  # AGC mode
        # For serial: ALC/comp/VD/Id meters move to slow state queries
        # (they are NOT in _FAST_CMDS_SERIAL to keep S-meter responsive)
        if self._is_serial:
            _COMMON_FEATURE_QUERIES.extend(
                [
                    (0x15, 0x13),  # ALC meter
                    (0x15, 0x14),  # Compressor meter
                    (0x15, 0x15),  # VD (voltage)
                    (0x15, 0x16),  # Id (PA drain current)
                ]
            )
        for cmd, sub in _COMMON_FEATURE_QUERIES:
            queries.append((cmd, sub, None))

        if self._profile.model == "IC-7610":
            queries.extend(
                [
                    (0x15, 0x07, None),  # Overflow status
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
                        await asyncio.sleep(self._gap)

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
                await self._queue.wait(timeout=self._fast_interval)
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
    ) -> Any:
        """Send a raw CI-V command if the backend provides a CI-V transport.

        For non-Icom backends this is a no-op — scope/meter polling simply
        won't happen, which is acceptable.

        Returns:
            CivFrame response if wait_response=True and backend supports it,
            else None.
        """
        from ..radio_protocol import CivCommandCapable

        if isinstance(self._radio, CivCommandCapable):
            return await self._radio.send_civ(
                cmd,
                sub=sub,
                data=data,
                wait_response=wait_response,
            )
        return None

    def _current_active(self) -> str:
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
                    await radio.set_freq(freq, receiver=rx)
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
                        await asyncio.sleep(self._gap)
                    await radio.set_freq(freq)
                    if current != "SUB":
                        await asyncio.sleep(self._gap)
                        await self._civ(0x07, data=bytes([self._profile.vfo_main_code]))
                else:
                    if current != "MAIN" and self._profile.vfo_main_code is not None:
                        await self._civ(0x07, data=bytes([self._profile.vfo_main_code]))
                        await asyncio.sleep(self._gap)
                    await radio.set_freq(freq)
                    if current != "MAIN" and self._profile.vfo_sub_code is not None:
                        await asyncio.sleep(self._gap)
                        await self._civ(0x07, data=bytes([self._profile.vfo_sub_code]))
                # Optimistic state update for frequency
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    if target:
                        target.freq = freq
                    self.bump_revision()
                    self.mark_polled("freq")
                if self._on_state_event:
                    self._on_state_event("freq_changed", {"freq": freq, "receiver": rx})
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
                        await asyncio.sleep(self._gap)
                    await radio.set_mode(mode, fw)
                    if current != "SUB":
                        await asyncio.sleep(self._gap)
                        await self._civ(0x07, data=bytes([self._profile.vfo_main_code]))
                else:
                    if current != "MAIN" and self._profile.vfo_main_code is not None:
                        await self._civ(0x07, data=bytes([self._profile.vfo_main_code]))
                        await asyncio.sleep(self._gap)
                    await radio.set_mode(mode, fw)
                    if current != "MAIN" and self._profile.vfo_sub_code is not None:
                        await asyncio.sleep(self._gap)
                        await self._civ(0x07, data=bytes([self._profile.vfo_sub_code]))
                # Optimistic state update for mode
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    if target:
                        target.mode = mode
                    self.bump_revision()
                    self.mark_polled("mode")
                if self._on_state_event:
                    self._on_state_event("mode_changed", {"mode": mode, "receiver": rx})
            case SetFilter(filter_num=fn, receiver=rx):
                if isinstance(radio, AdvancedControlCapable):
                    self._ensure_receiver_supported(rx, operation="set_filter")
                    await radio.set_filter(fn, receiver=rx)
            case SetFilterWidth(width=width, receiver=rx):
                self._ensure_receiver_supported(rx, operation="set_filter_width")
                if not 50 <= width <= 10000:
                    raise CommandError(
                        f"set_filter_width value must be 50-10000 Hz, got {width}"
                    )
                target = (
                    self._radio_state.sub
                    if self._radio_state and rx != 0
                    else self._radio_state.main if self._radio_state else None
                )
                mode_name = getattr(target, "mode", None)
                data_mode = int(getattr(target, "data_mode", 0) or 0)
                rule = self._profile.resolve_filter_rule(mode_name, data_mode=data_mode)
                min_hz = self._profile.filter_width_min
                max_hz = self._profile.filter_width_max
                if rule is not None:
                    if rule.fixed:
                        raise CommandError(
                            "set_filter_width is unsupported for fixed-width mode "
                            f"{mode_name}"
                        )
                    if rule.min_hz is not None:
                        min_hz = rule.min_hz
                    if rule.max_hz is not None:
                        max_hz = rule.max_hz
                if not min_hz <= width <= max_hz:
                    raise CommandError(
                        f"set_filter_width value must be {min_hz}-{max_hz} Hz for {mode_name}, got {width}"
                    )

                clamped = min(width, 9999)
                payload_value = clamped
                if self._profile.filter_width_encoding == "segmented_bcd_index":
                    if rule is None or not rule.segments:
                        raise CommandError(
                            f"set_filter_width has no filter-width mapping for mode {mode_name}"
                        )
                    try:
                        payload_value = filter_hz_to_index(
                            clamped, segments=rule.segments
                        )
                    except ValueError as exc:
                        raise CommandError(str(exc)) from exc

                bcd_index_byte = bcd_encode_value(payload_value, byte_count=1)
                # CI-V 1A 03 SET format: <FIL_number> <width_index_BCD>
                # FIL number: 01=FIL1, 02=FIL2, 03=FIL3
                current_filter = 1
                if self._radio_state:
                    t = (
                        self._radio_state.sub if rx != 0
                        else self._radio_state.main
                    )
                    current_filter = getattr(t, "filter", 1) or 1
                logger.info(
                    "set_filter_width: mode=%s, width=%d Hz, index=%d, "
                    "bcd=0x%s, rx=%d",
                    mode_name, width, payload_value,
                    bcd_index_byte.hex(), rx,
                )
                # CI-V 1A 03: 1-byte BCD index, cmd29-wrapped for receiver
                if self._profile.supports_cmd29(0x1A, 0x03):
                    await self._civ(
                        0x29, data=bytes([rx, 0x1A, 0x03]) + bcd_index_byte
                    )
                else:
                    await self._civ(0x1A, sub=0x03, data=bcd_index_byte)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.filter_width = width
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event(
                        "filter_width_changed", {"width": width, "receiver": rx}
                    )
            case SetFilterShape(shape=shape, receiver=rx):
                self._ensure_receiver_supported(rx, operation="set_filter_shape")
                if shape not in (0, 1):
                    raise CommandError(
                        f"set_filter_shape value must be 0 or 1, got {shape}"
                    )
                if not isinstance(radio, AdvancedControlCapable):
                    raise CommandError(
                        "set_filter_shape is not supported by this backend"
                    )
                await radio.set_filter_shape(shape, receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.filter_shape = shape
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event(
                        "filter_shape_changed", {"shape": shape, "receiver": rx}
                    )
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
                        async def _noop_rx(_pkt: Any) -> None:
                            pass

                        await radio.start_audio_rx_opus(_noop_rx)
                        logger.info("poller: RX audio stream restarted")
                    except Exception as e:
                        logger.debug("poller: audio stream transition failed: %s", e)
            case SetPower(level=level):
                if isinstance(radio, PowerControlCapable):
                    await radio.set_rf_power(level)
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
                self._ensure_receiver_supported(rx, operation="set_nb")
                if hasattr(radio, "set_nb"):
                    await radio.set_nb(on, receiver=rx)
                else:
                    await self._send_cmd(
                        "set_nb",
                        bytes([0x01 if on else 0x00]),
                        receiver=rx,
                    )
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.nb = on
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event("nb_changed", {"on": on, "receiver": rx})
            case SetNR(on=on, receiver=rx):
                self._ensure_receiver_supported(rx, operation="set_nr")
                if hasattr(radio, "set_nr"):
                    await radio.set_nr(on, receiver=rx)
                else:
                    await self._send_cmd(
                        "set_nr",
                        bytes([0x01 if on else 0x00]),
                        receiver=rx,
                    )
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.nr = on
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event("nr_changed", {"on": on, "receiver": rx})
            case SetDigiSel(on=on, receiver=rx):
                if hasattr(radio, "set_digisel"):
                    self._ensure_receiver_supported(rx, operation="set_digisel")
                    await radio.set_digisel(on, receiver=rx)
                if self._on_state_event:
                    self._on_state_event("digisel_changed", {"on": on, "receiver": rx})
            case SetIpPlus(on=on, receiver=rx):
                if hasattr(radio, "set_ip_plus"):
                    self._ensure_receiver_supported(rx, operation="set_ipplus")
                    await radio.set_ip_plus(on, receiver=rx)
                if self._on_state_event:
                    self._on_state_event("ipplus_changed", {"on": on, "receiver": rx})
            case SetAttenuator(db=db, receiver=rx):
                if hasattr(radio, "set_attenuator_level"):
                    self._ensure_receiver_supported(rx, operation="set_attenuator")
                    await radio.set_attenuator_level(db, receiver=rx)
                else:
                    # Wire bytes from TOML: set_attenuator = [0x11]
                    bcd = ((db // 10) << 4) | (db % 10)
                    await self._send_cmd("set_attenuator", bytes([bcd]), receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.att = db
                    if db > 0:
                        target.preamp = 0
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event(
                        "attenuator_changed", {"db": db, "receiver": rx}
                    )
            case SetPreamp(level=level, receiver=rx):
                if hasattr(radio, "set_preamp"):
                    self._ensure_receiver_supported(rx, operation="set_preamp")
                    await radio.set_preamp(level, receiver=rx)
                else:
                    # Wire bytes from TOML: set_preamp = [0x16, 0x02]
                    await self._send_cmd("set_preamp", bytes([level]), receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.preamp = level
                    if level > 0:
                        target.att = 0
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event(
                        "preamp_changed", {"level": level, "receiver": rx}
                    )
            case SetPbtInner(level=level, receiver=rx):
                await radio.set_pbt_inner(level, receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.pbt_inner = level
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event(
                        "pbt_inner_changed", {"level": level, "receiver": rx}
                    )
            case SetPbtOuter(level=level, receiver=rx):
                await radio.set_pbt_outer(level, receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.pbt_outer = level
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event(
                        "pbt_outer_changed", {"level": level, "receiver": rx}
                    )
            case SetNRLevel(level=level, receiver=rx):
                await radio.set_nr_level(level, receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.nr_level = level
                    self.bump_revision()
            case SetNBLevel(level=level, receiver=rx):
                await radio.set_nb_level(level, receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.nb_level = level
                    self.bump_revision()
            case SetAutoNotch(on=on, receiver=rx):
                await radio.set_auto_notch(on, receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.auto_notch = on
                    self.bump_revision()
            case SetManualNotch(on=on, receiver=rx):
                await radio.set_manual_notch(on, receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.manual_notch = on
                    self.bump_revision()
            case SetNotchFilter(level=level):
                await radio.set_notch_filter(level)
                if self._radio_state:
                    self._radio_state.notch_filter = level
                    self.bump_revision()
            case SetAgcTimeConstant(value=value, receiver=rx):
                await radio.set_agc_time_constant(value, receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.agc_time_constant = value
                    self.bump_revision()
            case SetCwPitch(value=value):
                await radio.set_cw_pitch(value)
                if self._radio_state:
                    self._radio_state.cw_pitch = value
                    self.bump_revision()
            case SetDataMode(mode=mode, receiver=rx):
                self._ensure_receiver_supported(rx, operation="set_data_mode")
                if not 0 <= mode <= 3:
                    raise CommandError(f"set_data_mode mode must be 0-3, got {mode}")
                await radio.set_data_mode(mode, receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.data_mode = mode
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event(
                        "data_mode_changed", {"mode": mode, "receiver": rx}
                    )
            case SetMicGain(level=level):
                await radio.set_mic_gain(level)
                if self._radio_state:
                    self._radio_state.mic_gain = level
                    self.bump_revision()
            case SetVox(on=on):
                await radio.set_vox(on)
                if self._radio_state:
                    self._radio_state.vox_on = on
                    self.bump_revision()
            case SetCompressorLevel(level=level):
                await radio.set_compressor_level(level)
                if self._radio_state:
                    self._radio_state.compressor_level = level
                    self.bump_revision()
            case SetMonitor(on=on):
                await radio.set_monitor(on)
                if self._radio_state:
                    self._radio_state.monitor_on = on
                    self.bump_revision()
            case SetMonitorGain(level=level):
                await radio.set_monitor_gain(level)
                if self._radio_state:
                    self._radio_state.monitor_gain = level
                    self.bump_revision()
            case SetDialLock(on=on):
                await radio.set_dial_lock(on)
                if self._radio_state:
                    self._radio_state.dial_lock = on
                    self.bump_revision()
            case SetAgc(mode=mode, receiver=rx):
                if hasattr(radio, "set_agc"):
                    self._ensure_receiver_supported(rx, operation="set_agc")
                    await radio.set_agc(mode, receiver=rx)
                else:
                    # Wire bytes from TOML: set_agc = [0x16, 0x12]
                    await self._send_cmd("set_agc", bytes([mode]), receiver=rx)
                if self._radio_state:
                    target = (
                        self._radio_state.sub if rx != 0 else self._radio_state.main
                    )
                    target.agc = mode
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event("agc_changed", {"mode": mode, "receiver": rx})
            case SetRitStatus(on=on):
                await radio.set_rit_status(on)
                if self._radio_state:
                    self._radio_state.rit_on = on
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event("rit_changed", {"on": on})
            case SetRitTxStatus(on=on):
                await radio.set_rit_tx_status(on)
                if self._radio_state:
                    self._radio_state.rit_tx = on
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event("rit_tx_changed", {"on": on})
            case SetRitFrequency(freq=freq):
                await radio.set_rit_frequency(freq)
                if self._radio_state:
                    self._radio_state.rit_freq = freq
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event("rit_freq_changed", {"hz": freq})
            case SetSplit(on=on):
                await radio.set_split_mode(on)
                if self._radio_state:
                    self._radio_state.split = on
                    self.bump_revision()
                if self._on_state_event:
                    self._on_state_event("split_changed", {"on": on})
            case SetBand(band=band):
                # Band Stack Register recall: 0x1A 0x01 <bsr_code> <register>
                # Read stored freq/mode from register 01 (latest)
                from ..commands import bcd_decode
                from ..types import Mode as CivMode

                bsr_ok = False
                try:
                    resp = await self._civ(
                        0x1A,
                        sub=0x01,
                        data=bytes([band, 0x01]),
                        wait_response=True,
                    )
                    if (
                        resp
                        and hasattr(resp, "data")
                        and resp.data
                        and len(resp.data) >= 8
                    ):
                        # BSR response: [1A 01 band reg] freq(5 BCD) mode filter ...
                        # Skip first 2 bytes (band + register) to get freq
                        freq = bcd_decode(resp.data[2:7])
                        mode_code = resp.data[7]
                        filter_num = resp.data[8] if len(resp.data) > 8 else 1
                        try:
                            mode_name = CivMode(mode_code).name.replace("_", "-")
                        except ValueError:
                            mode_name = "USB"
                        logger.info(
                            "BSR recall: band=%d freq=%d mode=%s fil=%d",
                            band,
                            freq,
                            mode_name,
                            filter_num,
                        )
                        await radio.set_freq(freq)
                        await asyncio.sleep(self._gap)
                        await radio.set_mode(mode_name, filter_num)
                        # Update local state immediately (don't wait for transceive echo)
                        if self._radio_state:
                            target = self._radio_state.main
                            if target:
                                target.freq = freq
                                target.mode = mode_name
                            self.bump_revision()
                            self.mark_polled("freq")
                            self.mark_polled("mode")
                        if self._on_state_event:
                            self._on_state_event(
                                "freq_changed", {"freq": freq, "receiver": 0}
                            )
                            self._on_state_event(
                                "mode_changed", {"mode": mode_name, "receiver": 0}
                            )
                        bsr_ok = True
                except Exception:
                    logger.debug("BSR recall failed", exc_info=True)

                if not bsr_ok:
                    # Fallback: set default freq from rig profile
                    default_freq: int | None = None
                    for fr in self._profile.freq_ranges:
                        for bi in fr.bands:
                            if bi.bsr_code == band:
                                default_freq = bi.default
                                break
                        if default_freq is not None:
                            break
                    if default_freq is not None:
                        logger.info(
                            "BSR fallback: band=%d → freq=%d", band, default_freq
                        )
                        await radio.set_freq(default_freq)
                    else:
                        logger.warning("set_band: unknown bsr_code=%d", band)
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
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_antenna_1(on)
            case SetAntenna2(on=on):
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_antenna_2(on)
            case SetRxAntennaAnt1(on=on):
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_rx_antenna_ant1(on)
            case SetRxAntennaAnt2(on=on):
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_rx_antenna_ant2(on)
            case SetSystemDate(year=year, month=month, day=day):
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_system_date(year, month, day)
            case SetSystemTime(hour=hour, minute=minute):
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_system_time(hour, minute)
            case SetAcc1ModLevel(level=level):
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_acc1_mod_level(level)
            case SetUsbModLevel(level=level):
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_usb_mod_level(level)
            case SetLanModLevel(level=level):
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_lan_mod_level(level)
            case SetDualWatch(on=on):
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_dual_watch(on)
            case SetCompressor(on=on):
                if isinstance(radio, AdvancedControlCapable):
                    await radio.set_compressor(on)

    # Fast: meters (polled on even cycles)
    # wfview: Priority=Highest, queue interval 25ms for LAN (HasFDComms)
    # For serial: only high-priority meters to keep S-meter responsive.
    _FAST_CMDS_LAN: list[tuple[int, int | None]] = [
        (0x15, 0x02),  # S-meter
        (0x15, 0x11),  # RF power
        (0x15, 0x12),  # SWR
        (0x15, 0x13),  # ALC
        (0x15, 0x14),  # Compressor meter
        (0x15, 0x15),  # VD (voltage)
        (0x15, 0x16),  # Id (PA drain current)
    ]
    _FAST_CMDS_SERIAL: list[tuple[int, int | None]] = [
        (0x15, 0x02),  # S-meter — polled every cycle for responsiveness
        (0x15, 0x11),  # RF power
        (0x15, 0x02),  # S-meter again (2:1 ratio vs other meters)
        (0x15, 0x12),  # SWR
    ]
    _FAST_CMDS: list[tuple[int, int | None]] = _FAST_CMDS_LAN  # class default

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
