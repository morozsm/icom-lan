"""Smoke coverage for web/rigctld consumers with serial mock backend."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import struct

import pytest

from icom_lan.backends.icom7610.drivers.serial_stub import SerialMockRadio
from icom_lan.rigctld.contract import RigctldConfig
from icom_lan.rigctld.server import RigctldServer
from icom_lan.web.server import WebConfig, WebServer


_WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _addr_from_asyncio_server(server: asyncio.Server) -> tuple[str, int]:
    return server.sockets[0].getsockname()


async def _http_get(
    host: str, port: int, path: str
) -> tuple[int, dict[str, str], bytes]:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        req = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
        writer.write(req.encode("ascii"))
        await writer.drain()
        raw = await asyncio.wait_for(reader.read(65536), timeout=2.0)
    finally:
        writer.close()
        await writer.wait_closed()
    header_end = raw.find(b"\r\n\r\n")
    header_bytes = raw[:header_end].decode("ascii", errors="replace").split("\r\n")
    status = int(header_bytes[0].split(" ", 2)[1])
    headers: dict[str, str] = {}
    for line in header_bytes[1:]:
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    return status, headers, raw[header_end + 4 :]


async def _ws_connect(
    host: str, port: int, path: str
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    reader, writer = await asyncio.open_connection(host, port)
    key = "dGhlIHNhbXBsZSBub25jZQ=="
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    writer.write(req.encode("ascii"))
    await writer.drain()
    resp = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=2.0)
    accept = base64.b64encode(
        hashlib.sha1((key + _WS_MAGIC).encode("ascii")).digest()
    ).decode("ascii")
    assert b"101" in resp
    assert accept.encode("ascii") in resp
    return reader, writer


async def _ws_send_text(writer: asyncio.StreamWriter, text: str) -> None:
    payload = text.encode("utf-8")
    mask = b"\x11\x22\x33\x44"
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    header = bytes([0x81, 0x80 | len(payload)]) + mask
    writer.write(header + masked)
    await writer.drain()


async def _ws_recv_frame(
    reader: asyncio.StreamReader,
) -> tuple[int, bytes]:
    header = await asyncio.wait_for(reader.readexactly(2), timeout=2.0)
    op = header[0] & 0x0F
    payload_len = header[1] & 0x7F
    if payload_len == 126:
        payload_len = struct.unpack("!H", await reader.readexactly(2))[0]
    elif payload_len == 127:
        payload_len = struct.unpack("!Q", await reader.readexactly(8))[0]
    payload = await reader.readexactly(payload_len)
    return op, payload


async def _close_writer(writer: asyncio.StreamWriter) -> None:
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_web_server_smoke_with_serial_mock_backend() -> None:
    radio = SerialMockRadio()
    server = WebServer(
        radio,
        WebConfig(host="127.0.0.1", port=0, keepalive_interval=9999.0),
    )
    await server.start()
    try:
        assert server._server is not None
        host, port = _addr_from_asyncio_server(server._server)

        status, _, body = await _http_get(host, port, "/api/v1/state")
        assert status == 200
        state = json.loads(body.decode("utf-8"))
        assert state["connected"] is False

        reader, writer = await _ws_connect(host, port, "/api/v1/ws")
        try:
            _op, payload = await _ws_recv_frame(reader)
            hello = json.loads(payload.decode("utf-8"))
            assert hello["type"] == "hello"
            assert hello["connected"] is False

            await _ws_send_text(
                writer,
                json.dumps({"type": "radio_connect", "id": "connect-1"}),
            )
            _op, payload = await _ws_recv_frame(reader)
            connect_resp = json.loads(payload.decode("utf-8"))
            assert connect_resp["type"] == "response"
            assert connect_resp["id"] == "connect-1"
            assert connect_resp["ok"] is True
        finally:
            await _close_writer(writer)
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_rigctld_smoke_with_serial_mock_backend() -> None:
    radio = SerialMockRadio()
    await radio.connect()
    server = RigctldServer(
        radio,
        RigctldConfig(
            host="127.0.0.1",
            port=0,
            client_timeout=1.0,
            command_timeout=1.0,
            poll_interval=0.5,
        ),
    )
    await server.start()
    try:
        assert server._server is not None
        host, port = _addr_from_asyncio_server(server._server)
        reader, writer = await asyncio.open_connection(host, port)
        try:
            writer.write(b"f\n")
            await writer.drain()
            freq_resp = await asyncio.wait_for(reader.readuntil(b"\n"), timeout=2.0)
            assert freq_resp.strip() == b"14074000"

            writer.write(b"m\n")
            await writer.drain()
            mode_line = await asyncio.wait_for(reader.readuntil(b"\n"), timeout=2.0)
            passband_line = await asyncio.wait_for(
                reader.readuntil(b"\n"), timeout=2.0
            )
            assert mode_line.strip() == b"USB"
            assert passband_line.strip() in {b"3000", b"2400", b"1800", b"0"}
        finally:
            await _close_writer(writer)
    finally:
        await server.stop()
