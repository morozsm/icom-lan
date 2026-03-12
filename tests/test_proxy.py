"""Tests for the UDP relay proxy."""

import asyncio

import pytest

from icom_lan.proxy import _RelayProtocol, run_proxy


class TestRelayProtocol:
    """Unit tests for _RelayProtocol."""

    def test_client_to_radio(self) -> None:
        """Packets from client are forwarded to radio."""
        relay = _RelayProtocol("192.168.1.100", 50001, "control")
        sent: list[tuple[bytes, tuple[str, int]]] = []

        class FakeTransport:
            def sendto(self, data: bytes, addr: tuple[str, int]) -> None:
                sent.append((data, addr))

            def get_extra_info(self, key: str) -> tuple[str, int]:
                return ("0.0.0.0", 50001)

        relay.connection_made(FakeTransport())  # type: ignore[arg-type]
        relay.datagram_received(b"hello", ("10.0.0.5", 12345))

        assert len(sent) == 1
        assert sent[0] == (b"hello", ("192.168.1.100", 50001))
        assert relay.client_addr == ("10.0.0.5", 12345)

    def test_radio_to_client(self) -> None:
        """Packets from radio are forwarded to remembered client."""
        relay = _RelayProtocol("192.168.1.100", 50001, "control")
        sent: list[tuple[bytes, tuple[str, int]]] = []

        class FakeTransport:
            def sendto(self, data: bytes, addr: tuple[str, int]) -> None:
                sent.append((data, addr))

            def get_extra_info(self, key: str) -> tuple[str, int]:
                return ("0.0.0.0", 50001)

        relay.connection_made(FakeTransport())  # type: ignore[arg-type]

        # First: client sends something to register
        relay.datagram_received(b"from_client", ("10.0.0.5", 12345))
        sent.clear()

        # Then: radio sends back
        relay.datagram_received(b"from_radio", ("192.168.1.100", 50001))
        assert len(sent) == 1
        assert sent[0] == (b"from_radio", ("10.0.0.5", 12345))

    def test_no_client_drops_radio_packet(self) -> None:
        """Radio packets are dropped when no client is registered."""
        relay = _RelayProtocol("192.168.1.100", 50001, "control")
        sent: list[tuple[bytes, tuple[str, int]]] = []

        class FakeTransport:
            def sendto(self, data: bytes, addr: tuple[str, int]) -> None:
                sent.append((data, addr))

            def get_extra_info(self, key: str) -> tuple[str, int]:
                return ("0.0.0.0", 50001)

        relay.connection_made(FakeTransport())  # type: ignore[arg-type]

        # Radio sends but no client registered
        relay.datagram_received(b"from_radio", ("192.168.1.100", 50001))
        assert len(sent) == 0

    def test_session_timeout(self) -> None:
        """Client addr is cleared after timeout."""
        import time

        relay = _RelayProtocol("192.168.1.100", 50001, "control")

        class FakeTransport:
            def sendto(self, data: bytes, addr: tuple[str, int]) -> None:
                pass

            def get_extra_info(self, key: str) -> tuple[str, int]:
                return ("0.0.0.0", 50001)

        relay.connection_made(FakeTransport())  # type: ignore[arg-type]
        relay.datagram_received(b"hello", ("10.0.0.5", 12345))
        assert relay.client_addr is not None

        # Simulate timeout
        relay.last_activity = time.monotonic() - 120.0
        from icom_lan.proxy import SESSION_TIMEOUT

        now = time.monotonic()
        if relay.client_addr and (now - relay.last_activity) > SESSION_TIMEOUT:
            relay.client_addr = None

        assert relay.client_addr is None


@pytest.mark.asyncio
async def test_run_proxy_starts_and_stops() -> None:
    """run_proxy can be started and cancelled."""
    task = asyncio.create_task(run_proxy("192.168.1.100", "127.0.0.1", 59001))
    await asyncio.sleep(0.1)
    assert not task.done()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
