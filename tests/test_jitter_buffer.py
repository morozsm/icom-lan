"""Tests for JitterBuffer — reordering, gaps, duplicates, wrapping, flush."""

import pytest

from icom_lan.audio import AudioPacket, JitterBuffer


def _pkt(seq: int, data: bytes = b"\x00") -> AudioPacket:
    """Helper to create an AudioPacket with given seq."""
    return AudioPacket(ident=0x0080, send_seq=seq, data=data)


class TestJitterBufferBasic:
    def test_depth_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="depth"):
            JitterBuffer(depth=0)
        with pytest.raises(ValueError, match="depth"):
            JitterBuffer(depth=-1)

    def test_initial_state(self) -> None:
        jb = JitterBuffer(depth=3)
        assert jb.depth == 3
        assert jb.pending == 0

    def test_buffering_below_depth(self) -> None:
        jb = JitterBuffer(depth=3)
        result = jb.push(_pkt(0))
        assert result == []
        result = jb.push(_pkt(1))
        assert result == []
        assert jb.pending == 2

    def test_delivers_after_depth(self) -> None:
        jb = JitterBuffer(depth=2)
        jb.push(_pkt(0))
        result = jb.push(_pkt(1))
        # With depth=2, 2 packets buffered, next_seq=0 is present → deliver
        assert len(result) >= 1
        assert result[0].send_seq == 0


class TestJitterBufferOrdering:
    def test_in_order(self) -> None:
        jb = JitterBuffer(depth=2)
        all_r = []
        for i in range(5):
            all_r.extend(jb.push(_pkt(i)))
        seqs = [p.send_seq for p in all_r if p is not None]
        # All delivered in order
        assert seqs == sorted(seqs)
        assert 0 in seqs

    def test_out_of_order(self) -> None:
        jb = JitterBuffer(depth=3)
        jb.push(_pkt(0))
        jb.push(_pkt(2))  # seq 1 missing
        result = jb.push(_pkt(1))  # now 0,1,2 all present
        assert len(result) >= 1
        seqs = [p.send_seq for p in result if p is not None]
        assert seqs == sorted(seqs)  # monotonically increasing

    def test_reorder_within_depth(self) -> None:
        """Packets arriving slightly out of order within buffer depth are reordered."""
        jb = JitterBuffer(depth=3)
        all_r = []
        # Arrive: 0, 2, 1, 3, 4, 5
        all_r.extend(jb.push(_pkt(0)))
        all_r.extend(jb.push(_pkt(2)))
        all_r.extend(jb.push(_pkt(1)))
        all_r.extend(jb.push(_pkt(3)))
        all_r.extend(jb.push(_pkt(4)))
        all_r.extend(jb.push(_pkt(5)))
        seqs = [p.send_seq for p in all_r if p is not None]
        assert seqs == sorted(seqs)
        assert 0 in seqs
        assert 1 in seqs
        assert 2 in seqs


class TestJitterBufferGaps:
    def test_gap_detection(self) -> None:
        jb = JitterBuffer(depth=2)
        all_results = []
        all_results.extend(jb.push(_pkt(0)))
        all_results.extend(jb.push(_pkt(2)))  # seq 1 missing
        all_results.extend(jb.push(_pkt(3)))
        all_results.extend(jb.push(_pkt(4)))
        # Enough packets ahead of gap at seq 1 → should deliver gap
        delivered_seqs = []
        for p in all_results:
            if p is None:
                delivered_seqs.append(None)
            else:
                delivered_seqs.append(p.send_seq)
        assert 0 in delivered_seqs
        assert None in delivered_seqs  # gap for missing seq 1

    def test_multiple_gaps(self) -> None:
        jb = JitterBuffer(depth=2)
        jb.push(_pkt(0))
        # Skip 1, 2
        jb.push(_pkt(3))
        jb.push(_pkt(5))
        result = jb.push(_pkt(6))
        nones = [p for p in result if p is None]
        assert len(nones) >= 1  # at least one gap


class TestJitterBufferDuplicates:
    def test_duplicate_ignored(self) -> None:
        jb = JitterBuffer(depth=3)
        jb.push(_pkt(0))
        result = jb.push(_pkt(0))  # duplicate
        assert result == []
        assert jb.pending == 1  # not 2


class TestJitterBufferWrap:
    def test_seq_wrap_around(self) -> None:
        """Test sequence number wrap from 0xFFFF to 0x0000."""
        jb = JitterBuffer(depth=2)
        all_results = []
        all_results.extend(jb.push(_pkt(0xFFFE)))
        all_results.extend(jb.push(_pkt(0xFFFF)))
        all_results.extend(jb.push(_pkt(0x0000)))
        all_results.extend(jb.push(_pkt(0x0001)))
        seqs = [p.send_seq for p in all_results if p is not None]
        assert 0xFFFE in seqs
        assert 0xFFFF in seqs
        assert 0x0000 in seqs

    def test_old_packet_ignored(self) -> None:
        """Packets far behind next_seq are ignored."""
        jb = JitterBuffer(depth=2)
        jb.push(_pkt(100))
        jb.push(_pkt(101))
        jb.push(_pkt(102))
        # Now next_seq should be ~101, so seq 50 is old
        result = jb.push(_pkt(50))
        assert result == []


class TestJitterBufferFlush:
    def test_flush_empty(self) -> None:
        jb = JitterBuffer(depth=3)
        assert jb.flush() == []

    def test_flush_delivers_all(self) -> None:
        jb = JitterBuffer(depth=5)
        jb.push(_pkt(0))
        jb.push(_pkt(1))
        jb.push(_pkt(2))
        # Not enough for auto-delivery
        result = jb.flush()
        assert len(result) == 3
        seqs = [p.send_seq for p in result if p is not None]
        assert seqs == [0, 1, 2]

    def test_flush_with_gaps(self) -> None:
        jb = JitterBuffer(depth=5)
        jb.push(_pkt(0))
        jb.push(_pkt(2))  # gap at 1
        jb.push(_pkt(4))  # gap at 3
        result = jb.flush()
        assert len(result) == 5  # 0, None, 2, None, 4
        assert result[0].send_seq == 0
        assert result[1] is None
        assert result[2].send_seq == 2
        assert result[3] is None
        assert result[4].send_seq == 4


class TestJitterBufferOverflow:
    def test_overflow_flushes(self) -> None:
        jb = JitterBuffer(depth=2)
        # max_held = depth * 4 = 8
        results = []
        for i in range(20):
            results.extend(jb.push(_pkt(i)))
        # Should have delivered most packets without crash
        assert len(results) > 0
        # All delivered should be in order
        seqs = [p.send_seq for p in results if p is not None]
        for i in range(1, len(seqs)):
            assert seqs[i] > seqs[i - 1]


class TestJitterBufferLargeDepth:
    def test_depth_10(self) -> None:
        jb = JitterBuffer(depth=10)
        all_results = []
        for i in range(20):
            all_results.extend(jb.push(_pkt(i)))
        assert len(all_results) >= 1
        seqs = [p.send_seq for p in all_results if p is not None]
        assert 0 in seqs
