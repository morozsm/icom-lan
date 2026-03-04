"""Tests for src/icom_lan/web/dx_cluster.py

Task 1: DXSpot dataclass + parse_spot
Task 2: DXClusterClient asyncio telnet
Task 3: SpotBuffer
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan.web.dx_cluster import DXClusterClient, DXSpot, SpotBuffer, parse_spot


# ---------------------------------------------------------------------------
# Task 1: parse_spot
# ---------------------------------------------------------------------------


class TestParseSpot:
    def test_basic_dxspider_spot(self):
        line = "DX de K1ABC:     14074.0  JA1XYZ       FT8 +05dB from PM95   1234Z"
        spot = parse_spot(line)
        assert spot is not None
        assert spot.spotter == "K1ABC"
        assert spot.freq == 14074000  # Hz
        assert spot.call == "JA1XYZ"
        assert spot.comment == "FT8 +05dB from PM95"

    def test_time_utc_extracted(self):
        line = "DX de K1ABC:     14074.0  JA1XYZ       FT8 +05dB from PM95   1234Z"
        spot = parse_spot(line)
        assert spot is not None
        assert spot.time_utc == "1234Z"

    def test_freq_converted_to_hz(self):
        line = "DX de W2XYZ:  21074.0  VK3ABC  FT8  0800Z"
        spot = parse_spot(line)
        assert spot is not None
        assert spot.freq == 21074000

    def test_freq_no_decimal(self):
        line = "DX de W2XYZ:  7000  VK3ABC  SSB 59  0800Z"
        spot = parse_spot(line)
        assert spot is not None
        assert spot.freq == 7000000

    def test_spot_no_time(self):
        line = "DX de K1ABC:  14074.0  JA1XYZ  FT8 -10dB"
        spot = parse_spot(line)
        assert spot is not None
        assert spot.call == "JA1XYZ"
        assert spot.time_utc == ""
        assert spot.comment == "FT8 -10dB"

    def test_spot_no_comment_no_time(self):
        line = "DX de K1ABC:  14074.0  JA1XYZ"
        spot = parse_spot(line)
        assert spot is not None
        assert spot.call == "JA1XYZ"
        assert spot.comment == ""
        assert spot.time_utc == ""

    def test_spot_no_comment_with_time(self):
        line = "DX de K1ABC:  14074.0  JA1XYZ  1234Z"
        spot = parse_spot(line)
        assert spot is not None
        assert spot.comment == ""
        assert spot.time_utc == "1234Z"

    def test_extra_whitespace(self):
        line = "DX de   K1ABC:    14074.0   JA1XYZ    FT8   1234Z"
        spot = parse_spot(line)
        assert spot is not None
        assert spot.spotter == "K1ABC"
        assert spot.freq == 14074000
        assert spot.call == "JA1XYZ"

    def test_high_freq_vhf(self):
        line = "DX de K1ABC:  144200.0  W1ABC  SSB  1800Z"
        spot = parse_spot(line)
        assert spot is not None
        assert spot.freq == 144200000

    def test_callsign_with_ssid(self):
        line = "DX de K1ABC-3:  14074.0  JA1XYZ  FT8  1234Z"
        spot = parse_spot(line)
        assert spot is not None
        assert spot.spotter == "K1ABC-3"

    def test_non_spot_line_returns_none(self):
        line = "Hello K1ABC-3 de dxspider 1.55"
        assert parse_spot(line) is None

    def test_empty_line_returns_none(self):
        assert parse_spot("") is None

    def test_login_prompt_returns_none(self):
        assert parse_spot("login: ") is None

    def test_cluster_info_line_returns_none(self):
        assert parse_spot("WWV de W0MU <18Z> :   SFI=85, A=8, K=2") is None

    def test_spot_is_frozen_dataclass(self):
        line = "DX de K1ABC:  14074.0  JA1XYZ  FT8  1234Z"
        spot = parse_spot(line)
        assert spot is not None
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            spot.call = "MODIFIED"  # type: ignore[misc]

    def test_spot_has_timestamp(self):
        line = "DX de K1ABC:  14074.0  JA1XYZ  FT8  1234Z"
        before = time.monotonic()
        spot = parse_spot(line)
        after = time.monotonic()
        assert spot is not None
        assert before <= spot.timestamp <= after


# ---------------------------------------------------------------------------
# Task 2: DXClusterClient
# ---------------------------------------------------------------------------

_SPOT_LINE_1 = b"DX de K1ABC:  14074.0  JA1XYZ  FT8 +05dB  1234Z\r\n"
_SPOT_LINE_2 = b"DX de W2DEF:  7074.0  VK3ABC  FT8 -10dB  0800Z\r\n"
_NON_SPOT_LINE = b"Hello K1ABC-3 de dxspider 1.55\r\n"


def _make_blocking_reader(*lines: bytes) -> asyncio.StreamReader:
    """Feed lines but NO EOF — reader blocks after them, preventing reconnect loops."""
    reader = asyncio.StreamReader()
    for line in lines:
        reader.feed_data(line)
    return reader


def _make_writer() -> MagicMock:
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.is_closing = MagicMock(return_value=False)
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    return writer


async def _run_and_cancel(coro, *, delay: float = 0.05) -> None:
    """Start a coroutine as a task, wait briefly, then cancel it."""
    task = asyncio.create_task(coro)
    await asyncio.sleep(delay)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


class TestDXClusterClient:
    async def test_connects_and_sends_callsign(self):
        """Client sends callsign immediately after connecting."""
        reader = _make_blocking_reader()
        writer = _make_writer()

        with patch(
            "icom_lan.web.dx_cluster.asyncio.open_connection",
            new=AsyncMock(return_value=(reader, writer)),
        ):
            client = DXClusterClient("dx.example.com", 7300, "K1ABC", on_spot=MagicMock())
            await _run_and_cancel(client.start())

        writer.write.assert_called_once_with(b"K1ABC\r\n")

    async def test_calls_on_spot_for_each_valid_line(self):
        """on_spot callback is invoked once per valid spot line."""
        reader = _make_blocking_reader(_SPOT_LINE_1, _SPOT_LINE_2)
        writer = _make_writer()
        spots: list[DXSpot] = []

        with patch(
            "icom_lan.web.dx_cluster.asyncio.open_connection",
            new=AsyncMock(return_value=(reader, writer)),
        ):
            client = DXClusterClient("dx.example.com", 7300, "K1ABC", on_spot=spots.append)
            await _run_and_cancel(client.start())

        assert len(spots) == 2
        assert spots[0].call == "JA1XYZ"
        assert spots[1].call == "VK3ABC"

    async def test_ignores_non_spot_lines(self):
        """Non-spot lines do not trigger on_spot."""
        reader = _make_blocking_reader(_NON_SPOT_LINE, _SPOT_LINE_1)
        writer = _make_writer()
        spots: list[DXSpot] = []

        with patch(
            "icom_lan.web.dx_cluster.asyncio.open_connection",
            new=AsyncMock(return_value=(reader, writer)),
        ):
            client = DXClusterClient("dx.example.com", 7300, "K1ABC", on_spot=spots.append)
            await _run_and_cancel(client.start())

        assert len(spots) == 1
        assert spots[0].call == "JA1XYZ"

    async def test_reconnects_after_disconnect(self):
        """Client retries once after a connection failure then reads spots."""
        call_count = 0
        spots: list[DXSpot] = []
        # Event set when the second (successful) connection occurs.
        connected = asyncio.Event()

        async def fake_open(host, port):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionRefusedError("refused")
            reader = _make_blocking_reader(_SPOT_LINE_1)
            connected.set()
            return reader, _make_writer()

        client = DXClusterClient("dx.example.com", 7300, "K1ABC", on_spot=spots.append)

        with patch("icom_lan.web.dx_cluster.asyncio.open_connection", new=fake_open):
            with patch("icom_lan.web.dx_cluster.asyncio.sleep", new=AsyncMock()):
                task = asyncio.create_task(client.start())
                # Wait for second connection (instant since sleep is mocked)
                await asyncio.wait_for(connected.wait(), timeout=2.0)
                await asyncio.sleep(0)  # let the spot be processed
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        assert call_count >= 2
        assert len(spots) >= 1

    async def test_stop_sets_flag_and_closes_writer(self):
        """stop() sets _running=False and closes the active writer."""
        reader = _make_blocking_reader()
        writer = _make_writer()

        client = DXClusterClient("dx.example.com", 7300, "K1ABC", on_spot=MagicMock())

        with patch(
            "icom_lan.web.dx_cluster.asyncio.open_connection",
            new=AsyncMock(return_value=(reader, writer)),
        ):
            task = asyncio.create_task(client.start())
            await asyncio.sleep(0.05)  # let it connect

            await client.stop()
            assert not client._running
            writer.close.assert_called()

            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def test_cancelled_error_propagates(self):
        """CancelledError from external task cancellation is not swallowed."""
        reader = _make_blocking_reader()
        writer = _make_writer()

        client = DXClusterClient("dx.example.com", 7300, "K1ABC", on_spot=MagicMock())

        with patch(
            "icom_lan.web.dx_cluster.asyncio.open_connection",
            new=AsyncMock(return_value=(reader, writer)),
        ):
            task = asyncio.create_task(client.start())
            await asyncio.sleep(0.05)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task


# ---------------------------------------------------------------------------
# Task 3: SpotBuffer
# ---------------------------------------------------------------------------


def _make_spot(call: str, freq: int = 14074000, *, ts: float | None = None) -> DXSpot:
    spot = DXSpot(spotter="K1ABC", freq=freq, call=call)
    if ts is not None:
        # dataclasses.replace works on frozen dataclasses
        spot = dataclasses.replace(spot, timestamp=ts)
    return spot


class TestSpotBuffer:
    def test_add_and_get_single_spot(self):
        buf = SpotBuffer()
        buf.add(_make_spot("JA1XYZ"))
        spots = buf.get_spots()
        assert len(spots) == 1
        assert spots[0]["call"] == "JA1XYZ"

    def test_max_len_drops_oldest(self):
        buf = SpotBuffer(maxlen=3)
        for i in range(5):
            buf.add(_make_spot(f"W{i}ABC"))
        spots = buf.get_spots()
        # Only 3 most recent remain
        assert len(spots) == 3
        calls = [s["call"] for s in spots]
        assert "W0ABC" not in calls
        assert "W1ABC" not in calls
        assert "W4ABC" in calls

    def test_get_spots_returns_dicts(self):
        buf = SpotBuffer()
        buf.add(_make_spot("JA1XYZ", freq=14074000))
        spot = buf.get_spots()[0]
        assert spot["call"] == "JA1XYZ"
        assert spot["freq"] == 14074000
        assert spot["spotter"] == "K1ABC"
        assert "comment" in spot
        assert "time_utc" in spot
        assert "timestamp" in spot

    def test_get_spots_filter_by_band_20m(self):
        buf = SpotBuffer()
        buf.add(_make_spot("JA1XYZ", freq=14074000))   # 20m
        buf.add(_make_spot("VK3ABC", freq=7074000))    # 40m
        buf.add(_make_spot("W1ABC", freq=21074000))    # 15m
        spots_20m = buf.get_spots(band="20m")
        assert len(spots_20m) == 1
        assert spots_20m[0]["call"] == "JA1XYZ"

    def test_get_spots_filter_all_bands(self):
        buf = SpotBuffer()
        buf.add(_make_spot("JA1XYZ", freq=14074000))
        buf.add(_make_spot("VK3ABC", freq=7074000))
        assert len(buf.get_spots()) == 2

    def test_get_spots_unknown_band_returns_empty(self):
        buf = SpotBuffer()
        buf.add(_make_spot("JA1XYZ", freq=14074000))
        assert buf.get_spots(band="99m") == []

    def test_expire_removes_old_spots(self):
        buf = SpotBuffer()
        now = time.monotonic()
        old = _make_spot("OLD", ts=now - 3000)   # 50 min ago
        fresh = _make_spot("FRESH", ts=now - 60)  # 1 min ago
        buf.add(old)
        buf.add(fresh)
        assert len(buf.get_spots()) == 2

        buf.expire(max_age_s=1800)  # 30 min threshold
        spots = buf.get_spots()
        assert len(spots) == 1
        assert spots[0]["call"] == "FRESH"

    def test_expire_empty_buffer_is_noop(self):
        buf = SpotBuffer()
        buf.expire(max_age_s=1800)
        assert buf.get_spots() == []

    def test_to_json_returns_valid_json(self):
        buf = SpotBuffer()
        buf.add(_make_spot("JA1XYZ", freq=14074000))
        raw = buf.to_json()
        parsed = json.loads(raw)
        assert isinstance(parsed, list)
        assert parsed[0]["call"] == "JA1XYZ"

    def test_to_json_empty_buffer(self):
        buf = SpotBuffer()
        assert json.loads(buf.to_json()) == []
