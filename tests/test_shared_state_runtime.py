from __future__ import annotations

"""Tests for icom_lan._shared_state_runtime helpers."""

import time

from icom_lan._shared_state_runtime import (
    DEFAULT_STATE_CACHE_TTL,
    is_cache_fresh,
)
from icom_lan.rigctld.state_cache import StateCache


def test_is_cache_fresh_false_when_ttl_none_or_non_positive() -> None:
    cache = StateCache()
    cache.update_freq(14_074_000)

    assert is_cache_fresh(cache, "freq", None) is False
    assert is_cache_fresh(cache, "freq", 0.0) is False
    assert is_cache_fresh(cache, "freq", -1.0) is False


def test_is_cache_fresh_delegates_to_state_cache() -> None:
    cache = StateCache()
    cache.update_freq(14_074_000)

    # Immediately after update the entry must be fresh.
    assert is_cache_fresh(cache, "freq", DEFAULT_STATE_CACHE_TTL) is True

    # Simulate staleness by moving the timestamp far into the past.
    cache.freq_ts -= 10.0
    assert is_cache_fresh(cache, "freq", DEFAULT_STATE_CACHE_TTL) is False


def test_is_cache_fresh_respects_never_written_fields() -> None:
    cache = StateCache()
    # No writes yet → timestamps are 0.0 and must be treated as stale.
    assert is_cache_fresh(cache, "mode", DEFAULT_STATE_CACHE_TTL) is False

