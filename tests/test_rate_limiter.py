"""Tests for the per-client command rate limiter in server.py.

Strategy: inject mock protocol/handler like test_rigctld_server.py,
configure command_rate_limit, and verify allowed/rejected behaviour
by observing the bytes returned to the TCP client.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from icom_lan.rigctld.contract import (
    HamlibError,
    RigctldCommand,
    RigctldConfig,
    RigctldResponse,
)
from icom_lan.rigctld.server import RigctldServer


# ---------------------------------------------------------------------------
# Shared canned objects
# ---------------------------------------------------------------------------

_FREQ_CMD = RigctldCommand(short_cmd="f", long_cmd="get_freq", is_set=False)
_FREQ_RESP = RigctldResponse(values=["14074000"], error=0)
_OK_BYTES = b"14074000\n"
_RATE_ERROR_BYTES = b"RPRT -6\n"


# ---------------------------------------------------------------------------
# Helpers (mirror test_rigctld_server.py)
# ---------------------------------------------------------------------------


def _addr(server: RigctldServer) -> tuple[str, int]:
    assert server._server is not None
    return server._server.sockets[0].getsockname()


async def _connect(
    server: RigctldServer,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    host, port = _addr(server)
    return await asyncio.open_connection(host, port)


async def _close(writer: asyncio.StreamWriter) -> None:
    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass


async def _read(reader: asyncio.StreamReader, *, timeout: float = 1.0) -> bytes:
    return await asyncio.wait_for(reader.read(4096), timeout=timeout)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_radio() -> MagicMock:
    return MagicMock(name="radio")


@pytest.fixture
def proto() -> MagicMock:
    m = MagicMock(name="protocol")
    m.parse_line.return_value = _FREQ_CMD
    m.format_response.return_value = _OK_BYTES
    m.format_error.side_effect = lambda code: f"RPRT {int(code)}\n".encode()
    return m


@pytest.fixture
def handler() -> MagicMock:
    m = MagicMock(name="handler")
    m.execute = AsyncMock(return_value=_FREQ_RESP)
    return m


def _make_server(
    mock_radio: MagicMock,
    proto: MagicMock,
    handler: MagicMock,
    rate_limit: float | None,
) -> RigctldServer:
    cfg = RigctldConfig(
        host="127.0.0.1",
        port=0,
        command_rate_limit=rate_limit,
        client_timeout=5.0,
        command_timeout=1.0,
    )
    return RigctldServer(mock_radio, cfg, _protocol=proto, _handler=handler)


# ---------------------------------------------------------------------------
# None = unlimited
# ---------------------------------------------------------------------------


class TestRateLimitNone:
    async def test_unlimited_many_commands(
        self,
        mock_radio: MagicMock,
        proto: MagicMock,
        handler: MagicMock,
    ) -> None:
        """command_rate_limit=None → all commands pass regardless of rate."""
        srv = _make_server(mock_radio, proto, handler, rate_limit=None)
        async with srv:
            r, w = await _connect(srv)
            # Send 20 commands as fast as possible — all should succeed.
            for _ in range(20):
                w.write(b"f\n")
                await w.drain()
                data = await _read(r)
                assert data == _OK_BYTES, "expected OK, got rate-limited response"
            await _close(w)


# ---------------------------------------------------------------------------
# Under the limit — commands go through
# ---------------------------------------------------------------------------


class TestUnderLimit:
    async def test_commands_under_limit_succeed(
        self,
        mock_radio: MagicMock,
        proto: MagicMock,
        handler: MagicMock,
    ) -> None:
        """Sending fewer commands than the limit in a 1-second window is fine."""
        srv = _make_server(mock_radio, proto, handler, rate_limit=5.0)
        async with srv:
            r, w = await _connect(srv)
            for _ in range(5):
                w.write(b"f\n")
                await w.drain()
                data = await _read(r)
                assert data == _OK_BYTES
            await _close(w)


# ---------------------------------------------------------------------------
# Over the limit — command rejected with EIO (-6)
# ---------------------------------------------------------------------------


class TestOverLimit:
    async def test_excess_command_rejected(
        self,
        mock_radio: MagicMock,
        proto: MagicMock,
        handler: MagicMock,
    ) -> None:
        """The (limit+1)th command within a 1-second window is rejected."""
        srv = _make_server(mock_radio, proto, handler, rate_limit=3.0)
        async with srv:
            r, w = await _connect(srv)

            # First 3 should succeed.
            for _ in range(3):
                w.write(b"f\n")
                await w.drain()
                data = await _read(r)
                assert data == _OK_BYTES

            # 4th should be rate-limited.
            w.write(b"f\n")
            await w.drain()
            data = await _read(r)
            assert data == b"RPRT -6\n"

            await _close(w)

    async def test_rate_limited_calls_format_error_with_eio(
        self,
        mock_radio: MagicMock,
        proto: MagicMock,
        handler: MagicMock,
    ) -> None:
        """format_error must be called with HamlibError.EIO when rate-limited."""
        srv = _make_server(mock_radio, proto, handler, rate_limit=1.0)
        async with srv:
            r, w = await _connect(srv)

            # First command: allowed.
            w.write(b"f\n")
            await w.drain()
            await _read(r)

            # Second command: rejected.
            w.write(b"f\n")
            await w.drain()
            await _read(r)

            # Verify the last format_error call used EIO.
            error_calls = [call for call in proto.format_error.call_args_list]
            assert any(call.args[0] == HamlibError.EIO for call in error_calls), (
                "format_error should have been called with HamlibError.EIO"
            )

            await _close(w)

    async def test_connection_usable_after_rate_limit(
        self,
        mock_radio: MagicMock,
        proto: MagicMock,
        handler: MagicMock,
    ) -> None:
        """After a rate-limit rejection, the connection stays open."""
        srv = _make_server(mock_radio, proto, handler, rate_limit=1.0)
        async with srv:
            r, w = await _connect(srv)

            # Allow first.
            w.write(b"f\n")
            await w.drain()
            data = await _read(r)
            assert data == _OK_BYTES

            # Reject second.
            w.write(b"f\n")
            await w.drain()
            rejected = await _read(r)
            assert rejected == b"RPRT -6\n"

            # Wait for window to expire, then succeed again.
            await asyncio.sleep(1.1)
            w.write(b"f\n")
            await w.drain()
            data = await _read(r)
            assert data == _OK_BYTES

            await _close(w)


# ---------------------------------------------------------------------------
# Window reset — after 1 second, quota refills
# ---------------------------------------------------------------------------


class TestWindowReset:
    async def test_commands_allowed_after_window_expires(
        self,
        mock_radio: MagicMock,
        proto: MagicMock,
        handler: MagicMock,
    ) -> None:
        """After the 1-second window elapses, rate-limited commands are accepted."""
        srv = _make_server(mock_radio, proto, handler, rate_limit=2.0)
        async with srv:
            r, w = await _connect(srv)

            # Saturate window (2 allowed).
            for _ in range(2):
                w.write(b"f\n")
                await w.drain()
                data = await _read(r)
                assert data == _OK_BYTES

            # 3rd rejected.
            w.write(b"f\n")
            await w.drain()
            data = await _read(r)
            assert data == b"RPRT -6\n"

            # Wait for window to reset.
            await asyncio.sleep(1.1)

            # Should be allowed again.
            w.write(b"f\n")
            await w.drain()
            data = await _read(r)
            assert data == _OK_BYTES

            await _close(w)


# ---------------------------------------------------------------------------
# Rate windows cleaned up on disconnect
# ---------------------------------------------------------------------------


class TestRateWindowCleanup:
    async def test_rate_window_removed_on_disconnect(
        self,
        mock_radio: MagicMock,
        proto: MagicMock,
        handler: MagicMock,
    ) -> None:
        """Client's rate window entry is removed after disconnect."""
        srv = _make_server(mock_radio, proto, handler, rate_limit=5.0)
        async with srv:
            r, w = await _connect(srv)
            w.write(b"f\n")
            await w.drain()
            await _read(r)

            # At least one window entry exists while connected.
            assert len(srv._rate_windows) >= 1

            await _close(w)
            # Give event loop a moment for the finally block to execute.
            await asyncio.sleep(0.05)

            assert len(srv._rate_windows) == 0

    async def test_rate_windows_independent_per_client(
        self,
        mock_radio: MagicMock,
        proto: MagicMock,
        handler: MagicMock,
    ) -> None:
        """Each client gets an independent rate window."""
        srv = _make_server(mock_radio, proto, handler, rate_limit=1.0)
        async with srv:
            r1, w1 = await _connect(srv)
            r2, w2 = await _connect(srv)

            # Saturate client1's window.
            w1.write(b"f\n")
            await w1.drain()
            data1 = await _read(r1)
            assert data1 == _OK_BYTES

            # client1 now rate-limited.
            w1.write(b"f\n")
            await w1.drain()
            rejected1 = await _read(r1)
            assert rejected1 == b"RPRT -6\n"

            # client2 still has its own quota — first command should succeed.
            w2.write(b"f\n")
            await w2.drain()
            data2 = await _read(r2)
            assert data2 == _OK_BYTES

            await _close(w1)
            await _close(w2)
