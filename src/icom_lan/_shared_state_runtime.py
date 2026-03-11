from __future__ import annotations

"""Shared state polling/cache helpers used by web and rigctld.

This module centralises:
- Default cache TTLs for short-lived radio state (freq/mode/data_mode).
- A tiny helper for checking :class:`rigctld.state_cache.StateCache`
  freshness so callers do not duplicate the ``is_fresh`` logic and
  magic numbers.

The goal is that both the Web UI and rigctld use the same TTL
semantics when deciding whether to serve cached values or hit the
radio again.
"""

from typing import Final

from .rigctld.state_cache import CacheField, StateCache

__all__ = [
    "DEFAULT_STATE_CACHE_TTL",
    "is_cache_fresh",
]


# Default TTL (seconds) for short-lived radio state such as frequency
# and mode.  Mirrors RigctldConfig.cache_ttl and is used by both
# rigctld and web snapshots unless a caller provides an override.
DEFAULT_STATE_CACHE_TTL: Final[float] = 0.2


def is_cache_fresh(
    cache: StateCache,
    field: CacheField,
    max_age_s: float | None,
) -> bool:
    """Return True if *field* in *cache* is fresh enough to use.

    Args:
        cache: Shared :class:`StateCache` instance.
        field: Cache field name (``"freq"``, ``"mode"``, etc.).
        max_age_s: Maximum acceptable age in seconds.  When ``None`` or
            non‑positive, the cache is treated as always stale and this
            function returns ``False``.
    """
    if max_age_s is None or max_age_s <= 0.0:
        return False
    return cache.is_fresh(field, max_age_s)

