"""Legacy get-frequency diagnostic migrated to pytest integration test (item 13)."""

from __future__ import annotations

import pytest

from icom_lan.commands import parse_frequency_response


pytestmark = pytest.mark.integration


class TestLegacyGetFreqMigration:
    """Migrated coverage from former handshake/get-frequency standalone script."""

    async def test_legacy_get_frequency_flow(self, radio) -> None:
        """Connect, issue raw CI-V get-frequency, and parse result."""
        frame = await radio.send_civ(0x03)
        assert frame is not None
        freq = parse_frequency_response(frame)
        assert freq > 0
        print(f"Legacy raw CI-V get_frequency: {freq} Hz ✓")
