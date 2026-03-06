"""Profile-driven routing and capability guard tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from icom_lan import IcomRadio
from icom_lan.exceptions import CommandError
from icom_lan.profiles import resolve_radio_profile
from icom_lan.rigctld.state_cache import StateCache
from icom_lan.web.handlers import ControlHandler
from icom_lan.web.radio_poller import CommandQueue, RadioPoller, SetFreq, SetMode


def _dual_radio_mock() -> MagicMock:
    profile = resolve_radio_profile(model="IC-7610")
    radio = MagicMock()
    radio.profile = profile
    radio.model = profile.model
    radio.capabilities = set(profile.capabilities)
    radio._radio_state = SimpleNamespace(active="MAIN")
    radio.send_civ = AsyncMock()
    radio.set_frequency = AsyncMock()
    radio.set_mode = AsyncMock()
    return radio


def _single_radio_mock() -> MagicMock:
    profile = resolve_radio_profile(model="IC-7300")
    radio = MagicMock()
    radio.profile = profile
    radio.model = profile.model
    radio.capabilities = set(profile.capabilities)
    radio._radio_state = SimpleNamespace(active="MAIN")
    radio.send_civ = AsyncMock()
    radio.set_frequency = AsyncMock()
    radio.set_mode = AsyncMock()
    return radio


def test_radio_model_and_capabilities_are_profile_derived() -> None:
    radio = IcomRadio("127.0.0.1", model="IC-7300")
    assert radio.model == "IC-7300"
    assert "dual_rx" not in radio.capabilities


@pytest.mark.asyncio
async def test_single_profile_receiver_guard_is_explicit() -> None:
    radio = IcomRadio("127.0.0.1", model="IC-7300")
    radio._check_connected = lambda: None  # type: ignore[method-assign]

    with pytest.raises(CommandError, match="receiver=1"):
        await radio.set_frequency(14_074_000, receiver=1)


@pytest.mark.asyncio
async def test_dual_profile_poller_routes_sub_freq_via_vfo_switch() -> None:
    radio = _dual_radio_mock()
    poller = RadioPoller(radio, StateCache(), CommandQueue())
    await poller._execute(SetFreq(14_074_000, receiver=1))  # noqa: SLF001

    assert radio.send_civ.await_count >= 2
    radio.set_frequency.assert_awaited_once_with(14_074_000)


@pytest.mark.asyncio
async def test_single_profile_poller_rejects_sub_receiver() -> None:
    radio = _single_radio_mock()
    poller = RadioPoller(radio, StateCache(), CommandQueue())

    with pytest.raises(CommandError, match="receiver=1"):
        await poller._execute(SetMode("USB", receiver=1))  # noqa: SLF001

    assert all(receiver in {0, None} for _, _, receiver in poller._STATE_QUERIES)  # noqa: SLF001


def test_control_handler_checks_capabilities_not_model_name() -> None:
    profile = resolve_radio_profile(model="IC-7300")
    ws = SimpleNamespace(send_text=AsyncMock(), recv=AsyncMock())
    queue = SimpleNamespace(put=lambda _cmd: None)
    server = SimpleNamespace(command_queue=queue)
    radio = SimpleNamespace(capabilities=set(profile.capabilities))
    handler = ControlHandler(ws, radio, "1.0", profile.model, server=server)

    with pytest.raises(ValueError, match="missing capability: nb"):
        handler._enqueue_command("set_nb", {"on": True, "receiver": 0})


@pytest.mark.asyncio
async def test_dual_profile_poller_routes_main_mode_via_vfo_switch_when_active_sub() -> None:
    radio = _dual_radio_mock()
    radio._radio_state.active = "SUB"
    poller = RadioPoller(radio, StateCache(), CommandQueue())

    await poller._execute(SetMode("USB", receiver=0))  # noqa: SLF001

    main_code = bytes([radio.profile.vfo_main_code])
    sub_code = bytes([radio.profile.vfo_sub_code])
    radio.send_civ.assert_any_await(0x07, sub=None, data=main_code, wait_response=False)
    radio.send_civ.assert_any_await(0x07, sub=None, data=sub_code, wait_response=False)
    radio.set_mode.assert_awaited_once_with("USB", None)
