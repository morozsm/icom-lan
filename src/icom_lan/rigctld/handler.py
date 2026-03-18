"""Rigctld command handler — dispatches parsed commands to IcomRadio.

Responsibilities:
- Command dispatch table (long_cmd → async handler method)
- Read-only gate (reject set commands with RPRT -22)
- RadioState-first reads with a small handler-local fallback cache
- Error translation (icom-lan exceptions → Hamlib error codes)

This module receives RigctldCommand from protocol.py and returns
RigctldResponse. It calls IcomRadio methods but knows nothing about
TCP or wire format.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from ..exceptions import ConnectionError, TimeoutError
from ..radio_state import RadioState, ReceiverState
from ..types import Mode
from .contract import (
    CIV_TO_HAMLIB_MODE,
    HAMLIB_MODE_MAP,
    HamlibError,
    RigctldCommand,
    RigctldConfig,
    RigctldResponse,
)
from .utils import get_mode_reader

if TYPE_CHECKING:
    from ..radio_protocol import Radio

from ..radio_protocol import MetersCapable

__all__ = ["RigctldHandler"]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# IC-7610 hardcoded dump_state (hamlib protocol v0 positional format)
# ---------------------------------------------------------------------------
# hamlib netrigctl.c parses dump_state as POSITIONAL bare values via atol/sscanf.
# NO 'key: value' pairs — just bare numbers/strings, one per list entry.
#
# Mode bits (RIG_MODE_*): AM=0x01 CW=0x02 USB=0x04 LSB=0x08 RTTY=0x10
#                          FM=0x20 WFM=0x40 CWR=0x80 RTTYR=0x100
# 0x1ff = all nine modes above
#
# has_get_level: RIG_LEVEL_STRENGTH(0x40000000) | RIG_LEVEL_SWR(0x10000000)
#              | RIG_LEVEL_ALC(0x04000000) | RIG_LEVEL_RFPOWER(0x00001000)
#              = 0x54001000
_IC7610_DUMP_STATE: list[str] = [
    "0",  # protocol version
    "3078",  # rig model (IC-7610)
    "1",  # ITU region
    "100000.000000 60000000.000000 0x1ff -1 -1 0x3 0xf",  # RX range
    "0 0 0 0 0 0 0",  # end of RX ranges
    "1800000.000000 60000000.000000 0x1ff 5000 100000 0x3 0xf",  # TX range
    "0 0 0 0 0 0 0",  # end of TX ranges
    "0x1ff 1",  # tuning step (all modes, 1 Hz)
    "0 0",  # end of tuning steps
    "0x1ff 3000",  # filter: wide 3000 Hz
    "0x1ff 2400",  # filter: normal 2400 Hz
    "0x1ff 1800",  # filter: narrow 1800 Hz
    "0 0",  # end of filters
    "0",  # max_rit
    "0",  # max_xit
    "0",  # max_ifshift
    "0",  # announces
    "12 20 0",  # preamp (dB values, 0-terminated)
    "6 12 18 0",  # attenuator (dB values, 0-terminated)
    "0",  # has_get_func
    "0",  # has_set_func
    "0x54001000",  # has_get_level (STRENGTH|SWR|ALC|RFPOWER)
    "0x00001000",  # has_set_level (RFPOWER)
    "0",  # has_get_parm
    "0",  # has_set_parm
]

# Filter number → approximate passband in Hz (IC-7610 USB defaults)
_FILTER_TO_PASSBAND: dict[int, int] = {1: 3000, 2: 2400, 3: 1800}


def _filter_to_passband(filt: int | None) -> int:
    """Convert IC-7610 filter number to passband Hz (0 = radio default)."""
    if filt is None:
        return 0
    return _FILTER_TO_PASSBAND.get(filt, 0)


def _passband_to_filter(passband_hz: int) -> int | None:
    """Convert passband in Hz to the nearest IC-7610 filter number."""
    if passband_hz <= 0:
        return None
    if passband_hz >= 2800:
        return 1
    if passband_hz >= 2000:
        return 2
    return 3


def _ok() -> RigctldResponse:
    return RigctldResponse(error=HamlibError.OK)


def _err(code: HamlibError) -> RigctldResponse:
    return RigctldResponse(error=code)


def _mode_to_hamlib_str(mode: object) -> str:
    """Normalize backend mode values to a hamlib-compatible string."""
    if isinstance(mode, Mode):
        return CIV_TO_HAMLIB_MODE.get(mode.value, mode.name)
    if isinstance(mode, str):
        return mode.upper()
    name = getattr(mode, "name", None)
    if isinstance(name, str):
        return name.upper()
    value = getattr(mode, "value", None)
    if isinstance(value, int):
        return CIV_TO_HAMLIB_MODE.get(value, "USB")
    return str(mode).upper()


@dataclass(slots=True)
class _PendingRigState:
    """Local optimistic write-through state until RadioState catches up."""

    freq: int | None = None
    mode: str | None = None
    filter_width: int | None = None
    data_mode: bool | None = None


@dataclass(slots=True)
class _FallbackRigState:
    """Handler-local fallback values used only until RadioState becomes valid."""

    freq: int = 0
    freq_ts: float = 0.0
    mode: str = "USB"
    filter_width: int | None = None
    mode_ts: float = 0.0
    data_mode: bool = False
    data_mode_ts: float = 0.0
    ptt: bool = False
    ptt_ts: float = 0.0
    s_meter: int | None = None
    s_meter_ts: float = 0.0
    rf_power: float | None = None
    rf_power_ts: float = 0.0
    swr: float | None = None
    swr_ts: float = 0.0

    def is_fresh(self, field: str, ttl: float | None) -> bool:
        if ttl is None or ttl <= 0.0:
            return False
        ts = getattr(self, f"{field}_ts", 0.0)
        return ts > 0.0 and (time.monotonic() - ts) < ttl

    def update_freq(self, freq: int) -> None:
        self.freq = freq
        self.freq_ts = time.monotonic()

    def update_mode(self, mode: str, filter_width: int | None) -> None:
        self.mode = mode
        self.filter_width = filter_width
        self.mode_ts = time.monotonic()

    def update_data_mode(self, on: bool) -> None:
        self.data_mode = on
        self.data_mode_ts = time.monotonic()

    def update_ptt(self, on: bool) -> None:
        self.ptt = on
        self.ptt_ts = time.monotonic()

    def update_s_meter(self, raw: int) -> None:
        self.s_meter = raw
        self.s_meter_ts = time.monotonic()

    def update_rf_power(self, value: float) -> None:
        self.rf_power = value
        self.rf_power_ts = time.monotonic()

    def update_swr(self, value: float) -> None:
        self.swr = value
        self.swr_ts = time.monotonic()


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


class RigctldHandler:
    """Dispatches parsed rigctld commands to IcomRadio.

    Args:
        radio: Connected IcomRadio instance.
        config: Server configuration (read_only, cache_ttl, etc.).
    """

    def __init__(
        self,
        radio: "Radio",
        config: RigctldConfig,
    ) -> None:
        self._radio = radio
        self._config = config
        self._ptt_state: bool | None = None
        self._cache = _FallbackRigState()
        self._pending = _PendingRigState()

    def _radio_state(self) -> RadioState | None:
        state = getattr(self._radio, "radio_state", None)
        return state if isinstance(state, RadioState) else None

    def _main_receiver_state(self) -> ReceiverState | None:
        state = self._radio_state()
        if state is None or state.main.freq <= 0:
            return None
        return state.main

    def _effective_pending_freq(self, main_state: ReceiverState | None) -> int | None:
        pending_freq = self._pending.freq
        if pending_freq is None:
            return None
        if main_state is not None and main_state.freq == pending_freq:
            self._pending.freq = None
            return None
        return pending_freq

    def _effective_pending_mode(
        self, main_state: ReceiverState | None
    ) -> tuple[str, int, bool] | None:
        pending_mode = self._pending.mode
        if pending_mode is None:
            return None

        pending_filter = self._pending.filter_width
        pending_data_mode = self._pending.data_mode

        if main_state is not None:
            state_mode = main_state.mode.upper()
            state_filter = main_state.filter
            state_data_mode = main_state.data_mode
            if (
                state_mode == pending_mode
                and state_filter == pending_filter
                and (pending_data_mode is None or state_data_mode == pending_data_mode)
            ):
                self._pending.mode = None
                self._pending.filter_width = None
                self._pending.data_mode = None
                return None

        data_mode = (
            pending_data_mode
            if pending_data_mode is not None
            else (
                main_state.data_mode
                if main_state is not None
                else self._cache.data_mode
            )
        )
        return pending_mode, _filter_to_passband(pending_filter), data_mode

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def execute(self, cmd: RigctldCommand) -> RigctldResponse:
        """Execute a parsed rigctld command and return the response.

        Args:
            cmd: Parsed command from the client.

        Returns:
            Response to send back.
        """
        # Read-only gate
        if self._config.read_only and cmd.is_set:
            logger.debug("read-only: rejecting set command %s", cmd.long_cmd)
            return _err(HamlibError.EACCESS)

        handler_fn = self._DISPATCH.get(cmd.long_cmd)
        if handler_fn is None:
            logger.debug("unimplemented command: %s", cmd.long_cmd)
            return _err(HamlibError.ENIMPL)

        try:
            return cast(RigctldResponse, await handler_fn(self, cmd))
        except ConnectionError:
            logger.warning("I/O error executing %s", cmd.long_cmd)
            return _err(HamlibError.EIO)
        except TimeoutError:
            logger.warning("Timeout executing %s", cmd.long_cmd)
            return _err(HamlibError.ETIMEOUT)
        except ValueError:
            logger.warning("Invalid value in %s", cmd.long_cmd)
            return _err(HamlibError.EINVAL)
        except Exception:
            logger.exception("Internal error executing %s", cmd.long_cmd)
            return _err(HamlibError.EINTERNAL)

    # ------------------------------------------------------------------
    # Frequency commands
    # ------------------------------------------------------------------

    async def _cmd_get_freq(self, cmd: RigctldCommand) -> RigctldResponse:
        main_state = self._main_receiver_state()
        pending_freq = self._effective_pending_freq(main_state)
        if pending_freq is not None:
            self._cache.update_freq(pending_freq)
            return RigctldResponse(values=[str(pending_freq)])
        if main_state is not None:
            self._cache.update_freq(main_state.freq)
            return RigctldResponse(values=[str(main_state.freq)])
        if self._cache.is_fresh("freq", self._config.cache_ttl):
            return RigctldResponse(values=[str(self._cache.freq)])
        freq = await self._radio.get_frequency()
        self._cache.update_freq(freq)
        return RigctldResponse(values=[str(freq)])

    async def _cmd_set_freq(self, cmd: RigctldCommand) -> RigctldResponse:
        if not cmd.args:
            return _err(HamlibError.EINVAL)
        try:
            freq = int(float(cmd.args[0]))
        except ValueError:
            return _err(HamlibError.EINVAL)
        await self._radio.set_frequency(freq)
        self._pending.freq = freq
        self._cache.update_freq(freq)
        return _ok()

    # ------------------------------------------------------------------
    # Mode commands
    # ------------------------------------------------------------------

    async def _cmd_get_mode(self, cmd: RigctldCommand) -> RigctldResponse:
        main_state = self._main_receiver_state()
        pending_mode = self._effective_pending_mode(main_state)
        if pending_mode is not None:
            mode_str, passband, data_mode = pending_mode
            self._cache.update_mode(mode_str, self._pending.filter_width)
            self._cache.update_data_mode(data_mode)
        elif main_state is not None:
            mode_str = main_state.mode.upper()
            passband = _filter_to_passband(main_state.filter)
            data_mode = main_state.data_mode
            self._cache.update_mode(mode_str, main_state.filter)
            self._cache.update_data_mode(data_mode)
        elif self._cache.is_fresh("mode", self._config.cache_ttl):
            mode_str = self._cache.mode
            passband = _filter_to_passband(self._cache.filter_width)
            data_mode = self._cache.data_mode
        else:
            get_mode = get_mode_reader(self._radio, _mode_to_hamlib_str)
            if get_mode is None:
                return _err(HamlibError.ENIMPL)
            mode_str, filt = await get_mode()
            self._cache.update_mode(mode_str, filt)
            passband = _filter_to_passband(filt)
            # Fetch data mode alongside mode to keep them in sync.
            try:
                data_mode = await self._radio.get_data_mode()
                self._cache.update_data_mode(data_mode)
            except Exception:
                logger.debug("get_data_mode failed, using cache", exc_info=True)
                data_mode = self._cache.data_mode

        # Map DATA overlays to packet modes where hamlib expects them.
        if data_mode:
            if mode_str == "USB":
                mode_str = "PKTUSB"
            elif mode_str == "LSB":
                mode_str = "PKTLSB"
            elif mode_str == "RTTY":
                mode_str = "PKTRTTY"

        return RigctldResponse(values=[mode_str, str(passband)])

    async def _cmd_set_mode(self, cmd: RigctldCommand) -> RigctldResponse:
        if not cmd.args:
            return _err(HamlibError.EINVAL)
        requested_mode = cmd.args[0].upper()
        if requested_mode not in HAMLIB_MODE_MAP:
            return _err(HamlibError.EINVAL)
        civ_val = HAMLIB_MODE_MAP[requested_mode]
        try:
            mode = Mode(civ_val)
        except ValueError:
            return _err(HamlibError.EINVAL)
        base_mode_str = CIV_TO_HAMLIB_MODE.get(mode.value, "USB")
        passband_hz = 0
        if len(cmd.args) >= 2:
            try:
                passband_hz = int(cmd.args[1])
            except ValueError:
                return _err(HamlibError.EINVAL)
        filter_width = _passband_to_filter(passband_hz)
        packet_modes = {"PKTUSB", "PKTLSB", "PKTRTTY"}

        await self._radio.set_mode(base_mode_str, filter_width=filter_width)

        # Only set DATA mode explicitly for packet modes.
        # For non-packet modes, avoid hidden side-effects (do not force DATA off).
        if requested_mode in packet_modes:
            await self._radio.set_data_mode(True)

            # Read-back sync: keep next get_mode deterministic for CAT clients.
            # Some radios acknowledge set-data quickly but reflect packet mode
            # with a short delay. We wait briefly to reduce client-side stalls.
            synced = False
            get_mode = get_mode_reader(self._radio, _mode_to_hamlib_str)
            if get_mode is not None:
                for _ in range(5):
                    try:
                        read_mode, _ = await get_mode()
                        read_data = await self._radio.get_data_mode()
                        if read_mode == base_mode_str and read_data:
                            synced = True
                            break
                    except Exception:
                        logger.debug("rigctld: sync poll failed", exc_info=True)
                    await asyncio.sleep(0.05)

            # Cache optimistic final state even if read-back lagged.
            self._cache.update_mode(base_mode_str, filter_width)
            self._cache.update_data_mode(True)
            self._pending.mode = base_mode_str
            self._pending.filter_width = filter_width
            self._pending.data_mode = True
            if not synced:
                logger.debug(
                    "set_mode(%s): packet read-back not fully synced yet; cached optimistic state",
                    requested_mode,
                )
        else:
            # For non-packet mode changes update mode cache, but preserve DATA
            # state (no forced DATA off side-effect).
            self._cache.update_mode(base_mode_str, filter_width)
            self._pending.mode = base_mode_str
            self._pending.filter_width = filter_width
            self._pending.data_mode = None

        return _ok()

    # ------------------------------------------------------------------
    # PTT commands
    # ------------------------------------------------------------------

    async def _cmd_get_ptt(self, cmd: RigctldCommand) -> RigctldResponse:
        state = self._radio_state()
        if state is not None:
            self._cache.update_ptt(state.ptt)
            if self._ptt_state is None:
                return RigctldResponse(values=[str(int(state.ptt))])
            if state.ptt == self._ptt_state:
                self._ptt_state = None
                return RigctldResponse(values=[str(int(state.ptt))])
            return RigctldResponse(values=[str(int(self._ptt_state))])
        return RigctldResponse(values=[str(int(bool(self._ptt_state)))])

    async def _cmd_set_ptt(self, cmd: RigctldCommand) -> RigctldResponse:
        if not cmd.args:
            return _err(HamlibError.EINVAL)
        try:
            on = bool(int(cmd.args[0]))
        except ValueError:
            return _err(HamlibError.EINVAL)
        await self._radio.set_ptt(on)
        self._ptt_state = on
        self._cache.update_ptt(on)
        return _ok()

    # ------------------------------------------------------------------
    # VFO commands
    # ------------------------------------------------------------------

    async def _cmd_get_vfo(self, cmd: RigctldCommand) -> RigctldResponse:
        return RigctldResponse(values=["VFOA"])

    async def _cmd_set_vfo(self, cmd: RigctldCommand) -> RigctldResponse:
        # Accept any VFO name; single-VFO operation always uses VFOA
        return _ok()

    # ------------------------------------------------------------------
    # Level commands
    # ------------------------------------------------------------------

    async def _cmd_get_level(self, cmd: RigctldCommand) -> RigctldResponse:
        if not cmd.args:
            return _err(HamlibError.EINVAL)
        level = cmd.args[0].upper()
        if level not in ("STRENGTH", "RFPOWER", "SWR"):
            return _err(HamlibError.EINVAL)
        main_state = self._main_receiver_state()
        if level == "STRENGTH" and main_state is not None:
            raw = main_state.s_meter
            self._cache.update_s_meter(raw)
            strength_db = round((raw / 241.0) * 114.0 - 54.0)
            return RigctldResponse(values=[str(strength_db)])
        if level == "RFPOWER":
            state = self._radio_state()
            if state is not None and main_state is not None:
                raw_power = state.power_level / 255.0
                self._cache.update_rf_power(raw_power)
                return RigctldResponse(values=[f"{raw_power:.6f}"])
        if not isinstance(self._radio, MetersCapable):
            # Return cached values if available, else unimplemented
            if level == "STRENGTH" and self._cache.s_meter is not None:
                raw = self._cache.s_meter
                strength_db = round((raw / 241.0) * 114.0 - 54.0)
                return RigctldResponse(values=[str(strength_db)])
            if level == "RFPOWER" and self._cache.rf_power is not None:
                return RigctldResponse(values=[f"{self._cache.rf_power:.6f}"])
            if level == "SWR" and self._cache.swr is not None:
                return RigctldResponse(values=[f"{self._cache.swr:.6f}"])
            return _err(HamlibError.ENIMPL)
        if level == "STRENGTH":
            raw = await self._radio.get_s_meter()
            self._cache.update_s_meter(raw)
            # IC-7610 S-meter: 0→S0(−54 dB), 120→S9(0 dB), 241→S9+60 dB
            strength_db = round((raw / 241.0) * 114.0 - 54.0)
            return RigctldResponse(values=[str(strength_db)])
        if level == "RFPOWER":
            raw = await self._radio.get_power()
            normalized = raw / 255.0
            self._cache.update_rf_power(normalized)
            return RigctldResponse(values=[f"{normalized:.6f}"])
        if level == "SWR":
            raw_val = await self._radio.get_swr()
            # Protocol returns float; backend may return int
            raw_swr: float = (
                float(raw_val) if isinstance(raw_val, (int, float)) else float(raw_val)
            )
            # Map 0-255 to 1.0-5.0
            swr = 1.0 + (raw_swr / 255.0) * 4.0
            self._cache.update_swr(swr)
            return RigctldResponse(values=[f"{swr:.6f}"])
        return _err(HamlibError.EINVAL)

    # ------------------------------------------------------------------
    # Split VFO commands
    # ------------------------------------------------------------------

    async def _cmd_get_split_vfo(self, cmd: RigctldCommand) -> RigctldResponse:
        state = self._radio_state()
        split = state.split if state is not None else False
        return RigctldResponse(values=[str(int(split)), "VFOA"])

    async def _cmd_set_split_vfo(self, cmd: RigctldCommand) -> RigctldResponse:
        return _ok()

    # ------------------------------------------------------------------
    # RIT
    # ------------------------------------------------------------------

    async def _cmd_get_rit(self, cmd: RigctldCommand) -> RigctldResponse:
        state = self._radio_state()
        rit = state.rit_freq if state is not None else 0
        return RigctldResponse(values=[str(rit)])

    # ------------------------------------------------------------------
    # Info / control commands
    # ------------------------------------------------------------------

    async def _cmd_dump_state(self, cmd: RigctldCommand) -> RigctldResponse:
        return RigctldResponse(values=list(_IC7610_DUMP_STATE))

    async def _cmd_dump_caps(self, cmd: RigctldCommand) -> RigctldResponse:
        return await self._cmd_dump_state(cmd)

    async def _cmd_get_info(self, cmd: RigctldCommand) -> RigctldResponse:
        raw_model = getattr(self._radio, "model", "IC-7610")
        model = raw_model if isinstance(raw_model, str) and raw_model else "IC-7610"
        return RigctldResponse(values=[f"Icom {model} (icom-lan)"])

    async def _cmd_chk_vfo(self, cmd: RigctldCommand) -> RigctldResponse:
        return RigctldResponse(values=["0"])

    async def _cmd_get_powerstat(self, cmd: RigctldCommand) -> RigctldResponse:
        return RigctldResponse(values=["1"])

    async def _cmd_quit(self, cmd: RigctldCommand) -> RigctldResponse:
        # Return OK; server.py detects cmd_echo == "quit" and closes the connection
        return RigctldResponse(values=[], error=HamlibError.OK, cmd_echo="quit")

    # ------------------------------------------------------------------
    # Power conversion (WSJT-X needs these)
    # ------------------------------------------------------------------

    _MAX_POWER_W: int = 100  # IC-7610 max power

    async def _cmd_power2mw(self, cmd: RigctldCommand) -> RigctldResponse:
        """Convert normalized power (0.0-1.0) to milliwatts.

        Args from rigctl: power_float freq mode (freq/mode ignored).
        """
        if not cmd.args:
            return _err(HamlibError.EINVAL)
        try:
            power = float(cmd.args[0])
        except ValueError:
            return _err(HamlibError.EINVAL)
        mw = int(power * self._MAX_POWER_W * 1000)
        return RigctldResponse(values=[str(mw)])

    async def _cmd_mw2power(self, cmd: RigctldCommand) -> RigctldResponse:
        """Convert milliwatts to normalized power (0.0-1.0).

        Args from rigctl: mw freq mode (freq/mode ignored).
        """
        if not cmd.args:
            return _err(HamlibError.EINVAL)
        try:
            mw = float(cmd.args[0])
        except ValueError:
            return _err(HamlibError.EINVAL)
        power = mw / (self._MAX_POWER_W * 1000)
        return RigctldResponse(values=[f"{power:.6f}"])

    async def _cmd_get_lock_mode(self, cmd: RigctldCommand) -> RigctldResponse:
        """Get lock mode — always unlocked."""
        return RigctldResponse(values=["0"])

    # ------------------------------------------------------------------
    # Dispatch table (populated after method definitions)
    # ------------------------------------------------------------------

    _DISPATCH: dict[str, Any] = {}  # filled below


# Build the dispatch table after the class is defined so all methods exist.
RigctldHandler._DISPATCH = {
    "get_freq": RigctldHandler._cmd_get_freq,
    "set_freq": RigctldHandler._cmd_set_freq,
    "get_mode": RigctldHandler._cmd_get_mode,
    "set_mode": RigctldHandler._cmd_set_mode,
    "get_ptt": RigctldHandler._cmd_get_ptt,
    "set_ptt": RigctldHandler._cmd_set_ptt,
    "get_vfo": RigctldHandler._cmd_get_vfo,
    "set_vfo": RigctldHandler._cmd_set_vfo,
    "get_level": RigctldHandler._cmd_get_level,
    "get_split_vfo": RigctldHandler._cmd_get_split_vfo,
    "set_split_vfo": RigctldHandler._cmd_set_split_vfo,
    "get_rit": RigctldHandler._cmd_get_rit,
    "dump_state": RigctldHandler._cmd_dump_state,
    "dump_caps": RigctldHandler._cmd_dump_caps,
    "get_info": RigctldHandler._cmd_get_info,
    "chk_vfo": RigctldHandler._cmd_chk_vfo,
    "get_powerstat": RigctldHandler._cmd_get_powerstat,
    "quit": RigctldHandler._cmd_quit,
    "power2mW": RigctldHandler._cmd_power2mw,
    "mW2power": RigctldHandler._cmd_mw2power,
    "get_lock_mode": RigctldHandler._cmd_get_lock_mode,
}
