"""Comprehensive tests for protocol parsing, serialization, and BCD encoding."""

import struct

import pytest

from rigplane.exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    RigplaneError,
    TimeoutError,
)
from rigplane.protocol import identify_packet_type, parse_header, serialize_header
from rigplane.types import (
    HEADER_SIZE,
    Mode,
    PacketHeader,
    PacketType,
    bcd_decode,
    bcd_encode,
)


# ── BCD encode/decode ────────────────────────────────────────────────────


class TestBCDEncode:
    """Tests for BCD frequency encoding."""

    @pytest.mark.parametrize(
        "freq_hz,expected_hex",
        [
            (14_074_000, "0040071400"),
            (7_074_000, "0040070700"),
            (3_573_000, "0030570300"),
            (28_074_000, "0040072800"),
            (0, "0000000000"),
            (145_000_000, "0000004501"),
            (1_296_000_000, "0000009612"),
        ],
    )
    def test_known_frequencies(self, freq_hz: int, expected_hex: str) -> None:
        result = bcd_encode(freq_hz)
        assert result.hex() == expected_hex, (
            f"BCD encode {freq_hz} Hz: got {result.hex()}, expected {expected_hex}"
        )

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            bcd_encode(-1)

    def test_too_large_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds"):
            bcd_encode(100_000_000_000)


class TestBCDDecode:
    """Tests for BCD frequency decoding."""

    @pytest.mark.parametrize(
        "hex_str,expected_hz",
        [
            ("0040071400", 14_074_000),
            ("0040070700", 7_074_000),
            ("0030570300", 3_573_000),
            ("0040072800", 28_074_000),
            ("0000000000", 0),
        ],
    )
    def test_known_frequencies(self, hex_str: str, expected_hz: int) -> None:
        result = bcd_decode(bytes.fromhex(hex_str))
        assert result == expected_hz

    def test_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError, match="5 bytes"):
            bcd_decode(b"\x00\x00\x00")

    def test_invalid_bcd_digit_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid BCD"):
            bcd_decode(bytes([0xFF, 0x00, 0x00, 0x00, 0x00]))

    @pytest.mark.parametrize(
        "freq_hz",
        [14_074_000, 7_074_000, 3_573_000, 28_074_000, 50_313_000, 144_200_000],
    )
    def test_roundtrip(self, freq_hz: int) -> None:
        assert bcd_decode(bcd_encode(freq_hz)) == freq_hz


# ── Header parse/serialize ───────────────────────────────────────────────


class TestParseHeader:
    """Tests for packet header parsing."""

    def test_control_packet(self, control_packet: bytes) -> None:
        h = parse_header(control_packet)
        assert h.length == HEADER_SIZE
        assert h.type == PacketType.CONTROL
        assert h.seq == 0
        assert h.sender_id == 0x12345678
        assert h.receiver_id == 0x9ABCDEF0

    def test_ping_packet(self, ping_packet: bytes) -> None:
        h = parse_header(ping_packet)
        assert h.length == 0x15
        assert h.type == PacketType.PING
        assert h.seq == 42
        assert h.sender_id == 0xAABBCCDD

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="too short"):
            parse_header(b"\x00" * 15)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="too short"):
            parse_header(b"")


class TestSerializeHeader:
    """Tests for packet header serialization."""

    def test_roundtrip(self) -> None:
        header = PacketHeader(
            length=0x10,
            type=PacketType.CONTROL,
            seq=99,
            sender_id=0xDEADBEEF,
            receiver_id=0xCAFEBABE,
        )
        data = serialize_header(header)
        assert len(data) == HEADER_SIZE
        assert parse_header(data) == header

    def test_roundtrip_all_types(self) -> None:
        for pt in PacketType:
            header = PacketHeader(
                length=0x10, type=pt, seq=0, sender_id=1, receiver_id=2
            )
            assert parse_header(serialize_header(header)) == header


# ── Packet type identification ───────────────────────────────────────────


class TestIdentifyPacketType:
    """Tests for packet type identification."""

    def test_control(self, control_packet: bytes) -> None:
        assert identify_packet_type(control_packet) == PacketType.CONTROL

    def test_ping(self, ping_packet: bytes) -> None:
        assert identify_packet_type(ping_packet) == PacketType.PING

    def test_data(self, data_packet_with_civ: bytes) -> None:
        assert identify_packet_type(data_packet_with_civ) == PacketType.DATA

    def test_unknown_type_returns_none(self) -> None:
        data = struct.pack("<IHHII", 0x10, 0xFF, 0, 0, 0)
        assert identify_packet_type(data) is None

    def test_too_short_returns_none(self) -> None:
        assert identify_packet_type(b"\x00\x00") is None

    def test_all_known_types(self) -> None:
        for pt in PacketType:
            data = struct.pack("<IHHII", 0x10, pt.value, 0, 0, 0)
            assert identify_packet_type(data) == pt


# ── Exception hierarchy ──────────────────────────────────────────────────


class TestExceptions:
    """Tests for the custom exception hierarchy."""

    def test_base_exception(self) -> None:
        assert issubclass(RigplaneError, Exception)

    @pytest.mark.parametrize(
        "exc_class",
        [ConnectionError, AuthenticationError, CommandError, TimeoutError],
    )
    def test_subclass_of_base(self, exc_class: type) -> None:
        assert issubclass(exc_class, RigplaneError)

    def test_catch_base_catches_all(self) -> None:
        for cls in (ConnectionError, AuthenticationError, CommandError, TimeoutError):
            with pytest.raises(RigplaneError):
                raise cls("test")


# ── Enums ────────────────────────────────────────────────────────────────


class TestEnums:
    """Tests for Mode and PacketType enums."""

    def test_mode_values(self) -> None:
        assert Mode.LSB == 0x00
        assert Mode.USB == 0x01
        assert Mode.CW == 0x03
        assert Mode.FM == 0x05

    def test_packet_type_values(self) -> None:
        assert PacketType.CONTROL == 0x01
        assert PacketType.PING == 0x07
        assert PacketType.DATA == 0x00

    def test_header_size_constant(self) -> None:
        assert HEADER_SIZE == 16
