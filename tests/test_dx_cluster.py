"""Tests for src/icom_lan/web/dx_cluster.py

Task 1: DXSpot dataclass + parse_spot
Task 2: DXClusterClient asyncio telnet
Task 3: SpotBuffer
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icom_lan.web.dx_cluster import DXSpot, parse_spot


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
