"""Shared radio state cache for the rigctld server.

Holds the last-known radio state fields with monotonic timestamps so
callers can decide whether a cached value is still fresh enough to use
without issuing another CI-V round-trip.

Not thread-safe by design: all access must happen on the same asyncio
event loop (single-loop model).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

__all__ = ["StateCache"]

# Literal union of all cacheable field names (used for is_fresh).
CacheField = Literal["freq", "mode", "vfo", "ptt", "s_meter", "rf_power"]


@dataclass(slots=True)
class StateCache:
    """Last-known radio state with per-field monotonic timestamps.

    Each logical value has a corresponding ``<field>_ts`` timestamp
    (``time.monotonic()``).  A timestamp of ``0.0`` means the field has
    never been written.

    Attributes:
        freq: Last-known VFO-A frequency in Hz.
        freq_ts: Monotonic timestamp of the last ``freq`` update.
        mode: Last-known mode as a hamlib mode string (e.g. ``"USB"``).
        filter_width: Last-known IC-7610 filter number (1–3) or ``None``.
        mode_ts: Monotonic timestamp of the last mode update.
        vfo: Current VFO name (always ``"VFOA"`` for now).
        vfo_ts: Monotonic timestamp of the last VFO update.
        ptt: Last-known PTT state.
        ptt_ts: Monotonic timestamp of the last PTT update.
        s_meter: Last-known raw S-meter value (0–241) or ``None``.
        s_meter_ts: Monotonic timestamp of the last S-meter update.
        rf_power: Last-known normalised RF power (0.0–1.0) or ``None``.
        rf_power_ts: Monotonic timestamp of the last RF-power update.
    """

    # Frequency
    freq: int = 0
    freq_ts: float = 0.0

    # Mode / filter
    mode: str = "USB"
    filter_width: int | None = None
    mode_ts: float = 0.0

    # VFO
    vfo: str = "VFOA"
    vfo_ts: float = 0.0

    # PTT
    ptt: bool = False
    ptt_ts: float = 0.0

    # S-meter
    s_meter: int | None = None
    s_meter_ts: float = 0.0

    # RF power (normalised 0.0–1.0)
    rf_power: float | None = None
    rf_power_ts: float = 0.0

    # ------------------------------------------------------------------
    # Freshness check
    # ------------------------------------------------------------------

    def is_fresh(self, field: CacheField, max_age_s: float) -> bool:
        """Return True if *field* was updated within *max_age_s* seconds.

        Args:
            field: Cache field name to check.
            max_age_s: Maximum acceptable age in seconds.

        Returns:
            ``True`` when the field has a timestamp and the elapsed time
            since that timestamp is strictly less than *max_age_s*.
        """
        ts: float
        match field:
            case "freq":
                ts = self.freq_ts
            case "mode":
                ts = self.mode_ts
            case "vfo":
                ts = self.vfo_ts
            case "ptt":
                ts = self.ptt_ts
            case "s_meter":
                ts = self.s_meter_ts
            case "rf_power":
                ts = self.rf_power_ts
            case _:  # pragma: no cover
                return False
        if ts == 0.0:
            return False
        return (time.monotonic() - ts) < max_age_s

    # ------------------------------------------------------------------
    # Update helpers
    # ------------------------------------------------------------------

    def update_freq(self, freq: int) -> None:
        """Store a new frequency value and record the current timestamp."""
        self.freq = freq
        self.freq_ts = time.monotonic()

    def invalidate_freq(self) -> None:
        """Mark the frequency as stale (forces the next read to hit radio)."""
        self.freq_ts = 0.0

    def update_mode(self, mode: str, filter_width: int | None) -> None:
        """Store a new mode/filter value and record the current timestamp.

        Args:
            mode: Hamlib mode string (e.g. ``"USB"``, ``"CW"``).
            filter_width: IC-7610 filter number (1–3) or ``None``.
        """
        self.mode = mode
        self.filter_width = filter_width
        self.mode_ts = time.monotonic()

    def invalidate_mode(self) -> None:
        """Mark the mode as stale (forces the next read to hit radio)."""
        self.mode_ts = 0.0

    def update_ptt(self, ptt: bool) -> None:
        """Store a new PTT state and record the current timestamp."""
        self.ptt = ptt
        self.ptt_ts = time.monotonic()

    def update_s_meter(self, value: int) -> None:
        """Store a new raw S-meter value and record the current timestamp."""
        self.s_meter = value
        self.s_meter_ts = time.monotonic()

    def update_rf_power(self, value: float) -> None:
        """Store a new normalised RF-power value and record the current timestamp."""
        self.rf_power = value
        self.rf_power_ts = time.monotonic()

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, object]:
        """Return a dict of current values and their ages in seconds.

        Age keys are ``<field>_age``.  The age is ``None`` if the field
        has never been written (timestamp is 0.0), otherwise it is a
        non-negative float.

        Returns:
            Dictionary with all cached fields and their ages.
        """
        now = time.monotonic()

        def _age(ts: float) -> float | None:
            return (now - ts) if ts > 0.0 else None

        return {
            "freq": self.freq,
            "freq_age": _age(self.freq_ts),
            "mode": self.mode,
            "filter_width": self.filter_width,
            "mode_age": _age(self.mode_ts),
            "vfo": self.vfo,
            "vfo_age": _age(self.vfo_ts),
            "ptt": self.ptt,
            "ptt_age": _age(self.ptt_ts),
            "s_meter": self.s_meter,
            "s_meter_age": _age(self.s_meter_ts),
            "rf_power": self.rf_power,
            "rf_power_age": _age(self.rf_power_ts),
        }
