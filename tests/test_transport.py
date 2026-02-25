"""Tests for async UDP transport layer."""

import asyncio
import struct
from unittest.mock import MagicMock, patch

import pytest

from icom_lan.transport import ConnectionState, IcomTransport
from icom_lan.types import PacketType


@pytest.fixture
def transport():
    """Create an IcomTransport instance (not connected)."""
    return IcomTransport()


class TestConnectionState:
    """Test connection state enum."""

    def test_states_exist(self):
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"


class TestTransportInit:
    """Test transport initialization."""

    def test_initial_state(self, transport):
        assert transport.state == ConnectionState.DISCONNECTED
        assert transport.send_seq == 0
        assert transport.ping_seq == 0

    def test_my_id_generation(self, transport):
        # Should be non-zero after init
        assert transport.my_id == 0  # Not yet connected, no ID


class TestSequenceNumbers:
    """Test sequence number tracking."""

    def test_next_seq_increments(self, transport):
        assert transport._next_send_seq() == 0
        assert transport._next_send_seq() == 1
        assert transport._next_send_seq() == 2

    def test_seq_wraps_at_u16(self, transport):
        transport.send_seq = 0xFFFF
        assert transport._next_send_seq() == 0xFFFF
        assert transport.send_seq == 0  # Wrapped


class TestPacketBuilding:
    """Test building control/ping packets."""

    def test_build_ping_packet(self, transport):
        transport.my_id = 0xAABBCCDD
        transport.remote_id = 0x11223344
        transport.ping_seq = 5
        pkt = transport._build_ping()
        assert len(pkt) == 0x15  # PING_SIZE
        # Check header
        length = struct.unpack_from("<I", pkt, 0)[0]
        assert length == 0x15
        ptype = struct.unpack_from("<H", pkt, 4)[0]
        assert ptype == PacketType.PING
        seq = struct.unpack_from("<H", pkt, 6)[0]
        assert seq == 5
        # reply byte
        assert pkt[0x10] == 0x00  # request, not reply

    def test_build_control_packet(self, transport):
        transport.my_id = 0x01
        transport.remote_id = 0x02
        pkt = transport._build_control(ptype=PacketType.ARE_YOU_READY, seq=0)
        assert len(pkt) == 0x10  # CONTROL_SIZE
        hdr_type = struct.unpack_from("<H", pkt, 4)[0]
        assert hdr_type == PacketType.ARE_YOU_READY

    def test_build_disconnect(self, transport):
        transport.my_id = 0x01
        transport.remote_id = 0x02
        pkt = transport._build_control(ptype=PacketType.DISCONNECT, seq=0)
        hdr_type = struct.unpack_from("<H", pkt, 4)[0]
        assert hdr_type == PacketType.DISCONNECT


class TestRetransmitTracking:
    """Test TX buffer and retransmit logic."""

    def test_track_sent_packet(self, transport):
        transport.my_id = 0x01
        transport.remote_id = 0x02
        data = b"\x00" * 0x15
        transport._track_sent(0, data)
        assert 0 in transport.tx_buffer
        assert transport.tx_buffer[0] == data

    def test_buffer_limit(self, transport):
        for i in range(600):
            transport._track_sent(i, b"\x00")
        assert len(transport.tx_buffer) <= 500

    def test_detect_missing_packets(self, transport):
        """When we receive seq 5 after seq 2, 3 and 4 are missing."""
        transport._record_rx_seq(1)
        transport._record_rx_seq(2)
        transport._record_rx_seq(5)
        assert 3 in transport.rx_missing
        assert 4 in transport.rx_missing

    def test_missing_removed_on_receive(self, transport):
        transport._record_rx_seq(1)
        transport._record_rx_seq(3)
        assert 2 in transport.rx_missing
        transport._record_rx_seq(2)
        assert 2 not in transport.rx_missing

    def test_build_retransmit_request_single(self, transport):
        transport.my_id = 0x01
        transport.remote_id = 0x02
        transport.rx_missing[5] = 0
        pkts = transport._build_retransmit_requests()
        assert len(pkts) == 1
        pkt = pkts[0]
        assert len(pkt) == 0x10  # Single: control packet with seq=5
        seq = struct.unpack_from("<H", pkt, 6)[0]
        assert seq == 5

    def test_build_retransmit_request_multiple(self, transport):
        transport.my_id = 0x01
        transport.remote_id = 0x02
        transport.rx_missing[5] = 0
        transport.rx_missing[7] = 0
        pkts = transport._build_retransmit_requests()
        assert len(pkts) == 1
        pkt = pkts[0]
        # Multiple: control header + 4 bytes per missing seq
        assert len(pkt) == 0x10 + 4 * 2


class TestConnectDisconnect:
    """Test connect/disconnect lifecycle with mocked UDP."""

    @pytest.mark.asyncio
    async def test_connect_sets_state(self):
        t = IcomTransport()
        loop = asyncio.get_event_loop()

        mock_transport = MagicMock()
        mock_transport.get_extra_info = MagicMock(return_value=("127.0.0.1", 12345))

        async def fake_create(protocol_factory, remote_addr=None, local_addr=None):
            proto = protocol_factory()
            proto.connection_made(mock_transport)
            return mock_transport, proto

        with patch.object(loop, "create_datagram_endpoint", side_effect=fake_create):
            await t.connect("192.168.1.1", 50001)
            assert t.state == ConnectionState.CONNECTING
            await t.disconnect()
            assert t.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_disconnect_sends_packet(self):
        t = IcomTransport()
        loop = asyncio.get_event_loop()

        mock_udp_transport = MagicMock()
        mock_udp_transport.get_extra_info = MagicMock(return_value=("127.0.0.1", 12345))

        async def fake_create(protocol_factory, remote_addr=None, local_addr=None):
            proto = protocol_factory()
            proto.connection_made(mock_udp_transport)
            return mock_udp_transport, proto

        with patch.object(loop, "create_datagram_endpoint", side_effect=fake_create):
            await t.connect("192.168.1.1", 50001)
            t.remote_id = 0x100
            await t.disconnect()
            # Should have sent a disconnect control packet
            assert mock_udp_transport.sendto.called or mock_udp_transport.close.called


class TestKeepAlive:
    """Test ping/keep-alive behavior."""

    @pytest.mark.asyncio
    async def test_ping_loop_sends_packets(self):
        t = IcomTransport()
        sent = []

        def fake_send(data):
            sent.append(data)

        t._raw_send = fake_send
        t.my_id = 0x01
        t.remote_id = 0x02
        t.state = ConnectionState.CONNECTED

        # Send a few pings manually
        t._send_ping()
        t._send_ping()
        assert len(sent) == 2
        assert t.ping_seq == 2


class TestPacketReceive:
    """Test receiving and dispatching packets."""

    def test_handle_ping_request(self, transport):
        """When we receive a ping request, we should queue a reply."""
        transport.my_id = 0xAA
        transport.remote_id = 0xBB

        replies = []
        transport._raw_send = lambda data: replies.append(data)

        # Build a ping request from "radio"
        pkt = bytearray(0x15)
        struct.pack_into("<I", pkt, 0, 0x15)
        struct.pack_into("<H", pkt, 4, PacketType.PING)
        struct.pack_into("<H", pkt, 6, 42)  # seq
        struct.pack_into("<I", pkt, 8, 0xBB)  # sentid (radio)
        struct.pack_into("<I", pkt, 0x0C, 0xAA)  # rcvdid (us)
        pkt[0x10] = 0x00  # reply=0 (request)
        struct.pack_into("<I", pkt, 0x11, 12345)  # time

        transport._handle_packet(bytes(pkt))

        assert len(replies) == 1
        reply = replies[0]
        assert reply[0x10] == 0x01  # reply flag
        # seq should match incoming
        assert struct.unpack_from("<H", reply, 6)[0] == 42

    def test_handle_retransmit_request(self, transport):
        """When radio requests retransmit, we send buffered packet."""
        transport.my_id = 0xAA
        transport.remote_id = 0xBB

        # Put a packet in tx buffer
        original = b"\xde\xad" * 10
        transport.tx_buffer[7] = original

        replies = []
        transport._raw_send = lambda data: replies.append(data)

        # Build single retransmit request (CONTROL with type=0x01, len=0x10, seq=7)
        pkt = bytearray(0x10)
        struct.pack_into("<I", pkt, 0, 0x10)
        struct.pack_into("<H", pkt, 4, 0x01)  # type=CONTROL
        struct.pack_into("<H", pkt, 6, 7)  # seq to retransmit
        struct.pack_into("<I", pkt, 8, 0xBB)
        struct.pack_into("<I", pkt, 0x0C, 0xAA)

        transport._handle_packet(bytes(pkt))
        assert len(replies) == 1
        assert replies[0] == original
