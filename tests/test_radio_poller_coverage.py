"""Additional coverage tests for icom_lan.web.radio_poller."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan.exceptions import CommandError
from icom_lan.rigctld.state_cache import StateCache
from icom_lan.profiles import resolve_radio_profile
from icom_lan.web.radio_poller import (
    CommandQueue,
    DisableScope,
    EnableScope,
    PttOff,
    PttOn,
    RadioPoller,
    SelectVfo,
    SetDigiSel,
    SetFreq,
    SetIpPlus,
    SetMode,
    SetNB,
    SetNR,
    SetPower,
    SwitchScopeReceiver,
    VfoSwap,
)


def _make_radio(active: str = "MAIN") -> MagicMock:
    profile = resolve_radio_profile(model="IC-7610")
    radio = MagicMock()
    radio.profile = profile
    radio.model = profile.model
    radio.capabilities = set(profile.capabilities)
    radio._radio_state = SimpleNamespace(active=active)
    radio.send_civ = AsyncMock()
    radio.set_frequency = AsyncMock()
    radio.set_mode = AsyncMock()
    radio.set_filter = AsyncMock()
    radio.set_ptt = AsyncMock()
    radio.set_power = AsyncMock()
    radio.set_rf_gain = AsyncMock()
    radio.set_af_level = AsyncMock()
    radio.set_squelch = AsyncMock()
    radio.set_nb = AsyncMock()
    radio.set_nr = AsyncMock()
    radio.set_digisel = AsyncMock()
    radio.set_ip_plus = AsyncMock()
    radio.set_attenuator_level = AsyncMock()
    radio.set_preamp = AsyncMock()
    radio.vfo_exchange = AsyncMock()
    radio.vfo_equalize = AsyncMock()
    radio.enable_scope = AsyncMock()
    radio.disable_scope = AsyncMock()
    radio.on_scope_data = MagicMock()
    return radio


@pytest.mark.asyncio
async def test_command_queue_wait_and_drain_behavior() -> None:
    q = CommandQueue()
    await q.wait(timeout=0.001)
    assert q.has_commands is False

    q.put(SetPower(1))
    q.put(SetPower(2))
    q.put(PttOn())
    q.put(PttOff())
    cmds = q.drain()
    assert q.has_commands is False
    assert sum(isinstance(c, SetPower) for c in cmds) == 1
    assert sum(isinstance(c, (PttOn, PttOff)) for c in cmds) == 2


@pytest.mark.asyncio
async def test_current_active_defaults_and_setfreq_setmode_branches() -> None:
    radio = _make_radio(active="MAIN")
    poller = RadioPoller(radio, StateCache(), CommandQueue())
    assert poller._current_active() == "MAIN"  # noqa: SLF001

    radio._radio_state.active = 7
    assert poller._current_active() == "MAIN"  # noqa: SLF001

    radio._radio_state.active = "MAIN"
    await poller._execute(SetFreq(14_074_000, receiver=1))  # noqa: SLF001
    assert radio.send_civ.await_count >= 2
    radio.set_frequency.assert_awaited_once_with(14_074_000)

    radio2 = _make_radio(active="SUB")
    poller2 = RadioPoller(radio2, StateCache(), CommandQueue())
    await poller2._execute(SetFreq(7_074_000, receiver=0))  # noqa: SLF001
    assert radio2.send_civ.await_count >= 2
    radio2.set_frequency.assert_awaited_once_with(7_074_000)

    await poller._execute(SetMode("USB", filter_width=2, receiver=1))  # noqa: SLF001
    radio.set_mode.assert_awaited_once_with("USB", 2)


@pytest.mark.asyncio
async def test_execute_event_emitting_commands_and_vfo_paths() -> None:
    events: list[tuple[str, dict]] = []
    radio = _make_radio(active="MAIN")
    poller = RadioPoller(
        radio,
        StateCache(),
        CommandQueue(),
        on_state_event=lambda name, data: events.append((name, data)),
    )

    await poller._execute(SetNB(True, receiver=0))  # noqa: SLF001
    await poller._execute(SetNR(False, receiver=1))  # noqa: SLF001
    await poller._execute(SetDigiSel(True, receiver=1))  # noqa: SLF001
    await poller._execute(SetIpPlus(False, receiver=0))  # noqa: SLF001
    assert any(name == "nb_changed" for name, _ in events)
    assert any(name == "nr_changed" for name, _ in events)
    assert any(name == "digisel_changed" for name, _ in events)
    assert any(name == "ipplus_changed" for name, _ in events)

    await poller._execute(SelectVfo("SUB"))  # noqa: SLF001
    assert radio._radio_state.active == "SUB"
    await poller._execute(SelectVfo("MAIN"))  # noqa: SLF001
    assert radio.send_civ.await_count >= 2

    await poller._execute(VfoSwap())  # noqa: SLF001
    assert any(name == "vfo_swapped" for name, _ in events)

    await poller._execute(EnableScope(policy="fast"))  # noqa: SLF001
    await poller._execute(DisableScope())  # noqa: SLF001
    await poller._execute(SwitchScopeReceiver(1))  # noqa: SLF001
    radio.enable_scope.assert_awaited_once_with(policy="fast")
    radio.disable_scope.assert_awaited_once()
    with pytest.raises(CommandError, match="receiver=2"):
        await poller._execute(SwitchScopeReceiver(2))  # noqa: SLF001


@pytest.mark.asyncio
async def test_send_query_even_and_odd_branch_variants() -> None:
    radio = _make_radio()
    poller = RadioPoller(radio, StateCache(), CommandQueue())

    poller._poll_index = 0  # even => fast meter query  # noqa: SLF001
    await poller._send_query()  # noqa: SLF001
    assert radio.send_civ.await_args.args[0] == 0x15

    poller._STATE_QUERIES = [(0x25, None, 0x01)]  # receiver in data payload  # noqa: SLF001
    poller._poll_index = 1  # odd  # noqa: SLF001
    await poller._send_query()  # noqa: SLF001
    assert radio.send_civ.await_args.args[0] == 0x25
    assert radio.send_civ.await_args.kwargs["data"] == bytes([0x01])

    poller._STATE_QUERIES = [(0x16, 0x22, 0x01)]  # cmd29 wrapper path  # noqa: SLF001
    poller._poll_index = 1  # noqa: SLF001
    await poller._send_query()  # noqa: SLF001
    assert radio.send_civ.await_args.args[0] == 0x29

    poller._STATE_QUERIES = [(0x0F, None, None)]  # global query  # noqa: SLF001
    poller._poll_index = 1  # noqa: SLF001
    await poller._send_query()  # noqa: SLF001
    assert radio.send_civ.await_args.args[0] == 0x0F


@pytest.mark.asyncio
async def test_run_backoff_and_query_error_paths() -> None:
    queue = CommandQueue()
    queue.put(SetPower(10))
    poller = RadioPoller(_make_radio(), StateCache(), queue)

    poller._execute = AsyncMock(side_effect=ConnectionError("down"))  # noqa: SLF001
    poller._send_query = AsyncMock(return_value=None)  # noqa: SLF001
    poller._queue.wait = AsyncMock(side_effect=asyncio.CancelledError())  # noqa: SLF001
    with patch("icom_lan.web.radio_poller.asyncio.sleep", new=AsyncMock()):
        await poller._run()  # noqa: SLF001
    assert poller._send_query.await_count >= 2  # restore probe + normal query

    poller2 = RadioPoller(_make_radio(), StateCache(), CommandQueue())
    poller2._send_query = AsyncMock(side_effect=RuntimeError("query failed"))  # noqa: SLF001
    poller2._queue.wait = AsyncMock(side_effect=asyncio.CancelledError())  # noqa: SLF001
    with patch("icom_lan.web.radio_poller.asyncio.sleep", new=AsyncMock()):
        await poller2._run()  # noqa: SLF001


def test_start_stop_running_and_emit_helpers() -> None:
    radio = _make_radio()
    poller = RadioPoller(radio, StateCache(), CommandQueue())

    with patch("asyncio.get_running_loop") as get_loop:
        task = MagicMock()
        task.done.return_value = False

        def create_task(coro, name=None):
            del name
            coro.close()
            return task

        get_loop.return_value.create_task.side_effect = create_task
        poller.start()
        assert poller.running is True
        poller.start()  # idempotent
        poller.stop()
        task.cancel.assert_called_once()
        assert poller.running is False

    events: list[tuple[str, dict]] = []
    meter_events: list[list[tuple[int, int]]] = []
    poller2 = RadioPoller(
        radio,
        StateCache(),
        CommandQueue(),
        on_state_event=lambda name, data: events.append((name, data)),
        on_meter_readings=lambda m: meter_events.append(m),
    )
    poller2._emit("x", {"a": 1})  # noqa: SLF001
    poller2._emit_meters(7, 99)  # noqa: SLF001
    assert events == [("x", {"a": 1})]
    assert meter_events == [[(7, 99)]]


def test_state_queries_include_operator_toggle_reads_for_ic7610() -> None:
    poller = RadioPoller(_make_radio(), StateCache(), CommandQueue())

    assert {
        (0x15, 0x01, 0x00),
        (0x15, 0x01, 0x01),
        (0x15, 0x07, None),
        (0x16, 0x12, None),
        (0x16, 0x32, 0x00),
        (0x16, 0x32, 0x01),
        (0x16, 0x41, 0x00),
        (0x16, 0x41, 0x01),
        (0x16, 0x44, None),
        (0x16, 0x45, None),
        (0x16, 0x46, None),
        (0x16, 0x47, None),
        (0x16, 0x48, 0x00),
        (0x16, 0x48, 0x01),
        (0x16, 0x4F, 0x00),
        (0x16, 0x4F, 0x01),
        (0x16, 0x50, None),
        (0x16, 0x56, 0x00),
        (0x16, 0x56, 0x01),
        (0x16, 0x58, None),
        (0x1A, 0x04, 0x00),
        (0x1A, 0x04, 0x01),
    }.issubset(set(poller._STATE_QUERIES))  # noqa: SLF001


def test_state_queries_include_transceiver_status_reads_for_ic7610() -> None:
    poller = RadioPoller(_make_radio(), StateCache(), CommandQueue())

    assert {
        (0x1C, 0x01, None),
        (0x1C, 0x03, None),
        (0x21, 0x00, None),
        (0x21, 0x01, None),
        (0x21, 0x02, None),
    }.issubset(set(poller._STATE_QUERIES))  # noqa: SLF001


def test_fast_cmds_include_comp_meter_for_ic7610() -> None:
    poller = RadioPoller(_make_radio(), StateCache(), CommandQueue())

    assert (0x15, 0x14) in poller._FAST_CMDS  # noqa: SLF001
