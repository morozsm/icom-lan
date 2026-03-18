"""Additional coverage tests for icom_lan.web.radio_poller."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan.exceptions import CommandError
from icom_lan.profiles import resolve_radio_profile
from icom_lan.radio_state import RadioState
from icom_lan.rigctld.state_cache import StateCache
from icom_lan.web.radio_poller import (
    CommandQueue,
    DisableScope,
    EnableScope,
    PttOff,
    PttOn,
    RadioPoller,
    SelectVfo,
    SetAgc,
    SetAttenuator,
    SetDataMode,
    SetDigiSel,
    SetFilterWidth,
    SetFreq,
    SetIpPlus,
    SetMode,
    SetNB,
    SetNR,
    SetPower,
    SetPreamp,
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
    radio.set_freq = AsyncMock()
    radio.set_mode = AsyncMock()
    radio.set_filter = AsyncMock()
    radio.set_ptt = AsyncMock()
    radio.set_rf_power = AsyncMock()
    radio.set_rf_gain = AsyncMock()
    radio.set_af_level = AsyncMock()
    radio.set_squelch = AsyncMock()
    radio.set_data_mode = AsyncMock()
    radio.set_nb = AsyncMock()
    radio.set_nr = AsyncMock()
    radio.set_digisel = AsyncMock()
    radio.set_ip_plus = AsyncMock()
    radio.set_attenuator_level = AsyncMock()
    radio.set_preamp = AsyncMock()
    radio.set_agc = AsyncMock()
    radio.vfo_exchange = AsyncMock()
    radio.vfo_equalize = AsyncMock()
    radio.enable_scope = AsyncMock()
    radio.disable_scope = AsyncMock()
    radio.on_scope_data = MagicMock()
    radio.capture_scope_frame = AsyncMock()
    radio.capture_scope_frames = AsyncMock()
    radio.set_scope_during_tx = AsyncMock()
    radio.set_scope_center_type = AsyncMock()
    radio.set_scope_fixed_edge = AsyncMock()
    return radio


@pytest.mark.asyncio
async def test_execute_set_data_mode_updates_sub_receiver_state_and_sends_wire_value() -> (
    None
):
    events: list[tuple[str, dict]] = []
    radio = _make_radio(active="MAIN")
    state = RadioState()
    poller = RadioPoller(
        radio,
        StateCache(),
        CommandQueue(),
        on_state_event=lambda name, data: events.append((name, data)),
        radio_state=state,
    )

    await poller._execute(SetDataMode(3, receiver=1))  # noqa: SLF001

    radio.set_data_mode.assert_awaited_once_with(3, receiver=1)
    assert state.main.data_mode == 0
    assert state.sub.data_mode == 3
    assert ("data_mode_changed", {"mode": 3, "receiver": 1}) in events


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
    radio.set_freq.assert_awaited_once_with(14_074_000)

    radio2 = _make_radio(active="SUB")
    poller2 = RadioPoller(radio2, StateCache(), CommandQueue())
    await poller2._execute(SetFreq(7_074_000, receiver=0))  # noqa: SLF001
    assert radio2.send_civ.await_count >= 2
    radio2.set_freq.assert_awaited_once_with(7_074_000)

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
async def test_execute_receiver_routed_set_commands_use_backend_receiver_and_target_state() -> (
    None
):
    events: list[tuple[str, dict]] = []
    radio = _make_radio(active="MAIN")
    state = RadioState()
    state.main.nb = False
    state.sub.nb = False
    state.main.nr = True
    state.sub.nr = False
    poller = RadioPoller(
        radio,
        StateCache(),
        CommandQueue(),
        on_state_event=lambda name, data: events.append((name, data)),
        radio_state=state,
    )

    await poller._execute(SetNB(True, receiver=1))  # noqa: SLF001
    await poller._execute(SetNR(True, receiver=1))  # noqa: SLF001
    await poller._execute(SetDataMode(3, receiver=1))  # noqa: SLF001

    radio.set_nb.assert_awaited_once_with(True, receiver=1)
    radio.set_nr.assert_awaited_once_with(True, receiver=1)
    radio.set_data_mode.assert_awaited_once_with(3, receiver=1)
    assert state.main.nb is False
    assert state.sub.nb is True
    assert state.main.nr is True
    assert state.sub.nr is True
    assert state.main.data_mode == 0
    assert state.sub.data_mode == 3
    assert ("nb_changed", {"on": True, "receiver": 1}) in events
    assert ("nr_changed", {"on": True, "receiver": 1}) in events
    assert ("data_mode_changed", {"mode": 3, "receiver": 1}) in events


@pytest.mark.asyncio
async def test_execute_set_attenuator_updates_sub_receiver_state_and_radio_call() -> (
    None
):
    events: list[tuple[str, dict]] = []
    radio = _make_radio(active="MAIN")
    state = RadioState()
    state.main.preamp = 2
    state.sub.preamp = 1
    poller = RadioPoller(
        radio,
        StateCache(),
        CommandQueue(),
        on_state_event=lambda name, data: events.append((name, data)),
        radio_state=state,
    )

    await poller._execute(SetAttenuator(12, receiver=1))  # noqa: SLF001

    radio.set_attenuator_level.assert_awaited_once_with(12, receiver=1)
    assert state.main.att == 0
    assert state.main.preamp == 2
    assert state.sub.att == 12
    assert state.sub.preamp == 0
    assert ("attenuator_changed", {"db": 12, "receiver": 1}) in events


@pytest.mark.asyncio
async def test_execute_set_preamp_updates_sub_receiver_state_and_radio_call() -> None:
    events: list[tuple[str, dict]] = []
    radio = _make_radio(active="MAIN")
    state = RadioState()
    state.main.att = 9
    state.sub.att = 12
    poller = RadioPoller(
        radio,
        StateCache(),
        CommandQueue(),
        on_state_event=lambda name, data: events.append((name, data)),
        radio_state=state,
    )

    await poller._execute(SetPreamp(2, receiver=1))  # noqa: SLF001

    radio.set_preamp.assert_awaited_once_with(2, receiver=1)
    assert state.main.preamp == 0
    assert state.main.att == 9
    assert state.sub.preamp == 2
    assert state.sub.att == 0
    assert ("preamp_changed", {"level": 2, "receiver": 1}) in events


@pytest.mark.asyncio
async def test_execute_set_filter_width_updates_sub_receiver_state_and_sends_cmd29() -> (
    None
):
    events: list[tuple[str, dict]] = []
    radio = _make_radio(active="MAIN")
    state = RadioState()
    poller = RadioPoller(
        radio,
        StateCache(),
        CommandQueue(),
        on_state_event=lambda name, data: events.append((name, data)),
        radio_state=state,
    )

    await poller._execute(SetFilterWidth(1500, receiver=1))  # noqa: SLF001

    radio.send_civ.assert_awaited_once_with(
        0x29, sub=None, data=b"\x01\x1a\x03\x15\x00", wait_response=False
    )
    assert state.main.filter_width is None
    assert state.sub.filter_width == 1500
    assert ("filter_width_changed", {"width": 1500, "receiver": 1}) in events


@pytest.mark.asyncio
async def test_execute_set_agc_updates_sub_receiver_state_and_radio_call() -> None:
    events: list[tuple[str, dict]] = []
    radio = _make_radio(active="MAIN")
    state = RadioState()
    state.main.agc = 1
    state.sub.agc = 1
    poller = RadioPoller(
        radio,
        StateCache(),
        CommandQueue(),
        on_state_event=lambda name, data: events.append((name, data)),
        radio_state=state,
    )

    await poller._execute(SetAgc(2, receiver=1))  # noqa: SLF001

    radio.set_agc.assert_awaited_once_with(2, receiver=1)
    assert state.main.agc == 1
    assert state.sub.agc == 2
    assert ("agc_changed", {"mode": 2, "receiver": 1}) in events


@pytest.mark.asyncio
async def test_send_query_even_and_odd_branch_variants() -> None:
    radio = _make_radio()
    poller = RadioPoller(radio, StateCache(), CommandQueue())

    poller._poll_index = 0  # even => fast meter query  # noqa: SLF001
    await poller._send_query()  # noqa: SLF001
    assert radio.send_civ.await_args.args[0] == 0x15

    poller._STATE_QUERIES = [
        (0x25, None, 0x01)
    ]  # receiver in data payload  # noqa: SLF001
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
    poller2._send_query = AsyncMock(
        side_effect=RuntimeError("query failed")
    )  # noqa: SLF001
    poller2._queue.wait = AsyncMock(
        side_effect=asyncio.CancelledError()
    )  # noqa: SLF001
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
    poller2 = RadioPoller(
        radio,
        StateCache(),
        CommandQueue(),
        on_state_event=lambda name, data: events.append((name, data)),
    )
    poller2._emit("x", {"a": 1})  # noqa: SLF001
    assert events == [("x", {"a": 1})]


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
    }.issubset(
        set(poller._STATE_QUERIES)
    )  # noqa: SLF001


def test_state_queries_include_transceiver_status_reads_for_ic7610() -> None:
    poller = RadioPoller(_make_radio(), StateCache(), CommandQueue())

    assert {
        (0x1C, 0x01, None),
        (0x1C, 0x03, None),
        (0x21, 0x00, None),
        (0x21, 0x01, None),
        (0x21, 0x02, None),
    }.issubset(
        set(poller._STATE_QUERIES)
    )  # noqa: SLF001


def test_fast_cmds_include_comp_meter_for_ic7610() -> None:
    poller = RadioPoller(_make_radio(), StateCache(), CommandQueue())

    assert (0x15, 0x14) in poller._FAST_CMDS  # noqa: SLF001
