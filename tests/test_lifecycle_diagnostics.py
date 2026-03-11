"""Tests for lifecycle diagnostics — WARN when Radio/WebServer/RigctldServer are GC'd with active tasks.

See GitHub issue 207: help diagnose 'forgot to disconnect/stop' by logging at GC time.
"""

from __future__ import annotations

import gc
import logging

import pytest

from icom_lan._connection_state import RadioConnectionState
from icom_lan.backends.icom7610.drivers.serial_stub import SerialMockRadio
from icom_lan.radio import IcomRadio
from icom_lan.rigctld.contract import RigctldConfig
from icom_lan.rigctld.server import RigctldServer
from icom_lan.web.server import WebConfig, WebServer


# ---------------------------------------------------------------------------
# Radio: GC with active connection
# ---------------------------------------------------------------------------


@pytest.mark.filterwarnings("ignore:coroutine .* was never awaited:RuntimeWarning")
def test_radio_gc_with_active_connection_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When a Radio is collected while still 'connected', a WARN is emitted."""
    with caplog.at_level(logging.WARNING, logger="icom_lan.radio"):
        radio = IcomRadio("192.168.1.1")
        # Simulate still connected (e.g. user forgot disconnect() or async with exit)
        radio._conn_state = RadioConnectionState.CONNECTED
        del radio
        gc.collect()

    assert any(
        "active" in r.message.lower() and "disconnect" in r.message.lower()
        for r in caplog.records
    ), f"Expected WARN about active connection; got: {[r.message for r in caplog.records]}"
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_radio_gc_when_disconnected_does_not_log_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When a Radio is collected after disconnect, no WARN is emitted."""
    with caplog.at_level(logging.WARNING, logger="icom_lan.radio"):
        radio = IcomRadio("192.168.1.1")
        assert radio._conn_state == RadioConnectionState.DISCONNECTED
        del radio
        gc.collect()

    assert not any(
        "active" in r.message.lower() and "disconnect" in r.message.lower()
        for r in caplog.records
    )


# ---------------------------------------------------------------------------
# WebServer: GC while running
# ---------------------------------------------------------------------------


async def test_web_server_gc_while_running_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When WebServer is collected while _server is still set (forgot stop()), a WARN is emitted."""
    with caplog.at_level(logging.WARNING, logger="icom_lan.web.server"):
        server = WebServer(config=WebConfig(port=0))
        await server.start()
        assert server._server is not None
        # Close the socket so we don't leave a listening port, but leave _server set
        # so __del__ still sees "running" (forgotten stop() scenario).
        server._server.close()
        await server._server.wait_closed()
        del server
        gc.collect()

    assert any(
        "running" in r.message.lower() or "stop" in r.message.lower()
        for r in caplog.records
    ), f"Expected WARN about running server; got: {[r.message for r in caplog.records]}"
    assert any(r.levelno == logging.WARNING for r in caplog.records)


async def test_web_server_gc_after_stop_does_not_log_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When WebServer is stopped before GC, no WARN is emitted."""
    with caplog.at_level(logging.WARNING, logger="icom_lan.web.server"):
        server = WebServer(config=WebConfig(port=0))
        await server.start()
        await server.stop()
        del server
        gc.collect()

    assert not any(
        "running" in r.message.lower() or "stop" in r.message.lower()
        for r in caplog.records
    )


# ---------------------------------------------------------------------------
# RigctldServer: GC while running
# ---------------------------------------------------------------------------


async def test_rigctld_server_gc_while_running_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When RigctldServer is collected while TCP server is still active, a WARN is emitted."""
    radio = SerialMockRadio()
    with caplog.at_level(logging.WARNING, logger="icom_lan.rigctld.server"):
        server = RigctldServer(radio, RigctldConfig(port=0))
        await server.start()
        assert server._server is not None
        server._server.close()
        await server._server.wait_closed()
        del server
        gc.collect()

    assert any(
        "running" in r.message.lower() or "stop" in r.message.lower()
        for r in caplog.records
    ), f"Expected WARN about active rigctld; got: {[r.message for r in caplog.records]}"
    assert any(r.levelno == logging.WARNING for r in caplog.records)


async def test_rigctld_server_gc_after_stop_does_not_log_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When RigctldServer is stopped before GC, no WARN is emitted."""
    radio = SerialMockRadio()
    with caplog.at_level(logging.WARNING, logger="icom_lan.rigctld.server"):
        server = RigctldServer(radio, RigctldConfig(port=0))
        await server.start()
        await server.stop()
        del server
        gc.collect()

    assert not any(
        "running" in r.message.lower() or "stop" in r.message.lower()
        for r in caplog.records
    )
