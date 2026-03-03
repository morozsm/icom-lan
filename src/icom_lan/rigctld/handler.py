"""Rigctld command handler — dispatches parsed commands to IcomRadio.

Responsibilities:
- Command dispatch table (long_cmd → async handler method)
- Read-only gate (reject set commands with RPRT -22)
- Frequency/mode cache with configurable TTL (via StateCache)
- Error translation (icom-lan exceptions → Hamlib error codes)

This module receives RigctldCommand from protocol.py and returns
RigctldResponse. It calls IcomRadio methods but knows nothing about
TCP or wire format.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from ..exceptions import ConnectionError, TimeoutError
from ..types import Mode
from .contract import (
    CIV_TO_HAMLIB_MODE,
    HAMLIB_MODE_MAP,
    HamlibError,
    RigctldCommand,
    RigctldConfig,
    RigctldResponse,
)
from .state_cache import StateCache

if TYPE_CHECKING:
    from ..radio import IcomRadio

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
    "0",                                                          # protocol version
    "3078",                                                       # rig model (IC-7610)
    "1",                                                          # ITU region
    "100000.000000 60000000.000000 0x1ff -1 -1 0x3 0xf",        # RX range
    "0 0 0 0 0 0 0",                                             # end of RX ranges
    "1800000.000000 60000000.000000 0x1ff 5000 100000 0x3 0xf", # TX range
    "0 0 0 0 0 0 0",                                             # end of TX ranges
    "0x1ff 1",                                                    # tuning step (all modes, 1 Hz)
    "0 0",                                                        # end of tuning steps
    "0x1ff 3000",                                                 # filter: wide 3000 Hz
    "0x1ff 2400",                                                 # filter: normal 2400 Hz
    "0x1ff 1800",                                                 # filter: narrow 1800 Hz
    "0 0",                                                        # end of filters
    "0",                                                          # max_rit
    "0",                                                          # max_xit
    "0",                                                          # max_ifshift
    "0",                                                          # announces
    "12 20 0",                                                    # preamp (dB values, 0-terminated)
    "6 12 18 0",                                                  # attenuator (dB values, 0-terminated)
    "0",                                                          # has_get_func
    "0",                                                          # has_set_func
    "0x54001000",                                                 # has_get_level (STRENGTH|SWR|ALC|RFPOWER)
    "0x00001000",                                                 # has_set_level (RFPOWER)
    "0",                                                          # has_get_parm
    "0",                                                          # has_set_parm
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


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class RigctldHandler:
    """Dispatches parsed rigctld commands to IcomRadio.

    Args:
        radio: Connected IcomRadio instance.
        config: Server configuration (read_only, cache_ttl, etc.).
        cache: Shared state cache; a fresh private one is created if omitted.
    """

    def __init__(
        self,
        radio: "IcomRadio",
        config: RigctldConfig,
        cache: StateCache | None = None,
    ) -> None:
        self._radio = radio
        self._config = config
        self._ptt_state: bool = False
        self._cache: StateCache = cache if cache is not None else StateCache()

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
            return await handler_fn(self, cmd)
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
        self._cache.invalidate_freq()
        return _ok()

    # ------------------------------------------------------------------
    # Mode commands
    # ------------------------------------------------------------------

    async def _cmd_get_mode(self, cmd: RigctldCommand) -> RigctldResponse:
        if self._cache.is_fresh("mode", self._config.cache_ttl):
            mode_str = self._cache.mode
            passband = _filter_to_passband(self._cache.filter_width)
            data_mode = self._cache.data_mode
        else:
            mode, filt = await self._radio.get_mode_info()
            mode_str = CIV_TO_HAMLIB_MODE.get(mode.value, "USB")
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
        mode_str = cmd.args[0].upper()
        if mode_str not in HAMLIB_MODE_MAP:
            return _err(HamlibError.EINVAL)
        civ_val = HAMLIB_MODE_MAP[mode_str]
        try:
            mode = Mode(civ_val)
        except ValueError:
            return _err(HamlibError.EINVAL)
        passband_hz = 0
        if len(cmd.args) >= 2:
            try:
                passband_hz = int(cmd.args[1])
            except ValueError:
                return _err(HamlibError.EINVAL)
        filter_width = _passband_to_filter(passband_hz)
        packet_modes = {"PKTUSB", "PKTLSB", "PKTRTTY"}

        await self._radio.set_mode(mode, filter_width=filter_width)

        # Only set DATA mode explicitly for packet modes.
        # For non-packet modes, avoid hidden side-effects (do not force DATA off).
        if mode_str in packet_modes:
            await self._radio.set_data_mode(True)

            # Read-back sync: keep next get_mode deterministic for CAT clients.
            # Some radios acknowledge set-data quickly but reflect packet mode
            # with a short delay. We wait briefly to reduce client-side stalls.
            synced = False
            for _ in range(5):
                try:
                    read_mode, _ = await self._radio.get_mode_info()
                    read_data = await self._radio.get_data_mode()
                    if read_mode == mode and read_data:
                        synced = True
                        break
                except Exception:
                    logger.debug("rigctld: sync poll failed", exc_info=True)
                await asyncio.sleep(0.05)

            # Cache optimistic final state even if read-back lagged.
            base_mode = CIV_TO_HAMLIB_MODE.get(mode.value, "USB")
            self._cache.update_mode(base_mode, filter_width)
            self._cache.update_data_mode(True)
            if not synced:
                logger.debug(
                    "set_mode(%s): packet read-back not fully synced yet; cached optimistic state",
                    mode_str,
                )
        else:
            # For non-packet mode changes update mode cache, but preserve DATA
            # state (no forced DATA off side-effect).
            self._cache.update_mode(mode_str, filter_width)

        return _ok()

    # ------------------------------------------------------------------
    # PTT commands
    # ------------------------------------------------------------------

    async def _cmd_get_ptt(self, cmd: RigctldCommand) -> RigctldResponse:
        return RigctldResponse(values=[str(int(self._ptt_state))])

    async def _cmd_set_ptt(self, cmd: RigctldCommand) -> RigctldResponse:
        if not cmd.args:
            return _err(HamlibError.EINVAL)
        try:
            on = bool(int(cmd.args[0]))
        except ValueError:
            return _err(HamlibError.EINVAL)
        await self._radio.set_ptt(on)
        self._ptt_state = on
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
        if level == "STRENGTH":
            raw = await self._radio.get_s_meter()
            # IC-7610 S-meter: 0→S0(−54 dB), 120→S9(0 dB), 241→S9+60 dB
            strength_db = round((raw / 241.0) * 114.0 - 54.0)
            return RigctldResponse(values=[str(strength_db)])
        if level == "RFPOWER":
            raw = await self._radio.get_power()
            return RigctldResponse(values=[f"{raw / 255.0:.6f}"])
        if level == "SWR":
            raw = await self._radio.get_swr()
            # Map 0-255 to 1.0-5.0
            swr = 1.0 + (raw / 255.0) * 4.0
            return RigctldResponse(values=[f"{swr:.6f}"])
        return _err(HamlibError.EINVAL)

    # ------------------------------------------------------------------
    # Split VFO commands
    # ------------------------------------------------------------------

    async def _cmd_get_split_vfo(self, cmd: RigctldCommand) -> RigctldResponse:
        return RigctldResponse(values=["0", "VFOA"])

    async def _cmd_set_split_vfo(self, cmd: RigctldCommand) -> RigctldResponse:
        return _ok()

    # ------------------------------------------------------------------
    # RIT
    # ------------------------------------------------------------------

    async def _cmd_get_rit(self, cmd: RigctldCommand) -> RigctldResponse:
        return RigctldResponse(values=["0"])

    # ------------------------------------------------------------------
    # Info / control commands
    # ------------------------------------------------------------------

    async def _cmd_dump_state(self, cmd: RigctldCommand) -> RigctldResponse:
        return RigctldResponse(values=list(_IC7610_DUMP_STATE))

    async def _cmd_dump_caps(self, cmd: RigctldCommand) -> RigctldResponse:
        return await self._cmd_dump_state(cmd)

    async def _cmd_get_info(self, cmd: RigctldCommand) -> RigctldResponse:
        return RigctldResponse(values=["Icom IC-7610 (icom-lan)"])

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
    "get_freq":       RigctldHandler._cmd_get_freq,
    "set_freq":       RigctldHandler._cmd_set_freq,
    "get_mode":       RigctldHandler._cmd_get_mode,
    "set_mode":       RigctldHandler._cmd_set_mode,
    "get_ptt":        RigctldHandler._cmd_get_ptt,
    "set_ptt":        RigctldHandler._cmd_set_ptt,
    "get_vfo":        RigctldHandler._cmd_get_vfo,
    "set_vfo":        RigctldHandler._cmd_set_vfo,
    "get_level":      RigctldHandler._cmd_get_level,
    "get_split_vfo":  RigctldHandler._cmd_get_split_vfo,
    "set_split_vfo":  RigctldHandler._cmd_set_split_vfo,
    "get_rit":        RigctldHandler._cmd_get_rit,
    "dump_state":     RigctldHandler._cmd_dump_state,
    "dump_caps":      RigctldHandler._cmd_dump_caps,
    "get_info":       RigctldHandler._cmd_get_info,
    "chk_vfo":        RigctldHandler._cmd_chk_vfo,
    "get_powerstat":  RigctldHandler._cmd_get_powerstat,
    "quit":           RigctldHandler._cmd_quit,
    "power2mW":       RigctldHandler._cmd_power2mw,
    "mW2power":       RigctldHandler._cmd_mw2power,
    "get_lock_mode":  RigctldHandler._cmd_get_lock_mode,
}
