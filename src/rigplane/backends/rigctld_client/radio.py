"""RigPlane Radio adapter for an external Hamlib ``rigctld`` server."""

from __future__ import annotations

from typing import Any

from ...exceptions import CommandError
from ...radio_state import RadioState
from .transport import RigctldTransport

_SUPPORTED_COMMANDS = {
    "get_freq",
    "set_freq",
    "get_mode",
    "set_mode",
    "get_ptt",
    "set_ptt",
    "get_vfo_slot",
    "set_vfo_slot",
}


class RigctldClientRadio:
    """Minimal Radio implementation backed by external Hamlib ``rigctld``."""

    def __init__(
        self,
        *,
        host: str,
        port: int = 4532,
        timeout: float = 5.0,
        model: str | None = None,
        transport: RigctldTransport | None = None,
    ) -> None:
        self._transport = transport or RigctldTransport(
            host=host,
            port=port,
            timeout=timeout,
        )
        self._model = model or "External rigctld"
        self._state = RadioState()
        self._vfo_supported = False

    async def connect(self) -> None:
        await self._transport.connect()
        await self._probe_vfo_support()

    async def disconnect(self) -> None:
        await self._transport.close()

    async def __aenter__(self) -> "RigctldClientRadio":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()

    @property
    def connected(self) -> bool:
        return self._transport.connected

    @property
    def radio_ready(self) -> bool:
        return self.connected

    @property
    def radio_state(self) -> RadioState:
        return self._state

    @property
    def model(self) -> str:
        return self._model

    @property
    def backend_id(self) -> str:
        return "rigctld"

    @property
    def capabilities(self) -> set[str]:
        caps = {"tx"}
        if self._vfo_supported:
            caps.add("vfo")
        return caps

    def supports_command(self, command: str) -> bool:
        if command in {"get_vfo_slot", "set_vfo_slot"}:
            return self._vfo_supported
        return command in _SUPPORTED_COMMANDS

    async def get_freq(self, receiver: int = 0) -> int:
        self._require_main_receiver(receiver, "get_freq")
        line = (await self._transport.query("f", response_lines=1))[0]
        try:
            freq = int(line)
        except ValueError as exc:
            raise CommandError(
                f"External rigctld returned malformed frequency: {line!r}."
            ) from exc
        if freq < 0:
            raise CommandError(
                f"External rigctld returned invalid negative frequency: {freq}."
            )
        self._state.main.freq = freq
        return freq

    async def set_freq(self, freq: int, receiver: int = 0) -> None:
        self._require_main_receiver(receiver, "set_freq")
        if freq <= 0:
            raise ValueError("freq must be > 0 Hz")
        await self._transport.command(f"F {int(freq)}")
        self._state.main.freq = int(freq)

    async def get_mode(self, receiver: int = 0) -> tuple[str, int | None]:
        self._require_main_receiver(receiver, "get_mode")
        mode, passband = await self._transport.query("m", response_lines=2)
        mode = mode.strip().upper()
        if not mode:
            raise CommandError("External rigctld returned an empty mode.")
        try:
            passband_hz = int(passband)
        except ValueError as exc:
            raise CommandError(
                f"External rigctld returned malformed passband: {passband!r}."
            ) from exc
        self._state.main.mode = mode
        self._state.main.filter_width = passband_hz
        return mode, passband_hz

    async def set_mode(
        self,
        mode: str,
        filter_width: int | None = None,
        receiver: int = 0,
    ) -> None:
        self._require_main_receiver(receiver, "set_mode")
        normalized = mode.strip().upper()
        if not normalized:
            raise ValueError("mode must be non-empty")
        command = f"M {normalized}"
        if filter_width is not None:
            if filter_width < 0:
                raise ValueError("filter_width must be >= 0")
            command = f"{command} {int(filter_width)}"
        await self._transport.command(command)
        self._state.main.mode = normalized
        self._state.main.filter_width = filter_width

    async def get_data_mode(self) -> bool:
        return False

    async def set_data_mode(self, on: int | bool, receiver: int = 0) -> None:
        self._require_main_receiver(receiver, "set_data_mode")
        if on:
            raise CommandError(
                "External rigctld backend does not support RigPlane data mode."
            )

    async def get_ptt(self) -> bool:
        line = (await self._transport.query("t", response_lines=1))[0]
        if line not in {"0", "1"}:
            raise CommandError(f"External rigctld returned malformed PTT: {line!r}.")
        ptt = line == "1"
        self._state.ptt = ptt
        return ptt

    async def set_ptt(self, on: bool) -> None:
        await self._transport.command(f"T {1 if on else 0}")
        self._state.ptt = bool(on)

    async def get_vfo_slot(self, receiver: int = 0) -> str:
        self._require_main_receiver(receiver, "get_vfo_slot")
        line = (await self._transport.query("v", response_lines=1))[0]
        slot = _normalize_vfo_slot(line)
        self._state.main.active_slot = slot
        return slot

    async def set_vfo_slot(self, slot: str, receiver: int = 0) -> None:
        self._require_main_receiver(receiver, "set_vfo_slot")
        normalized = _normalize_vfo_slot(slot)
        await self._transport.command(f"V VFO{normalized}")
        self._state.main.active_slot = normalized

    async def _probe_vfo_support(self) -> None:
        try:
            await self.get_vfo_slot()
        except CommandError:
            self._vfo_supported = False
        else:
            self._vfo_supported = True

    @staticmethod
    def _require_main_receiver(receiver: int, operation: str) -> None:
        if receiver != 0:
            raise ValueError(
                f"{operation}: external rigctld backend only supports receiver 0"
            )


def _normalize_vfo_slot(value: str) -> str:
    normalized = value.strip().upper()
    if normalized in {"A", "VFOA"}:
        return "A"
    if normalized in {"B", "VFOB"}:
        return "B"
    raise CommandError(f"External rigctld returned unsupported VFO: {value!r}.")
