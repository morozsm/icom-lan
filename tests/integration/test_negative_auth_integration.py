"""Negative integration tests for auth/connect paths (backlog item 12)."""

from __future__ import annotations

import os

import pytest

from icom_lan import IcomRadio
from icom_lan.exceptions import AuthenticationError, ConnectionError, TimeoutError


pytestmark = pytest.mark.integration


def _flag_enabled(name: str) -> bool:
    return os.environ.get(name, "0") == "1"


class TestNegativeAuthConnect:
    """Negative-path integration coverage with explicit gate."""

    async def test_invalid_credentials_rejected(self, radio_config: dict) -> None:
        """Invalid password should fail authentication."""
        if not _flag_enabled("ICOM_ALLOW_NEGATIVE_TESTS"):
            pytest.skip("Set ICOM_ALLOW_NEGATIVE_TESTS=1 to run negative auth tests")

        bad_password = os.environ.get("ICOM_BAD_PASS", "")
        if not bad_password:
            bad_password = f"{radio_config['password']}_bad"

        if bad_password == radio_config["password"]:
            bad_password = f"{bad_password}_x"

        r = IcomRadio(
            host=radio_config["host"],
            username=radio_config["username"],
            password=bad_password,
            radio_addr=radio_config["radio_addr"],
            timeout=4.0,
        )
        try:
            with pytest.raises(AuthenticationError):
                await r.connect()
        finally:
            try:
                await r.disconnect()
            except Exception:
                pass

    async def test_unreachable_target_fails_fast(self, radio_config: dict) -> None:
        """Unreachable host/port should fail with connection/timeout."""
        if not _flag_enabled("ICOM_ALLOW_NEGATIVE_TESTS"):
            pytest.skip("Set ICOM_ALLOW_NEGATIVE_TESTS=1 to run negative connect tests")

        host = os.environ.get("ICOM_NEGATIVE_HOST", "192.0.2.1")
        port = int(os.environ.get("ICOM_NEGATIVE_PORT", "59999"))

        r = IcomRadio(
            host=host,
            port=port,
            username=radio_config["username"],
            password=radio_config["password"],
            radio_addr=radio_config["radio_addr"],
            timeout=2.0,
        )
        try:
            with pytest.raises((ConnectionError, TimeoutError, OSError)):
                await r.connect()
        finally:
            try:
                await r.disconnect()
            except Exception:
                pass
