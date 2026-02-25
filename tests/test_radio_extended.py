"""Extended tests for IcomRadio — VFO, split, attenuator, preamp, CW, power control, audio, disconnected states."""

import pytest

from icom_lan.commands import (
    CONTROLLER_ADDR,
    IC_7610_ADDR,
    build_civ_frame,
    RECEIVER_MAIN,
)
from icom_lan.exceptions import ConnectionError, CommandError
from icom_lan.radio import IcomRadio

# Reuse helpers from test_radio
from test_radio import (
    MockTransport,
    _ack_response,
    _nak_response,
    _wrap_civ_in_udp,
)


def _digisel_off_response() -> bytes:
    """DIGI-SEL response: OFF (0x00) — Command29-wrapped."""
    # Radio responds: FE FE E0 98 29 00 16 4E 00 FD
    civ = build_civ_frame(
        CONTROLLER_ADDR,
        IC_7610_ADDR,
        0x29,
        data=bytes([RECEIVER_MAIN, 0x16, 0x4E, 0x00]),
    )
    return _wrap_civ_in_udp(civ)


# ---------------------------------------------------------------------------
# Fixtures
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


# ---------------------------------------------------------------------------
# VFO tests
# ---------------------------------------------------------------------------


class TestVFO:
    @pytest.mark.asyncio
    async def test_select_vfo_a(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.select_vfo("A")
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_select_vfo_b(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.select_vfo("B")

    @pytest.mark.asyncio
    async def test_select_vfo_main(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.select_vfo("MAIN")

    @pytest.mark.asyncio
    async def test_select_vfo_nak(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.select_vfo("A")

    @pytest.mark.asyncio
    async def test_vfo_equalize(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.vfo_equalize()
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_vfo_exchange(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.vfo_exchange()
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_select_vfo_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.select_vfo("A")

    @pytest.mark.asyncio
    async def test_vfo_equalize_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.vfo_equalize()

    @pytest.mark.asyncio
    async def test_vfo_exchange_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.vfo_exchange()


# ---------------------------------------------------------------------------
# Split mode
# ---------------------------------------------------------------------------


class TestSplitMode:
    @pytest.mark.asyncio
    async def test_split_on(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_split_mode(True)

    @pytest.mark.asyncio
    async def test_split_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_split_mode(False)

    @pytest.mark.asyncio
    async def test_split_nak(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.set_split_mode(True)

    @pytest.mark.asyncio
    async def test_split_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.set_split_mode(True)


# ---------------------------------------------------------------------------
# Attenuator
# ---------------------------------------------------------------------------


class TestAttenuator:
    @pytest.mark.asyncio
    async def test_att_on(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_attenuator(True)

    @pytest.mark.asyncio
    async def test_att_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_attenuator(False)

    @pytest.mark.asyncio
    async def test_att_nak(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.set_attenuator(True)

    @pytest.mark.asyncio
    async def test_att_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.set_attenuator(True)


# ---------------------------------------------------------------------------
# Preamp
# ---------------------------------------------------------------------------


class TestPreamp:
    @pytest.mark.asyncio
    async def test_preamp_on(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(
            _digisel_off_response()
        )  # pre-flight DIGI-SEL check
        mock_transport.queue_response(_ack_response())
        await radio.set_preamp(1)

    @pytest.mark.asyncio
    async def test_preamp_level2(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(
            _digisel_off_response()
        )  # pre-flight DIGI-SEL check
        mock_transport.queue_response(_ack_response())
        await radio.set_preamp(2)

    @pytest.mark.asyncio
    async def test_preamp_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        # level=0 skips DIGI-SEL check
        mock_transport.queue_response(_ack_response())
        await radio.set_preamp(0)

    @pytest.mark.asyncio
    async def test_preamp_nak(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(
            _digisel_off_response()
        )  # pre-flight DIGI-SEL check
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.set_preamp(1)

    @pytest.mark.asyncio
    async def test_preamp_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.set_preamp(1)


# ---------------------------------------------------------------------------
# CW keying
# ---------------------------------------------------------------------------


class TestCW:
    @pytest.mark.asyncio
    async def test_send_cw_text(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.send_cw_text("CQ")
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_send_cw_long_text(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """Text longer than 30 chars should produce multiple frames."""
        text = "A" * 60  # 2 chunks
        mock_transport.queue_response(_ack_response())
        mock_transport.queue_response(_ack_response())
        await radio.send_cw_text(text)
        assert len(mock_transport.sent_packets) == 2

    @pytest.mark.asyncio
    async def test_send_cw_nak(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.send_cw_text("CQ")

    @pytest.mark.asyncio
    async def test_stop_cw(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.stop_cw_text()

    @pytest.mark.asyncio
    async def test_cw_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.send_cw_text("CQ")

    @pytest.mark.asyncio
    async def test_stop_cw_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.stop_cw_text()


# ---------------------------------------------------------------------------
# Power control
# ---------------------------------------------------------------------------


class TestPowerControl:
    @pytest.mark.asyncio
    async def test_power_on(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.power_control(True)

    @pytest.mark.asyncio
    async def test_power_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.power_control(False)

    @pytest.mark.asyncio
    async def test_power_nak(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.power_control(True)

    @pytest.mark.asyncio
    async def test_power_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.power_control(True)


# ---------------------------------------------------------------------------
# Audio (disconnected / error paths)
# ---------------------------------------------------------------------------


class TestAudio:
    @pytest.mark.asyncio
    async def test_start_rx_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.start_audio_rx(lambda pkt: None)

    @pytest.mark.asyncio
    async def test_start_tx_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.start_audio_tx()

    @pytest.mark.asyncio
    async def test_push_tx_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.push_audio_tx(b"\x00" * 100)

    @pytest.mark.asyncio
    async def test_push_tx_not_started(self, radio: IcomRadio) -> None:
        with pytest.raises(RuntimeError, match="Audio TX not started"):
            await radio.push_audio_tx(b"\x00" * 100)

    @pytest.mark.asyncio
    async def test_no_audio_port(self, radio: IcomRadio) -> None:
        radio._audio_port = 0
        with pytest.raises(ConnectionError, match="Audio port not available"):
            await radio.start_audio_rx(lambda pkt: None)

    @pytest.mark.asyncio
    async def test_stop_rx_noop_when_no_stream(self, radio: IcomRadio) -> None:
        await radio.stop_audio_rx()  # should not raise

    @pytest.mark.asyncio
    async def test_stop_tx_noop_when_no_stream(self, radio: IcomRadio) -> None:
        await radio.stop_audio_tx()  # should not raise


# ---------------------------------------------------------------------------
# PTT disconnected
# ---------------------------------------------------------------------------


class TestPttDisconnected:
    @pytest.mark.asyncio
    async def test_set_ptt_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.set_ptt(True)

    @pytest.mark.asyncio
    async def test_ptt_nak(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.set_ptt(True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestInternals:
    def test_check_connected_raises(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            r._check_connected()

    def test_wrap_civ(self, radio: IcomRadio) -> None:
        civ = build_civ_frame(IC_7610_ADDR, CONTROLLER_ADDR, 0x03)
        pkt = radio._wrap_civ(civ)
        assert len(pkt) == 0x15 + len(civ)
        assert pkt[0x10] == 0xC1

    @pytest.mark.asyncio
    async def test_flush_queue_empty(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        count = await IcomRadio._flush_queue(mock_transport)
        assert count == 0

    @pytest.mark.asyncio
    async def test_flush_queue_with_data(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(b"\x00" * 16)
        mock_transport.queue_response(b"\x00" * 16)
        count = await IcomRadio._flush_queue(mock_transport)
        assert count == 2


# ---------------------------------------------------------------------------
# Constructor defaults
# ---------------------------------------------------------------------------


class TestConstructor:
    def test_defaults(self) -> None:
        r = IcomRadio("10.0.0.1")
        assert r._host == "10.0.0.1"
        assert r._port == 50001
        assert r._radio_addr == IC_7610_ADDR
        assert r._timeout == 5.0

    def test_custom_params(self) -> None:
        r = IcomRadio(
            "10.0.0.2",
            port=50002,
            username="u",
            password="p",
            radio_addr=0x94,
            timeout=10.0,
        )
        assert r._host == "10.0.0.2"
        assert r._port == 50002
        assert r._username == "u"
        assert r._password == "p"
        assert r._radio_addr == 0x94
        assert r._timeout == 10.0
