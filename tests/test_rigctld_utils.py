from __future__ import annotations

import asyncio
from typing import Any

import pytest

from icom_lan.rigctld.utils import get_mode_reader
from icom_lan.types import Mode


class _ModeInfoRadio:
    def __init__(self, mode: Mode, filt: int | None) -> None:
        self.mode = mode
        self.filt = filt
        self.get_mode_info_calls: list[int] = []
        self.get_mode_calls: list[int] = []

    async def get_mode_info(self, receiver: int = 0) -> tuple[Mode, int | None]:
        self.get_mode_info_calls.append(receiver)
        return self.mode, self.filt

    async def get_mode(self, receiver: int = 0) -> tuple[Mode, int | None]:
        self.get_mode_calls.append(receiver)
        return self.mode, self.filt


class _ContractModeRadio:
    def __init__(self, mode: str, filt: int | None) -> None:
        self.mode = mode
        self.filt = filt
        self.get_mode_calls: list[int] = []

    async def get_mode(self, receiver: int = 0) -> tuple[str, int | None]:
        self.get_mode_calls.append(receiver)
        return self.mode, self.filt


class _DynamicModeInfoRadio:
    def __init__(self, mode: Any, filt: int | None) -> None:
        self.mode = mode
        self.filt = filt
        self.get_mode_info_calls: list[int] = []

    async def get_mode_info(self, receiver: int = 0) -> tuple[Any, int | None]:
        self.get_mode_info_calls.append(receiver)
        return self.mode, self.filt


@pytest.mark.asyncio
async def test_get_mode_reader_prefers_mode_info_capable() -> None:
    radio = _ModeInfoRadio(Mode.USB, 2)

    def normalizer(mode: object) -> str:
        assert isinstance(mode, Mode)
        return mode.name

    reader = get_mode_reader(radio, normalizer)
    assert reader is not None

    mode_str, filt = await reader(receiver=1)

    assert mode_str == "USB"
    assert filt == 2
    assert radio.get_mode_info_calls == [1]
    assert radio.get_mode_calls == []


@pytest.mark.asyncio
async def test_get_mode_reader_uses_dynamic_get_mode_info_when_available() -> None:
    radio = _DynamicModeInfoRadio("LSB", 1)

    def normalizer(mode: object) -> str:
        return str(mode).upper()

    reader = get_mode_reader(radio, normalizer)
    assert reader is not None

    mode_str, filt = await reader()

    assert mode_str == "LSB"
    assert filt == 1
    assert radio.get_mode_info_calls == [0]


@pytest.mark.asyncio
async def test_get_mode_reader_falls_back_to_core_contract_get_mode() -> None:
    radio = _ContractModeRadio("AM", None)

    def normalizer(mode: object) -> str:
        return str(mode).upper()

    reader = get_mode_reader(radio, normalizer)
    assert reader is not None

    mode_str, filt = await reader()

    assert mode_str == "AM"
    assert filt is None
    assert radio.get_mode_calls == [0]


def test_get_mode_reader_returns_none_when_no_mode_methods() -> None:
    class _NoModeRadio:
        pass

    def normalizer(mode: object) -> str:
        return str(mode)

    reader = get_mode_reader(_NoModeRadio(), normalizer)
    assert reader is None

