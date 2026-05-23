"""Provider-facing contract tests for a future external Hamlib backend."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from fake_rigctld import FakeRigctldBehavior, FakeRigctldServer
from rigplane.rigctld.contract import HamlibError


@dataclass(frozen=True, slots=True)
class _ModeReply:
    mode: str
    passband_hz: int


class _ProviderFacingRigctldClient:
    """Minimal test-local client that documents future backend assumptions."""

    def __init__(self, host: str, port: int, *, timeout: float = 0.5) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    async def get_freq(self) -> int:
        line = (await self._request("f", value_lines=1))[0]
        try:
            return int(line)
        except ValueError as exc:
            raise ValueError("Malformed rigctld frequency response") from exc

    async def set_freq(self, frequency_hz: int) -> None:
        await self._request(f"F {frequency_hz}", value_lines=0)

    async def get_mode(self) -> _ModeReply:
        mode, passband = await self._request("m", value_lines=2)
        try:
            passband_hz = int(passband)
        except ValueError as exc:
            raise ValueError("Malformed rigctld mode response") from exc
        return _ModeReply(mode=mode, passband_hz=passband_hz)

    async def set_mode(self, mode: str, passband_hz: int) -> None:
        await self._request(f"M {mode} {passband_hz}", value_lines=0)

    async def get_ptt(self) -> bool:
        line = (await self._request("t", value_lines=1))[0]
        if line not in {"0", "1"}:
            raise ValueError("Malformed rigctld PTT response")
        return line == "1"

    async def set_ptt(self, enabled: bool) -> None:
        await self._request(f"T {int(enabled)}", value_lines=0)

    async def get_vfo(self) -> str:
        return (await self._request("v", value_lines=1))[0]

    async def set_vfo(self, vfo: str) -> None:
        await self._request(f"V {vfo}", value_lines=0)

    async def unsupported_probe(self) -> None:
        await self._request(r"\dump_state", value_lines=1)

    async def _request(self, command: str, *, value_lines: int) -> list[str]:
        reader: asyncio.StreamReader | None = None
        writer: asyncio.StreamWriter | None = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            writer.write(f"{command}\n".encode("ascii"))
            await writer.drain()

            first = await self._read_line(reader)
            if first.startswith("RPRT "):
                self._handle_report(first)
                return []
            if value_lines == 0:
                raise ValueError(f"Expected RPRT response, got {first!r}")

            values = [first]
            for _ in range(value_lines - 1):
                values.append(await self._read_line(reader))
            return values
        finally:
            if writer is not None:
                writer.close()
                await writer.wait_closed()

    async def _read_line(self, reader: asyncio.StreamReader) -> str:
        line = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
        if line == b"":
            raise ConnectionError("rigctld disconnected")
        return line.decode("ascii").rstrip("\n")

    @staticmethod
    def _handle_report(line: str) -> None:
        try:
            code = int(line.split(maxsplit=1)[1])
        except (IndexError, ValueError) as exc:
            raise ValueError("Malformed rigctld RPRT response") from exc

        if code == HamlibError.OK:
            return
        if code == HamlibError.ENIMPL:
            raise NotImplementedError("rigctld command is unsupported")
        raise RuntimeError(f"rigctld command failed with RPRT {code}")


def _client(
    server: FakeRigctldServer, *, timeout: float = 0.5
) -> _ProviderFacingRigctldClient:
    host, port = server.address
    return _ProviderFacingRigctldClient(host, port, timeout=timeout)


async def test_rigplane_owned_provider_happy_path_golden() -> None:
    async with FakeRigctldServer() as server:
        client = _client(server)

        assert await client.get_freq() == 14_074_000
        await client.set_freq(7_050_000)
        assert await client.get_freq() == 7_050_000

        assert await client.get_mode() == _ModeReply("USB", 2400)
        await client.set_mode("LSB", 1800)
        assert await client.get_mode() == _ModeReply("LSB", 1800)

        assert await client.get_ptt() is False
        await client.set_ptt(True)
        assert await client.get_ptt() is True

        assert await client.get_vfo() == "VFOA"
        await client.set_vfo("VFOB")
        assert await client.get_vfo() == "VFOB"

    assert server.commands_seen == [
        "f",
        "F 7050000",
        "f",
        "m",
        "M LSB 1800",
        "m",
        "t",
        "T 1",
        "t",
        "v",
        "V VFOB",
        "v",
    ]


async def test_rigplane_owned_provider_times_out_when_rigctld_delays_reply() -> None:
    behavior = FakeRigctldBehavior(command_delays={"f": 0.2})

    async with FakeRigctldServer(behavior=behavior) as server:
        client = _client(server, timeout=0.05)
        with pytest.raises(asyncio.TimeoutError):
            await client.get_freq()


async def test_rigplane_owned_provider_rejects_malformed_frequency_response() -> None:
    behavior = FakeRigctldBehavior(malformed_responses={"f": b"not-a-frequency\n"})

    async with FakeRigctldServer(behavior=behavior) as server:
        client = _client(server)
        with pytest.raises(ValueError, match="Malformed rigctld frequency response"):
            await client.get_freq()


async def test_rigplane_owned_provider_reports_rigctld_disconnect() -> None:
    behavior = FakeRigctldBehavior(disconnect_commands={"f"})

    async with FakeRigctldServer(behavior=behavior) as server:
        client = _client(server)
        with pytest.raises(ConnectionError, match="rigctld disconnected"):
            await client.get_freq()


async def test_rigplane_owned_provider_maps_unsupported_to_not_implemented() -> None:
    async with FakeRigctldServer() as server:
        client = _client(server)
        with pytest.raises(NotImplementedError, match="unsupported"):
            await client.unsupported_probe()


@pytest.mark.parametrize(
    ("operation", "command", "malformed_response", "expected_message"),
    [
        pytest.param(
            lambda client: client.get_mode(),
            "m",
            b"USB\nwide\n",
            "Malformed rigctld mode response",
            id="mode-passband",
        ),
        pytest.param(
            lambda client: client.get_ptt(),
            "t",
            b"enabled\n",
            "Malformed rigctld PTT response",
            id="ptt-bool",
        ),
    ],
)
async def test_rigplane_owned_provider_rejects_other_malformed_responses(
    operation: Callable[[_ProviderFacingRigctldClient], Awaitable[Any]],
    command: str,
    malformed_response: bytes,
    expected_message: str,
) -> None:
    behavior = FakeRigctldBehavior(malformed_responses={command: malformed_response})

    async with FakeRigctldServer(behavior=behavior) as server:
        client = _client(server)
        with pytest.raises(ValueError, match=expected_message):
            await operation(client)
