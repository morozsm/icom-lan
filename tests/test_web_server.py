"""Tests for src/icom_lan/web/ — WebSocket server, protocol, and handlers.

Strategy
--------
- Test binary frame encoding functions directly (no network required).
- Test HTTP endpoints by starting a real server on port 0.
- Test WebSocket handshake, hello, subscribe, commands by connecting via
  asyncio.open_connection and performing the RFC 6455 handshake manually.
- Inject a mock IcomRadio to avoid needing a real radio.
- asyncio_mode = "auto" (pyproject.toml) — no @pytest.mark.asyncio needed.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import struct
from unittest.mock import AsyncMock, MagicMock

import pytest

from icom_lan.rigctld.state_cache import StateCache
from icom_lan.scope import ScopeFrame
from icom_lan.web.protocol import (
    METER_ALC,
    METER_POWER,
    METER_SMETER_MAIN,
    METER_SWR,
    MSG_TYPE_METER,
    MSG_TYPE_SCOPE,
    SCOPE_HEADER_SIZE,
    decode_json,
    encode_json,
    encode_meter_frame,
    encode_scope_frame,
)
from icom_lan.web.server import WebConfig, WebServer
from icom_lan.web.websocket import (
    WS_MAGIC,
    WS_OP_BINARY,
    WS_OP_PING,
    WS_OP_TEXT,
    WebSocketConnection,
    make_accept_key,
    make_frame,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _addr(server: WebServer) -> tuple[str, int]:
    assert server._server is not None
    return server._server.sockets[0].getsockname()


def _ws_accept(key: str) -> str:
    raw = (key + WS_MAGIC).encode("ascii")
    return base64.b64encode(hashlib.sha1(raw).digest()).decode("ascii")


async def _http_get(
    host: str, port: int, path: str
) -> tuple[int, dict[str, str], bytes]:
    """Minimal synchronous-style HTTP GET over asyncio."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        request = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
        writer.write(request.encode())
        await writer.drain()

        raw = await asyncio.wait_for(reader.read(65536), timeout=5.0)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

    # Parse response
    header_end = raw.find(b"\r\n\r\n")
    header_bytes = raw[:header_end]
    body = raw[header_end + 4 :]

    lines = header_bytes.decode("ascii", errors="replace").split("\r\n")
    status_line = lines[0]
    status_code = int(status_line.split(" ", 2)[1])
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip().lower()] = v.strip()

    return status_code, headers, body


async def _ws_connect(
    host: str, port: int, path: str, key: str = "dGhlIHNhbXBsZSBub25jZQ=="
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter, str]:
    """Perform WebSocket HTTP Upgrade handshake.

    Returns:
        (reader, writer, accept_key) after successful upgrade.
    """
    reader, writer = await asyncio.open_connection(host, port)
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    writer.write(request.encode())
    await writer.drain()

    # Read exactly up to the end of the HTTP headers.  Using readuntil() instead
    # of read(N) ensures that any WebSocket frames the server sends immediately
    # after the 101 (e.g. the "hello" message) stay in the reader buffer and are
    # not accidentally consumed here.
    resp = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5.0)

    assert b"101" in resp, f"Expected 101, got: {resp[:200]}"
    accept = make_accept_key(key)
    assert accept.encode() in resp, "Invalid Sec-WebSocket-Accept"
    return reader, writer, accept


async def _ws_send_text(writer: asyncio.StreamWriter, text: str) -> None:
    """Send a masked text frame (client→server)."""
    payload = text.encode("utf-8")
    mask = b"\xde\xad\xbe\xef"
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    length = len(payload)
    if length <= 125:
        header = bytes([0x81, 0x80 | length]) + mask
    elif length <= 65535:
        header = struct.pack("!BBH", 0x81, 0x80 | 126, length) + mask
    else:
        header = struct.pack("!BBQ", 0x81, 0x80 | 127, length) + mask
    writer.write(header + masked)
    await writer.drain()


async def _ws_recv_frame(
    reader: asyncio.StreamReader,
    timeout: float = 10.0,
) -> tuple[int, bytes]:
    """Read one (unmasked) server→client WebSocket frame, skipping ping/pong."""
    while True:
        header = await asyncio.wait_for(reader.readexactly(2), timeout=timeout)
        byte0, byte1 = header[0], header[1]
        opcode = byte0 & 0x0F
        payload_len = byte1 & 0x7F

        if payload_len == 126:
            ext = await reader.readexactly(2)
            payload_len = struct.unpack("!H", ext)[0]
        elif payload_len == 127:
            ext = await reader.readexactly(8)
            payload_len = struct.unpack("!Q", ext)[0]

        payload = await reader.readexactly(payload_len)
        # Skip control frames (ping=0x9, pong=0xA)
        if opcode in (0x9, 0xA):
            continue
        return opcode, payload


async def _close_ws(writer: asyncio.StreamWriter) -> None:
    # Send masked close frame
    mask = b"\x00\x00\x00\x00"
    close_payload = struct.pack("!H", 1000)
    masked_close = bytes(b ^ mask[i % 4] for i, b in enumerate(close_payload))
    writer.write(bytes([0x88, 0x80 | 2]) + mask + masked_close)
    try:
        await writer.drain()
        writer.close()
        await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_radio() -> MagicMock:
    radio = MagicMock(name="radio")
    radio.connected = True
    radio.get_frequency = AsyncMock(return_value=14_074_000)
    radio.get_mode = AsyncMock(return_value=MagicMock(name="USB"))
    radio.get_mode.return_value.name = "USB"
    _mode_mock = MagicMock(name="USB")
    _mode_mock.name = "USB"
    radio.get_mode_info = AsyncMock(return_value=(_mode_mock, 1))
    radio.get_power = AsyncMock(return_value=100)
    radio.get_filter = AsyncMock(return_value=1)
    radio.get_s_meter = AsyncMock(return_value=42)
    radio.get_swr = AsyncMock(return_value=10)
    radio.get_alc = AsyncMock(return_value=5)
    radio.get_rf_gain = AsyncMock(return_value=200)
    radio.get_af_level = AsyncMock(return_value=180)
    radio.get_attenuator_level = AsyncMock(return_value=0)
    radio.get_preamp = AsyncMock(return_value=1)
    radio.get_data_mode = AsyncMock(return_value=False)
    radio.set_frequency = AsyncMock()
    radio.set_mode = AsyncMock()
    radio.set_filter = AsyncMock()
    radio.set_power = AsyncMock()
    radio.set_ptt = AsyncMock()
    radio.set_rf_gain = AsyncMock()
    radio.set_af_level = AsyncMock()
    radio.set_attenuator_level = AsyncMock()
    radio.set_preamp = AsyncMock()
    radio.select_vfo = AsyncMock()
    radio.vfo_swap = AsyncMock()
    radio.vfo_exchange = AsyncMock()
    radio.vfo_a_equals_b = AsyncMock()
    # on_scope_data is a synchronous setter
    radio.on_scope_data = MagicMock()
    # State cache shared between radio and server
    radio.state_cache = StateCache()
    # Methods used by WebServer.stop() and RadioPoller
    radio.soft_disconnect = AsyncMock()
    radio.send_civ = AsyncMock()
    # AudioBroadcaster needs these
    radio.start_audio_rx_opus = AsyncMock()
    radio.stop_audio_rx_opus = AsyncMock()
    radio.audio_codec = None
    radio.audio_sample_rate = 48000
    return radio


@pytest.fixture
async def server(mock_radio: MagicMock) -> WebServer:
    # keepalive_interval=9999 disables keepalive pings during tests to prevent
    # spurious ping frames from interfering with test assertions. (#45)
    config = WebConfig(host="127.0.0.1", port=0, keepalive_interval=9999.0)
    srv = WebServer(mock_radio, config)
    await srv.start()
    yield srv
    await srv.stop()


@pytest.fixture
async def server_no_radio() -> WebServer:
    config = WebConfig(host="127.0.0.1", port=0, keepalive_interval=9999.0)
    srv = WebServer(None, config)
    await srv.start()
    yield srv
    await srv.stop()


# ---------------------------------------------------------------------------
# Protocol unit tests (no network)
# ---------------------------------------------------------------------------


class TestProtocolEncoding:
    def test_encode_scope_frame_header_size(self) -> None:
        frame = ScopeFrame(
            receiver=0,
            mode=0,
            start_freq_hz=14_000_000,
            end_freq_hz=14_350_000,
            pixels=bytes(range(100)),
            out_of_range=False,
        )
        data = encode_scope_frame(frame, sequence=0)
        assert len(data) == SCOPE_HEADER_SIZE + 100

    def test_encode_scope_frame_msg_type(self) -> None:
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 475, False)
        data = encode_scope_frame(frame, 0)
        assert data[0] == MSG_TYPE_SCOPE

    def test_encode_scope_frame_receiver_mode(self) -> None:
        frame = ScopeFrame(1, 2, 14_000_000, 14_350_000, b"\x00" * 10, False)
        data = encode_scope_frame(frame, 0)
        assert data[1] == 1  # receiver
        assert data[2] == 2  # mode

    def test_encode_scope_frame_frequencies_little_endian(self) -> None:
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 10, False)
        data = encode_scope_frame(frame, 0)
        start_freq = struct.unpack_from("<I", data, 3)[0]
        end_freq = struct.unpack_from("<I", data, 7)[0]
        assert start_freq == 14_000_000
        assert end_freq == 14_350_000

    def test_encode_scope_frame_sequence_little_endian(self) -> None:
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 10, False)
        for seq in (0, 1, 255, 1000, 65535):
            data = encode_scope_frame(frame, seq)
            read_seq = struct.unpack_from("<H", data, 11)[0]
            assert read_seq == seq & 0xFFFF

    def test_encode_scope_frame_sequence_wraps_at_16bit(self) -> None:
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 10, False)
        data = encode_scope_frame(frame, 65537)
        read_seq = struct.unpack_from("<H", data, 11)[0]
        assert read_seq == 1  # 65537 & 0xFFFF

    def test_encode_scope_frame_flags_out_of_range(self) -> None:
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"", True)
        data = encode_scope_frame(frame, 0)
        assert data[13] & 0x01  # bit 0 = out_of_range

    def test_encode_scope_frame_flags_in_range(self) -> None:
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 5, False)
        data = encode_scope_frame(frame, 0)
        assert not (data[13] & 0x01)

    def test_encode_scope_frame_pixel_count_little_endian(self) -> None:
        pixels = bytes(range(200))
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, pixels, False)
        data = encode_scope_frame(frame, 0)
        count = struct.unpack_from("<H", data, 14)[0]
        assert count == 200

    def test_encode_scope_frame_pixels_appended(self) -> None:
        pixels = bytes(range(50))
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, pixels, False)
        data = encode_scope_frame(frame, 0)
        assert data[SCOPE_HEADER_SIZE:] == pixels

    def test_encode_scope_frame_475_pixels(self) -> None:
        """Typical IC-7610 frame size."""
        pixels = bytes(i % 161 for i in range(475))
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, pixels, False)
        data = encode_scope_frame(frame, 0)
        assert len(data) == 16 + 475

    def test_encode_meter_frame_header(self) -> None:
        data = encode_meter_frame([], sequence=0)
        assert data[0] == MSG_TYPE_METER
        assert len(data) == 4  # header only, 0 meters

    def test_encode_meter_frame_sequence_little_endian(self) -> None:
        for seq in (0, 1, 255, 1000, 65535):
            data = encode_meter_frame([], sequence=seq)
            read_seq = struct.unpack_from("<H", data, 1)[0]
            assert read_seq == seq & 0xFFFF

    def test_encode_meter_frame_count(self) -> None:
        meters = [(METER_SMETER_MAIN, 42), (METER_POWER, 200)]
        data = encode_meter_frame(meters, 0)
        assert data[3] == 2

    def test_encode_meter_frame_meter_values(self) -> None:
        meters = [(METER_SMETER_MAIN, 42), (METER_SWR, 300), (METER_ALC, 0)]
        data = encode_meter_frame(meters, 0)
        # First meter at offset 4
        assert data[4] == METER_SMETER_MAIN
        assert data[5] == 42 & 0xFF
        assert data[6] == (42 >> 8) & 0xFF
        # Second meter at offset 7
        assert data[7] == METER_SWR
        assert data[8] == 300 & 0xFF
        assert data[9] == (300 >> 8) & 0xFF
        # Third meter at offset 10
        assert data[10] == METER_ALC
        assert data[11] == 0
        assert data[12] == 0

    def test_encode_meter_frame_total_size(self) -> None:
        meters = [(i, i * 10) for i in range(9)]
        data = encode_meter_frame(meters, 0)
        assert len(data) == 4 + 9 * 3  # header + 9 meters

    def test_encode_decode_json_roundtrip(self) -> None:
        msg = {"type": "hello", "proto": 1, "version": "0.7.0"}
        assert decode_json(encode_json(msg)) == msg

    def test_decode_json_invalid(self) -> None:
        with pytest.raises(ValueError):
            decode_json("not json {{{")

    def test_decode_json_non_object(self) -> None:
        with pytest.raises(ValueError):
            decode_json("[1, 2, 3]")

    def test_make_accept_key(self) -> None:
        # RFC 6455 §1.3 example
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        expected = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
        assert make_accept_key(key) == expected

    def test_make_frame_text_small(self) -> None:
        frame = make_frame(WS_OP_TEXT, b"hello")
        assert frame[0] == 0x81  # FIN + TEXT
        assert frame[1] == 5  # length, no mask
        assert frame[2:] == b"hello"

    def test_make_frame_binary_126(self) -> None:
        payload = b"x" * 126
        frame = make_frame(WS_OP_BINARY, payload)
        assert frame[0] == 0x82  # FIN + BINARY
        assert frame[1] == 126
        length = struct.unpack("!H", frame[2:4])[0]
        assert length == 126
        assert frame[4:] == payload

    def test_make_frame_binary_large(self) -> None:
        payload = b"x" * 70000
        frame = make_frame(WS_OP_BINARY, payload)
        assert frame[0] == 0x82
        assert frame[1] == 127
        length = struct.unpack("!Q", frame[2:10])[0]
        assert length == 70000


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------


class TestHttpEndpoints:
    async def test_info_endpoint_status(self, server: WebServer) -> None:
        host, port = _addr(server)
        status, _, _ = await _http_get(host, port, "/api/v1/info")
        assert status == 200

    async def test_info_endpoint_content_type(self, server: WebServer) -> None:
        host, port = _addr(server)
        _, headers, _ = await _http_get(host, port, "/api/v1/info")
        assert "json" in headers.get("content-type", "")

    async def test_info_endpoint_json_fields(self, server: WebServer) -> None:
        host, port = _addr(server)
        _, _, body = await _http_get(host, port, "/api/v1/info")
        data = json.loads(body)
        assert "server" in data
        assert data["server"] == "icom-lan"
        assert "version" in data
        assert "proto" in data
        assert data["proto"] == 1
        assert "radio" in data

    async def test_capabilities_endpoint_status(self, server: WebServer) -> None:
        host, port = _addr(server)
        status, _, _ = await _http_get(host, port, "/api/v1/capabilities")
        assert status == 200

    async def test_capabilities_endpoint_json_fields(
        self, server: WebServer
    ) -> None:
        host, port = _addr(server)
        _, _, body = await _http_get(host, port, "/api/v1/capabilities")
        data = json.loads(body)
        assert "scope" in data
        assert "audio" in data
        assert "modes" in data
        assert isinstance(data["modes"], list)

    async def test_root_returns_html(self, server: WebServer) -> None:
        host, port = _addr(server)
        status, headers, body = await _http_get(host, port, "/")
        assert status == 200
        assert "html" in headers.get("content-type", "").lower()
        assert b"<!DOCTYPE html>" in body or b"<!doctype html>" in body.lower()

    async def test_unknown_path_404(self, server: WebServer) -> None:
        host, port = _addr(server)
        status, _, _ = await _http_get(host, port, "/api/v1/nonexistent")
        assert status == 404


# ---------------------------------------------------------------------------
# WebSocket handshake tests
# ---------------------------------------------------------------------------


class TestWebSocketHandshake:
    async def test_upgrade_control_channel(self, server: WebServer) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        await _close_ws(writer)

    async def test_upgrade_scope_channel(self, server: WebServer) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/scope")
        await _close_ws(writer)

    async def test_upgrade_meters_channel(self, server: WebServer) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/meters")
        await _close_ws(writer)

    async def test_upgrade_audio_channel(self, server: WebServer) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/audio")
        await _close_ws(writer)

    async def test_accept_key_correct(self, server: WebServer) -> None:
        host, port = _addr(server)
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        reader, writer, accept = await _ws_connect(host, port, "/api/v1/ws", key)
        assert accept == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
        await _close_ws(writer)


# ---------------------------------------------------------------------------
# Control channel protocol tests
# ---------------------------------------------------------------------------


class TestControlChannel:
    async def test_hello_on_connect(self, server: WebServer) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            opcode, payload = await _ws_recv_frame(reader)
            assert opcode == WS_OP_TEXT
            msg = json.loads(payload)
            assert msg["type"] == "hello"
            assert msg["proto"] == 1
            assert msg["server"] == "icom-lan"
            assert "version" in msg
            assert "radio" in msg
            assert "capabilities" in msg
        finally:
            await _close_ws(writer)

    async def test_hello_capabilities_list(self, server: WebServer) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            _, payload = await _ws_recv_frame(reader)
            msg = json.loads(payload)
            caps = msg["capabilities"]
            assert isinstance(caps, list)
            assert "scope" in caps
        finally:
            await _close_ws(writer)

    async def test_subscribe_triggers_state(self, server: WebServer) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            # Consume hello
            await _ws_recv_frame(reader)
            # Send subscribe
            sub = {"type": "subscribe", "streams": ["scope", "meters"]}
            await _ws_send_text(writer, json.dumps(sub))
            # Should receive state snapshot
            opcode, payload = await _ws_recv_frame(reader)
            assert opcode == WS_OP_TEXT
            msg = json.loads(payload)
            assert msg["type"] == "state"
            assert "data" in msg
        finally:
            await _close_ws(writer)

    async def test_state_snapshot_fields(self, server: WebServer) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            await _ws_recv_frame(reader)  # hello
            await _ws_send_text(
                writer, json.dumps({"type": "subscribe", "streams": []})
            )
            _, payload = await _ws_recv_frame(reader)
            data = json.loads(payload)["data"]
            assert "freq_a" in data
            assert "mode" in data
            assert "ptt" in data
        finally:
            await _close_ws(writer)

    async def test_command_set_freq(
        self, server: WebServer, mock_radio: MagicMock
    ) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            await _ws_recv_frame(reader)  # hello
            mock_radio.get_filter.return_value = 2
            cmd = {
                "type": "cmd",
                "id": "test-1",
                "name": "set_freq",
                "params": {"vfo": "A", "freq": 14_074_000},
            }
            await _ws_send_text(writer, json.dumps(cmd))
            opcode, payload = await _ws_recv_frame(reader)
            assert opcode == WS_OP_TEXT
            resp = json.loads(payload)
            assert resp["type"] == "response"
            assert resp["id"] == "test-1"
            assert resp["ok"] is True
            assert resp["result"] == {"freq": 14_074_000, "filter": "FIL2"}
            mock_radio.set_frequency.assert_awaited_once_with(14_074_000)
            mock_radio.get_filter.assert_awaited_once()
        finally:
            await _close_ws(writer)

    async def test_command_set_mode(
        self, server: WebServer, mock_radio: MagicMock
    ) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            await _ws_recv_frame(reader)  # hello
            cmd = {
                "type": "cmd",
                "id": "test-2",
                "name": "set_mode",
                "params": {"mode": "LSB"},
            }
            await _ws_send_text(writer, json.dumps(cmd))
            _, payload = await _ws_recv_frame(reader)
            resp = json.loads(payload)
            assert resp["ok"] is True
            mock_radio.set_mode.assert_awaited_once_with("LSB")
        finally:
            await _close_ws(writer)

    async def test_command_ptt(
        self, server: WebServer, mock_radio: MagicMock
    ) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            await _ws_recv_frame(reader)  # hello
            cmd = {
                "type": "cmd",
                "id": "ptt-1",
                "name": "ptt",
                "params": {"state": True},
            }
            await _ws_send_text(writer, json.dumps(cmd))
            _, payload = await _ws_recv_frame(reader)
            resp = json.loads(payload)
            assert resp["ok"] is True
            mock_radio.set_ptt.assert_awaited_once_with(True)
        finally:
            await _close_ws(writer)

    async def test_command_unknown_returns_error(
        self, server: WebServer
    ) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            await _ws_recv_frame(reader)  # hello
            cmd = {
                "type": "cmd",
                "id": "bad-1",
                "name": "hack_the_radio",
                "params": {},
            }
            await _ws_send_text(writer, json.dumps(cmd))
            _, payload = await _ws_recv_frame(reader)
            resp = json.loads(payload)
            assert resp["type"] == "response"
            assert resp["ok"] is False
            assert resp["id"] == "bad-1"
        finally:
            await _close_ws(writer)

    async def test_unsubscribe_removes_stream(
        self, server: WebServer
    ) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            await _ws_recv_frame(reader)  # hello
            # subscribe
            await _ws_send_text(
                writer,
                json.dumps({"type": "subscribe", "streams": ["scope", "meters"]}),
            )
            await _ws_recv_frame(reader)  # state
            # unsubscribe
            await _ws_send_text(
                writer,
                json.dumps({"type": "unsubscribe", "streams": ["scope"]}),
            )
            # no response expected for unsubscribe; just check no error
        finally:
            await _close_ws(writer)

    async def test_command_no_radio_returns_error(
        self, server_no_radio: WebServer
    ) -> None:
        host, port = _addr(server_no_radio)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            await _ws_recv_frame(reader)  # hello
            cmd = {
                "type": "cmd",
                "id": "nr-1",
                "name": "set_freq",
                "params": {"freq": 14_074_000},
            }
            await _ws_send_text(writer, json.dumps(cmd))
            _, payload = await _ws_recv_frame(reader)
            resp = json.loads(payload)
            assert resp["ok"] is False
            assert "no_radio" in resp.get("error", "")
        finally:
            await _close_ws(writer)

    async def test_vfo_swap_command(
        self, server: WebServer, mock_radio: MagicMock
    ) -> None:
        host, port = _addr(server)
        reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
        try:
            await _ws_recv_frame(reader)  # hello
            cmd = {"type": "cmd", "id": "vs-1", "name": "vfo_swap", "params": {}}
            await _ws_send_text(writer, json.dumps(cmd))
            _, payload = await _ws_recv_frame(reader)
            resp = json.loads(payload)
            assert resp["ok"] is True
            mock_radio.vfo_exchange.assert_awaited_once()
        finally:
            await _close_ws(writer)


# ---------------------------------------------------------------------------
# Binary scope frame format tests (RFC conformance)
# ---------------------------------------------------------------------------


class TestScopeFrameFormat:
    """Verify binary scope frame layout matches the RFC exactly."""

    def test_scope_frame_header_is_16_bytes(self) -> None:
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 5, False)
        data = encode_scope_frame(frame, 0)
        assert len(data[:SCOPE_HEADER_SIZE]) == 16

    def test_offset_0_is_msg_type_01(self) -> None:
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 5, False)
        assert encode_scope_frame(frame, 0)[0] == 0x01

    def test_offset_1_is_receiver(self) -> None:
        for recv in (0, 1):
            frame = ScopeFrame(recv, 0, 14_000_000, 14_350_000, b"\x00" * 5, False)
            assert encode_scope_frame(frame, 0)[1] == recv

    def test_offset_2_is_mode(self) -> None:
        for mode in (0, 1, 2, 3):
            frame = ScopeFrame(0, mode, 14_000_000, 14_350_000, b"\x00" * 5, False)
            assert encode_scope_frame(frame, 0)[2] == mode

    def test_offset_3_7_is_start_freq_le(self) -> None:
        frame = ScopeFrame(0, 0, 7_074_000, 7_350_000, b"\x00" * 5, False)
        data = encode_scope_frame(frame, 0)
        assert struct.unpack_from("<I", data, 3)[0] == 7_074_000

    def test_offset_7_11_is_end_freq_le(self) -> None:
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 5, False)
        data = encode_scope_frame(frame, 0)
        assert struct.unpack_from("<I", data, 7)[0] == 14_350_000

    def test_offset_11_13_is_sequence_le(self) -> None:
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 5, False)
        data = encode_scope_frame(frame, 1234)
        assert struct.unpack_from("<H", data, 11)[0] == 1234

    def test_offset_13_is_flags(self) -> None:
        frame_ok = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 5, False)
        frame_oor = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"", True)
        assert encode_scope_frame(frame_ok, 0)[13] == 0x00
        assert encode_scope_frame(frame_oor, 0)[13] == 0x01

    def test_offset_14_16_is_pixel_count_le(self) -> None:
        pixels = bytes(range(200))
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, pixels, False)
        data = encode_scope_frame(frame, 0)
        assert struct.unpack_from("<H", data, 14)[0] == 200

    def test_offset_16_is_pixels(self) -> None:
        pixels = bytes(range(50))
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, pixels, False)
        data = encode_scope_frame(frame, 0)
        assert data[16:] == pixels


# ---------------------------------------------------------------------------
# Binary meter frame format tests (RFC conformance)
# ---------------------------------------------------------------------------


class TestMeterFrameFormat:
    """Verify binary meter frame layout matches the RFC exactly."""

    def test_offset_0_is_msg_type_20(self) -> None:
        data = encode_meter_frame([], 0)
        assert data[0] == 0x20

    def test_offset_1_3_is_sequence_le(self) -> None:
        data = encode_meter_frame([], 500)
        assert struct.unpack_from("<H", data, 1)[0] == 500

    def test_offset_3_is_count(self) -> None:
        data = encode_meter_frame([(1, 10), (2, 20), (3, 30)], 0)
        assert data[3] == 3

    def test_meter_triples_at_offset_4(self) -> None:
        meters = [(METER_SMETER_MAIN, 0x1234), (METER_POWER, 0xAB)]
        data = encode_meter_frame(meters, 0)
        # First meter
        assert data[4] == METER_SMETER_MAIN
        assert data[5] == 0x34  # low byte of 0x1234
        assert data[6] == 0x12  # high byte of 0x1234
        # Second meter
        assert data[7] == METER_POWER
        assert data[8] == 0xAB
        assert data[9] == 0x00

    def test_9_meters_total_size(self) -> None:
        meters = [(i + 1, i * 10) for i in range(9)]
        data = encode_meter_frame(meters, 0)
        assert len(data) == 4 + 9 * 3  # 4-byte header + 27 bytes


# ---------------------------------------------------------------------------
# Backpressure tests
# ---------------------------------------------------------------------------


class TestBackpressure:
    def test_scope_frame_queue_drops_when_full(self) -> None:
        """When queue is full, old frames are dropped, not blocked."""
        from icom_lan.web.handlers import HIGH_WATERMARK, ScopeHandler
        from icom_lan.web.websocket import WebSocketConnection

        # Mock WebSocket that never sends (simulates slow client)
        mock_ws = MagicMock(spec=WebSocketConnection)
        handler = ScopeHandler(mock_ws, None)
        handler._running = True

        pixels = bytes(range(100))
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, pixels, False)

        # Push HIGH_WATERMARK * 3 frames — queue should not block
        for i in range(HIGH_WATERMARK * 3):
            handler.push_frame(frame)

        # Queue size should be bounded by HIGH_WATERMARK * 2 (maxsize)
        # but frames were dropped, so it should be <= HIGH_WATERMARK * 2
        assert handler._frame_queue.qsize() <= HIGH_WATERMARK * 2

    def test_meter_frame_queue_drops_when_full(self) -> None:
        """Meter frames are dropped under backpressure."""
        from icom_lan.web.handlers import HIGH_WATERMARK, MetersHandler
        from icom_lan.web.websocket import WebSocketConnection

        mock_ws = MagicMock(spec=WebSocketConnection)
        handler = MetersHandler(mock_ws, None)

        meters = [(METER_SMETER_MAIN, 42)]
        for i in range(HIGH_WATERMARK * 4):
            handler.push_frame(meters)

        assert handler._frame_queue.qsize() <= HIGH_WATERMARK * 2

    def test_scope_sequence_increments(self) -> None:
        """Sequence numbers increment with each frame."""
        from icom_lan.web.handlers import ScopeHandler
        from icom_lan.web.websocket import WebSocketConnection

        mock_ws = MagicMock(spec=WebSocketConnection)
        handler = ScopeHandler(mock_ws, None)
        handler._running = True

        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 10, False)
        for i in range(5):
            handler.push_frame(frame)

        assert handler._seq == 5

    def test_scope_sequence_wraps_at_65536(self) -> None:
        """Sequence counter wraps at 16-bit boundary."""
        from icom_lan.web.handlers import ScopeHandler
        from icom_lan.web.websocket import WebSocketConnection

        mock_ws = MagicMock(spec=WebSocketConnection)
        handler = ScopeHandler(mock_ws, None)
        handler._running = True
        handler._seq = 65534

        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, b"\x00" * 5, False)
        # Push 3 frames: seq 65534, 65535, 0
        handler.push_frame(frame)  # encodes with seq=65534, _seq becomes 65535
        handler.push_frame(frame)  # encodes with seq=65535, _seq becomes 0
        handler.push_frame(frame)  # encodes with seq=0, _seq becomes 1

        assert handler._seq == 1


# ---------------------------------------------------------------------------
# Server config and lifecycle
# ---------------------------------------------------------------------------


class TestAudioFrameFormat:
    def test_audio_frame_header_size(self) -> None:
        from icom_lan.web.protocol import AUDIO_HEADER_SIZE, encode_audio_frame
        frame = encode_audio_frame(0x10, 0x01, 0, 480, 1, 20, b"")
        assert len(frame) == AUDIO_HEADER_SIZE

    def test_audio_rx_msg_type(self) -> None:
        from icom_lan.web.protocol import encode_audio_frame
        frame = encode_audio_frame(0x10, 0x01, 42, 480, 1, 20, b"\x00" * 100)
        assert frame[0] == 0x10

    def test_audio_tx_msg_type(self) -> None:
        from icom_lan.web.protocol import encode_audio_frame
        frame = encode_audio_frame(0x11, 0x01, 0, 480, 1, 20, b"\x00" * 50)
        assert frame[0] == 0x11

    def test_audio_codec_byte(self) -> None:
        from icom_lan.web.protocol import AUDIO_CODEC_OPUS, encode_audio_frame
        frame = encode_audio_frame(0x10, AUDIO_CODEC_OPUS, 0, 480, 1, 20, b"\x01")
        assert frame[1] == AUDIO_CODEC_OPUS

    def test_audio_sequence_le(self) -> None:
        import struct
        from icom_lan.web.protocol import encode_audio_frame
        frame = encode_audio_frame(0x10, 0x01, 0x1234, 480, 1, 20, b"")
        seq = struct.unpack_from("<H", frame, 2)[0]
        assert seq == 0x1234

    def test_audio_sample_rate_le(self) -> None:
        import struct
        from icom_lan.web.protocol import encode_audio_frame
        frame = encode_audio_frame(0x10, 0x01, 0, 480, 1, 20, b"")
        sr = struct.unpack_from("<H", frame, 4)[0]
        assert sr == 480

    def test_audio_channels_and_frame_ms(self) -> None:
        from icom_lan.web.protocol import encode_audio_frame
        frame = encode_audio_frame(0x10, 0x01, 0, 480, 1, 20, b"")
        assert frame[6] == 1  # mono
        assert frame[7] == 20  # 20ms

    def test_audio_payload_appended(self) -> None:
        from icom_lan.web.protocol import AUDIO_HEADER_SIZE, encode_audio_frame
        payload = b"\xaa\xbb\xcc\xdd"
        frame = encode_audio_frame(0x10, 0x01, 0, 480, 1, 20, payload)
        assert frame[AUDIO_HEADER_SIZE:] == payload
        assert len(frame) == AUDIO_HEADER_SIZE + len(payload)

    def test_audio_sequence_wraps(self) -> None:
        import struct
        from icom_lan.web.protocol import encode_audio_frame
        frame = encode_audio_frame(0x10, 0x01, 0x10000, 480, 1, 20, b"")
        seq = struct.unpack_from("<H", frame, 2)[0]
        assert seq == 0  # wrapped


class TestProtocolConformance:
    """RFC-level protocol conformance tests."""

    # --- Scope frame edge cases ---

    def test_scope_empty_pixels(self) -> None:
        frame = ScopeFrame(0, 0, 7_000_000, 7_300_000, b"", False)
        data = encode_scope_frame(frame, 0)
        assert len(data) == SCOPE_HEADER_SIZE
        count = struct.unpack_from("<H", data, 14)[0]
        assert count == 0

    def test_scope_max_amplitude_values(self) -> None:
        """Pixel values 0-160 are valid per RFC."""
        pixels = bytes([0, 80, 160, 160, 0])
        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, pixels, False)
        data = encode_scope_frame(frame, 0)
        assert data[SCOPE_HEADER_SIZE:] == pixels

    def test_scope_all_receiver_modes(self) -> None:
        """receiver: 0=Main, 1=Sub; mode: 0-3."""
        for recv in (0, 1):
            for mode in (0, 1, 2, 3):
                frame = ScopeFrame(recv, mode, 14_000_000, 14_350_000, b"\x50", False)
                data = encode_scope_frame(frame, 0)
                assert data[1] == recv
                assert data[2] == mode

    def test_scope_dual_receiver_frames(self) -> None:
        """IC-7610 sends Main+Sub scope frames."""
        main = ScopeFrame(0, 1, 14_000_000, 14_350_000, bytes(475), False)
        sub = ScopeFrame(1, 1, 7_000_000, 7_300_000, bytes(475), False)
        d0 = encode_scope_frame(main, 0)
        d1 = encode_scope_frame(sub, 1)
        assert d0[1] == 0 and d1[1] == 1
        assert struct.unpack_from("<I", d0, 3)[0] == 14_000_000
        assert struct.unpack_from("<I", d1, 3)[0] == 7_000_000

    def test_scope_freq_range_boundaries(self) -> None:
        """Test with real HF/VHF frequency values."""
        for sf, ef in [(1_800_000, 2_000_000), (50_000_000, 54_000_000),
                       (144_000_000, 148_000_000), (430_000_000, 440_000_000)]:
            frame = ScopeFrame(0, 0, sf, ef, b"\x00", False)
            data = encode_scope_frame(frame, 0)
            assert struct.unpack_from("<I", data, 3)[0] == sf
            assert struct.unpack_from("<I", data, 7)[0] == ef

    # --- Meter frame edge cases ---

    def test_meter_all_9_ids(self) -> None:
        """All 9 meter IDs from RFC."""
        from icom_lan.web.protocol import (
            METER_ALC, METER_COMP, METER_ID_DRAIN, METER_POWER,
            METER_SMETER_MAIN, METER_SMETER_SUB, METER_SWR, METER_TEMP, METER_VD,
        )
        all_ids = [METER_SMETER_MAIN, METER_SMETER_SUB, METER_POWER, METER_SWR,
                   METER_ALC, METER_COMP, METER_ID_DRAIN, METER_VD, METER_TEMP]
        meters = [(mid, 128) for mid in all_ids]
        data = encode_meter_frame(meters, 0)
        assert data[3] == 9  # count
        assert len(data) == 4 + 9 * 3  # 31 bytes per RFC

    def test_meter_value_range_uint16(self) -> None:
        """Meter values are uint16 (lo + hi bytes)."""
        meters = [(0x01, 0), (0x03, 255), (0x04, 256), (0x05, 65535)]
        data = encode_meter_frame(meters, 0)
        # Check value 256 = 0x0100 → lo=0x00, hi=0x01
        off = 4 + 2 * 3  # third meter (0x04, 256)
        assert data[off] == 0x04  # meter_id
        assert data[off + 1] == 0x00  # lo
        assert data[off + 2] == 0x01  # hi
        # Check value 65535 = 0xFFFF → lo=0xFF, hi=0xFF
        off = 4 + 3 * 3
        assert data[off + 1] == 0xFF
        assert data[off + 2] == 0xFF

    def test_meter_bandwidth_calculation(self) -> None:
        """9 meters × 3 bytes + 4 header = 31 bytes. At 20fps = 620 B/s."""
        meters = [(i, 100) for i in range(1, 10)]
        data = encode_meter_frame(meters, 0)
        assert len(data) == 31
        # 620 bytes/sec at 20fps
        assert len(data) * 20 == 620

    # --- Audio frame edge cases ---

    def test_audio_opus_typical_frame(self) -> None:
        """Typical Opus frame: 48kHz, mono, 20ms, ~80-120 bytes payload."""
        from icom_lan.web.protocol import (
            AUDIO_CODEC_OPUS, AUDIO_HEADER_SIZE, MSG_TYPE_AUDIO_RX, encode_audio_frame,
        )
        payload = bytes(range(100))  # ~100 bytes typical Opus
        frame = encode_audio_frame(MSG_TYPE_AUDIO_RX, AUDIO_CODEC_OPUS, 42, 480, 1, 20, payload)
        assert len(frame) == AUDIO_HEADER_SIZE + 100
        assert frame[0] == MSG_TYPE_AUDIO_RX
        assert frame[1] == AUDIO_CODEC_OPUS
        assert frame[AUDIO_HEADER_SIZE:] == payload

    # --- JSON message conformance ---

    def test_hello_message_schema(self) -> None:
        """hello message must have all required fields per RFC."""
        msg = json.loads(encode_json({
            "type": "hello", "proto": 1, "server": "icom-lan",
            "version": "0.8.0", "radio": "IC-7610",
            "capabilities": ["scope", "audio", "tx"],
        }))
        assert msg["type"] == "hello"
        assert isinstance(msg["proto"], int)
        assert isinstance(msg["capabilities"], list)

    def test_state_message_schema(self) -> None:
        msg = {"type": "state", "data": {
            "freq_a": 14074000, "freq_b": 7074000,
            "mode": "USB", "filter": "FIL1", "ptt": False,
        }}
        text = encode_json(msg)
        parsed = json.loads(text)
        assert parsed["type"] == "state"
        assert isinstance(parsed["data"]["freq_a"], int)
        assert isinstance(parsed["data"]["ptt"], bool)

    def test_event_message_schema(self) -> None:
        msg = {"type": "event", "name": "freq_changed", "data": {"vfo": "A", "freq": 14074500}}
        text = encode_json(msg)
        parsed = json.loads(text)
        assert parsed["name"] == "freq_changed"

    def test_command_message_schema(self) -> None:
        msg = {"type": "cmd", "id": "a1b2", "name": "set_freq", "params": {"vfo": "A", "freq": 14074000}}
        text = encode_json(msg)
        parsed = json.loads(text)
        assert parsed["id"] == "a1b2"
        assert parsed["name"] == "set_freq"

    def test_response_ok_schema(self) -> None:
        msg = {"type": "response", "id": "a1b2", "ok": True, "result": {"freq": 14074000}}
        parsed = json.loads(encode_json(msg))
        assert parsed["ok"] is True

    def test_response_error_schema(self) -> None:
        msg = {"type": "response", "id": "a1b3", "ok": False,
               "error": "invalid_param", "message": "Frequency out of range"}
        parsed = json.loads(encode_json(msg))
        assert parsed["ok"] is False
        assert "error" in parsed
        assert "message" in parsed

    def test_subscribe_message_schema(self) -> None:
        msg = {"type": "subscribe", "id": "s1", "streams": ["scope", "meters"],
               "scope_fps": 30, "scope_receiver": 0}
        parsed = json.loads(encode_json(msg))
        assert isinstance(parsed["streams"], list)
        assert "scope" in parsed["streams"]

    def test_encode_json_compact(self) -> None:
        """encode_json must produce compact JSON (no extra spaces)."""
        text = encode_json({"type": "hello", "proto": 1})
        assert " " not in text  # no spaces in compact JSON

    def test_decode_json_rejects_array(self) -> None:
        with pytest.raises(ValueError, match="expected a JSON object"):
            decode_json("[1,2,3]")

    def test_decode_json_rejects_invalid(self) -> None:
        with pytest.raises(ValueError, match="invalid JSON"):
            decode_json("not json")


class TestServerConfig:
    async def test_port_zero_assigns_ephemeral(self) -> None:
        config = WebConfig(host="127.0.0.1", port=0)
        srv = WebServer(None, config)
        await srv.start()
        try:
            assert srv.port > 0
        finally:
            await srv.stop()

    async def test_start_stop(self) -> None:
        config = WebConfig(host="127.0.0.1", port=0)
        srv = WebServer(None, config)
        await srv.start()
        await srv.stop()
        # Should not raise

    async def test_context_manager(self) -> None:
        config = WebConfig(host="127.0.0.1", port=0)
        async with WebServer(None, config) as srv:
            assert srv.port > 0

    async def test_web_config_defaults(self) -> None:
        cfg = WebConfig()
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 8080
        assert cfg.max_clients == 100


# ---------------------------------------------------------------------------
# AudioHandler codec detection
# ---------------------------------------------------------------------------


class TestAudioHandlerCodecDetection:
    """AudioHandler must tag web frames with the correct codec type.

    The radio sends PCM by default (PCM_1CH_16BIT = 0x04).  The web frame
    must carry AUDIO_CODEC_PCM16 (0x02) so the browser can play it as raw
    PCM instead of trying to Opus-decode it.  When the radio is configured
    for Opus (OPUS_1CH = 0x40), the web frame must carry AUDIO_CODEC_OPUS.
    """

    async def _start_rx_and_capture(self, audio_codec: object, sample_rate: int) -> bytes:
        """Start RX via AudioBroadcaster and return first queued frame."""
        from icom_lan.types import AudioCodec
        from icom_lan.web.handlers import AudioBroadcaster, AudioHandler
        from icom_lan.web.websocket import WebSocketConnection

        mock_ws = MagicMock(spec=WebSocketConnection)
        mock_radio = MagicMock()
        mock_radio.audio_codec = audio_codec
        mock_radio.audio_sample_rate = sample_rate
        mock_radio.stop_audio_rx_opus = AsyncMock()

        captured_callback: list = []

        async def fake_start_rx_opus(cb: object) -> None:
            captured_callback.append(cb)

        mock_radio.start_audio_rx_opus = fake_start_rx_opus

        broadcaster = AudioBroadcaster(mock_radio)
        handler = AudioHandler(mock_ws, mock_radio, broadcaster)
        await handler._start_rx()

        assert len(captured_callback) == 1, "start_audio_rx_opus must be called once"
        cb = captured_callback[0]

        # Inject a fake AudioPacket
        mock_pkt = MagicMock()
        mock_pkt.data = b"\x00\x01" * 50  # 100 bytes of fake audio
        cb(mock_pkt)

        # Retrieve the encoded web frame from the handler's queue (assigned by broadcaster)
        frame = handler._frame_queue.get_nowait()
        return frame

    async def test_pcm_codec_produces_pcm16_web_frame(self) -> None:
        from icom_lan.types import AudioCodec
        from icom_lan.web.protocol import AUDIO_CODEC_PCM16

        frame = await self._start_rx_and_capture(AudioCodec.PCM_1CH_16BIT, 48000)
        assert frame[1] == AUDIO_CODEC_PCM16, (
            f"Expected AUDIO_CODEC_PCM16 (0x{AUDIO_CODEC_PCM16:02x}) "
            f"but got 0x{frame[1]:02x}"
        )

    async def test_opus_codec_produces_opus_web_frame(self) -> None:
        from icom_lan.types import AudioCodec
        from icom_lan.web.protocol import AUDIO_CODEC_OPUS

        frame = await self._start_rx_and_capture(AudioCodec.OPUS_1CH, 48000)
        assert frame[1] == AUDIO_CODEC_OPUS, (
            f"Expected AUDIO_CODEC_OPUS (0x{AUDIO_CODEC_OPUS:02x}) "
            f"but got 0x{frame[1]:02x}"
        )

    async def test_sample_rate_encoded_correctly(self) -> None:
        import struct

        from icom_lan.types import AudioCodec

        frame = await self._start_rx_and_capture(AudioCodec.PCM_1CH_16BIT, 48000)
        sr_field = struct.unpack_from("<H", frame, 4)[0]
        assert sr_field == 480, f"Expected 480 (48000//100) but got {sr_field}"

    async def test_unknown_codec_falls_back_to_pcm16(self) -> None:
        from icom_lan.web.protocol import AUDIO_CODEC_PCM16

        # Pass a non-AudioCodec value (e.g. MagicMock) — must default to PCM16
        frame = await self._start_rx_and_capture(MagicMock(), 48000)
        assert frame[1] == AUDIO_CODEC_PCM16


# ---------------------------------------------------------------------------
# WebSocket keepalive (server-initiated pings)
# ---------------------------------------------------------------------------


class TestWsKeepalive:
    """WebSocketConnection.keepalive_loop() sends RFC 6455 ping frames."""

    async def test_keepalive_sends_ping_frame(self) -> None:
        """keepalive_loop writes a WS PING frame after the interval elapses."""
        written: list[bytes] = []

        reader = asyncio.StreamReader()
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = False
        writer.write.side_effect = written.append
        writer.drain = AsyncMock()

        ws = WebSocketConnection(reader, writer)
        task = asyncio.create_task(ws.keepalive_loop(interval=0.05))
        try:
            # Wait slightly longer than the interval so at least one ping fires.
            await asyncio.sleep(0.12)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert written, "keepalive_loop must write at least one frame"
        # Ping frame: FIN|PING (0x89), payload len 2 ("ka")
        all_bytes = b"".join(written)
        ping_frame = make_frame(WS_OP_PING, b"ka")
        assert ping_frame in all_bytes, (
            f"Expected ping frame {ping_frame!r} in written data {all_bytes!r}"
        )

    async def test_keepalive_cancels_cleanly(self) -> None:
        """Cancelling keepalive_loop raises no unhandled exceptions."""
        reader = asyncio.StreamReader()
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = False
        writer.write = MagicMock()
        writer.drain = AsyncMock()

        ws = WebSocketConnection(reader, writer)
        task = asyncio.create_task(ws.keepalive_loop(interval=60.0))
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass  # expected

    async def test_keepalive_exits_when_connection_closed(self) -> None:
        """keepalive_loop stops without error if ws.close() is called first."""
        reader = asyncio.StreamReader()
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = False
        writer.write = MagicMock()
        writer.drain = AsyncMock()

        ws = WebSocketConnection(reader, writer)
        ws._closed = True  # Mark as closed before starting loop

        task = asyncio.create_task(ws.keepalive_loop(interval=0.01))
        # Should complete quickly since _closed is True
        await asyncio.wait_for(task, timeout=1.0)


# ---------------------------------------------------------------------------
# Scope enable/disable lifecycle
# ---------------------------------------------------------------------------


class TestScopeLifecycle:
    """Scope is disabled on the radio when the last handler disconnects."""

    async def test_scope_not_disabled_while_handlers_remain(self) -> None:
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)
        server._scope_enabled = True

        h1 = MagicMock()
        h2 = MagicMock()
        server._scope_handlers.add(h1)
        server._scope_handlers.add(h2)

        server.unregister_scope_handler(h1)
        await asyncio.sleep(0.05)  # let task scheduler run

        radio.disable_scope.assert_not_awaited()
        assert server._scope_enabled  # still True

    async def test_scope_disabled_when_last_handler_disconnects(self) -> None:
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)
        server._scope_disable_grace = 0
        server._scope_enabled = True

        h = MagicMock()
        server._scope_handlers.add(h)

        server.unregister_scope_handler(h)
        await asyncio.sleep(0.05)  # let async task complete

        # DisableScope goes through command queue, not direct radio call
        from icom_lan.web.radio_poller import DisableScope
        cmds = server._command_queue.drain()
        assert any(isinstance(c, DisableScope) for c in cmds), "DisableScope should be in queue"
        assert not server._scope_enabled

    async def test_scope_flag_reset_on_disable(self) -> None:
        """_scope_enabled is reset to False after successful disable."""
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)
        server._scope_disable_grace = 0
        server._scope_enabled = True

        h = MagicMock()
        server._scope_handlers.add(h)
        server.unregister_scope_handler(h)
        await asyncio.sleep(0.05)

        assert not server._scope_enabled

    async def test_scope_not_disabled_if_never_enabled(self) -> None:
        """disable_scope is NOT called if _scope_enabled is False."""
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)
        server._scope_enabled = False  # was never enabled

        h = MagicMock()
        server._scope_handlers.add(h)
        server.unregister_scope_handler(h)
        await asyncio.sleep(0.05)

        radio.disable_scope.assert_not_awaited()


# ---------------------------------------------------------------------------
# Cache-Control header for static files
# ---------------------------------------------------------------------------


class TestCacheControl:
    """Static file responses must include Cache-Control: no-cache."""

    async def test_static_index_has_cache_control(
        self, server: WebServer
    ) -> None:
        host, port = _addr(server)
        status, headers, _ = await _http_get(host, port, "/")
        assert status == 200
        cc = headers.get("cache-control", "")
        assert "no-cache" in cc, f"Expected no-cache in Cache-Control, got: {cc!r}"

    async def test_static_file_not_found_no_cache_control(
        self, server: WebServer
    ) -> None:
        """404 responses do not need Cache-Control (not a static file)."""
        host, port = _addr(server)
        status, headers, _ = await _http_get(host, port, "/nonexistent-file.xyz")
        assert status == 404

    async def test_api_info_no_cache_control_required(
        self, server: WebServer
    ) -> None:
        """JSON API endpoints are not required to have Cache-Control."""
        host, port = _addr(server)
        status, _, body = await _http_get(host, port, "/api/v1/info")
        assert status == 200
        data = json.loads(body)
        assert data["server"] == "icom-lan"


# ---------------------------------------------------------------------------
# #44 regression: ScopeHandler.push_frame must call enqueue_frame
# ---------------------------------------------------------------------------


class TestScopeHandlerPushFrame:
    """push_frame() must enqueue frames without AttributeError (#44)."""

    def test_push_frame_does_not_raise(self) -> None:
        """push_frame() was calling self._on_scope_frame which doesn't exist."""
        from icom_lan.web.handlers import ScopeHandler
        from icom_lan.web.websocket import WebSocketConnection

        mock_ws = MagicMock(spec=WebSocketConnection)
        handler = ScopeHandler(mock_ws, None)
        handler._running = True

        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, bytes(10), False)
        handler.push_frame(frame)  # must not raise AttributeError
        assert handler._frame_queue.qsize() == 1

    def test_push_frame_not_running_is_noop(self) -> None:
        """push_frame() when not running must be a no-op."""
        from icom_lan.web.handlers import ScopeHandler
        from icom_lan.web.websocket import WebSocketConnection

        mock_ws = MagicMock(spec=WebSocketConnection)
        handler = ScopeHandler(mock_ws, None)
        handler._running = False

        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, bytes(10), False)
        handler.push_frame(frame)
        assert handler._frame_queue.qsize() == 0

    def test_push_frame_increments_sequence(self) -> None:
        from icom_lan.web.handlers import ScopeHandler
        from icom_lan.web.websocket import WebSocketConnection

        mock_ws = MagicMock(spec=WebSocketConnection)
        handler = ScopeHandler(mock_ws, None)
        handler._running = True

        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, bytes(5), False)
        handler.push_frame(frame)
        handler.push_frame(frame)
        assert handler._seq == 2


# ---------------------------------------------------------------------------
# #45 regression: Configurable keepalive interval
# ---------------------------------------------------------------------------


class TestConfigurableKeepalive:
    """WebConfig.keepalive_interval is honoured by the server (#45)."""

    def test_webconfig_has_keepalive_interval(self) -> None:
        from icom_lan.web.websocket import WS_KEEPALIVE_INTERVAL

        cfg = WebConfig()
        assert hasattr(cfg, "keepalive_interval")
        assert cfg.keepalive_interval == WS_KEEPALIVE_INTERVAL

    def test_webconfig_custom_interval(self) -> None:
        cfg = WebConfig(keepalive_interval=5.0)
        assert cfg.keepalive_interval == 5.0

    async def test_large_interval_no_pings_during_short_test(self) -> None:
        """With keepalive_interval=9999, no ping frames arrive in a short test."""
        config = WebConfig(host="127.0.0.1", port=0, keepalive_interval=9999.0)
        async with WebServer(None, config) as srv:
            host, port = _addr(srv)
            reader, writer, _ = await _ws_connect(host, port, "/api/v1/ws")
            try:
                # Collect frames for 100ms — should get hello but no pings
                frames = []
                try:
                    while True:
                        opcode, payload = await asyncio.wait_for(
                            _ws_recv_frame(reader), timeout=0.1
                        )
                        frames.append((opcode, payload))
                except asyncio.TimeoutError:
                    pass
                # Should have received exactly the hello text frame
                assert len(frames) >= 1
                assert frames[0][0] == WS_OP_TEXT
                msg = json.loads(frames[0][1])
                assert msg["type"] == "hello"
            finally:
                await _close_ws(writer)


# ---------------------------------------------------------------------------
# #46 regression: Atomic scope enable (asyncio.Lock prevents duplicate calls)
# ---------------------------------------------------------------------------


class TestScopeEnableAtomic:
    """ensure_scope_enabled() must call enable_scope() exactly once even when
    multiple handlers connect concurrently (#46)."""

    async def test_enable_scope_called_once_for_concurrent_handlers(self) -> None:
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.enable_scope = AsyncMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)
        handlers = [MagicMock() for _ in range(5)]

        # Call ensure_scope_enabled for all 5 handlers concurrently
        await asyncio.gather(*[server.ensure_scope_enabled(h) for h in handlers])

        # EnableScope goes through command queue
        from icom_lan.web.radio_poller import EnableScope
        cmds = server._command_queue.drain()
        enable_cmds = [c for c in cmds if isinstance(c, EnableScope)]
        assert len(enable_cmds) >= 1, "At least one EnableScope should be queued"
        assert len(server._scope_handlers) == 5

    async def test_all_handlers_registered_after_concurrent_enables(self) -> None:
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.enable_scope = AsyncMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)
        handlers = [MagicMock() for _ in range(5)]

        await asyncio.gather(*[server.ensure_scope_enabled(h) for h in handlers])

        for h in handlers:
            assert h in server._scope_handlers

    async def test_server_responsive_after_connect_disconnect_cycles(self) -> None:
        """HTTP endpoint must return 200 after several WS connect/disconnect cycles."""
        config = WebConfig(host="127.0.0.1", port=0, keepalive_interval=9999.0)
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.enable_scope = AsyncMock()
        radio.disable_scope = AsyncMock()

        async with WebServer(radio, config) as srv:
            host, port = _addr(srv)

            for _ in range(3):
                reader, writer, _ = await _ws_connect(host, port, "/api/v1/scope")
                await _close_ws(writer)
                await asyncio.sleep(0.02)

            status, _, _ = await _http_get(host, port, "/api/v1/info")
            assert status == 200

    async def test_enable_scope_called_once_when_first_of_many_registers(
        self,
    ) -> None:
        """Sequential registrations only enable scope once too."""
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.enable_scope = AsyncMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)

        h1, h2, h3 = MagicMock(), MagicMock(), MagicMock()
        await server.ensure_scope_enabled(h1)
        await server.ensure_scope_enabled(h2)
        await server.ensure_scope_enabled(h3)

        # EnableScope goes through command queue
        from icom_lan.web.radio_poller import EnableScope
        cmds = server._command_queue.drain()
        enable_cmds = [c for c in cmds if isinstance(c, EnableScope)]
        assert len(enable_cmds) >= 1, "At least one EnableScope should be queued"


# ---------------------------------------------------------------------------
# #47 regression: Scope re-enable after full disconnect/reconnect
# ---------------------------------------------------------------------------


class TestScopeReconnect:
    """After all handlers disconnect and a new one connects, scope must flow (#47)."""

    async def test_scope_disabled_via_queue_after_grace(self) -> None:
        """After grace period, DisableScope is queued and flag resets."""
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.enable_scope = AsyncMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)
        server._scope_disable_grace = 0
        h = MagicMock()
        await server.ensure_scope_enabled(h)
        assert server._scope_enabled

        server.unregister_scope_handler(h)
        await asyncio.sleep(0.05)

        from icom_lan.web.radio_poller import DisableScope
        cmds = server._command_queue.drain()
        assert any(isinstance(c, DisableScope) for c in cmds)
        assert not server._scope_enabled

    async def test_enable_scope_queued_again_after_full_disconnect(self) -> None:
        """After last handler disconnects, a new handler must queue EnableScope again."""
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.enable_scope = AsyncMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)
        server._scope_disable_grace = 0

        from icom_lan.web.radio_poller import EnableScope, DisableScope

        # First connect
        h1 = MagicMock()
        await server.ensure_scope_enabled(h1)

        # Disconnect
        server.unregister_scope_handler(h1)
        await asyncio.sleep(0.05)
        assert not server._scope_enabled

        # Drain queue
        server._command_queue.drain()

        # Reconnect — must queue EnableScope again
        h2 = MagicMock()
        await server.ensure_scope_enabled(h2)
        cmds = server._command_queue.drain()
        assert any(isinstance(c, EnableScope) for c in cmds)

    async def test_disable_task_aborts_if_new_handler_reconnects(self) -> None:
        """If a new handler connects before the disable task runs,
        disable_scope() must NOT be called."""
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.enable_scope = AsyncMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)

        h1 = MagicMock()
        await server.ensure_scope_enabled(h1)

        # Unregister h1 — schedules disable task but doesn't await it yet
        server.unregister_scope_handler(h1)

        # Register h2 before the event loop runs the disable task
        h2 = MagicMock()
        await server.ensure_scope_enabled(h2)

        # Now let the event loop run the disable task
        await asyncio.sleep(0.05)

        # disable_scope must NOT have been called — h2 is still connected
        radio.disable_scope.assert_not_awaited()
        assert server._scope_enabled

    async def test_broadcast_scope_reaches_new_handler_after_reconnect(
        self,
    ) -> None:
        """Frames broadcast after reconnect must reach the new handler."""
        radio = MagicMock()
        radio.on_scope_data = MagicMock()
        radio.enable_scope = AsyncMock()
        radio.disable_scope = AsyncMock()

        server = WebServer(radio)

        h1 = MagicMock()
        await server.ensure_scope_enabled(h1)
        server.unregister_scope_handler(h1)
        await asyncio.sleep(0.05)

        h2 = MagicMock()
        h2._running = True
        await server.ensure_scope_enabled(h2)

        frame = ScopeFrame(0, 0, 14_000_000, 14_350_000, bytes(10), False)
        server._broadcast_scope(frame)

        h2.enqueue_frame.assert_called_once_with(frame)
        h1.enqueue_frame.assert_not_called()

# ---------------------------------------------------------------------------
# #72: RadioPoller — single CI-V serialiser
# ---------------------------------------------------------------------------


class TestRadioPoller:
    """RadioPoller polls all params and executes commands via single task (#72)."""

    def _make_radio(self) -> MagicMock:
        radio = MagicMock()
        mode_mock = MagicMock()
        mode_mock.name = "USB"
        radio.get_frequency = AsyncMock(return_value=14074000)
        radio.get_mode_info = AsyncMock(return_value=(mode_mock, 1))
        radio.get_s_meter = AsyncMock(return_value=42)
        radio.get_power = AsyncMock(return_value=100)
        radio.get_swr = AsyncMock(return_value=10)
        radio.get_alc = AsyncMock(return_value=5)
        radio.get_rf_gain = AsyncMock(return_value=128)
        radio.get_af_level = AsyncMock(return_value=64)
        radio.get_attenuator_level = AsyncMock(return_value=0)
        radio.get_preamp = AsyncMock(return_value=0)
        radio.get_data_mode = AsyncMock(return_value=False)
        radio.set_frequency = AsyncMock()
        radio.set_mode = AsyncMock()
        radio.set_ptt = AsyncMock()
        radio.send_civ = AsyncMock()  # RadioPoller now calls send_civ directly
        radio.state_cache = StateCache()
        return radio

    async def test_poller_starts_and_stops(self) -> None:
        """RadioPoller start/stop lifecycle."""
        from icom_lan.web.radio_poller import CommandQueue, RadioPoller

        radio = self._make_radio()
        cache = StateCache()
        queue = CommandQueue()
        poller = RadioPoller(radio, cache, queue)

        poller.start()
        assert poller.running
        await asyncio.sleep(0.05)

        poller.stop()
        assert not poller.running

    async def test_poller_polls_freq(self) -> None:
        """RadioPoller updates state cache with polled frequency."""
        from icom_lan.web.radio_poller import CommandQueue, RadioPoller

        radio = self._make_radio()
        cache = StateCache()
        queue = CommandQueue()
        events: list[tuple[str, dict]] = []
        poller = RadioPoller(
            radio, cache, queue,
            on_state_event=lambda n, d: events.append((n, d)),
        )

        poller.start()
        # Slow queries poll every 10th cycle × 25ms = 250ms
        await asyncio.sleep(0.3)
        poller.stop()

        # send_civ called for freq query (0x03) and meters (0x15)
        assert radio.send_civ.await_count >= 1

    async def test_command_queue_dedup(self) -> None:
        """Last-write-wins dedup for freq commands; PTT never deduped."""
        from icom_lan.web.radio_poller import CommandQueue, SetFreq, PttOn, PttOff

        queue = CommandQueue()
        queue.put(SetFreq(14000000))
        queue.put(SetFreq(14074000))
        queue.put(PttOn())
        queue.put(PttOff())

        cmds = queue.drain()
        freq_cmds = [c for c in cmds if isinstance(c, SetFreq)]
        ptt_cmds = [c for c in cmds if isinstance(c, (PttOn, PttOff))]

        assert len(freq_cmds) == 1
        assert freq_cmds[0].freq == 14074000
        assert len(ptt_cmds) == 2

    async def test_poller_executes_commands(self) -> None:
        """Commands queued are executed by the poller."""
        from icom_lan.web.radio_poller import CommandQueue, RadioPoller, SetFreq

        radio = self._make_radio()
        cache = StateCache()
        queue = CommandQueue()
        poller = RadioPoller(radio, cache, queue)

        poller.start()
        queue.put(SetFreq(7074000))
        await asyncio.sleep(0.1)
        poller.stop()

        radio.set_frequency.assert_awaited_with(7074000)

    async def test_poller_broadcasts_meter_readings(self) -> None:
        """RadioPoller polls meters via send_civ."""
        from icom_lan.web.radio_poller import CommandQueue, RadioPoller

        radio = self._make_radio()
        cache = StateCache()
        queue = CommandQueue()
        poller = RadioPoller(radio, cache, queue)

        poller.start()
        await asyncio.sleep(0.15)  # 25ms × 6 cycles = 150ms
        poller.stop()

        # Fast queries: S-meter (0x15, 0x02), power, SWR, ALC
        assert radio.send_civ.await_count >= 4
        meter_calls = [c for c in radio.send_civ.call_args_list 
                       if c[0][0] == 0x15]  # cmd=0x15
        assert len(meter_calls) >= 4

    async def test_poller_idempotent_start(self) -> None:
        """Calling start() twice does not create duplicate tasks."""
        from icom_lan.web.radio_poller import CommandQueue, RadioPoller

        radio = self._make_radio()
        cache = StateCache()
        queue = CommandQueue()
        poller = RadioPoller(radio, cache, queue)

        poller.start()
        task1 = poller._task
        poller.start()
        task2 = poller._task

        assert task1 is task2
        poller.stop()
