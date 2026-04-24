"""Tests for timing-safe token comparison (issue #947).

Verifies that the HTTP API and WebSocket auth paths in web/server.py
use ``hmac.compare_digest`` for token comparison. These tests don't
measure timing directly — they assert correctness (accept on match,
reject on mismatch) and that the module imports ``hmac``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from icom_lan.web import server as web_server
from icom_lan.web.server import WebConfig, WebServer


def test_server_module_imports_hmac() -> None:
    """Regression guard: ensure the web server imports hmac.

    If this fails, someone has removed the import and fallen back to
    timing-unsafe `==` comparisons.
    """
    assert hasattr(web_server, "hmac")


class _MemoryWriter:
    """Minimal asyncio.StreamWriter stand-in that captures written bytes."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.closed = False

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:  # pragma: no cover - trivial
        return

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:  # pragma: no cover
        return

    def is_closing(self) -> bool:
        return self.closed

    def get_extra_info(self, *_args: Any, **_kwargs: Any) -> Any:
        return ("127.0.0.1", 0)


def _make_server(token: str) -> WebServer:
    cfg = WebConfig(auth_token=token)
    return WebServer(radio=None, config=cfg)


def test_http_api_accepts_correct_bearer_token() -> None:
    """HTTP API endpoint accepts the correct Bearer token."""
    srv = _make_server("s3cr3t")
    writer = _MemoryWriter()
    headers = {"authorization": "Bearer s3cr3t"}

    async def run() -> None:
        # _handle_http needs a reader too; use an empty one for a GET with no body.
        reader = asyncio.StreamReader()
        reader.feed_eof()
        await srv._handle_http(writer, "GET", "/api/v1/info", headers, reader, None)  # type: ignore[arg-type]

    asyncio.run(run())
    # Correct token → should NOT produce a 401.
    assert b"401" not in bytes(writer.buffer[:32])


def test_http_api_rejects_wrong_bearer_token() -> None:
    """HTTP API endpoint rejects a bearer value that differs from the token."""
    srv = _make_server("s3cr3t")
    writer = _MemoryWriter()
    headers = {"authorization": "Bearer wrong"}

    async def run() -> None:
        reader = asyncio.StreamReader()
        reader.feed_eof()
        await srv._handle_http(writer, "GET", "/api/v1/info", headers, reader, None)  # type: ignore[arg-type]

    asyncio.run(run())
    assert b"401" in bytes(writer.buffer[:32])


def test_http_api_rejects_missing_bearer_prefix() -> None:
    """Header without the `Bearer ` prefix must be rejected."""
    srv = _make_server("s3cr3t")
    writer = _MemoryWriter()
    headers = {"authorization": "s3cr3t"}  # no prefix

    async def run() -> None:
        reader = asyncio.StreamReader()
        reader.feed_eof()
        await srv._handle_http(writer, "GET", "/api/v1/info", headers, reader, None)  # type: ignore[arg-type]

    asyncio.run(run())
    assert b"401" in bytes(writer.buffer[:32])


@pytest.mark.parametrize(
    "auth_header,token_param,should_pass",
    [
        ("Bearer s3cr3t", "", True),
        ("", "s3cr3t", True),
        ("Bearer wrong", "", False),
        ("", "wrong", False),
        ("Bearer wrong", "wrong", False),
    ],
)
def test_websocket_auth_matrix(
    auth_header: str, token_param: str, should_pass: bool
) -> None:
    """WebSocket upgrade path accepts either header OR query token when correct."""
    srv = _make_server("s3cr3t")
    writer = _MemoryWriter()
    headers = {
        "upgrade": "websocket",
        "connection": "Upgrade",
        "sec-websocket-key": "dGhlIHNhbXBsZSBub25jZQ==",
        "sec-websocket-version": "13",
    }
    if auth_header:
        headers["authorization"] = auth_header
    query = {"token": [token_param]} if token_param else {}

    async def run() -> None:
        reader = asyncio.StreamReader()
        reader.feed_eof()
        await srv._handle_websocket(  # type: ignore[attr-defined]
            reader,
            writer,
            "/api/v1/ws",
            headers,
            query,  # type: ignore[arg-type]
        )

    asyncio.run(run())
    head = bytes(writer.buffer[:32])
    if should_pass:
        assert b"401" not in head
    else:
        assert b"401" in head
