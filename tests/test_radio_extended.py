"""Extended tests for IcomRadio — VFO, split, attenuator, preamp, CW, power control, audio, disconnected states."""

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from icom_lan import IC_7610_ADDR
from icom_lan.commands import CONTROLLER_ADDR, build_civ_frame
from icom_lan.commander import Priority
from icom_lan.exceptions import ConnectionError, CommandError
from icom_lan.radio import IcomRadio
from icom_lan.types import CivFrame, Mode, bcd_encode

# Reuse helpers from test_radio
from test_radio import (
    MockTransport,
    _ack_response,
    _nak_response,
    _wrap_civ_in_udp,
)


def _digisel_off_response() -> bytes:
    # Radio responds: FE FE E0 98 29 00 16 4E 00 FD
    civ = bytes.fromhex("fefee0982900164e00fd")
    return _wrap_civ_in_udp(civ)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_transport() -> MockTransport:
    return MockTransport()


@pytest.fixture
def radio(mock_transport: MockTransport) -> IcomRadio:
    r = IcomRadio("192.168.1.100", timeout=0.05)
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
        await radio.set_vfo("A")
        assert len(mock_transport.sent_packets) > 0

    @pytest.mark.asyncio
    async def test_select_vfo_b(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_vfo("B")

    @pytest.mark.asyncio
    async def test_select_vfo_main(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_vfo("MAIN")

    @pytest.mark.asyncio
    async def test_select_vfo_nak(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.set_vfo("A")

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
            await r.set_vfo("A")

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
        await radio.set_split(True)

    @pytest.mark.asyncio
    async def test_split_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_ack_response())
        await radio.set_split(False)

    @pytest.mark.asyncio
    async def test_split_nak(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.set_split(True)

    @pytest.mark.asyncio
    async def test_split_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.set_split(True)

    @pytest.mark.asyncio
    async def test_set_split_mode_deprecation(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """``set_split_mode`` still works but emits a DeprecationWarning."""
        mock_transport.queue_response(_ack_response())
        with pytest.warns(DeprecationWarning, match="set_split_mode"):
            await radio.set_split_mode(True)
        assert radio._last_split is True

    @pytest.mark.asyncio
    async def test_get_split_round_trip(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """``set_split(True)`` followed by ``get_split()`` returns True."""
        # Set: ACK
        mock_transport.queue_response(_ack_response())
        await radio.set_split(True)
        # Get: radio responds with cmd 0x0F + data byte 0x01
        civ = build_civ_frame(CONTROLLER_ADDR, IC_7610_ADDR, 0x0F, data=b"\x01")
        mock_transport.queue_response(_wrap_civ_in_udp(civ))
        assert await radio.get_split() is True

    @pytest.mark.asyncio
    async def test_get_split_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        civ = build_civ_frame(CONTROLLER_ADDR, IC_7610_ADDR, 0x0F, data=b"\x00")
        mock_transport.queue_response(_wrap_civ_in_udp(civ))
        assert await radio.get_split() is False


# ---------------------------------------------------------------------------
# Attenuator
# ---------------------------------------------------------------------------


class TestAttenuator:
    @pytest.mark.asyncio
    async def test_att_on(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        await radio.set_attenuator(True)
        assert radio._attenuator_state is True

    @pytest.mark.asyncio
    async def test_att_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        await radio.set_attenuator(False)
        assert radio._attenuator_state is False

    @pytest.mark.asyncio
    async def test_att_no_response_needed(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_attenuator is fire-and-forget — completes without a radio response."""
        await radio.set_attenuator(True)  # must not raise

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
        )  # pre-flight DIGI-SEL check (send #1)
        # set_preamp is fire-and-forget — no ACK needed
        await radio.set_preamp(1)
        assert radio._preamp_level == 1

    @pytest.mark.asyncio
    async def test_preamp_level2(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(
            _digisel_off_response()
        )  # pre-flight DIGI-SEL check (send #1)
        # set_preamp is fire-and-forget — no ACK needed
        await radio.set_preamp(2)
        assert radio._preamp_level == 2

    @pytest.mark.asyncio
    async def test_preamp_off(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        # level=0 skips DIGI-SEL check; fire-and-forget, no response needed
        await radio.set_preamp(0)
        assert radio._preamp_level == 0

    @pytest.mark.asyncio
    async def test_preamp_no_response_needed(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_preamp is fire-and-forget — completes without a radio response."""
        mock_transport.queue_response(
            _digisel_off_response()
        )  # pre-flight DIGI-SEL check still awaits response
        await radio.set_preamp(1)  # must not raise

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
        mock_transport.queue_response(_ack_response())  # ACK for chunk #1 (send #1)
        mock_transport.queue_response_on_send(
            2, _ack_response()
        )  # ACK for chunk #2 (send #2)
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


# ---------------------------------------------------------------------------
# Receiver-aware contract / fallback routing
# ---------------------------------------------------------------------------


class TestReceiverAwareContract:
    @pytest.mark.asyncio
    async def test_get_frequency_receiver_sub_uses_cmd25(
        self, radio: IcomRadio
    ) -> None:
        expected = 7_074_000
        radio._send_civ_raw = AsyncMock(  # type: ignore[method-assign]
            return_value=CivFrame(
                to_addr=CONTROLLER_ADDR,
                from_addr=IC_7610_ADDR,
                command=0x25,
                sub=None,
                data=bytes([0x01]) + bcd_encode(expected),
            )
        )

        got = await radio.get_freq(receiver=1)

        assert got == expected

    @pytest.mark.asyncio
    async def test_get_mode_receiver_sub_uses_cmd26(self, radio: IcomRadio) -> None:
        radio._send_civ_raw = AsyncMock(  # type: ignore[method-assign]
            return_value=CivFrame(
                to_addr=CONTROLLER_ADDR,
                from_addr=IC_7610_ADDR,
                command=0x26,
                sub=None,
                data=bytes([0x01, Mode.LSB, 0x00, 2]),
            )
        )

        mode_name, filt = await radio.get_mode(receiver=1)

        assert mode_name == "LSB"
        assert filt == 2

    @pytest.mark.asyncio
    async def test_set_frequency_receiver_sub_uses_vfo_fallback(
        self, radio: IcomRadio
    ) -> None:
        radio.set_vfo = AsyncMock()  # type: ignore[method-assign]
        radio._send_civ_raw = AsyncMock(return_value=None)  # type: ignore[method-assign]

        await radio.set_freq(14_074_000, receiver=1)

        radio.set_vfo.assert_has_awaits([call("SUB"), call("MAIN")])
        radio._send_civ_raw.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_mode_receiver_sub_uses_vfo_fallback(
        self, radio: IcomRadio
    ) -> None:
        radio.set_vfo = AsyncMock()  # type: ignore[method-assign]
        radio._send_civ_raw = AsyncMock(return_value=None)  # type: ignore[method-assign]

        await radio.set_mode("USB", receiver=1)

        radio.set_vfo.assert_has_awaits([call("SUB"), call("MAIN")])
        radio._send_civ_raw.assert_awaited_once()

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
    async def test_power_on_nak_tolerated(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """Power ON with NAK is tolerated (IC-7610 may NAK while booting)."""
        mock_transport.queue_response(_nak_response())
        # Should NOT raise — power-on NAK is logged but not fatal
        await radio.power_control(True)

    @pytest.mark.asyncio
    async def test_power_off_nak_raises(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """Power OFF with NAK should still raise."""
        mock_transport.queue_response(_nak_response())
        with pytest.raises(CommandError):
            await radio.power_control(False)

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
    async def test_start_audio_rx_alias_warns_and_calls_opus(
        self, radio: IcomRadio
    ) -> None:
        radio._audio_stream = MagicMock()
        radio._audio_stream.start_rx = AsyncMock()

        with pytest.warns(DeprecationWarning, match="start_audio_rx_opus"):
            await radio.start_audio_rx(lambda pkt: None)

        radio._audio_stream.start_rx.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_push_audio_tx_alias_warns_and_calls_opus(
        self, radio: IcomRadio
    ) -> None:
        radio._audio_stream = MagicMock()
        radio._audio_stream.push_tx = AsyncMock()

        with pytest.warns(DeprecationWarning, match="push_audio_tx_opus"):
            await radio.push_audio_tx(b"\x00" * 10)

        radio._audio_stream.push_tx.assert_awaited_once_with(b"\x00" * 10)

    @pytest.mark.asyncio
    async def test_start_audio_alias_warns_and_calls_opus(
        self, radio: IcomRadio
    ) -> None:
        radio._audio_stream = MagicMock()
        radio._audio_stream.start_rx = AsyncMock()
        radio._audio_stream.start_tx = AsyncMock()

        with pytest.warns(DeprecationWarning, match="start_audio_opus"):
            await radio.start_audio(lambda pkt: None, tx_enabled=True)

        radio._audio_stream.start_rx.assert_awaited_once()
        radio._audio_stream.start_tx.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_rx_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.start_audio_rx_opus(lambda pkt: None)

    @pytest.mark.asyncio
    async def test_start_tx_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.start_audio_tx_opus()

    @pytest.mark.asyncio
    async def test_push_tx_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.push_audio_tx_opus(b"\x00" * 100)

    @pytest.mark.asyncio
    async def test_push_tx_not_started(self, radio: IcomRadio) -> None:
        with pytest.raises(RuntimeError, match="Audio TX not started"):
            await radio.push_audio_tx_opus(b"\x00" * 100)

    @pytest.mark.asyncio
    async def test_start_tx_pcm_disconnected(self) -> None:
        r = IcomRadio("192.168.1.100")
        with pytest.raises(ConnectionError):
            await r.start_audio_tx_pcm()

    @pytest.mark.asyncio
    async def test_push_tx_pcm_not_started(self, radio: IcomRadio) -> None:
        with pytest.raises(RuntimeError, match="start_audio_tx_pcm"):
            await radio.push_audio_tx_pcm(b"\x00" * 1920)

    @pytest.mark.asyncio
    async def test_no_audio_port(self, radio: IcomRadio) -> None:
        radio._audio_port = 0
        with pytest.raises(ConnectionError, match="Audio port not available"):
            await radio.start_audio_rx_opus(lambda pkt: None)

    @pytest.mark.asyncio
    async def test_stop_rx_noop_when_no_stream(self, radio: IcomRadio) -> None:
        await radio.stop_audio_rx_opus()  # should not raise

    @pytest.mark.asyncio
    async def test_stop_tx_noop_when_no_stream(self, radio: IcomRadio) -> None:
        await radio.stop_audio_tx_opus()  # should not raise

    @pytest.mark.asyncio
    async def test_stop_tx_pcm_noop_when_no_stream(self, radio: IcomRadio) -> None:
        await radio.stop_audio_tx_pcm()  # should not raise

    def test_get_audio_stats_idle_without_stream(self, radio: IcomRadio) -> None:
        stats = radio.get_audio_stats()
        assert stats["active"] is False
        assert stats["state"] == "idle"
        assert stats["packet_loss_percent"] == 0.0

    def test_get_audio_stats_delegates_to_audio_stream(self, radio: IcomRadio) -> None:
        expected = {"active": True, "state": "receiving", "rx_packets_received": 5}
        radio._audio_stream = MagicMock()
        radio._audio_stream.get_audio_stats.return_value = expected

        assert radio.get_audio_stats() == expected


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
    async def test_ptt_is_fire_and_forget(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """set_ptt is fire-and-forget: IMMEDIATE priority, no ACK wait."""
        send_mock = AsyncMock()
        radio._send_civ_raw = send_mock  # type: ignore[method-assign]

        await radio.set_ptt(True)

        send_mock.assert_awaited_once()
        _, kwargs = send_mock.await_args
        assert kwargs["priority"] == Priority.IMMEDIATE
        assert kwargs["wait_response"] is False


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
        pkt = radio._civ_runtime._wrap_civ(civ)
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

    def test_model_sets_profile_default_radio_addr_when_not_overridden(self) -> None:
        r = IcomRadio("10.0.0.3", model="IC-7300")
        assert r.model == "IC-7300"
        assert r._radio_addr == 0x94

    def test_explicit_radio_addr_override_wins_over_profile_default(self) -> None:
        r = IcomRadio("10.0.0.4", model="IC-7300", radio_addr=0x98)
        assert r.model == "IC-7300"
        assert r._radio_addr == 0x98
