"""Tests for the Radio protocol surface in radio_protocol.py."""

from __future__ import annotations

from typing import Any

from icom_lan.radio_protocol import (
    MetersCapable,
    PowerControlCapable,
    Radio,
    VoiceControlCapable,
)
from icom_lan.radio_state import RadioState


class _StubRadio:
    """Minimal conforming stub that implements the Radio protocol."""

    @property
    def backend_id(self) -> str:
        return "icom_lan"

    @property
    def connected(self) -> bool:
        return False

    @property
    def radio_ready(self) -> bool:
        return False

    @property
    def radio_state(self) -> RadioState:
        return RadioState()

    @property
    def model(self) -> str:
        return "IC-TEST"

    @property
    def capabilities(self) -> set[str]:
        return set()

    def supports_command(self, command: str) -> bool:
        return False

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def __aenter__(self) -> "_StubRadio": return self
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...
    async def get_freq(self, receiver: int = 0) -> int: return 0
    async def set_freq(self, freq: int, receiver: int = 0) -> None: ...
    async def get_mode(self, receiver: int = 0) -> tuple[str, int | None]: return ("USB", None)
    async def set_mode(self, mode: str, filter_width: int | None = None, receiver: int = 0) -> None: ...
    async def get_data_mode(self) -> bool: return False
    async def set_data_mode(self, on: int | bool, receiver: int = 0) -> None: ...
    async def set_ptt(self, on: bool) -> None: ...


def test_backend_id_property_on_stub() -> None:
    """Radio protocol surface includes backend_id returning a str."""
    stub = _StubRadio()
    assert isinstance(stub, Radio)
    assert stub.backend_id == "icom_lan"
    assert isinstance(stub.backend_id, str)


def test_backend_id_known_values() -> None:
    """backend_id can hold any of the documented family values."""
    known_ids = {"icom_lan", "icom_serial", "yaesu_cat"}
    assert _StubRadio().backend_id in known_ids


class _PowerStub:
    """Stub implementing both PowerControlCapable and MetersCapable surfaces.

    Verifies that ``get_rf_power`` declared on PowerControlCapable does not
    break the duplicate declaration on MetersCapable — both ``isinstance``
    checks must still pass for backends that implement the read+write pair.
    """

    async def get_powerstat(self) -> bool: return True
    async def set_powerstat(self, on: bool) -> None: ...
    async def get_rf_power(self) -> int: return 128
    async def set_rf_power(self, level: int) -> None: ...
    # MetersCapable surface
    async def get_s_meter(self, receiver: int = 0) -> int: return 0
    async def get_swr(self) -> float: return 1.0
    async def get_comp_meter(self) -> int: return 0
    async def get_id_meter(self) -> int: return 0
    async def get_vd_meter(self) -> int: return 0


def test_get_rf_power_visible_on_power_control_capable() -> None:
    """get_rf_power is reachable through a PowerControlCapable typed reference.

    The declaration was lifted into PowerControlCapable so the read+write pair
    lives together, while remaining declared on MetersCapable for backwards
    compatibility (refs #1109).
    """
    stub: PowerControlCapable = _PowerStub()
    assert hasattr(stub, "get_rf_power")
    assert hasattr(stub, "set_rf_power")


def test_power_stub_satisfies_both_protocols() -> None:
    """A radio implementing get_rf_power satisfies both protocols."""
    stub = _PowerStub()
    assert isinstance(stub, PowerControlCapable)
    assert isinstance(stub, MetersCapable)


# ---------------------------------------------------------------------------
# VoiceControlCapable: get_compressor + set_compressor pair (issue #1097)
# ---------------------------------------------------------------------------


class _VoiceStub:
    """Minimal stub exposing every VoiceControlCapable method."""

    def __init__(self) -> None:
        self._compressor: bool = False
        self._vox: bool = False
        self._vox_gain: int = 0
        self._anti_vox_gain: int = 0
        self._vox_delay: int = 0
        self._monitor: bool = False
        self._monitor_gain: int = 0
        self._ssb_tx_bandwidth: int = 0

    async def get_vox(self) -> bool:
        return self._vox

    async def set_vox(self, on: bool) -> None:
        self._vox = on

    async def get_vox_gain(self) -> int:
        return self._vox_gain

    async def set_vox_gain(self, level: int) -> None:
        self._vox_gain = level

    async def get_anti_vox_gain(self) -> int:
        return self._anti_vox_gain

    async def set_anti_vox_gain(self, level: int) -> None:
        self._anti_vox_gain = level

    async def get_vox_delay(self) -> int:
        return self._vox_delay

    async def set_vox_delay(self, level: int) -> None:
        self._vox_delay = level

    async def get_compressor(self) -> bool:
        return self._compressor

    async def set_compressor(self, on: bool) -> None:
        self._compressor = on

    async def get_monitor(self) -> bool:
        return self._monitor

    async def set_monitor(self, on: bool) -> None:
        self._monitor = on

    async def get_monitor_gain(self) -> int:
        return self._monitor_gain

    async def set_monitor_gain(self, level: int) -> None:
        self._monitor_gain = level

    async def set_acc1_mod_level(self, level: int) -> None: ...
    async def set_usb_mod_level(self, level: int) -> None: ...
    async def set_lan_mod_level(self, level: int) -> None: ...
    async def get_ssb_tx_bandwidth(self) -> int:
        return self._ssb_tx_bandwidth

    async def set_ssb_tx_bandwidth(self, value: int) -> None:
        self._ssb_tx_bandwidth = value


def test_voice_control_capable_includes_get_compressor() -> None:
    """A class implementing every VoiceControlCapable method satisfies isinstance."""
    assert isinstance(_VoiceStub(), VoiceControlCapable)


def test_voice_control_capable_missing_get_compressor_fails() -> None:
    """Without get_compressor the class no longer satisfies the protocol."""

    class _MissingGetCompressor(_VoiceStub):
        get_compressor = None  # type: ignore[assignment]

    assert not isinstance(_MissingGetCompressor(), VoiceControlCapable)


async def _voice_compressor_round_trip(radio: VoiceControlCapable) -> tuple[bool, bool]:
    """Helper: read-set-read round trip on a VoiceControlCapable radio."""
    initial = await radio.get_compressor()
    await radio.set_compressor(not initial)
    return initial, await radio.get_compressor()


def test_voice_compressor_round_trip_protocol_typed() -> None:
    """get→set→get works against a VoiceControlCapable-typed reference."""
    import asyncio

    stub = _VoiceStub()
    initial, after = asyncio.run(_voice_compressor_round_trip(stub))
    assert initial is False
    assert after is True
