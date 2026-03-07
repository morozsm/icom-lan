"""Simplified memory integration test - SET commands only (no GET).

Tests fire-and-forget commands that don't wait for responses.
"""

import asyncio
import pytest
from icom_lan.radio import IcomRadio
from icom_lan.types import MemoryChannel, BandStackRegister

pytestmark = pytest.mark.integration

_SETTLE = 0.2


@pytest.mark.asyncio
async def test_memory_contents_set_only(radio: IcomRadio) -> None:
    """Test memory contents SET (0x1A 0x00 SET)."""
    mem = MemoryChannel(
        channel=99,
        frequency_hz=14074000,
        mode=1,  # USB
        filter=1,
        scan=0,
        datamode=0,
        tonemode=0,
        name="SETONLY"
    )
    # This is fire-and-forget, should not timeout
    await radio.set_memory_contents(mem)
    await asyncio.sleep(_SETTLE)
    # Success if no exception


@pytest.mark.asyncio
async def test_band_stack_set_only(radio: IcomRadio) -> None:
    """Test band stack SET (0x1A 0x01 SET)."""
    bsr = BandStackRegister(
        band=15,
        register=3,
        frequency_hz=14200000,
        mode=1,
        filter=1
    )
    # Fire-and-forget
    await radio.set_band_stack(bsr)
    await asyncio.sleep(_SETTLE)
    # Success if no exception


@pytest.mark.asyncio
async def test_memory_mode_set_only(radio: IcomRadio) -> None:
    """Test memory mode SET (0x08 SET)."""
    # Fire-and-forget
    await radio.set_memory_mode(42)
    await asyncio.sleep(_SETTLE)
    # Success if no exception
