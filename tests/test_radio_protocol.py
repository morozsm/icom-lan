"""Tests for the Radio protocol surface in radio_protocol.py."""

from __future__ import annotations

from typing import Any

from icom_lan.radio_protocol import Radio
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
