"""Tests for CI-V 0x25/0x26 selected/unselected freq & mode commands."""


import pytest

from icom_lan import IC_7610_ADDR
from icom_lan.commands import (
    CONTROLLER_ADDR,
    _CMD_SELECTED_FREQ,
    _CMD_SELECTED_MODE,
    build_civ_frame,
    get_selected_freq,
    get_unselected_freq,
    get_selected_mode,
    get_unselected_mode,
    parse_selected_freq_response,
    parse_selected_mode_response,
)
from icom_lan.radio import IcomRadio
from icom_lan.types import CivFrame, Mode, bcd_encode

from test_radio import MockTransport, _wrap_civ_in_udp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _selected_freq_response(receiver: int, freq_hz: int) -> bytes:
    """Build a CI-V 0x25 frequency response wrapped in UDP."""
    civ = build_civ_frame(
        CONTROLLER_ADDR,
        IC_7610_ADDR,
        _CMD_SELECTED_FREQ,
        data=bytes([receiver]) + bcd_encode(freq_hz),
    )
    return _wrap_civ_in_udp(civ)


def _selected_mode_response(
    receiver: int, mode: Mode, data_mode: int = 0, filt: int = 1
) -> bytes:
    """Build a CI-V 0x26 mode response wrapped in UDP."""
    civ = build_civ_frame(
        CONTROLLER_ADDR,
        IC_7610_ADDR,
        _CMD_SELECTED_MODE,
        data=bytes([receiver, mode, data_mode, filt]),
    )
    return _wrap_civ_in_udp(civ)


# ---------------------------------------------------------------------------
# Command builder tests
# ---------------------------------------------------------------------------


class TestCommandBuilders:
    def test_get_selected_freq_frame(self) -> None:
        frame = get_selected_freq(to_addr=0x98)
        assert b"\x25\x00" in frame
        assert frame.startswith(b"\xfe\xfe")
        assert frame.endswith(b"\xfd")

    def test_get_unselected_freq_frame(self) -> None:
        frame = get_unselected_freq(to_addr=0x98)
        assert b"\x25\x01" in frame

    def test_get_selected_mode_frame(self) -> None:
        frame = get_selected_mode(to_addr=0x98)
        assert b"\x26\x00" in frame

    def test_get_unselected_mode_frame(self) -> None:
        frame = get_unselected_mode(to_addr=0x98)
        assert b"\x26\x01" in frame


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestParsers:
    def test_parse_selected_freq_response_main(self) -> None:
        freq_hz = 14_074_000
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x25,
            sub=None,
            data=bytes([0x00]) + bcd_encode(freq_hz),
        )
        rcvr, freq = parse_selected_freq_response(frame)
        assert rcvr == 0x00
        assert freq == freq_hz

    def test_parse_selected_freq_response_sub(self) -> None:
        freq_hz = 7_074_000
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x25,
            sub=None,
            data=bytes([0x01]) + bcd_encode(freq_hz),
        )
        rcvr, freq = parse_selected_freq_response(frame)
        assert rcvr == 0x01
        assert freq == freq_hz

    def test_parse_selected_freq_wrong_command(self) -> None:
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x03,
            sub=None,
            data=bcd_encode(14_074_000),
        )
        with pytest.raises(ValueError, match="Not a 0x25 response"):
            parse_selected_freq_response(frame)

    def test_parse_selected_freq_too_short(self) -> None:
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x25,
            sub=None,
            data=bytes([0x00, 0x01]),
        )
        with pytest.raises(ValueError, match="too short"):
            parse_selected_freq_response(frame)

    def test_parse_selected_mode_response_full(self) -> None:
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x26,
            sub=None,
            data=bytes([0x00, Mode.USB, 0x01, 0x02]),
        )
        rcvr, mode, data_mode, filt = parse_selected_mode_response(frame)
        assert rcvr == 0x00
        assert mode == Mode.USB
        assert data_mode == 0x01
        assert filt == 0x02

    def test_parse_selected_mode_response_minimal(self) -> None:
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x26,
            sub=None,
            data=bytes([0x01, Mode.CW]),
        )
        rcvr, mode, data_mode, filt = parse_selected_mode_response(frame)
        assert rcvr == 0x01
        assert mode == Mode.CW
        assert data_mode is None
        assert filt is None

    def test_parse_selected_mode_wrong_command(self) -> None:
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x04,
            sub=None,
            data=bytes([Mode.USB]),
        )
        with pytest.raises(ValueError, match="Not a 0x26 response"):
            parse_selected_mode_response(frame)

    def test_parse_selected_mode_too_short(self) -> None:
        frame = CivFrame(
            to_addr=CONTROLLER_ADDR,
            from_addr=IC_7610_ADDR,
            command=0x26,
            sub=None,
            data=bytes([0x00]),
        )
        with pytest.raises(ValueError, match="too short"):
            parse_selected_mode_response(frame)


# ---------------------------------------------------------------------------
# Radio integration tests
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


class TestRadioSelectedFreq:
    @pytest.mark.asyncio
    async def test_get_selected_freq(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(
            _selected_freq_response(0x00, 14_074_000)
        )
        freq = await radio._get_selected_freq()
        assert freq == 14_074_000

    @pytest.mark.asyncio
    async def test_get_unselected_freq(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(
            _selected_freq_response(0x01, 7_074_000)
        )
        freq = await radio._get_unselected_freq()
        assert freq == 7_074_000

    @pytest.mark.asyncio
    async def test_get_freq_receiver_sub_uses_cmd25(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """get_freq(receiver=1) should use 0x25 0x01 instead of VFO swap."""
        mock_transport.queue_response(
            _selected_freq_response(0x01, 7_074_000)
        )
        freq = await radio.get_freq(receiver=1)
        assert freq == 7_074_000


class TestRadioSelectedMode:
    @pytest.mark.asyncio
    async def test_get_selected_mode(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(
            _selected_mode_response(0x00, Mode.USB, filt=1)
        )
        mode, filt = await radio._get_selected_mode()
        assert mode == Mode.USB
        assert filt == 1

    @pytest.mark.asyncio
    async def test_get_unselected_mode(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        mock_transport.queue_response(
            _selected_mode_response(0x01, Mode.LSB, filt=2)
        )
        mode, filt = await radio._get_unselected_mode()
        assert mode == Mode.LSB
        assert filt == 2

    @pytest.mark.asyncio
    async def test_get_mode_receiver_sub_uses_cmd26(
        self, radio: IcomRadio, mock_transport: MockTransport
    ) -> None:
        """get_mode(receiver=1) should use 0x26 0x01 instead of VFO swap."""
        mock_transport.queue_response(
            _selected_mode_response(0x01, Mode.CW, filt=3)
        )
        mode_name, filt = await radio.get_mode(receiver=1)
        assert mode_name == "CW"
        assert filt == 3
