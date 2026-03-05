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
from icom_lan.types import CivFrame, Mode, PacketType, bcd_encode


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
        await radio.set_frequency(7_074_000)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_frequency_no_response_needed(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_frequency is fire-and-forget — completes without any radio response."""
        await radio.set_frequency(14_074_000)
        assert radio._last_freq_hz == 14_074_000


class TestMode:
    """Test mode get/set."""

    @pytest.mark.asyncio
    async def test_get_mode(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_mode_response(Mode.USB))
        mode_name, _filt = await radio.get_mode()
        assert mode_name == "USB"

    @pytest.mark.asyncio
    async def test_set_mode(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        await radio.set_mode(Mode.LSB)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_mode_no_response_needed(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_mode is fire-and-forget — completes without any radio response."""
        await radio.set_mode(Mode.USB)
        assert radio._last_mode == Mode.USB

    @pytest.mark.asyncio
    async def test_set_mode_from_string(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
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
        await radio.set_power(200)
        assert len(mock_transport.sent_packets) > 0


class TestRfGainAfLevel:
    """Test RF Gain and AF Level get/set."""

    @pytest.mark.asyncio
    async def test_set_rf_gain(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        await radio.set_rf_gain(200)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_rf_gain_zero(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        await radio.set_rf_gain(0)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_rf_gain_out_of_range(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        with pytest.raises(ValueError):
            await radio.set_rf_gain(256)
        with pytest.raises(ValueError):
            await radio.set_rf_gain(-1)

    @pytest.mark.asyncio
    async def test_set_af_level(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        await radio.set_af_level(128)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_af_level_zero(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        await radio.set_af_level(0)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_af_level_out_of_range(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        with pytest.raises(ValueError):
            await radio.set_af_level(256)
        with pytest.raises(ValueError):
            await radio.set_af_level(-1)


class TestPtt:
    """Test PTT toggle."""

    @pytest.mark.asyncio
    async def test_set_ptt_on(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_ptt is fire-and-forget — no ACK response needed."""
        await radio.set_ptt(True)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_ptt_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_ptt is fire-and-forget — no ACK response needed."""
        await radio.set_ptt(False)
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_set_ptt_updates_state_cache(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_ptt updates the state cache optimistically."""
        await radio.set_ptt(True)
        assert radio.state_cache.ptt is True
        assert radio.state_cache.ptt_ts > 0.0

        await radio.set_ptt(False)
        assert radio.state_cache.ptt is False


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

        # set_frequency is fire-and-forget — completes without any response.
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

        # set_frequency is fire-and-forget — RX pump unaffected.
        await radio.set_frequency(7_074_000)


# ---------------------------------------------------------------------------
# set_mode fire-and-forget (IC-7610 ACK quirk fix)
# ---------------------------------------------------------------------------


class TestSetModeFireAndForget:
    """set_mode is fire-and-forget — no ACK required, no timeout to swallow."""

    @pytest.mark.asyncio
    async def test_set_mode_no_ack_needed(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_mode completes without queuing any radio response."""
        await radio.set_mode(Mode.USB)  # must not raise
        assert radio._last_mode == Mode.USB

    @pytest.mark.asyncio
    async def test_set_mode_string_no_ack_needed(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """String mode variant also completes without a response."""
        await radio.set_mode("USB")
        assert radio._last_mode == Mode.USB

    @pytest.mark.asyncio
    async def test_set_mode_string_case_insensitive(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        await radio.set_mode(" usb ")
        assert radio._last_mode == Mode.USB

    @pytest.mark.asyncio
    async def test_set_mode_string_invalid_raises_value_error(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        with pytest.raises(ValueError, match="Unknown mode"):
            await radio.set_mode("not-a-mode")

    @pytest.mark.asyncio
    async def test_set_mode_updates_last_mode(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_mode updates _last_mode regardless of radio response."""
        await radio.set_mode(Mode.LSB)
        assert radio._last_mode == Mode.LSB

    @pytest.mark.asyncio
    async def test_set_mode_send_failure_propagates(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """A send-level error (e.g. OSError) still propagates from set_mode."""
        with patch.object(
            radio, "_send_civ_raw", side_effect=OSError("send failed")
        ):
            with pytest.raises(OSError):
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

        # set_frequency is fire-and-forget — succeeds without a response
        await radio.set_frequency(14_074_000)  # must not raise


# ---------------------------------------------------------------------------
# Issue #56: state cache populated from unsolicited CI-V frames
# ---------------------------------------------------------------------------


class TestStateCacheFromUnsolicitedFrames:
    """_update_state_cache_from_frame populates cache from radio-pushed frames."""

    def _make_radio(self) -> IcomRadio:
        radio = IcomRadio("192.168.1.100")
        radio._connected = True
        return radio

    def test_freq_frame_updates_cache(self) -> None:
        """A frequency frame (cmd 0x03) updates the freq cache."""
        radio = self._make_radio()
        assert radio.state_cache.freq_ts == 0.0
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x03,
            data=bcd_encode(14_200_000),
        )
        radio._update_state_cache_from_frame(frame)
        assert radio.state_cache.freq == 14_200_000
        assert radio.state_cache.freq_ts > 0.0

    def test_mode_frame_updates_cache(self) -> None:
        """A mode frame (cmd 0x04) updates the mode cache."""
        radio = self._make_radio()
        assert radio.state_cache.mode_ts == 0.0
        # cmd 0x04: data = [mode_byte, filter_byte]; mode 0x00=LSB, filter 0x01=FIL1
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x04,
            data=bytes([0x00, 0x01]),
        )
        radio._update_state_cache_from_frame(frame)
        assert radio.state_cache.mode == "LSB"
        assert radio.state_cache.filter_width == 1
        assert radio.state_cache.mode_ts > 0.0

    def test_ptt_frame_updates_cache(self) -> None:
        """A PTT frame (cmd 0x1C sub 0x00, data=0x01) updates ptt cache."""
        radio = self._make_radio()
        assert radio.state_cache.ptt_ts == 0.0
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x1C,
            sub=0x00,
            data=bytes([0x01]),
        )
        radio._update_state_cache_from_frame(frame)
        assert radio.state_cache.ptt is True
        assert radio.state_cache.ptt_ts > 0.0

    def test_ptt_off_frame_updates_cache(self) -> None:
        """A PTT frame with data=0x00 clears the ptt cache."""
        radio = self._make_radio()
        radio.state_cache.update_ptt(True)
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x1C,
            sub=0x00,
            data=bytes([0x00]),
        )
        radio._update_state_cache_from_frame(frame)
        assert radio.state_cache.ptt is False

    def test_unknown_frame_is_ignored_safely(self) -> None:
        """Frames with unrecognised commands are silently ignored."""
        radio = self._make_radio()
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0xFF,
            data=b"\x01\x02",
        )
        radio._update_state_cache_from_frame(frame)  # must not raise
        assert radio.state_cache.freq_ts == 0.0


# ---------------------------------------------------------------------------
# Issue #56: GET commands fall back to cache on timeout
# ---------------------------------------------------------------------------


class TestGetFallbackToCache:
    """GET commands return cached values instead of raising on timeout."""

    @pytest.mark.asyncio
    async def test_get_frequency_returns_cache_on_timeout(
        self, mock_transport: MockTransport
    ) -> None:
        """get_frequency returns cached freq when radio is silent."""
        radio = IcomRadio("192.168.1.100", timeout=0.05)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio.state_cache.update_freq(7_200_000)

        freq = await radio.get_frequency()
        assert freq == 7_200_000

    @pytest.mark.asyncio
    async def test_get_frequency_raises_when_cache_empty(
        self, mock_transport: MockTransport
    ) -> None:
        """get_frequency raises TimeoutError when cache is empty and radio is silent."""
        radio = IcomRadio("192.168.1.100", timeout=0.05)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True

        with pytest.raises(TimeoutError):
            await radio.get_frequency()

    @pytest.mark.asyncio
    async def test_get_mode_info_returns_cache_on_timeout(
        self, mock_transport: MockTransport
    ) -> None:
        """get_mode_info returns cached mode/filter when radio is silent."""
        radio = IcomRadio("192.168.1.100", timeout=0.05)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio.state_cache.update_mode("CW", 2)

        mode, filt = await radio.get_mode_info()
        assert mode == Mode.CW
        assert filt == 2

    @pytest.mark.asyncio
    async def test_get_mode_info_raises_when_cache_empty(
        self, mock_transport: MockTransport
    ) -> None:
        """get_mode_info raises TimeoutError when cache is empty and radio is silent."""
        radio = IcomRadio("192.168.1.100", timeout=0.05)
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True

        with pytest.raises(TimeoutError):
            await radio.get_mode_info()


# ---------------------------------------------------------------------------
# Issue #63: GET fallbacks respect cache TTL
# ---------------------------------------------------------------------------


class TestGetFallbackCacheTTL:
    """GET commands raise TimeoutError when cache is stale (exceeds TTL)."""

    @pytest.mark.asyncio
    async def test_get_frequency_raises_when_cache_stale(
        self, mock_transport: MockTransport
    ) -> None:
        """get_frequency raises TimeoutError when cached value is older than TTL."""
        radio = IcomRadio("192.168.1.100", timeout=0.05, cache_ttl_s={"freq": 10.0})
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio.state_cache.update_freq(7_200_000)
        # Back-date to make it stale
        radio.state_cache.freq_ts = radio.state_cache.freq_ts - 20.0

        with pytest.raises(TimeoutError):
            await radio.get_frequency()

    @pytest.mark.asyncio
    async def test_get_frequency_returns_cache_within_ttl(
        self, mock_transport: MockTransport
    ) -> None:
        """get_frequency returns cached value when it is within TTL."""
        radio = IcomRadio("192.168.1.100", timeout=0.05, cache_ttl_s={"freq": 10.0})
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio.state_cache.update_freq(7_200_000)

        freq = await radio.get_frequency()
        assert freq == 7_200_000

    @pytest.mark.asyncio
    async def test_get_mode_info_raises_when_cache_stale(
        self, mock_transport: MockTransport
    ) -> None:
        """get_mode_info raises TimeoutError when cached value is older than TTL."""
        radio = IcomRadio("192.168.1.100", timeout=0.05, cache_ttl_s={"mode": 10.0})
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio.state_cache.update_mode("CW", 2)
        radio.state_cache.mode_ts = radio.state_cache.mode_ts - 20.0

        with pytest.raises(TimeoutError):
            await radio.get_mode_info()

    @pytest.mark.asyncio
    async def test_get_mode_info_returns_cache_within_ttl(
        self, mock_transport: MockTransport
    ) -> None:
        """get_mode_info returns cached value when it is within TTL."""
        radio = IcomRadio("192.168.1.100", timeout=0.05, cache_ttl_s={"mode": 10.0})
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio.state_cache.update_mode("CW", 2)

        mode, filt = await radio.get_mode_info()
        assert mode == Mode.CW
        assert filt == 2

    @pytest.mark.asyncio
    async def test_get_power_raises_when_cache_stale(
        self, mock_transport: MockTransport
    ) -> None:
        """get_power raises TimeoutError when cached value is older than TTL."""
        radio = IcomRadio("192.168.1.100", timeout=0.05, cache_ttl_s={"rf_power": 30.0})
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio.state_cache.update_rf_power(128 / 255.0)
        radio.state_cache.rf_power_ts = radio.state_cache.rf_power_ts - 60.0

        with pytest.raises(TimeoutError):
            await radio.get_power()

    @pytest.mark.asyncio
    async def test_get_power_returns_cache_within_ttl(
        self, mock_transport: MockTransport
    ) -> None:
        """get_power returns cached value when it is within TTL."""
        radio = IcomRadio("192.168.1.100", timeout=0.05, cache_ttl_s={"rf_power": 30.0})
        radio._ctrl_transport = mock_transport
        radio._civ_transport = mock_transport
        radio._connected = True
        radio.state_cache.update_rf_power(128 / 255.0)

        level = await radio.get_power()
        assert level == 128

    @pytest.mark.asyncio
    async def test_cache_ttl_s_overrides_default_per_field(
        self, mock_transport: MockTransport
    ) -> None:
        """cache_ttl_s merges with defaults, overriding individual fields."""
        # Only override freq TTL; mode/rf_power keep defaults.
        radio = IcomRadio("192.168.1.100", timeout=0.05, cache_ttl_s={"freq": 1.0})
        assert radio._cache_ttl_freq == 1.0
        assert radio._cache_ttl_mode == 10.0
        assert radio._cache_ttl_rf_power == 30.0


# ---------------------------------------------------------------------------
# Issue #56: SET commands update the state cache optimistically
# ---------------------------------------------------------------------------


class TestSetCommandsUpdateCache:
    """SET commands update the state cache without waiting for ACK."""

    @pytest.mark.asyncio
    async def test_set_frequency_updates_state_cache(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_frequency updates the frequency cache immediately."""
        await radio.set_frequency(21_074_000)
        assert radio.state_cache.freq == 21_074_000
        assert radio.state_cache.freq_ts > 0.0

    @pytest.mark.asyncio
    async def test_set_mode_updates_state_cache(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_mode updates the mode cache immediately."""
        await radio.set_mode(Mode.CW)
        assert radio.state_cache.mode == "CW"
        assert radio.state_cache.mode_ts > 0.0

    @pytest.mark.asyncio
    async def test_rapid_set_frequency_does_not_block(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """Rapid consecutive set_frequency calls are all fire-and-forget."""
        for freq in [7_000_000, 7_100_000, 7_200_000]:
            await radio.set_frequency(freq)
        # Cache holds the last value sent.
        assert radio.state_cache.freq == 7_200_000
