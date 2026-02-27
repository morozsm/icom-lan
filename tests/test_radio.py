"""Tests for IcomRadio high-level API."""

import asyncio
import struct
from unittest.mock import patch

import pytest

from icom_lan.commands import (
    CONTROLLER_ADDR,
    IC_7610_ADDR,
    build_civ_frame,
    _CMD_ACK,
    _CMD_FREQ_GET,
    _CMD_MODE_GET,
    _CMD_METER,
    _CMD_PTT,
    _CMD_LEVEL,
    _SUB_S_METER,
    _SUB_SWR_METER,
    _SUB_ALC_METER,
    _SUB_RF_POWER,
    _SUB_PTT,
)
from icom_lan.exceptions import ConnectionError, TimeoutError, CommandError
from icom_lan.radio import IcomRadio
from icom_lan.types import Mode, PacketType, bcd_encode


# ---------------------------------------------------------------------------
# Helpers — build fake radio responses as UDP packets wrapping CI-V frames
# ---------------------------------------------------------------------------


def _wrap_civ_in_udp(
    civ_data: bytes,
    sender_id: int = 0xDEADBEEF,
    receiver_id: int = 0x00010001,
    seq: int = 1,
) -> bytes:
    """Wrap a CI-V frame in a minimal UDP data packet."""
    # Data packet layout: 16-byte header + payload
    # For CIV data packets, after the 16-byte header there's a small sub-header
    # We'll use a simplified format that the radio module will parse
    total_len = 0x15 + len(civ_data)
    pkt = bytearray(total_len)
    struct.pack_into("<I", pkt, 0, total_len)
    struct.pack_into("<H", pkt, 4, PacketType.DATA)
    struct.pack_into("<H", pkt, 6, seq)
    struct.pack_into("<I", pkt, 8, sender_id)
    struct.pack_into("<I", pkt, 0x0C, receiver_id)
    # Sub-header at 0x10: type(1) + datalen(2) + sendseq(2)
    pkt[0x10] = 0x00
    struct.pack_into("<H", pkt, 0x11, len(civ_data))
    struct.pack_into("<H", pkt, 0x13, 0)
    pkt[0x15:] = civ_data
    return bytes(pkt)


def _freq_response(freq_hz: int) -> bytes:
    """Build a CI-V frequency response wrapped in UDP."""
    civ = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, _CMD_FREQ_GET, data=bcd_encode(freq_hz)
    )
    return _wrap_civ_in_udp(civ)


def _mode_response(mode: Mode, filt: int = 1) -> bytes:
    """Build a CI-V mode response wrapped in UDP."""
    civ = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, _CMD_MODE_GET, data=bytes([mode, filt])
    )
    return _wrap_civ_in_udp(civ)


def _meter_response(sub: int, value: int) -> bytes:
    """Build a CI-V meter response wrapped in UDP."""
    # BCD encode the value (0-255 as 4-digit BCD in 2 bytes)
    d = f"{value:04d}"
    b0 = (int(d[0]) << 4) | int(d[1])
    b1 = (int(d[2]) << 4) | int(d[3])
    civ = build_civ_frame(
        CONTROLLER_ADDR, IC_7610_ADDR, _CMD_METER, sub=sub, data=bytes([b0, b1])
    )
    return _wrap_civ_in_udp(civ)


def _ack_response() -> bytes:
    """Build a CI-V ACK wrapped in UDP."""
    civ = build_civ_frame(CONTROLLER_ADDR, IC_7610_ADDR, _CMD_ACK)
    return _wrap_civ_in_udp(civ)


def _nak_response() -> bytes:
    """Build a CI-V NAK wrapped in UDP."""
    civ = build_civ_frame(CONTROLLER_ADDR, IC_7610_ADDR, 0xFA)
    return _wrap_civ_in_udp(civ)


def _power_response(level: int) -> bytes:
    """Build a CI-V power level response wrapped in UDP."""
    d = f"{level:04d}"
    b0 = (int(d[0]) << 4) | int(d[1])
    b1 = (int(d[2]) << 4) | int(d[3])
    civ = build_civ_frame(
        CONTROLLER_ADDR,
        IC_7610_ADDR,
        _CMD_LEVEL,
        sub=_SUB_RF_POWER,
        data=bytes([b0, b1]),
    )
    return _wrap_civ_in_udp(civ)


def _ptt_response(on: bool) -> bytes:
    """Build a CI-V PTT status response wrapped in UDP."""
    civ = build_civ_frame(
        CONTROLLER_ADDR,
        IC_7610_ADDR,
        _CMD_PTT,
        sub=_SUB_PTT,
        data=bytes([0x01 if on else 0x00]),
    )
    return _wrap_civ_in_udp(civ)


# ---------------------------------------------------------------------------
# MockTransport — replaces IcomTransport for unit testing
# ---------------------------------------------------------------------------


class MockTransport:
    """Mock transport that queues responses for receive_packet."""

    def __init__(self) -> None:
        self.connected = False
        self.disconnected = False
        self.sent_packets: list[bytes] = []
        self._responses: asyncio.Queue[bytes] = asyncio.Queue()
        self._responses_by_send: dict[int, list[bytes]] = {}
        self._packet_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.my_id: int = 0x00010001
        self.remote_id: int = 0xDEADBEEF
        self.send_seq: int = 0
        self.ping_seq: int = 0
        self.rx_packet_count: int = 0

    async def connect(self, host: str, port: int) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.disconnected = True
        self.connected = False

    def start_ping_loop(self) -> None:
        pass

    def start_retransmit_loop(self) -> None:
        pass

    async def send_tracked(self, data: bytes) -> None:
        self.sent_packets.append(data)
        self.send_seq += 1
        for pkt in self._responses_by_send.pop(self.send_seq, []):
            self._responses.put_nowait(pkt)

    async def receive_packet(self, timeout: float = 5.0) -> bytes:
        try:
            return await asyncio.wait_for(self._responses.get(), timeout=timeout)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError()

    def queue_response(self, data: bytes) -> None:
        self._responses.put_nowait(data)

    def queue_response_on_send(self, send_number: int, data: bytes) -> None:
        """Queue a response to be released after N-th send_tracked() call.

        Useful for tests where one high-level API call sends multiple CI-V commands
        and each command should receive its own response in-order.
        """
        self._responses_by_send.setdefault(send_number, []).append(data)

    @property
    def _raw_send(self):
        return lambda data: self.sent_packets.append(data)

    @_raw_send.setter
    def _raw_send(self, value):
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_transport() -> MockTransport:
    return MockTransport()


@pytest.fixture
def radio(mock_transport: MockTransport) -> IcomRadio:
    r = IcomRadio("192.168.1.100")
    r._civ_transport = mock_transport
    r._ctrl_transport = mock_transport
    r._connected = True
    return r


class TestContextManager:
    """Test connect/disconnect lifecycle with mocked transport."""

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_transport: MockTransport) -> None:
        radio = IcomRadio("192.168.1.100")
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True

        await radio.disconnect()
        assert not radio.connected
        assert mock_transport.disconnected

    @pytest.mark.asyncio
    async def test_context_manager_exit(self, mock_transport: MockTransport) -> None:
        radio = IcomRadio("192.168.1.100")
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True

        # __aenter__ calls connect() which redoes handshake;
        # test __aexit__ path directly instead
        assert radio.connected
        await radio.__aexit__(None, None, None)
        assert not radio.connected


class TestFrequency:
    """Test frequency get/set."""

    @pytest.mark.asyncio
    async def test_get_frequency(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_freq_response(14_074_000))
        freq = await radio.get_frequency()
        assert freq == 14_074_000

    @pytest.mark.asyncio
    async def test_set_frequency(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_frequency(7_074_000)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_frequency_nak(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.set_frequency(999_999_999)


class TestMode:
    """Test mode get/set."""

    @pytest.mark.asyncio
    async def test_get_mode(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_mode_response(Mode.USB))
        mode = await radio.get_mode()
        assert mode == Mode.USB

    @pytest.mark.asyncio
    async def test_set_mode(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_mode(Mode.LSB)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_mode_from_string(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_mode("USB")
        assert len(mock_transport.sent_packets) > 0


class TestMeters:
    """Test meter readings."""

    @pytest.mark.asyncio
    async def test_get_s_meter(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_meter_response(_SUB_S_METER, 120))
        val = await radio.get_s_meter()
        assert val == 120

    @pytest.mark.asyncio
    async def test_get_swr(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_meter_response(_SUB_SWR_METER, 50))
        val = await radio.get_swr()
        assert val == 50

    @pytest.mark.asyncio
    async def test_get_alc(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_meter_response(_SUB_ALC_METER, 80))
        val = await radio.get_alc()
        assert val == 80


class TestPower:
    """Test power get/set."""

    @pytest.mark.asyncio
    async def test_get_power(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_power_response(128))
        val = await radio.get_power()
        assert val == 128

    @pytest.mark.asyncio
    async def test_set_power(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_power(200)
        assert len(mock_transport.sent_packets) > 0


class TestPtt:
    """Test PTT toggle."""

    @pytest.mark.asyncio
    async def test_set_ptt_on(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_ptt(True)

    @pytest.mark.asyncio
    async def test_set_ptt_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_ptt(False)


class TestTimeout:
    """Test timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_on_no_response(self, mock_transport: MockTransport) -> None:
        radio = IcomRadio("192.168.1.100", timeout=0.1)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        with pytest.raises(TimeoutError):
            await radio.get_frequency()

    @pytest.mark.asyncio
    async def test_deadline_timeout_does_not_always_send_three_attempts(
        self, mock_transport: MockTransport
    ) -> None:
        radio = IcomRadio("192.168.1.100", timeout=0.2)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True

        with pytest.raises(TimeoutError):
            await radio.get_frequency()

        # Deadline-based retries should stop when overall deadline is exhausted.
        assert len(mock_transport.sent_packets) < 3


class TestDisconnected:
    """Test that operations raise when disconnected."""

    @pytest.mark.asyncio
    async def test_get_frequency_disconnected(self) -> None:
        radio = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await radio.get_frequency()

    @pytest.mark.asyncio
    async def test_set_frequency_disconnected(self) -> None:
        radio = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await radio.set_frequency(14_074_000)

    @pytest.mark.asyncio
    async def test_send_civ_disconnected(self) -> None:
        radio = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await radio.send_civ(0x03)


class TestSendCiv:
    """Test low-level CI-V access."""

    @pytest.mark.asyncio
    async def test_send_civ(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_freq_response(14_074_000))
        frame = await radio.send_civ(0x03)
        assert frame.command == _CMD_FREQ_GET


class TestConnectedProperty:
    """Test connected property."""

    def test_initially_disconnected(self) -> None:
        radio = IcomRadio("192.168.1.100")
        assert not radio.connected


class TestAckSinkRobustness:
    """Regression tests for fire-and-forget ACK sink behavior."""

    @pytest.mark.asyncio
    async def test_fire_and_forget_missing_ack_does_not_poison_next_ack(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        # Fire-and-forget scope enable (ACK intentionally missing)
        ff = build_civ_frame(IC_7610_ADDR, CONTROLLER_ADDR, 0x27, sub=0x10, data=b"\x01")
        await radio._execute_civ_raw(ff, wait_response=False)

        # Next ACK should satisfy this set command, not a stale sink.
        mock_transport.queue_response_on_send(2, _ack_response())
        await radio.set_frequency(7_074_000)

    @pytest.mark.asyncio
    async def test_fire_and_forget_send_failure_rolls_back_sink(self) -> None:
        class FailingTransport(MockTransport):
            async def send_tracked(self, data: bytes) -> None:  # pragma: no cover - simple stub
                raise OSError("send failed")

        t = FailingTransport()
        radio = IcomRadio("192.168.1.100")
        radio._ctrl_transport = t
        radio._civ_transport = t
        radio._connected = True

        ff = build_civ_frame(IC_7610_ADDR, CONTROLLER_ADDR, 0x27, sub=0x10, data=b"\x01")
        with pytest.raises(OSError):
            await radio._execute_civ_raw(ff, wait_response=False)

        assert radio._civ_request_tracker.pending_count == 0

    @pytest.mark.asyncio
    async def test_cancelled_execute_cleans_pending_waiter(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        cmd = build_civ_frame(IC_7610_ADDR, CONTROLLER_ADDR, 0x03)
        task = asyncio.create_task(radio._execute_civ_raw(cmd))
        await asyncio.sleep(0.01)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert radio._civ_request_tracker.pending_count == 0


class TestScopeCallbackSafety:
    """Scope callback failures must not break command routing."""

    @pytest.mark.asyncio
    async def test_scope_callback_exception_does_not_break_ack_flow(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        def _bad_callback(_frame) -> None:
            raise RuntimeError("boom")

        radio.on_scope_data(_bad_callback)

        scope_payload = bytes(
            [
                0x00,  # receiver
                0x01,  # seq
                0x01,  # seq_max
                0x01,  # mode=fixed
                *bcd_encode(14_000_000),
                *bcd_encode(14_350_000),
                0x00,  # out_of_range
                0x10,  # one pixel
            ]
        )
        scope_frame = build_civ_frame(
            CONTROLLER_ADDR,
            IC_7610_ADDR,
            0x27,
            sub=0x00,
            data=scope_payload,
        )

        mock_transport.queue_response(_wrap_civ_in_udp(scope_frame))
        mock_transport.queue_response(_ack_response())

        cmd = build_civ_frame(
            IC_7610_ADDR,
            CONTROLLER_ADDR,
            0x05,
            data=bcd_encode(14_074_000),
        )
        resp = await radio._execute_civ_raw(cmd)
        assert resp is not None
        assert resp.command == _CMD_ACK

        # RX pump should continue to route subsequent ACK traffic.
        mock_transport.queue_response(_ack_response())
        await radio.set_frequency(7_074_000)


# ---------------------------------------------------------------------------
# set_mode timeout resilience
# ---------------------------------------------------------------------------


class TestSetModeTimeout:
    """set_mode must swallow TimeoutError (known IC-7610 ACK quirk)."""

    @pytest.mark.asyncio
    async def test_set_mode_swallows_icom_timeout(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """When _send_civ_raw raises our TimeoutError, set_mode must not re-raise."""
        with patch.object(
            radio, "_send_civ_raw", side_effect=TimeoutError("no ACK")
        ):
            await radio.set_mode(Mode.USB)  # must not raise
        assert radio._last_mode == Mode.USB

    @pytest.mark.asyncio
    async def test_set_mode_swallows_asyncio_timeout(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """When _send_civ_raw raises asyncio.TimeoutError, set_mode must not re-raise."""
        with patch.object(
            radio, "_send_civ_raw", side_effect=asyncio.TimeoutError()
        ):
            await radio.set_mode(Mode.CW)  # must not raise
        assert radio._last_mode == Mode.CW

    @pytest.mark.asyncio
    async def test_set_mode_ack_received_succeeds(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """When ACK arrives, set_mode completes normally and updates _last_mode."""
        mock_transport.queue_response(_ack_response())
        await radio.set_mode(Mode.LSB)
        assert radio._last_mode == Mode.LSB

    @pytest.mark.asyncio
    async def test_set_mode_string_timeout_swallowed(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """String mode variant also swallows timeout."""
        with patch.object(
            radio, "_send_civ_raw", side_effect=TimeoutError("no ACK")
        ):
            await radio.set_mode("USB")
        assert radio._last_mode == Mode.USB

    @pytest.mark.asyncio
    async def test_set_mode_does_not_swallow_command_error(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """CommandError (NAK from radio) must still propagate."""
        from icom_lan.exceptions import CommandError

        with patch.object(
            radio, "_send_civ_raw", side_effect=CommandError("NAK")
        ):
            with pytest.raises(CommandError):
                await radio.set_mode(Mode.USB)
