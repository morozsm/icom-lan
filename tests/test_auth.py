"""Tests for authentication logic."""

import struct

import pytest

from icom_lan.auth import (
    PASSCODE_SEQUENCE,
    build_conninfo_packet,
    build_login_packet,
    encode_credentials,
    parse_auth_response,
    parse_status_response,
)
from icom_lan.protocol import parse_header


class TestEncodeCredentials:
    """Test the XOR-style credential encoding from wfview."""

    def test_empty_string(self):
        assert encode_credentials("") == b""

    def test_single_char(self):
        # 'a' = 0x61, position 0 => p = 0x61 + 0 = 97
        # sequence[97] = lookup from the table
        result = encode_credentials("a")
        assert len(result) == 1
        # 'a' ascii=97, pos=0, p=97 => sequence[97]
        assert result[0] == PASSCODE_SEQUENCE[97]

    def test_known_username(self):
        """Verify encoding produces deterministic output."""
        result = encode_credentials("admin")
        assert len(result) == 5
        # Each char: ascii + position, then lookup
        for i, ch in enumerate("admin"):
            p = ord(ch) + i
            if p > 126:
                p = 32 + p % 127
            assert result[i] == PASSCODE_SEQUENCE[p]

    def test_truncates_at_16(self):
        result = encode_credentials("a" * 32)
        assert len(result) == 16

    def test_position_offset_matters(self):
        """Same char at different positions produces different output."""
        r1 = encode_credentials("aa")
        assert r1[0] != r1[1]  # 'a'+0 != 'a'+1

    def test_high_ascii_wraps(self):
        """Characters where ascii+position > 126 should wrap."""
        # '~' = 126, position 1 => p = 127 > 126 => 32 + 127 % 127 = 32
        result = encode_credentials("a~")
        p = 126 + 1  # > 126
        p = 32 + p % 127
        assert result[1] == PASSCODE_SEQUENCE[p]


class TestBuildLoginPacket:
    """Test login packet construction."""

    def test_packet_size(self):
        pkt = build_login_packet("user", "pass", sender_id=0x123, receiver_id=0x456)
        assert len(pkt) == 0x80  # LOGIN_SIZE

    def test_header_fields(self):
        pkt = build_login_packet("user", "pass", sender_id=0x123, receiver_id=0x456)
        hdr = parse_header(pkt)
        assert hdr.length == 0x80
        assert hdr.sender_id == 0x123
        assert hdr.receiver_id == 0x456

    def test_payload_size_field(self):
        pkt = build_login_packet("user", "pass", sender_id=1, receiver_id=2)
        # payloadsize at offset 0x10, big-endian u32
        payload_size = struct.unpack_from(">I", pkt, 0x10)[0]
        assert payload_size == 0x80 - 0x10

    def test_request_type(self):
        pkt = build_login_packet("user", "pass", sender_id=1, receiver_id=2)
        assert pkt[0x14] == 0x01  # requestreply
        assert pkt[0x15] == 0x00  # requesttype (login)

    def test_username_encoded(self):
        pkt = build_login_packet("admin", "secret", sender_id=1, receiver_id=2)
        encoded_user = encode_credentials("admin")
        # username at offset 0x40, 16 bytes
        assert pkt[0x40 : 0x40 + len(encoded_user)] == encoded_user

    def test_password_encoded(self):
        pkt = build_login_packet("admin", "secret", sender_id=1, receiver_id=2)
        encoded_pass = encode_credentials("secret")
        # password at offset 0x50, 16 bytes
        assert pkt[0x50 : 0x50 + len(encoded_pass)] == encoded_pass

    def test_computer_name(self):
        pkt = build_login_packet(
            "u", "p", sender_id=1, receiver_id=2, computer_name="mypc"
        )
        # name at offset 0x60, 16 bytes
        assert pkt[0x60:0x64] == b"mypc"

    def test_tokrequest_set(self):
        pkt = build_login_packet(
            "u", "p", sender_id=1, receiver_id=2, tok_request=0xABCD
        )
        tok = struct.unpack_from("<H", pkt, 0x1A)[0]
        assert tok == 0xABCD


class TestBuildConninfoPacket:
    """Test conninfo (stream request) packet construction."""

    def test_packet_size(self):
        pkt = build_conninfo_packet(
            sender_id=1,
            receiver_id=2,
            username="admin",
            token=0x12345678,
            tok_request=0xABCD,
            radio_name="IC-7610",
            mac_address=bytes(6),
        )
        assert len(pkt) == 0x90  # CONNINFO_SIZE

    def test_token_fields(self):
        pkt = build_conninfo_packet(
            sender_id=1,
            receiver_id=2,
            username="admin",
            token=0xDEADBEEF,
            tok_request=0x1234,
            radio_name="IC-7610",
            mac_address=bytes(6),
        )
        tok = struct.unpack_from("<I", pkt, 0x1C)[0]
        assert tok == 0xDEADBEEF
        tokr = struct.unpack_from("<H", pkt, 0x1A)[0]
        assert tokr == 0x1234


class TestParseAuthResponse:
    """Test parsing login response packets."""

    def _make_login_response(
        self,
        *,
        error: int = 0,
        token: int = 0,
        tok_request: int = 0,
        connection: str = "",
    ) -> bytes:
        pkt = bytearray(0x60)  # LOGIN_RESPONSE_SIZE
        struct.pack_into("<I", pkt, 0x00, 0x60)  # len
        struct.pack_into("<H", pkt, 0x04, 0x00)  # type
        struct.pack_into("<I", pkt, 0x08, 0x100)  # sentid (radio)
        struct.pack_into("<I", pkt, 0x0C, 0x200)  # rcvdid (us)
        struct.pack_into("<H", pkt, 0x1A, tok_request)
        struct.pack_into("<I", pkt, 0x1C, token)
        struct.pack_into("<I", pkt, 0x30, error)
        conn_bytes = connection.encode("ascii")[:16]
        pkt[0x40 : 0x40 + len(conn_bytes)] = conn_bytes
        return bytes(pkt)

    def test_successful_login(self):
        data = self._make_login_response(
            token=0xCAFE, tok_request=0x42, connection="FTTH"
        )
        resp = parse_auth_response(data)
        assert resp.success is True
        assert resp.token == 0xCAFE
        assert resp.tok_request == 0x42
        assert resp.connection_type == "FTTH"

    def test_failed_login(self):
        data = self._make_login_response(error=0xFEFFFFFF)
        resp = parse_auth_response(data)
        assert resp.success is False

    def test_short_packet_raises(self):
        with pytest.raises(ValueError):
            parse_auth_response(b"\x00" * 10)


class TestParseStatusResponse:
    """Test parsing status packets."""

    def _make_status(
        self, *, error: int = 0, disc: int = 0, civport: int = 0, audioport: int = 0
    ) -> bytes:
        pkt = bytearray(0x50)  # STATUS_SIZE
        struct.pack_into("<I", pkt, 0x00, 0x50)
        struct.pack_into("<H", pkt, 0x04, 0x00)
        struct.pack_into("<I", pkt, 0x30, error)
        pkt[0x40] = disc
        struct.pack_into(">H", pkt, 0x42, civport)  # big-endian!
        struct.pack_into(">H", pkt, 0x46, audioport)  # big-endian!
        return bytes(pkt)

    def test_parse_ports(self):

        data = self._make_status(civport=50001, audioport=50002)
        resp = parse_status_response(data)
        assert resp.civ_port == 50001
        assert resp.audio_port == 50002
        assert resp.error == 0
        assert resp.disconnected is False

    def test_disconnected(self):

        data = self._make_status(disc=1)
        resp = parse_status_response(data)
        assert resp.disconnected is True

    def test_error(self):

        data = self._make_status(error=0xFFFFFFFF)
        resp = parse_status_response(data)
        assert resp.error == 0xFFFFFFFF
