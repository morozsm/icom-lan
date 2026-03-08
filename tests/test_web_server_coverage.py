"""Additional coverage tests for icom_lan.web.server without real sockets."""

from __future__ import annotations

import asyncio
import pathlib
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan.web.radio_poller import EnableScope
from icom_lan.web.server import WebConfig, WebServer, _send_response, run_web_server


class _FakeSocket:
    def __init__(self, host: str = "127.0.0.1", port: int = 4242) -> None:
        self._host = host
        self._port = port

    def getsockname(self):
        return (self._host, self._port)


class _FakeAsyncServer:
    def __init__(self) -> None:
        self.sockets = [_FakeSocket()]
        self.closed = False

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


class _FakeWriter:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.closed = False
        self.wait_closed_called = False

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        self.wait_closed_called = True

    def get_extra_info(self, name: str, default=None):
        if name == "peername":
            return ("127.0.0.1", 55555)
        return default


def _reader_with(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


def _scope_radio(*, ready: bool = True, connected: bool = True) -> MagicMock:
    radio = MagicMock()
    radio.radio_ready = ready
    radio.connected = connected
    radio.capabilities = {"scope"}
    radio.on_scope_data = MagicMock()
    radio.enable_scope = AsyncMock()
    radio.disable_scope = AsyncMock()
    return radio


@pytest.mark.asyncio
async def test_start_and_stop_with_radio_sets_callbacks() -> None:
    radio = MagicMock()
    radio.state_cache = MagicMock()
    radio.disconnect = AsyncMock()
    fake_server = _FakeAsyncServer()
    fake_poller = MagicMock()

    srv = WebServer(radio, WebConfig(host="127.0.0.1", port=0))
    with (
        patch("icom_lan.web.server.asyncio.start_server", new=AsyncMock(return_value=fake_server)),
        patch("icom_lan.web.server.RadioPoller", return_value=fake_poller),
    ):
        await srv.start()
        assert srv.port == 4242
        radio.set_state_change_callback.assert_called_once_with(srv._on_radio_state_change)
        radio.set_reconnect_callback.assert_called_once_with(srv._on_radio_reconnect)
        fake_poller.start.assert_called_once()
        await srv.stop()

    fake_poller.stop.assert_called_once()
    radio.disconnect.assert_awaited_once()
    assert fake_server.closed is True


@pytest.mark.asyncio
async def test_stop_handles_disconnect_failure_and_cancels_client_tasks() -> None:
    radio = MagicMock()
    radio.disconnect = AsyncMock(side_effect=RuntimeError("disconnect failed"))
    srv = WebServer(radio)
    srv._server = _FakeAsyncServer()
    srv._radio_poller = MagicMock()

    blocker = asyncio.Event()

    async def slow_client() -> None:
        await blocker.wait()

    task = asyncio.create_task(slow_client())
    srv._client_tasks.add(task)
    await srv.stop()
    assert task.cancelled() or task.done()


@pytest.mark.asyncio
async def test_accept_client_max_clients_and_normal_path() -> None:
    srv = WebServer(None, WebConfig(max_clients=0))
    writer = _FakeWriter()
    srv._accept_client(_reader_with(b""), writer)
    assert writer.closed is True

    srv2 = WebServer(None, WebConfig(max_clients=10))
    with patch.object(srv2, "_handle_connection", new=AsyncMock()) as handle_conn:
        writer2 = _FakeWriter()
        srv2._accept_client(_reader_with(b""), writer2)
        await asyncio.sleep(0)
    handle_conn.assert_awaited()


@pytest.mark.asyncio
async def test_read_request_parses_and_handles_invalid_cases() -> None:
    srv = WebServer(None)
    reader = _reader_with(
        b"GET /x%20y?q=1 HTTP/1.1\r\nHost: localhost\r\nX-Test: abc\r\n\r\n"
    )
    method, path, headers = await srv._read_request(reader)  # noqa: SLF001
    assert method == "GET"
    assert path == "/x y"
    assert headers["host"] == "localhost"
    assert headers["x-test"] == "abc"

    bad = _reader_with(b"BROKEN\r\n\r\n")
    assert await srv._read_request(bad) is None  # noqa: SLF001

    async def timeout_wait_for(coro, timeout):
        del timeout
        if hasattr(coro, "close"):
            coro.close()
        raise asyncio.TimeoutError

    with patch("icom_lan.web.server.asyncio.wait_for", side_effect=timeout_wait_for):
        assert await srv._read_request(_reader_with(b"GET / HTTP/1.1\r\n")) is None  # noqa: SLF001


@pytest.mark.asyncio
async def test_handle_http_routes_and_405_404() -> None:
    srv = WebServer(None)
    writer = _FakeWriter()
    with patch("icom_lan.web.server._send_response", new=AsyncMock()) as send_resp:
        await srv._handle_http(writer, "POST", "/")  # noqa: SLF001
    send_resp.assert_awaited_once()

    srv2 = WebServer(None)
    writer2 = _FakeWriter()
    srv2._serve_info = AsyncMock()
    srv2._serve_state = AsyncMock()
    srv2._serve_capabilities = AsyncMock()
    srv2._serve_static = AsyncMock()
    with patch("icom_lan.web.server._send_response", new=AsyncMock()) as send_resp2:
        await srv2._handle_http(writer2, "GET", "/api/v1/info")  # noqa: SLF001
        await srv2._handle_http(writer2, "GET", "/api/v1/state")  # noqa: SLF001
        await srv2._handle_http(writer2, "GET", "/api/v1/capabilities")  # noqa: SLF001
        await srv2._handle_http(writer2, "GET", "/")  # noqa: SLF001
        await srv2._handle_http(writer2, "GET", "/file.js")  # noqa: SLF001
        await srv2._handle_http(writer2, "GET", "relative-path")  # noqa: SLF001
    assert srv2._serve_info.await_count == 1
    assert srv2._serve_state.await_count == 1
    assert srv2._serve_capabilities.await_count == 1
    assert srv2._serve_static.await_count == 2
    send_resp2.assert_awaited_once()


@pytest.mark.asyncio
async def test_serve_static_forbidden_missing_read_error_and_success(tmp_path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    index = static_dir / "index.html"
    index.write_text("<html>ok</html>", encoding="utf-8")

    srv = WebServer(None, WebConfig(static_dir=static_dir))
    writer = _FakeWriter()

    await srv._serve_static(writer, "../secret")  # noqa: SLF001
    assert b"403 Forbidden" in writer.buffer

    writer = _FakeWriter()
    await srv._serve_static(writer, "missing.txt")  # noqa: SLF001
    assert b"404 Not Found" in writer.buffer

    writer = _FakeWriter()
    with patch.object(pathlib.Path, "read_bytes", side_effect=OSError("read fail")):
        await srv._serve_static(writer, "index.html")  # noqa: SLF001
    assert b"500 Internal Server Error" in writer.buffer

    writer = _FakeWriter()
    await srv._serve_static(writer, "index.html")  # noqa: SLF001
    text = writer.buffer.decode("ascii", errors="replace")
    assert "200 OK" in text
    assert "Cache-Control: no-cache, no-store, must-revalidate" in text


@pytest.mark.asyncio
async def test_handle_websocket_missing_key_unknown_channel_and_control_handler() -> None:
    srv = WebServer(None)
    writer = _FakeWriter()
    with patch("icom_lan.web.server._send_response", new=AsyncMock()) as send_resp:
        await srv._handle_websocket(_reader_with(b""), writer, "/api/v1/ws", {})  # noqa: SLF001
    send_resp.assert_awaited_once()

    ws_unknown = MagicMock()
    ws_unknown.close = AsyncMock()
    ws_unknown.keepalive_loop = AsyncMock()
    with patch("icom_lan.web.server.WebSocketConnection", return_value=ws_unknown):
        await srv._handle_websocket(  # noqa: SLF001
            _reader_with(b""), _FakeWriter(), "/api/v1/unknown",
            {"sec-websocket-key": "abc"},
        )
    ws_unknown.close.assert_awaited_once_with(1008, "unknown channel")

    ws_ok = MagicMock()

    async def keepalive_loop(_interval: float) -> None:
        await asyncio.sleep(3600)

    ws_ok.keepalive_loop = keepalive_loop
    ws_ok.close = AsyncMock()
    handler = MagicMock()
    handler.run = AsyncMock(side_effect=RuntimeError("handler failed"))
    writer_ok = _FakeWriter()
    with (
        patch("icom_lan.web.server.WebSocketConnection", return_value=ws_ok),
        patch("icom_lan.web.server.ControlHandler", return_value=handler),
    ):
        await srv._handle_websocket(  # noqa: SLF001
            _reader_with(b""), writer_ok, "/api/v1/ws",
            {"sec-websocket-key": "abc"},
        )
    assert b"101 Switching Protocols" in writer_ok.buffer
    handler.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_connection_none_http_ws_and_exception() -> None:
    srv = WebServer(None)
    writer = _FakeWriter()

    srv._read_request = AsyncMock(return_value=None)
    await srv._handle_connection(_reader_with(b""), writer)  # noqa: SLF001
    assert writer.closed is True

    writer2 = _FakeWriter()
    srv._read_request = AsyncMock(return_value=("GET", "/api/v1/info", {}))
    srv._handle_http = AsyncMock()
    await srv._handle_connection(_reader_with(b""), writer2)  # noqa: SLF001
    srv._handle_http.assert_awaited_once()

    writer3 = _FakeWriter()
    srv._read_request = AsyncMock(return_value=(
        "GET", "/api/v1/ws", {"upgrade": "websocket", "connection": "Upgrade"},
    ))
    srv._handle_websocket = AsyncMock()
    await srv._handle_connection(_reader_with(b""), writer3)  # noqa: SLF001
    srv._handle_websocket.assert_awaited_once()

    writer4 = _FakeWriter()
    srv._read_request = AsyncMock(side_effect=RuntimeError("boom"))
    await srv._handle_connection(_reader_with(b""), writer4)  # noqa: SLF001
    assert writer4.closed is True


@pytest.mark.asyncio
async def test_scope_health_and_radio_state_event_paths() -> None:
    meter_handler = MagicMock()
    radio = _scope_radio()
    srv = WebServer(radio)
    srv._meter_handlers.add(meter_handler)

    frame = SimpleNamespace(pixels=b"\x00\x01")
    before = srv._scope_last_nonzero
    srv._scope_health_check(frame)  # noqa: SLF001
    assert srv._scope_last_nonzero >= before

    bad = SimpleNamespace(pixels=123)
    srv._scope_health_check(bad)  # noqa: SLF001

    srv._on_radio_state_change("meter", {"type": "power", "raw": 77})  # noqa: SLF001
    sent = meter_handler.enqueue_frame.call_args.args[0]
    assert sent[0][1] == 77

    scope_handler = MagicMock()
    srv._scope_handlers.add(scope_handler)
    srv._on_radio_reconnect()  # noqa: SLF001
    cmds = srv.command_queue.drain
    assert any(isinstance(c, EnableScope) for c in cmds())


@pytest.mark.asyncio
async def test_on_radio_reconnect_waits_until_radio_ready() -> None:
    radio = _scope_radio(ready=False)
    srv = WebServer(radio)
    srv._scope_handlers.add(MagicMock())
    srv._scope_reenable_poll_interval = 0.01  # noqa: SLF001
    srv._scope_reenable_timeout = 0.2  # noqa: SLF001

    srv._on_radio_reconnect()  # noqa: SLF001
    assert not any(isinstance(c, EnableScope) for c in srv.command_queue.drain())

    radio.radio_ready = True
    await asyncio.sleep(0.03)
    assert any(isinstance(c, EnableScope) for c in srv.command_queue.drain())


@pytest.mark.asyncio
async def test_ensure_scope_enabled_defers_enable_when_radio_not_ready() -> None:
    radio = _scope_radio(ready=False)
    srv = WebServer(radio)
    srv._scope_reenable_poll_interval = 0.01  # noqa: SLF001
    srv._scope_reenable_timeout = 0.2  # noqa: SLF001

    await srv.ensure_scope_enabled(MagicMock())
    assert not any(isinstance(c, EnableScope) for c in srv.command_queue.drain())

    radio.radio_ready = True
    await asyncio.sleep(0.03)
    assert any(isinstance(c, EnableScope) for c in srv.command_queue.drain())


@pytest.mark.asyncio
async def test_ensure_scope_enabled_skips_when_scope_capability_absent() -> None:
    radio = MagicMock()
    radio.connected = True
    radio.radio_ready = True
    radio.capabilities = set()
    srv = WebServer(radio)

    await srv.ensure_scope_enabled(MagicMock())

    assert not any(isinstance(c, EnableScope) for c in srv.command_queue.drain())
    assert srv._scope_enabled is False


@pytest.mark.asyncio
async def test_scope_health_monitor_disconnected_and_reenable() -> None:
    radio = _scope_radio(connected=False)
    srv = WebServer(radio)
    srv._scope_handlers.add(MagicMock())
    srv._scope_health_interval = 0.01
    srv._scope_last_nonzero = 0.0

    task = asyncio.create_task(srv._scope_health_monitor())  # noqa: SLF001
    await asyncio.sleep(0.03)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert srv._scope_last_nonzero > 0

    radio.connected = True
    srv._scope_last_nonzero = time.monotonic() - 1.0
    task = asyncio.create_task(srv._scope_health_monitor())  # noqa: SLF001
    await asyncio.sleep(0.03)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    cmds = srv.command_queue.drain()
    assert any(isinstance(c, EnableScope) for c in cmds)


@pytest.mark.asyncio
async def test_send_response_and_run_web_server() -> None:
    writer = _FakeWriter()
    await _send_response(writer, 200, "OK", b"abc", {"Content-Type": "text/plain"})
    assert b"HTTP/1.1 200 OK" in writer.buffer
    assert b"Content-Length: 3" in writer.buffer

    fake_server = MagicMock()
    fake_server.serve_forever = AsyncMock()
    with patch("icom_lan.web.server.WebServer", return_value=fake_server):
        await run_web_server(None, host="127.0.0.1", port=8000)
    fake_server.serve_forever.assert_awaited_once()


@pytest.mark.asyncio
async def test_broadcast_notification_puts_to_all_queues() -> None:
    """broadcast_notification pushes notification dict to all registered queues."""
    srv = WebServer()
    q1: asyncio.Queue[dict] = asyncio.Queue()
    q2: asyncio.Queue[dict] = asyncio.Queue()
    srv.register_control_event_queue(q1)
    srv.register_control_event_queue(q2)

    srv.broadcast_notification("success", "Radio connected", "connection")

    assert not q1.empty()
    assert not q2.empty()
    n1 = q1.get_nowait()
    n2 = q2.get_nowait()
    assert n1["type"] == "notification"
    assert n1["level"] == "success"
    assert n1["message"] == "Radio connected"
    assert n1["category"] == "connection"
    assert n1 == n2


@pytest.mark.asyncio
async def test_broadcast_notification_default_category() -> None:
    """broadcast_notification uses 'system' as default category."""
    srv = WebServer()
    q: asyncio.Queue[dict] = asyncio.Queue()
    srv.register_control_event_queue(q)

    srv.broadcast_notification("info", "Hello")

    n = q.get_nowait()
    assert n["category"] == "system"


@pytest.mark.asyncio
async def test_broadcast_notification_full_queue_no_crash() -> None:
    """broadcast_notification silently skips full queues (dead clients)."""
    srv = WebServer()
    q: asyncio.Queue[dict] = asyncio.Queue(maxsize=1)
    q.put_nowait({"type": "other"})  # fill the queue
    srv.register_control_event_queue(q)

    # Should not raise even though queue is full
    srv.broadcast_notification("warning", "Test")
    assert q.qsize() == 1  # queue still has the old item, notification was dropped
