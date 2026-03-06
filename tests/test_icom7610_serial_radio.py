"""Lifecycle and readiness tests for Icom7610SerialRadio."""

from __future__ import annotations

import asyncio

import pytest

from icom_lan import RadioConnectionState
from icom_lan.backends.icom7610 import Icom7610SerialRadio
from icom_lan.commands import CONTROLLER_ADDR, IC_7610_ADDR, _CMD_FREQ_GET, build_civ_frame
from icom_lan.exceptions import ConnectionError
from icom_lan.types import bcd_encode


def _freq_response_frame(freq_hz: int) -> bytes:
    return build_civ_frame(
        CONTROLLER_ADDR,
        IC_7610_ADDR,
        _CMD_FREQ_GET,
        data=bcd_encode(freq_hz),
    )


async def _wait_until(predicate, *, timeout_s: float = 1.0) -> bool:  # type: ignore[no-untyped-def]
    deadline = asyncio.get_running_loop().time() + timeout_s
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.02)
    return bool(predicate())


class _FakeSerialCivLink:
    def __init__(
        self,
        *,
        fail_connect: BaseException | None = None,
        fail_connect_calls: set[int] | None = None,
    ) -> None:
        self._fail_connect = fail_connect
        self._fail_connect_calls = set(fail_connect_calls or set())
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.connected = False
        self.ready = False
        self.healthy = False
        self.sent_frames: list[bytes] = []
        self._responses: asyncio.Queue[bytes] = asyncio.Queue()
        self._responses_by_send: dict[int, list[bytes]] = {}

    async def connect(self) -> None:
        self.connect_calls += 1
        if self.connect_calls in self._fail_connect_calls:
            raise OSError(f"connect failed on call {self.connect_calls}")
        if self._fail_connect is not None:
            raise self._fail_connect
        self.connected = True
        self.ready = True
        self.healthy = True

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        self.connected = False
        self.ready = False
        self.healthy = False

    async def send(self, frame: bytes) -> None:
        if not self.connected:
            raise ConnectionError("Serial CI-V link is disconnected.")
        payload = bytes(frame)
        self.sent_frames.append(payload)
        send_no = len(self.sent_frames)
        for response in self._responses_by_send.pop(send_no, []):
            self._responses.put_nowait(response)

    async def receive(self, timeout: float | None = None) -> bytes | None:
        if not self.connected:
            return None
        timeout_s = 0.05 if timeout is None else timeout
        try:
            return await asyncio.wait_for(self._responses.get(), timeout=timeout_s)
        except asyncio.TimeoutError:
            return None

    def queue_response_on_send(self, send_no: int, frame: bytes) -> None:
        self._responses_by_send.setdefault(send_no, []).append(frame)


@pytest.mark.asyncio
async def test_serial_radio_connect_disconnect_and_core_command_execution() -> None:
    link = _FakeSerialCivLink()
    link.queue_response_on_send(1, _freq_response_frame(14_074_000))
    radio = Icom7610SerialRadio(
        device="/dev/ttyUSB0",
        civ_link=link,
    )

    await radio.connect()
    assert radio.connected is True
    assert radio.control_connected is True
    assert await radio.get_frequency() == 14_074_000
    assert link.sent_frames
    assert radio.radio_ready is True

    await radio.disconnect()
    assert radio.connected is False
    assert radio.control_connected is False
    assert radio.radio_ready is False
    assert radio._civ_transport is None
    assert radio._civ_rx_task is None
    assert getattr(radio, "_civ_data_watchdog_task", None) is None


@pytest.mark.asyncio
async def test_serial_radio_connect_failure_sets_disconnected_state() -> None:
    radio = Icom7610SerialRadio(
        device="/dev/ttyUSB0",
        civ_link=_FakeSerialCivLink(fail_connect=OSError("permission denied")),
    )

    with pytest.raises(ConnectionError, match="Failed to connect serial session"):
        await radio.connect()

    assert radio.connected is False
    assert radio.control_connected is False
    assert radio.radio_ready is False


@pytest.mark.asyncio
async def test_serial_radio_ready_tracks_serial_link_health() -> None:
    link = _FakeSerialCivLink()
    radio = Icom7610SerialRadio(
        device="/dev/ttyUSB0",
        civ_link=link,
    )

    await radio.connect()
    assert await _wait_until(lambda: radio.radio_ready)

    link.ready = False
    link.healthy = False
    assert await _wait_until(lambda: not radio.radio_ready)

    link.ready = True
    link.healthy = True
    assert await _wait_until(lambda: radio.radio_ready)

    await radio.disconnect()


@pytest.mark.asyncio
async def test_serial_watchdog_retries_after_transient_soft_reconnect_failure() -> None:
    link = _FakeSerialCivLink(fail_connect_calls={2})
    radio = Icom7610SerialRadio(
        device="/dev/ttyUSB0",
        civ_link=link,
    )
    radio._SERIAL_WATCHDOG_INTERVAL_S = 0.05  # type: ignore[attr-defined]
    radio._SERIAL_WATCHDOG_RETRY_S = 0.01  # type: ignore[attr-defined]

    await radio.connect()
    assert link.connect_calls == 1
    assert radio.radio_ready is True

    link.ready = False
    link.healthy = False
    assert await _wait_until(lambda: link.connect_calls >= 3, timeout_s=2.0)
    assert await _wait_until(lambda: radio.radio_ready, timeout_s=2.0)
    assert radio.conn_state == RadioConnectionState.CONNECTED

    await radio.disconnect()


@pytest.mark.asyncio
async def test_serial_disconnect_cleans_watchdog_when_already_disconnected() -> None:
    radio = Icom7610SerialRadio(
        device="/dev/ttyUSB0",
        civ_link=_FakeSerialCivLink(),
    )
    radio._conn_state = RadioConnectionState.DISCONNECTED
    radio._civ_data_watchdog_task = asyncio.create_task(asyncio.sleep(10))
    await radio.disconnect()
    assert getattr(radio, "_civ_data_watchdog_task", None) is None
