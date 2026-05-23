"""Tests for the external Hamlib ``rigctld`` client backend."""

from __future__ import annotations

import asyncio

import pytest

from fake_rigctld import FakeRigctldBehavior, FakeRigctldServer
from rigplane.backends.config import RigctldBackendConfig
from rigplane.backends.factory import create_radio
from rigplane.backends.rigctld_client import RigctldClientRadio, RigctldTransport
from rigplane.exceptions import CommandError
from rigplane.exceptions import ConnectionError as RadioConnectionError
from rigplane.exceptions import TimeoutError as RadioTimeoutError


async def test_transport_connect_query_and_close() -> None:
    async with FakeRigctldServer() as server:
        transport = RigctldTransport(host=server.host, port=server.port)

        await transport.connect()
        try:
            assert transport.connected
            assert await transport.query("f", response_lines=1) == ["14074000"]
        finally:
            await transport.close()

        assert not transport.connected


async def test_transport_serializes_requests() -> None:
    behavior = FakeRigctldBehavior(command_delays={"f": 0.02})

    async with FakeRigctldServer(behavior=behavior) as server:
        transport = RigctldTransport(host=server.host, port=server.port)
        await transport.connect()
        try:
            results = await asyncio.gather(
                transport.query("f", response_lines=1),
                transport.query("t", response_lines=1),
            )
        finally:
            await transport.close()

    assert results == [["14074000"], ["0"]]
    assert server.commands_seen == ["f", "t"]


async def test_transport_timeout_eof_malformed_and_negative_rprt() -> None:
    timeout_behavior = FakeRigctldBehavior(command_delays={"f": 0.2})
    async with FakeRigctldServer(behavior=timeout_behavior) as server:
        transport = RigctldTransport(
            host=server.host,
            port=server.port,
            timeout=0.01,
        )
        await transport.connect()
        try:
            with pytest.raises(RadioTimeoutError, match="timed out"):
                await transport.query("f", response_lines=1)
        finally:
            await transport.close()

    eof_behavior = FakeRigctldBehavior(disconnect_commands={"f"})
    async with FakeRigctldServer(behavior=eof_behavior) as server:
        transport = RigctldTransport(host=server.host, port=server.port)
        await transport.connect()
        try:
            with pytest.raises(RadioConnectionError, match="closed"):
                await transport.query("f", response_lines=1)
        finally:
            await transport.close()

    malformed_behavior = FakeRigctldBehavior(malformed_responses={"F": b"nope\n"})
    async with FakeRigctldServer(behavior=malformed_behavior) as server:
        transport = RigctldTransport(host=server.host, port=server.port)
        await transport.connect()
        try:
            with pytest.raises(CommandError, match="malformed"):
                await transport.command("F 14074000")
        finally:
            await transport.close()

    unsupported_behavior = FakeRigctldBehavior(unsupported_commands={"F"})
    async with FakeRigctldServer(behavior=unsupported_behavior) as server:
        transport = RigctldTransport(host=server.host, port=server.port)
        await transport.connect()
        try:
            with pytest.raises(CommandError, match="unsupported"):
                await transport.command("F 14074000")
        finally:
            await transport.close()

    unsupported_query = FakeRigctldBehavior(unsupported_commands={"m"})
    async with FakeRigctldServer(behavior=unsupported_query) as server:
        transport = RigctldTransport(host=server.host, port=server.port)
        await transport.connect()
        try:
            with pytest.raises(CommandError, match="unsupported"):
                await transport.query("m", response_lines=2)
        finally:
            await transport.close()


async def test_radio_core_frequency_mode_ptt_and_vfo() -> None:
    async with FakeRigctldServer() as server:
        radio = RigctldClientRadio(host=server.host, port=server.port)
        await radio.connect()
        try:
            assert radio.connected
            assert radio.radio_ready
            assert radio.backend_id == "rigctld"
            assert radio.model == "External rigctld"
            assert radio.capabilities == {"tx", "vfo"}
            assert radio.supports_command("set_freq")
            assert radio.supports_command("get_vfo_slot")
            assert not radio.supports_command("start_audio_rx_opus")

            assert await radio.get_freq() == 14_074_000
            await radio.set_freq(7_050_000)
            assert radio.radio_state.main.freq == 7_050_000

            assert await radio.get_mode() == ("USB", 2400)
            await radio.set_mode("LSB", 1800)
            assert radio.radio_state.main.mode == "LSB"
            assert radio.radio_state.main.filter_width == 1800

            assert await radio.get_ptt() is False
            await radio.set_ptt(True)
            assert radio.radio_state.ptt is True

            assert await radio.get_vfo_slot() == "A"
            await radio.set_vfo_slot("B")
            assert radio.radio_state.main.active_slot == "B"
        finally:
            await radio.disconnect()


async def test_radio_reports_actionable_connection_failure() -> None:
    radio = RigctldClientRadio(host="127.0.0.1", port=9, timeout=0.01)

    with pytest.raises(RadioConnectionError, match="127.0.0.1:9"):
        await radio.connect()


async def test_radio_rejects_unsupported_data_mode() -> None:
    async with FakeRigctldServer() as server:
        radio = RigctldClientRadio(host=server.host, port=server.port)
        await radio.connect()
        try:
            assert await radio.get_data_mode() is False
            with pytest.raises(CommandError, match="data mode"):
                await radio.set_data_mode(True)
        finally:
            await radio.disconnect()


def test_config_factory_builds_rigctld_client_backend() -> None:
    config = RigctldBackendConfig(host="localhost")

    radio = create_radio(config)

    assert isinstance(radio, RigctldClientRadio)
    assert config.backend == "rigctld"
    assert config.port == 4532
    assert radio.backend_id == "rigctld"


def test_config_validates_rigctld_client_backend() -> None:
    with pytest.raises(ValueError, match="host"):
        RigctldBackendConfig(host="")
    with pytest.raises(ValueError, match="port"):
        RigctldBackendConfig(host="localhost", port=0)
    with pytest.raises(ValueError, match="timeout"):
        RigctldBackendConfig(host="localhost", timeout=0)
