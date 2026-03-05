"""Integration tests configuration and fixtures.

Tests require a real Icom radio on the network.
Set environment variables to enable:

    export ICOM_HOST=192.168.55.40
    export ICOM_USER=your_username
    export ICOM_PASS=your_password

Without these, all integration tests are skipped.
"""

from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

import pytest

# Add src to path for imports
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from icom_lan import IcomRadio  # noqa: E402

# Environment variables
ICOM_HOST = os.environ.get("ICOM_HOST", "")
ICOM_USER = os.environ.get("ICOM_USER", "")
ICOM_PASS = os.environ.get("ICOM_PASS", "")
ICOM_RADIO_ADDR = int(os.environ.get("ICOM_RADIO_ADDR", "0x98"), 16)  # IC-7610 default


def has_radio_config() -> bool:
    """Check if radio connection is configured."""
    return bool(ICOM_HOST and ICOM_USER and ICOM_PASS)


async def _connect_with_retries(radio: IcomRadio, attempts: int = 7) -> None:
    """Connect with firmware-aware cooldown retries for real hardware."""
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            await radio.connect()
            return
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            text = str(exc).lower()
            if "status error=0xffffffff" in text or "rejected session allocation" in text:
                # IC-7610 can hold old session slot for tens of seconds.
                pause = min(12 + attempt * 4, 40)
            else:
                pause = min(attempt * 2, 12)
            await asyncio.sleep(float(pause))
    assert last_exc is not None
    raise last_exc


@pytest.fixture
def radio_config() -> dict:
    """Radio connection configuration."""
    return {
        "host": ICOM_HOST,
        "username": ICOM_USER,
        "password": ICOM_PASS,
        "radio_addr": ICOM_RADIO_ADDR,
    }


@pytest.fixture
async def radio(radio_config: dict) -> AsyncGenerator[IcomRadio, None]:
    """Connected radio instance for integration tests.

    Automatically connects before test and disconnects after.
    Skips test if radio is not configured.
    """
    if not has_radio_config():
        pytest.skip("Radio not configured (set ICOM_HOST, ICOM_USER, ICOM_PASS)")

    r = IcomRadio(**radio_config)
    await _connect_with_retries(r)
    assert r.connected, "Failed to connect to radio"

    # Wait for status packet with audio port mapping
    await asyncio.sleep(0.5)

    # Per-test baseline (best effort).
    baseline_freq = None
    baseline_mode = None
    baseline_filter = None
    baseline_power = None
    baseline_digisel = None
    try:
        baseline_freq = await r.get_frequency()
        baseline_mode, baseline_filter = await r.get_mode_info()
        baseline_power = await r.get_power()
        baseline_digisel = await r.get_digisel()
    except Exception:
        # Don't fail fixture on baseline read issues.
        pass

    try:
        yield r
    finally:
        # Guardrails: restore safe/common state after each test.
        try:
            await r.set_split_mode(False)
        except Exception:
            pass
        try:
            await r.select_vfo("MAIN")
        except Exception:
            pass

        # Restore baseline values if we captured them.
        if baseline_power is not None:
            try:
                await r.set_power(baseline_power)
            except Exception:
                pass
        if baseline_mode is not None:
            try:
                await r.set_mode(baseline_mode, filter_width=baseline_filter)
            except Exception:
                pass
        if baseline_digisel is not None:
            try:
                await r.set_digisel(baseline_digisel)
            except Exception:
                pass
        if baseline_freq is not None:
            try:
                await r.set_frequency(baseline_freq)
            except Exception:
                pass

        await r.disconnect()


# Pytest configuration
def pytest_configure(config: pytest.Config) -> None:
    """Register integration marker."""
    config.addinivalue_line(
        "markers",
        "integration: tests requiring real radio hardware (skip if not configured)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip integration tests if radio not configured."""
    if not has_radio_config():
        skip = pytest.mark.skip(
            reason="Radio not configured (set ICOM_HOST, ICOM_USER, ICOM_PASS)"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
