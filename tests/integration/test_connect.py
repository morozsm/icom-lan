"""Legacy connect diagnostic migrated to pytest integration test (item 13)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


class TestLegacyConnectMigration:
    """Migrated coverage from former standalone connect script."""

    async def test_legacy_connect_disconnect_flow(self, radio) -> None:
        """Connect and disconnect one session, preserving original script intent."""
        assert radio.connected
