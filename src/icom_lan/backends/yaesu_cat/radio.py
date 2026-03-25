"""Yaesu CAT radio backend — FTX-1 and compatible transceivers.

Implements the core :class:`~icom_lan.radio_protocol.Radio` protocol
using :class:`YaesuCatTransport` for serial I/O and
:class:`CatCommandParser` / :func:`format_command` for encoding.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...command_spec import CatCommandSpec
from ...exceptions import CommandError
from ...exceptions import ConnectionError as RadioConnectionError
from ...radio_state import RadioState
from .parser import CatCommandParser, format_command
from .transport import YaesuCatTransport

__all__ = ["YaesuCatRadio"]

logger = logging.getLogger(__name__)

# Path to rigs/ directory: src/icom_lan/backends/yaesu_cat/radio.py → 4 levels up
_RIGS_DIR = Path(__file__).parents[4] / "rigs"


def _load_config(profile: Any) -> Any:
    """Load RigConfig from a profile name or return an existing RigConfig."""
    from ...rig_loader import RigConfig, load_rig

    if isinstance(profile, str):
        path = _RIGS_DIR / f"{profile}.toml"
        return load_rig(path)
    if isinstance(profile, RigConfig):
        return profile
    raise TypeError(f"profile must be str or RigConfig, got {type(profile).__name__}")


class YaesuCatRadio:
    """Radio backend for Yaesu FTX-1 (and compatible) transceivers.

    Communicates via Yaesu CAT protocol over serial.  Supports the four
    core operations needed for the FTX-1 smoke test: frequency, mode,
    PTT, and S-meter.

    Usage::

        async with YaesuCatRadio("/dev/cu.usbserial-...") as radio:
            freq = await radio.get_freq()
            await radio.set_freq(14_074_000)
            mode, _ = await radio.get_mode()
            await radio.set_ptt(True)
            s = await radio.get_s_meter()
    """

    def __init__(
        self,
        device: str,
        baudrate: int = 38400,
        profile: str | Any = "ftx1",
    ) -> None:
        """Create a YaesuCatRadio instance.

        Args:
            device: Serial port path (e.g. ``"/dev/cu.usbserial-01AE340D0"``).
            baudrate: Serial baud rate (default 38400 for FTX-1).
            profile: Rig profile name (``"ftx1"``) or a loaded ``RigConfig``.
        """
        self._config = _load_config(profile)
        self._transport = YaesuCatTransport(device=device, baudrate=baudrate)
        self._state = RadioState()

        # Build bidirectional mode code ↔ name maps.
        # FTX-1 CAT codes are 1-based: index 0 in modes list → code "1".
        self._code_to_mode: dict[str, str] = {}
        self._mode_to_code: dict[str, str] = {}
        for i, name in enumerate(self._config.modes, start=1):
            code = str(i)
            self._code_to_mode[code] = name
            self._mode_to_code[name] = code

        # Compile response parsers once at init time (keyed by command name).
        # Commands with unsupported placeholders (e.g. {vfo}, {band}) are skipped.
        self._parsers: dict[str, CatCommandParser] = {}
        for cmd_name, spec in self._config.commands.items():
            if isinstance(spec, CatCommandSpec) and spec.parse:
                try:
                    self._parsers[cmd_name] = CatCommandParser(spec.parse)
                except ValueError:
                    logger.debug(
                        "Skipping parser for %r (unsupported placeholder)", cmd_name
                    )

    # -- Lifecycle ----------------------------------------------------------

    async def connect(self) -> None:
        """Open the serial port."""
        await self._transport.connect()

    async def disconnect(self) -> None:
        """Close the serial port."""
        await self._transport.close()

    async def __aenter__(self) -> "YaesuCatRadio":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()

    @property
    def connected(self) -> bool:
        """Whether the serial transport is connected."""
        return self._transport.connected

    @property
    def radio_ready(self) -> bool:
        """Whether the backend is ready for commands."""
        return self._transport.connected

    @property
    def model(self) -> str:
        """Human-readable radio model name (e.g. ``'FTX-1'``)."""
        return self._config.model

    @property
    def capabilities(self) -> set[str]:
        """Set of capability tags from the rig profile."""
        return set(self._config.capabilities)

    @property
    def radio_state(self) -> RadioState:
        """Live radio state snapshot (updated by get_* calls)."""
        return self._state

    # -- Internal helpers ---------------------------------------------------

    def _get_spec(self, name: str) -> CatCommandSpec:
        """Return the CatCommandSpec for *name*, raising CommandError if absent."""
        spec = self._config.commands.get(name)
        if spec is None:
            raise CommandError(
                f"Command {name!r} not found in profile {self._config.model!r}"
            )
        if not isinstance(spec, CatCommandSpec):
            raise CommandError(
                f"Command {name!r} is not a CAT command spec"
            )
        return spec

    def _require_connected(self) -> None:
        if not self._transport.connected:
            raise RadioConnectionError("Radio not connected — call connect() first")

    async def _query(self, cmd_name: str) -> dict[str, Any]:
        """Send a read command and return the parsed response fields.

        The transport strips the trailing ``;`` from responses; we add it
        back before passing to the parser (templates include the semicolon).
        """
        self._require_connected()
        spec = self._get_spec(cmd_name)
        if spec.read is None:
            raise CommandError(f"Command {cmd_name!r} has no read template")

        raw = await self._transport.query(spec.read)

        parser = self._parsers.get(cmd_name)
        if parser is None:
            raise CommandError(f"Command {cmd_name!r} has no parse template")

        # Transport strips trailing ';'; add it back for the parser.
        return parser.parse(raw + ";")

    async def _write(self, cmd_name: str, **kwargs: Any) -> None:
        """Format and send a write command (no response expected)."""
        self._require_connected()
        spec = self._get_spec(cmd_name)
        if spec.write is None:
            raise CommandError(f"Command {cmd_name!r} has no write template")

        cmd = format_command(spec.write, **kwargs)
        await self._transport.write(cmd)

    # -- Frequency ----------------------------------------------------------

    async def get_freq(self, receiver: int = 0) -> int:
        """Get the current VFO frequency in Hz.

        Args:
            receiver: 0 = main (VFO-A), 1 = sub (VFO-B).
        """
        cmd = "get_freq" if receiver == 0 else "get_freq_sub"
        result = await self._query(cmd)
        freq: int = result["freq"]
        if receiver == 0:
            self._state.main.freq = freq
        else:
            self._state.sub.freq = freq
        return freq

    async def set_freq(self, freq: int, receiver: int = 0) -> None:
        """Set the VFO frequency in Hz.

        Args:
            freq: Frequency in Hz (e.g. ``14_074_000``).
            receiver: 0 = main (VFO-A), 1 = sub (VFO-B).
        """
        cmd = "set_freq" if receiver == 0 else "set_freq_sub"
        await self._write(cmd, freq=freq)
        if receiver == 0:
            self._state.main.freq = freq
        else:
            self._state.sub.freq = freq

    # -- Mode ---------------------------------------------------------------

    async def get_mode(self, receiver: int = 0) -> tuple[str, int | None]:
        """Get the current operating mode.

        Returns:
            Tuple of (mode_name, None).  Mode names are from the rig
            profile (e.g. ``"USB"``, ``"LSB"``, ``"CW-U"``).
        """
        cmd = "get_mode" if receiver == 0 else "get_mode_sub"
        result = await self._query(cmd)
        code: str = result["mode"]
        mode_name = self._code_to_mode.get(code, f"UNKNOWN({code})")
        if receiver == 0:
            self._state.main.mode = mode_name
        else:
            self._state.sub.mode = mode_name
        return mode_name, None

    async def set_mode(
        self,
        mode: str,
        filter_width: int | None = None,
        receiver: int = 0,
    ) -> None:
        """Set the operating mode.

        Args:
            mode: Mode name from the rig profile (e.g. ``"USB"``).
            filter_width: Ignored (not supported by this backend).
            receiver: 0 = main, 1 = sub.
        """
        code = self._mode_to_code.get(mode)
        if code is None:
            raise CommandError(
                f"Unknown mode {mode!r} for {self._config.model!r}. "
                f"Available: {list(self._mode_to_code)}"
            )
        cmd = "set_mode" if receiver == 0 else "set_mode_sub"
        await self._write(cmd, mode=code)
        if receiver == 0:
            self._state.main.mode = mode
        else:
            self._state.sub.mode = mode

    async def get_data_mode(self) -> bool:
        """Data mode is not implemented in this minimal backend."""
        return False

    async def set_data_mode(self, on: int | bool, receiver: int = 0) -> None:
        """Data mode is not implemented in this minimal backend."""

    # -- PTT ----------------------------------------------------------------

    async def set_ptt(self, on: bool) -> None:
        """Key or un-key the transmitter.

        Args:
            on: ``True`` to transmit, ``False`` to receive.
        """
        await self._write("set_ptt", state="1" if on else "0")
        self._state.ptt = on

    async def get_ptt(self) -> bool:
        """Query the current PTT state.

        Returns:
            ``True`` if transmitting, ``False`` if receiving.
        """
        result = await self._query("get_ptt")
        ptt = result["state"] == "1"
        self._state.ptt = ptt
        return ptt

    # -- S-meter ------------------------------------------------------------

    async def get_s_meter(self, receiver: int = 0) -> int:
        """Get the S-meter raw value.

        Args:
            receiver: 0 = main, 1 = sub.

        Returns:
            Raw S-meter reading (0–255, vendor scale).
        """
        cmd = "get_s_meter" if receiver == 0 else "get_s_meter_sub"
        result = await self._query(cmd)
        raw: int = result["raw"]
        if receiver == 0:
            self._state.main.s_meter = raw
        else:
            self._state.sub.s_meter = raw
        return raw
