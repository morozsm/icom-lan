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
        # Fire-and-forget: no ACK response needed
        await radio.set_frequency(7_074_000)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_frequency_fire_and_forget(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_frequency is fire-and-forget: no ACK/NAK wait, completes fast."""
        # No response queued — must complete without blocking.
        await radio.set_frequency(14_074_000)
        assert len(mock_transport.sent_packets) > 0
        # Optimistic cache update.
        assert radio._state_cache.get("freq") == 14_074_000


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
        # Fire-and-forget: no ACK response needed
        await radio.set_mode(Mode.LSB)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_mode_from_string(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        # Fire-and-forget: no ACK response needed
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
        # Fire-and-forget: no ACK response needed
        await radio.set_power(200)
        assert len(mock_transport.sent_packets) > 0


class TestPtt:
    """Test PTT toggle."""

    @pytest.mark.asyncio
    async def test_set_ptt_on(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        # Fire-and-forget: no ACK response needed
        await radio.set_ptt(True)
        assert radio._state_cache.get("ptt") is True

    @pytest.mark.asyncio
    async def test_set_ptt_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        # Fire-and-forget: no ACK response needed
        await radio.set_ptt(False)
        assert radio._state_cache.get("ptt") is False


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
    async def test_fire_and_forget_multiple_sinks_do_not_stack(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """Multiple fire-and-forget commands must all complete without exception."""
        # scope enable: fire-and-forget (ACK intentionally missing)
        ff = build_civ_frame(IC_7610_ADDR, CONTROLLER_ADDR, 0x27, sub=0x10, data=b"\x01")
        await radio._execute_civ_raw(ff, wait_response=False)

        # set_frequency: also fire-and-forget — must not block waiting for ACK
        await radio.set_frequency(7_074_000)
        assert radio._state_cache.get("freq") == 7_074_000

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

        # set_frequency is now fire-and-forget: no ACK response needed.
        await radio.set_frequency(7_074_000)
        assert radio._state_cache.get("freq") == 7_074_000


# ---------------------------------------------------------------------------
# set_mode timeout resilience
# ---------------------------------------------------------------------------


class TestSetModeTimeout:
    """set_mode is now fire-and-forget — no ACK wait, no timeout to swallow."""

    @pytest.mark.asyncio
    async def test_set_mode_completes_without_ack(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_mode completes immediately without queuing any response."""
        # No response queued — fire-and-forget must complete without blocking.
        await radio.set_mode(Mode.USB)
        assert radio._last_mode == Mode.USB
        assert radio._state_cache.get("mode") == Mode.USB

    @pytest.mark.asyncio
    async def test_set_mode_string_completes_without_ack(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """String mode variant also completes fire-and-forget."""
        await radio.set_mode("CW")
        assert radio._last_mode == Mode.CW

    @pytest.mark.asyncio
    async def test_set_mode_with_filter_updates_cache(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_mode with filter_width updates state cache optimistically."""
        await radio.set_mode(Mode.LSB, filter_width=2)
        assert radio._last_mode == Mode.LSB
        assert radio._state_cache.get("mode") == Mode.LSB
        assert radio._state_cache.get("filter") == 2

    @pytest.mark.asyncio
    async def test_set_mode_does_not_swallow_transport_error(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """Transport-layer errors (not ACK timeout) still propagate."""
        from icom_lan.exceptions import CommandError

        with patch.object(
            radio, "_send_civ_raw", side_effect=CommandError("NAK")
        ):
            with pytest.raises(CommandError):
                await radio.set_mode(Mode.USB)


# ---------------------------------------------------------------------------
# #48 regression: CI-V timeout isolation
# ---------------------------------------------------------------------------


class TestCivTimeoutIsolation:
    """A CI-V timeout must not corrupt state for subsequent commands (#48)."""

    @pytest.mark.asyncio
    async def test_timeout_does_not_affect_subsequent_command(
        self, mock_transport: MockTransport
    ) -> None:
        """After a CI-V timeout, the next command must succeed independently."""
        radio = IcomRadio("192.168.1.100", timeout=0.1)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True

        # First command: no response → times out
        with pytest.raises(TimeoutError):
            await radio.get_frequency()

        # Tracker must be clean — no stale waiters
        assert radio._civ_request_tracker.pending_count == 0

        # Second command: queue response before calling
        mock_transport.queue_response(_freq_response(7_074_000))
        freq = await radio.get_frequency()
        assert freq == 7_074_000

    @pytest.mark.asyncio
    async def test_multiple_timeouts_followed_by_success(
        self, mock_transport: MockTransport
    ) -> None:
        """Multiple consecutive timeouts do not corrupt tracker state."""
        radio = IcomRadio("192.168.1.100", timeout=0.1)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True

        # Two timeouts in a row
        for _ in range(2):
            with pytest.raises(TimeoutError):
                await radio.get_frequency()

        assert radio._civ_request_tracker.pending_count == 0

        # Then a successful command
        mock_transport.queue_response(_freq_response(14_074_000))
        freq = await radio.get_frequency()
        assert freq == 14_074_000

    @pytest.mark.asyncio
    async def test_timeout_then_different_command_succeeds(
        self, mock_transport: MockTransport
    ) -> None:
        """A timeout on get_frequency does not block a subsequent set_frequency."""
        radio = IcomRadio("192.168.1.100", timeout=0.1)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True

        # get_frequency times out
        with pytest.raises(TimeoutError):
            await radio.get_frequency()

        assert radio._civ_request_tracker.pending_count == 0

        # set_frequency is now fire-and-forget — no ACK needed, must not raise
        await radio.set_frequency(14_074_000)


# ---------------------------------------------------------------------------
# New tests: fire-and-forget, cache fallback, dedupe, unsolicited frames
# ---------------------------------------------------------------------------


class TestFireAndForget:
    """SET commands complete in <50ms and update state cache optimistically."""

    @pytest.mark.asyncio
    async def test_set_frequency_no_response_needed(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_frequency returns without queuing any response."""
        import time

        t0 = time.monotonic()
        await radio.set_frequency(14_200_000)
        elapsed = time.monotonic() - t0

        assert elapsed < 0.05, f"set_frequency took {elapsed:.3f}s (>50ms)"
        assert len(mock_transport.sent_packets) > 0
        assert radio._state_cache.get("freq") == 14_200_000
        assert radio._last_freq_hz == 14_200_000

    @pytest.mark.asyncio
    async def test_set_power_no_response_needed(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_power returns without waiting for ACK."""
        await radio.set_power(128)
        assert radio._state_cache.get("power") == 128
        assert radio._last_power == 128

    @pytest.mark.asyncio
    async def test_set_ptt_updates_cache(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_ptt updates state cache optimistically."""
        await radio.set_ptt(True)
        assert radio._state_cache.get("ptt") is True
        await radio.set_ptt(False)
        assert radio._state_cache.get("ptt") is False

    @pytest.mark.asyncio
    async def test_set_mode_updates_cache(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_mode updates mode and filter in state cache."""
        await radio.set_mode(Mode.CW, filter_width=2)
        assert radio._state_cache.get("mode") == Mode.CW
        assert radio._state_cache.get("filter") == 2

    @pytest.mark.asyncio
    async def test_set_frequency_packet_sent(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_frequency sends the CI-V packet."""
        await radio.set_frequency(7_074_000)
        assert len(mock_transport.sent_packets) == 1


class TestStateCache:
    """State cache is updated from both SET commands and unsolicited frames."""

    @pytest.mark.asyncio
    async def test_get_frequency_falls_back_to_cache_on_timeout(
        self, mock_transport: MockTransport
    ) -> None:
        """get_frequency returns cached value when radio doesn't respond."""
        radio = IcomRadio("192.168.1.100", timeout=0.1)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio._state_cache["freq"] = 14_074_000

        # No response queued → times out → returns cached value
        freq = await radio.get_frequency()
        assert freq == 14_074_000

    @pytest.mark.asyncio
    async def test_get_mode_falls_back_to_cache_on_timeout(
        self, mock_transport: MockTransport
    ) -> None:
        """get_mode_info returns cached mode when radio doesn't respond."""
        radio = IcomRadio("192.168.1.100", timeout=0.1)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio._state_cache["mode"] = Mode.USB
        radio._state_cache["filter"] = 2

        mode, filt = await radio.get_mode_info()
        assert mode == Mode.USB
        assert filt == 2

    @pytest.mark.asyncio
    async def test_get_power_falls_back_to_cache_on_timeout(
        self, mock_transport: MockTransport
    ) -> None:
        """get_power returns cached power when radio doesn't respond."""
        radio = IcomRadio("192.168.1.100", timeout=0.1)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio._state_cache["power"] = 200

        power = await radio.get_power()
        assert power == 200

    @pytest.mark.asyncio
    async def test_get_frequency_raises_when_cache_empty(
        self, mock_transport: MockTransport
    ) -> None:
        """get_frequency raises TimeoutError when cache is empty too."""
        radio = IcomRadio("192.168.1.100", timeout=0.1)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        # Empty cache

        with pytest.raises(TimeoutError):
            await radio.get_frequency()

    @pytest.mark.asyncio
    async def test_unsolicited_frequency_frame_updates_cache(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """Unsolicited CI-V frame (radio knob turn) updates state cache.

        Strategy: first do a blocking get_frequency to start the RX pump,
        then queue an unsolicited 0x00 frame and yield control so the RX
        loop can process it.
        """
        # Seed cache via a real frequency query
        mock_transport.queue_response(_freq_response(14_074_000))
        await radio._execute_civ_raw(
            build_civ_frame(IC_7610_ADDR, CONTROLLER_ADDR, 0x03)
        )
        assert radio._state_cache.get("freq") == 14_074_000

        # Now queue an unsolicited 0x00 frame (knob turn → new freq)
        freq_data = bcd_encode(14_250_000)
        unsol = build_civ_frame(CONTROLLER_ADDR, IC_7610_ADDR, 0x00, data=freq_data)
        mock_transport.queue_response(_wrap_civ_in_udp(unsol))

        # Yield control so the RX loop can consume the queued packet
        await asyncio.sleep(0.05)

        assert radio._state_cache.get("freq") == 14_250_000

    @pytest.mark.asyncio
    async def test_unsolicited_mode_frame_updates_cache(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """Unsolicited mode CI-V frame (radio knob turn) updates mode in cache."""
        # Seed cache via a real mode query first
        mock_transport.queue_response(_mode_response(Mode.USB, filt=1))
        await radio._execute_civ_raw(
            build_civ_frame(IC_7610_ADDR, CONTROLLER_ADDR, 0x04)
        )
        assert radio._state_cache.get("mode") == Mode.USB

        # Queue unsolicited 0x01 mode update frame
        unsol = build_civ_frame(
            CONTROLLER_ADDR, IC_7610_ADDR, 0x01, data=bytes([Mode.CW, 0x01])
        )
        mock_transport.queue_response(_wrap_civ_in_udp(unsol))
        await asyncio.sleep(0.05)

        assert radio._state_cache.get("mode") == Mode.CW

    @pytest.mark.asyncio
    async def test_state_cache_property_returns_copy(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """state_cache property returns a snapshot copy, not a live reference."""
        radio._state_cache["freq"] = 14_000_000
        cache1 = radio.state_cache
        radio._state_cache["freq"] = 7_000_000
        cache2 = radio.state_cache

        assert cache1["freq"] == 14_000_000
        assert cache2["freq"] == 7_000_000


class TestRapidDedupe:
    """Rapid SET commands: latest value wins via commander replace mechanism."""

    @pytest.mark.asyncio
    async def test_rapid_set_frequency_latest_wins(self) -> None:
        """When many set_frequency calls arrive rapidly, only the latest is sent."""
        sent: list[bytes] = []
        pause = asyncio.Event()

        async def execute(cmd: bytes, wait_response: bool = True) -> None:
            sent.append(cmd)
            await pause.wait()  # stall so queue builds up
            return None  # type: ignore[return-value]

        from icom_lan.commander import IcomCommander, Priority

        c = IcomCommander(execute, min_interval=0.0)
        c.start()
        try:
            # First call blocks the worker (paused)
            t1 = asyncio.create_task(c.send(b"freq1", wait_response=False, key="set_freq", replace=True))
            await asyncio.sleep(0.005)  # let worker start on freq1

            # Rapid subsequent calls — each replaces the previous in queue
            t2 = asyncio.create_task(c.send(b"freq2", wait_response=False, key="set_freq", replace=True))
            t3 = asyncio.create_task(c.send(b"freq3", wait_response=False, key="set_freq", replace=True))
            t4 = asyncio.create_task(c.send(b"freq4", wait_response=False, key="set_freq", replace=True))

            # t2, t3 get replaced by later calls → their futures resolve immediately
            await asyncio.sleep(0.01)
            pause.set()  # unblock worker

            await asyncio.gather(t1, t2, t3, t4, return_exceptions=True)
        finally:
            await c.stop()

        # freq1 was already being executed when freq2 arrived
        # freq2 and freq3 were replaced by freq3 and freq4 respectively
        # So we expect freq1 (in flight) + freq4 (latest queued)
        assert b"freq1" in sent
        assert b"freq4" in sent
        # freq2 and freq3 should NOT have been sent (replaced)
        assert b"freq2" not in sent
        assert b"freq3" not in sent

    @pytest.mark.asyncio
    async def test_replace_resolves_old_future_with_none(self) -> None:
        """When a command is replaced, the old future resolves to None (no error)."""
        pause = asyncio.Event()

        async def execute(cmd: bytes, wait_response: bool = True) -> None:
            await pause.wait()
            return None  # type: ignore[return-value]

        from icom_lan.commander import IcomCommander

        c = IcomCommander(execute, min_interval=0.0)
        c.start()
        try:
            t1 = asyncio.create_task(c.send(b"old", wait_response=False, key="k", replace=True))
            await asyncio.sleep(0.005)  # queue t1

            # t2 replaces t1 in the queue; t1's future resolves with None
            t2 = asyncio.create_task(c.send(b"new", wait_response=False, key="k", replace=True))
            await asyncio.sleep(0.005)

            pause.set()
            result1 = await asyncio.wait_for(t1, timeout=0.5)
            result2 = await asyncio.wait_for(t2, timeout=0.5)

            # t1 was replaced → resolved with None (no exception)
            assert result1 is None
            # t2 was executed → also None (fire-and-forget)
            assert result2 is None
        finally:
            await c.stop()
