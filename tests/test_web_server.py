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
    WS_OP_TEXT,
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

    # Read upgrade response
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = await asyncio.wait_for(reader.read(4096), timeout=5.0)
        if not chunk:
            break
        resp += chunk

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
) -> tuple[int, bytes]:
    """Read one (unmasked) server→client WebSocket frame."""
    header = await asyncio.wait_for(reader.readexactly(2), timeout=5.0)
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
    radio.get_frequency = AsyncMock(return_value=14_074_000)
    radio.get_mode = AsyncMock(return_value=MagicMock(name="USB"))
    radio.get_mode.return_value.name = "USB"
    radio.get_power = AsyncMock(return_value=100)
    radio.get_s_meter = AsyncMock(return_value=42)
    radio.get_swr = AsyncMock(return_value=10)
    radio.get_alc = AsyncMock(return_value=5)
    radio.set_frequency = AsyncMock()
    radio.set_mode = AsyncMock()
    radio.set_power = AsyncMock()
    radio.set_ptt = AsyncMock()
    radio.set_attenuator_level = AsyncMock()
    radio.set_preamp = AsyncMock()
    radio.vfo_swap = AsyncMock()
    radio.vfo_a_equals_b = AsyncMock()
    # on_scope_data is a synchronous setter
    radio.on_scope_data = MagicMock()
    return radio


@pytest.fixture
async def server(mock_radio: MagicMock) -> WebServer:
    config = WebConfig(host="127.0.0.1", port=0)
    srv = WebServer(mock_radio, config)
    await srv.start()
    yield srv
    await srv.stop()


@pytest.fixture
async def server_no_radio() -> WebServer:
    config = WebConfig(host="127.0.0.1", port=0)
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
            mock_radio.set_frequency.assert_awaited_once_with(14_074_000)
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
            mock_radio.vfo_swap.assert_awaited_once()
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
        assert cfg.max_clients == 20
