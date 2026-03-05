from __future__ import annotations

import asyncio
import struct
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from icom_lan.scope import ScopeFrame
from icom_lan.types import AudioCodec
from icom_lan.web.handlers import (
    AudioBroadcaster,
    AudioHandler,
    ControlHandler,
    MetersHandler,
    ScopeHandler,
)
from icom_lan.web.protocol import (
    AUDIO_CODEC_OPUS,
    AUDIO_CODEC_PCM16,
    AUDIO_HEADER_SIZE,
    decode_json,
    encode_json,
)
from icom_lan.web.radio_poller import (
    PttOff,
    PttOn,
    SelectVfo,
    SetAfLevel,
    SetAttenuator,
    SetBand,
    SetDigiSel,
    SetFilter,
    SetFreq,
    SetIpPlus,
    SetMode,
    SetNB,
    SetNR,
    SetPower,
    SetPreamp,
    SetRfGain,
    SetSquelch,
    SwitchScopeReceiver,
    VfoEqualize,
    VfoSwap,
)
from icom_lan.web.websocket import WS_OP_BINARY, WS_OP_TEXT


class _QueueRecorder:
    def __init__(self) -> None:
        self.items: list[object] = []

    def put(self, item: object) -> None:
        self.items.append(item)


def _control_handler(
    ws: object | None = None,
    radio: object | None = None,
    server: object | None = None,
) -> ControlHandler:
    if ws is None:
        ws = SimpleNamespace(send_text=AsyncMock(), recv=AsyncMock())
    return ControlHandler(ws, radio, "9.9.9", "IC-7610", server=server)


def _scope_frame() -> ScopeFrame:
    return ScopeFrame(
        receiver=0,
        mode=0,
        start_freq_hz=14_000_000,
        end_freq_hz=14_350_000,
        pixels=b"\x01\x02\x03",
        out_of_range=False,
    )


@pytest.mark.parametrize(
    ("name", "params", "expected_type", "expected_attrs", "expected_result"),
    [
        ("set_band", {"band": 3}, SetBand, {"band": 3}, {"band": 3}),
        (
            "set_freq",
            {"freq": 7_074_000, "receiver": 1},
            SetFreq,
            {"freq": 7_074_000, "receiver": 1},
            {"freq": 7_074_000, "receiver": 1},
        ),
        (
            "set_mode",
            {"mode": "LSB", "receiver": 1},
            SetMode,
            {"mode": "LSB", "receiver": 1},
            {"mode": "LSB", "receiver": 1},
        ),
        (
            "set_filter",
            {"filter": "FIL3", "receiver": 1},
            SetFilter,
            {"filter_num": 3, "receiver": 1},
            {"filter": "FIL3", "receiver": 1},
        ),
        (
            "set_filter",
            {"filter": "WIDE"},
            SetFilter,
            {"filter_num": 1, "receiver": 0},
            {"filter": "WIDE", "receiver": 0},
        ),
        ("ptt", {"state": True}, PttOn, {}, {"state": True}),
        ("ptt", {"state": False}, PttOff, {}, {"state": False}),
        ("set_power", {"level": 88}, SetPower, {"level": 88}, {"level": 88}),
        (
            "set_rf_gain",
            {"level": 77, "receiver": 1},
            SetRfGain,
            {"level": 77, "receiver": 1},
            {"level": 77, "receiver": 1},
        ),
        (
            "set_af_level",
            {"level": 66, "receiver": 1},
            SetAfLevel,
            {"level": 66, "receiver": 1},
            {"level": 66, "receiver": 1},
        ),
        (
            "set_sql",
            {"level": 55, "receiver": 1},
            SetSquelch,
            {"level": 55, "receiver": 1},
            {"level": 55, "receiver": 1},
        ),
        (
            "set_nb",
            {"on": True, "receiver": 1},
            SetNB,
            {"on": True, "receiver": 1},
            {"on": True, "receiver": 1},
        ),
        (
            "set_nr",
            {"on": True, "receiver": 1},
            SetNR,
            {"on": True, "receiver": 1},
            {"on": True, "receiver": 1},
        ),
        (
            "set_digisel",
            {"on": True, "receiver": 1},
            SetDigiSel,
            {"on": True, "receiver": 1},
            {"on": True, "receiver": 1},
        ),
        (
            "set_ipplus",
            {"on": True, "receiver": 1},
            SetIpPlus,
            {"on": True, "receiver": 1},
            {"on": True, "receiver": 1},
        ),
        (
            "set_att",
            {"db": 12, "receiver": 1},
            SetAttenuator,
            {"db": 12, "receiver": 1},
            {"db": 12, "receiver": 1},
        ),
        (
            "set_preamp",
            {"level": 2, "receiver": 1},
            SetPreamp,
            {"level": 2, "receiver": 1},
            {"level": 2, "receiver": 1},
        ),
        ("select_vfo", {"vfo": "SUB"}, SelectVfo, {"vfo": "SUB"}, {"vfo": "SUB"}),
        ("vfo_swap", {}, VfoSwap, {}, {}),
        ("vfo_equalize", {}, VfoEqualize, {}, {}),
        (
            "switch_scope_receiver",
            {"receiver": 1},
            SwitchScopeReceiver,
            {"receiver": 1},
            {"receiver": 1},
        ),
    ],
)
def test_enqueue_command_variants(
    name: str,
    params: dict[str, object],
    expected_type: type,
    expected_attrs: dict[str, object],
    expected_result: dict[str, object],
) -> None:
    queue = _QueueRecorder()
    server = SimpleNamespace(command_queue=queue)
    handler = _control_handler(server=server)
    result = handler._enqueue_command(name, params)
    assert result == expected_result
    assert len(queue.items) == 1
    cmd = queue.items[0]
    assert isinstance(cmd, expected_type)
    for key, value in expected_attrs.items():
        assert getattr(cmd, key) == value


def test_enqueue_command_errors() -> None:
    handler = _control_handler(server=None)
    with pytest.raises(RuntimeError, match="no command queue"):
        handler._enqueue_command("set_freq", {"freq": 1})

    queue = _QueueRecorder()
    handler = _control_handler(server=SimpleNamespace(command_queue=queue))
    with pytest.raises(ValueError, match="unhandled command"):
        handler._enqueue_command("definitely_unknown", {})


async def test_control_run_registers_unregisters_and_sends_hello() -> None:
    ws = SimpleNamespace(
        send_text=AsyncMock(),
        recv=AsyncMock(side_effect=[(WS_OP_BINARY, b""), EOFError()]),
    )
    radio = SimpleNamespace(connected=True, radio_ready=True)
    server = SimpleNamespace(
        register_control_event_queue=MagicMock(),
        unregister_control_event_queue=MagicMock(),
    )
    handler = _control_handler(ws=ws, radio=radio, server=server)
    await handler.run()

    server.register_control_event_queue.assert_called_once()
    server.unregister_control_event_queue.assert_called_once()
    hello = decode_json(ws.send_text.await_args_list[0].args[0])
    assert hello["type"] == "hello"
    assert hello["connected"] is True
    assert hello["radio_ready"] is True


async def test_control_event_sender_loop_filters_by_subscription() -> None:
    ws = SimpleNamespace(send_text=AsyncMock())
    handler = _control_handler(ws=ws)
    task = asyncio.create_task(handler._event_sender_loop())
    try:
        await handler._event_queue.put({"type": "event", "ignored": True})
        await asyncio.sleep(0)
        assert ws.send_text.await_count == 0

        handler._subscribed_streams.add("state")
        await handler._event_queue.put({"type": "event", "state": {"freq": 1}})
        await asyncio.sleep(0)
        assert ws.send_text.await_count == 1
    finally:
        task.cancel()
        await task


async def test_handle_text_dispatches_supported_types() -> None:
    handler = _control_handler()
    handler._handle_subscribe = AsyncMock()  # type: ignore[method-assign]
    handler._handle_unsubscribe = AsyncMock()  # type: ignore[method-assign]
    handler._handle_command = AsyncMock()  # type: ignore[method-assign]
    handler._handle_radio_connect = AsyncMock()  # type: ignore[method-assign]
    handler._handle_radio_disconnect = AsyncMock()  # type: ignore[method-assign]

    await handler._handle_text(encode_json({"type": "subscribe"}))
    await handler._handle_text(encode_json({"type": "unsubscribe"}))
    await handler._handle_text(encode_json({"type": "cmd"}))
    await handler._handle_text(encode_json({"type": "radio_connect"}))
    await handler._handle_text(encode_json({"type": "radio_disconnect"}))
    await handler._handle_text("not-json")
    await handler._handle_text(encode_json({"type": "unknown"}))

    handler._handle_subscribe.assert_awaited_once()
    handler._handle_unsubscribe.assert_awaited_once()
    handler._handle_command.assert_awaited_once()
    handler._handle_radio_connect.assert_awaited_once()
    handler._handle_radio_disconnect.assert_awaited_once()


async def test_subscribe_unsubscribe_and_subscribed_streams_property() -> None:
    ws = SimpleNamespace(send_text=AsyncMock())
    handler = _control_handler(ws=ws)
    await handler._handle_subscribe({"streams": ["state", 1, "meters"]})
    assert handler.subscribed_streams == frozenset({"state", "1", "meters"})

    await handler._handle_unsubscribe({"streams": ["1"]})
    assert handler.subscribed_streams == frozenset({"state", "meters"})

    await handler._handle_subscribe({"streams": "not-a-list"})
    await handler._handle_unsubscribe({"streams": "not-a-list"})


async def test_send_state_snapshot_uses_server_cache() -> None:
    ws = SimpleNamespace(send_text=AsyncMock())
    cache = SimpleNamespace(
        freq_ts=1.0,
        freq=14_074_000,
        mode_ts=1.0,
        mode="USB",
        filter_width=2,
        ptt=True,
    )
    handler = _control_handler(
        ws=ws,
        radio=SimpleNamespace(connected=True, radio_ready=True),
        server=SimpleNamespace(state_cache=cache),
    )
    await handler._send_state_snapshot()
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["type"] == "state"
    assert msg["data"]["freq_a"] == 14_074_000
    assert msg["data"]["filter"] == "FIL2"
    assert msg["data"]["ptt"] is True
    assert msg["radio_ready"] is True


async def test_send_state_snapshot_uses_radio_cache_when_server_cache_missing() -> None:
    ws = SimpleNamespace(send_text=AsyncMock())
    radio = SimpleNamespace(
        radio_ready=False,
        state_cache=SimpleNamespace(
            freq_ts=1.0,
            freq=7_074_000,
            mode_ts=1.0,
            mode="LSB",
            filter_width=None,
            ptt=False,
        )
    )
    handler = _control_handler(
        ws=ws,
        radio=radio,
        server=SimpleNamespace(state_cache=None),
    )
    await handler._send_state_snapshot()
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["data"]["freq_a"] == 7_074_000
    assert msg["data"]["mode"] == "LSB"
    assert msg["data"]["filter"] == "FIL1"
    assert msg["radio_ready"] is False


async def test_send_state_snapshot_cache_errors_are_ignored() -> None:
    ws = SimpleNamespace(send_text=AsyncMock())

    class _BadCache:
        @property
        def freq_ts(self) -> float:
            raise RuntimeError("boom")

    handler = _control_handler(ws=ws, server=SimpleNamespace(state_cache=_BadCache()))
    await handler._send_state_snapshot()
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["data"]["freq_a"] == 0
    assert msg["data"]["mode"] == "USB"
    assert "radio_ready" in msg


async def test_handle_command_response_paths() -> None:
    ws = SimpleNamespace(send_text=AsyncMock())
    handler = _control_handler(ws=ws, radio=SimpleNamespace(connected=True), server=None)

    await handler._handle_command({"id": "a", "name": "bad", "params": {}})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["ok"] is False and msg["error"] == "unknown_command"

    handler = _control_handler(ws=ws, radio=None, server=SimpleNamespace(command_queue=_QueueRecorder()))
    await handler._handle_command({"id": "b", "name": "set_freq", "params": {"freq": 1}})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["ok"] is False and msg["error"] == "no_radio"

    queue = _QueueRecorder()
    handler = _control_handler(
        ws=ws,
        radio=SimpleNamespace(connected=True),
        server=SimpleNamespace(command_queue=queue),
    )
    await handler._handle_command({"id": "c", "name": "set_freq", "params": {"freq": 123}})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["ok"] is True and msg["result"]["freq"] == 123

    await handler._handle_command({"id": "d", "name": "set_freq", "params": {}})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["ok"] is False and msg["error"] == "command_failed"


async def test_radio_connect_paths() -> None:
    ws = SimpleNamespace(send_text=AsyncMock())

    h = _control_handler(ws=ws, radio=None)
    await h._handle_radio_connect({"id": "x"})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["error"] == "no_radio"

    radio = SimpleNamespace(connected=True)
    h = _control_handler(ws=ws, radio=radio)
    await h._handle_radio_connect({"id": "x2"})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["result"]["status"] == "already_connected"

    radio = SimpleNamespace(
        connected=False,
        soft_reconnect=AsyncMock(),
        connect=AsyncMock(),
    )
    h = _control_handler(ws=ws, radio=radio)
    await h._handle_radio_connect({"id": "x3"})
    msgs = [decode_json(c.args[0]) for c in ws.send_text.await_args_list[-2:]]
    assert msgs[0]["result"]["status"] == "connected"
    assert msgs[1]["type"] == "event" and msgs[1]["connected"] is True

    radio = SimpleNamespace(
        connected=False,
        soft_reconnect=AsyncMock(side_effect=RuntimeError("nope")),
        connect=AsyncMock(),
    )
    h = _control_handler(ws=ws, radio=radio)
    await h._handle_radio_connect({"id": "x4"})
    radio.connect.assert_awaited_once()

    class _RadioNoSoft:
        connected = False

        def __init__(self) -> None:
            self.connect = AsyncMock(side_effect=RuntimeError("fail"))

    h = _control_handler(ws=ws, radio=_RadioNoSoft())
    await h._handle_radio_connect({"id": "x5"})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["ok"] is False and msg["error"] == "connect_failed"


async def test_radio_connect_rejected_while_backend_recovering() -> None:
    ws = SimpleNamespace(send_text=AsyncMock())
    radio = SimpleNamespace(
        connected=True,
        radio_ready=False,
        soft_reconnect=AsyncMock(),
        connect=AsyncMock(),
    )
    h = _control_handler(ws=ws, radio=radio)
    await h._handle_radio_connect({"id": "busy"})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["ok"] is False
    assert msg["error"] == "backend_recovering"
    radio.soft_reconnect.assert_not_awaited()
    radio.connect.assert_not_awaited()


async def test_radio_disconnect_paths() -> None:
    ws = SimpleNamespace(send_text=AsyncMock())

    h = _control_handler(ws=ws, radio=None)
    await h._handle_radio_disconnect({"id": "d0"})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["error"] == "no_radio"

    radio = SimpleNamespace(connected=False, soft_disconnect=AsyncMock())
    h = _control_handler(ws=ws, radio=radio)
    await h._handle_radio_disconnect({"id": "d1"})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["result"]["status"] == "already_disconnected"

    radio = SimpleNamespace(connected=True, soft_disconnect=AsyncMock())
    h = _control_handler(ws=ws, radio=radio)
    await h._handle_radio_disconnect({"id": "d2"})
    msgs = [decode_json(c.args[0]) for c in ws.send_text.await_args_list[-2:]]
    assert msgs[0]["result"]["status"] == "disconnected"
    assert msgs[1]["event"] == "connection_state" and msgs[1]["connected"] is False

    radio = SimpleNamespace(
        connected=True,
        soft_disconnect=AsyncMock(side_effect=RuntimeError("boom")),
    )
    h = _control_handler(ws=ws, radio=radio)
    await h._handle_radio_disconnect({"id": "d3"})
    msg = decode_json(ws.send_text.await_args_list[-1].args[0])
    assert msg["ok"] is False and msg["error"] == "disconnect_failed"


async def test_scope_run_and_control_handling() -> None:
    ws = SimpleNamespace(
        recv=AsyncMock(
            side_effect=[
                (WS_OP_TEXT, encode_json({"type": "noop"}).encode("utf-8")),
                (WS_OP_TEXT, b"{"),
                EOFError(),
            ]
        ),
        send_binary=AsyncMock(),
    )
    server = SimpleNamespace(
        ensure_scope_enabled=AsyncMock(),
        unregister_scope_handler=MagicMock(),
    )
    handler = ScopeHandler(ws, None, server=server)
    handler._sender = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await handler.run()
    server.ensure_scope_enabled.assert_awaited_once_with(handler)
    server.unregister_scope_handler.assert_called_once_with(handler)
    assert handler._running is False


async def test_scope_sender_timeout_and_error_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    ws = SimpleNamespace(send_binary=AsyncMock())
    handler = ScopeHandler(ws, None)
    calls = {"count": 0}

    async def _fake_wait_for(coro: object, **_kwargs: object) -> bytes:
        calls["count"] += 1
        if calls["count"] == 1:
            if hasattr(coro, "close"):
                coro.close()
            raise TimeoutError
        if hasattr(coro, "close"):
            coro.close()
        raise RuntimeError("stop")

    monkeypatch.setattr("icom_lan.web.handlers.asyncio.wait_for", _fake_wait_for)
    await handler._sender()
    assert ws.send_binary.await_count == 0


async def test_scope_sender_sends_and_stops_on_send_error() -> None:
    ws = SimpleNamespace(
        send_binary=AsyncMock(side_effect=[None, RuntimeError("boom")])
    )
    handler = ScopeHandler(ws, None)
    await handler._frame_queue.put(b"one")
    await handler._frame_queue.put(b"two")
    await handler._sender()
    assert ws.send_binary.await_count == 2


async def test_scope_enqueue_and_push_paths() -> None:
    handler = ScopeHandler(SimpleNamespace(send_binary=AsyncMock()), None)
    frame = _scope_frame()
    handler.enqueue_frame(frame)
    assert handler._frame_queue.qsize() == 0
    handler._running = True
    handler.push_frame(frame)
    assert handler._frame_queue.qsize() == 1


async def test_meters_run_and_control_messages() -> None:
    ws = SimpleNamespace(
        recv=AsyncMock(
            side_effect=[
                (WS_OP_BINARY, b"x"),
                (WS_OP_TEXT, b"not-json"),
                (WS_OP_TEXT, encode_json({"type": "meters_start"}).encode("utf-8")),
                (WS_OP_TEXT, encode_json({"type": "meters_stop"}).encode("utf-8")),
                EOFError(),
            ]
        ),
        send_binary=AsyncMock(),
    )
    server = SimpleNamespace(
        register_meter_handler=MagicMock(),
        unregister_meter_handler=MagicMock(),
    )
    handler = MetersHandler(ws, None, server=server)
    handler._sender = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await handler.run()
    server.register_meter_handler.assert_called_once_with(handler)
    assert server.unregister_meter_handler.call_count >= 1
    assert handler._active is False


async def test_meters_enqueue_sender_and_push_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = SimpleNamespace(send_binary=AsyncMock())
    handler = MetersHandler(ws, None)
    handler.enqueue_frame([(1, 1)])
    assert handler._frame_queue.qsize() == 0
    handler._active = True
    handler.enqueue_frame([(1, 2)])
    assert handler._frame_queue.qsize() == 1
    handler.push_frame([(1, 3)])
    assert handler._frame_queue.qsize() == 2

    calls = {"count": 0}

    async def _fake_wait_for(coro: object, timeout: float) -> bytes:
        del timeout
        calls["count"] += 1
        if calls["count"] == 1:
            return await coro  # type: ignore[misc]
        if calls["count"] == 2:
            if hasattr(coro, "close"):
                coro.close()
            raise asyncio.TimeoutError()
        if hasattr(coro, "close"):
            coro.close()
        raise RuntimeError("stop")

    monkeypatch.setattr("icom_lan.web.handlers.asyncio.wait_for", _fake_wait_for)
    with pytest.raises(RuntimeError, match="stop"):
        await handler._sender()
    assert ws.send_binary.await_count == 1


async def test_audio_broadcaster_subscribe_unsubscribe_lifecycle() -> None:
    from icom_lan.audio_bus import AudioBus

    radio = SimpleNamespace(
        audio_codec=AudioCodec.PCM_1CH_16BIT,
        audio_sample_rate=48_000,
        start_audio_rx_opus=AsyncMock(),
        stop_audio_rx_opus=AsyncMock(),
        push_audio_tx_opus=AsyncMock(),
    )
    bus = AudioBus(radio)
    radio.audio_bus = bus

    broadcaster = AudioBroadcaster(radio)
    q1 = await broadcaster.subscribe()
    q2 = await broadcaster.subscribe()
    # AudioBus starts RX on first subscriber
    radio.start_audio_rx_opus.assert_awaited_once()
    await broadcaster.unsubscribe(q1)
    radio.stop_audio_rx_opus.assert_not_awaited()
    await broadcaster.unsubscribe(q2)
    # Give the scheduled stop task a chance to run
    await asyncio.sleep(0.05)
    radio.stop_audio_rx_opus.assert_awaited_once()


async def test_audio_broadcaster_codec_and_frame_metadata() -> None:
    from icom_lan.audio_bus import AudioBus

    radio = SimpleNamespace(
        audio_codec=AudioCodec.OPUS_2CH,
        audio_sample_rate=96_000,
        start_audio_rx_opus=AsyncMock(),
        stop_audio_rx_opus=AsyncMock(),
        push_audio_tx_opus=AsyncMock(),
    )
    bus = AudioBus(radio)
    radio.audio_bus = bus

    broadcaster = AudioBroadcaster(radio)
    queue = await broadcaster.subscribe()

    # Deliver a packet through the bus
    bus._on_opus_packet(None)  # should be skipped
    bus._on_opus_packet(SimpleNamespace(data=b"\xaa\xbb\xcc"))

    await asyncio.sleep(0.1)
    frame = queue.get_nowait()
    assert frame[1] == AUDIO_CODEC_OPUS
    assert struct.unpack_from("<H", frame, 4)[0] == 960
    assert frame[6] == 2

    await broadcaster.unsubscribe(queue)


async def test_audio_broadcaster_start_relay_failure() -> None:
    from icom_lan.audio_bus import AudioBus

    failing_radio = SimpleNamespace(
        audio_codec=AudioCodec.OPUS_1CH,
        audio_sample_rate=48_000,
        start_audio_rx_opus=AsyncMock(side_effect=RuntimeError("start fail")),
        stop_audio_rx_opus=AsyncMock(),
        push_audio_tx_opus=AsyncMock(),
    )
    bus = AudioBus(failing_radio)
    failing_radio.audio_bus = bus

    bad = AudioBroadcaster(failing_radio)
    await bad._start_relay()
    # Bus subscription exists but RX failed to start
    assert not bus.rx_active


async def test_audio_broadcaster_without_radio_noops() -> None:
    broadcaster = AudioBroadcaster(None)
    queue = await broadcaster.subscribe()
    assert isinstance(queue, asyncio.Queue)
    await broadcaster._stop_relay()


async def test_audio_handler_reader_control_tx_and_sender_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from icom_lan.radio_protocol import AudioCapable

    broadcaster = SimpleNamespace(
        subscribe=AsyncMock(return_value=asyncio.Queue()),
        unsubscribe=AsyncMock(),
    )
    # Mock radio needs to pass isinstance(AudioCapable) check
    radio = MagicMock(spec=AudioCapable)
    radio.push_audio_tx_opus = AsyncMock()
    ws = SimpleNamespace(
        recv=AsyncMock(
            side_effect=[
                (WS_OP_TEXT, b"invalid"),
                (WS_OP_TEXT, encode_json({"type": "audio_start", "direction": "rx"}).encode("utf-8")),
                (WS_OP_TEXT, encode_json({"type": "audio_start", "direction": "tx"}).encode("utf-8")),
                (WS_OP_BINARY, b"\x00" * AUDIO_HEADER_SIZE + b"\x11\x22"),
                (WS_OP_TEXT, encode_json({"type": "audio_stop", "direction": "tx"}).encode("utf-8")),
                EOFError(),
            ]
        ),
        send_binary=AsyncMock(),
    )
    handler = AudioHandler(ws, radio, broadcaster)
    await handler._reader_loop()
    assert handler._rx_active is True
    assert handler._tx_active is False
    radio.push_audio_tx_opus.assert_awaited_once_with(b"\x11\x22")

    handler._done.clear()
    frame = b"frame"
    await handler._frame_queue.put(frame)

    async def _send_binary(data: bytes) -> None:
        assert data == frame
        handler._done.set()

    ws.send_binary = AsyncMock(side_effect=_send_binary)
    await handler._sender_loop()
    assert ws.send_binary.await_count == 1

    # Force timeout then exit with EOFError to hit sender exception path.
    calls = {"count": 0}

    async def _fake_wait_for(coro: object, timeout: float) -> bytes:
        del timeout
        calls["count"] += 1
        if calls["count"] == 1:
            if hasattr(coro, "close"):
                coro.close()
            raise TimeoutError
        return await coro  # type: ignore[misc]

    ws.send_binary = AsyncMock(side_effect=EOFError("closed"))
    handler._done.clear()
    await handler._frame_queue.put(b"x")
    monkeypatch.setattr("icom_lan.web.handlers.asyncio.wait_for", _fake_wait_for)
    await handler._sender_loop()


async def test_audio_handler_control_and_tx_guard_paths() -> None:
    ws = SimpleNamespace(send_binary=AsyncMock(), recv=AsyncMock())
    from icom_lan.radio_protocol import AudioCapable

    class _FakeAudioRadio(AudioCapable):
        push_audio_tx_opus = AsyncMock(side_effect=RuntimeError("boom"))
        start_audio_rx_opus = AsyncMock()
        stop_audio_rx_opus = AsyncMock()
        audio_bus = None

    radio = _FakeAudioRadio()
    broadcaster = SimpleNamespace(
        subscribe=AsyncMock(return_value=asyncio.Queue()),
        unsubscribe=AsyncMock(),
    )
    handler = AudioHandler(ws, radio, broadcaster)

    await handler._start_rx()
    assert handler._rx_active is True
    await handler._handle_control({"type": "audio_stop", "direction": "rx"})
    assert handler._rx_active is False
    broadcaster.unsubscribe.assert_awaited_once()

    handler_no_broadcast = AudioHandler(ws, radio, None)
    await handler_no_broadcast._start_rx()
    await handler_no_broadcast._stop_rx()

    await handler._handle_tx_audio(b"\x00")
    handler._tx_active = True
    await handler._handle_tx_audio(b"\x00" * (AUDIO_HEADER_SIZE - 1))
    await handler._handle_tx_audio(b"\x00" * AUDIO_HEADER_SIZE)
    await handler._handle_tx_audio(b"\x00" * AUDIO_HEADER_SIZE + b"\x99")
    radio.push_audio_tx_opus.assert_awaited_once_with(b"\x99")


async def test_audio_handler_run_calls_stop_rx_on_exit() -> None:
    ws = SimpleNamespace(recv=AsyncMock(side_effect=[EOFError()]), send_binary=AsyncMock())
    broadcaster = SimpleNamespace(
        subscribe=AsyncMock(return_value=asyncio.Queue()),
        unsubscribe=AsyncMock(),
    )
    handler = AudioHandler(ws, SimpleNamespace(push_audio_tx_opus=AsyncMock()), broadcaster)
    handler._rx_active = True
    handler._frame_queue = asyncio.Queue()
    await handler.run()
    assert handler._done.is_set()
    broadcaster.unsubscribe.assert_awaited_once()


def test_audio_handler_constants_are_expected() -> None:
    assert AUDIO_CODEC_PCM16 != AUDIO_CODEC_OPUS
