"""IC-7610 meter calibration tables from wfview IC-7610.rig.

Each table is a list of (raw_value, actual_value) pairs.
Linear interpolation between points.
"""

from __future__ import annotations

__all__ = ["calibrate", "interpolate_swr", "MeterType"]

from enum import Enum
from typing import Any, Sequence


class MeterType(str, Enum):
    SMETER = "smeter"
    POWER = "power"
    SWR = "swr"
    ALC = "alc"
    CURRENT = "id"
    VOLTAGE = "vd"
    COMP = "comp"


# (raw_bcd_value, actual_value) — from wfview IC-7610.rig Meters section
_TABLES: dict[MeterType, list[tuple[int, float]]] = {
    MeterType.SMETER: [
        (0, -54),
        (11, -48),
        (21, -42),
        (34, -36),
        (50, -30),
        (59, -24),
        (75, -18),
        (93, -12),
        (103, -6),
        (124, 0),
        (145, 10),
        (160, 20),
        (183, 30),
        (204, 40),
        (222, 50),
        (246, 60),
    ],
    MeterType.POWER: [
        (0, 0),
        (21, 5),
        (43, 10),
        (65, 15),
        (83, 20),
        (95, 25),
        (105, 30),
        (114, 35),
        (124, 40),
        (143, 50),
        (183, 75),
        (213, 100),
        (255, 120),
    ],
    MeterType.SWR: [
        (0, 1.0),
        (48, 1.5),
        (80, 2.0),
        (120, 3.0),
        (255, 6.0),
    ],
    MeterType.ALC: [
        (0, 0),
        (120, 100),
        (255, 200),
    ],
    MeterType.COMP: [
        (0, 0),
        (130, 15),
        (241, 30),
    ],
    MeterType.CURRENT: [
        (0, 0),
        (77, 10),
        (165, 20),
        (241, 30),
    ],
    MeterType.VOLTAGE: [
        (0, 0),
        (151, 10),
        (185, 13.8),
        (211, 16),
    ],
}


def _interp(table: Sequence[tuple[int, float]], raw: int) -> float:
    """Linear interpolation over calibration table."""
    if raw <= table[0][0]:
        return table[0][1]
    for i in range(1, len(table)):
        x0, y0 = table[i - 1]
        x1, y1 = table[i]
        if raw <= x1:
            return y0 + (raw - x0) * (y1 - y0) / (x1 - x0)
    return table[-1][1]


def calibrate(meter: MeterType | str, raw: int) -> float:
    """Convert raw BCD meter value to calibrated actual value.

    Returns the raw value unchanged if no calibration table exists.
    """
    if isinstance(meter, str):
        try:
            meter = MeterType(meter)
        except ValueError:
            return float(raw)
    table = _TABLES.get(meter)
    if table is None:
        return float(raw)
    return _interp(table, raw)


def interpolate_swr(raw: int, meter_calibrations: dict[str, list[Any]] | None) -> float:
    """Convert raw SWR meter value (0-255) to a calibrated SWR ratio.

    Uses the ``swr`` calibration table from ``meter_calibrations`` (loaded
    from TOML's ``[[meters.swr.calibration]]`` blocks) when available,
    interpolating piecewise-linearly between points. Returns the legacy
    linear approximation ``1.0 + raw/255 * 8.9`` when no table is
    configured (preserves backward compat for rigs that don't yet ship
    calibration data).

    Mirrors ``yaesu_cat.radio._interpolate_swr`` so all backends share a
    single algorithm — the wfview piecewise-linear curve.
    """
    points = (meter_calibrations or {}).get("swr")
    if points:
        # Points are typically already sorted by raw, but sort defensively.
        sorted_pts = sorted(points, key=lambda p: p["raw"])
        if raw <= sorted_pts[0]["raw"]:
            return float(sorted_pts[0]["actual"])
        if raw >= sorted_pts[-1]["raw"]:
            return float(sorted_pts[-1]["actual"])
        for lo, hi in zip(sorted_pts, sorted_pts[1:]):
            if lo["raw"] <= raw <= hi["raw"]:
                span = hi["raw"] - lo["raw"]
                if span == 0:
                    return float(lo["actual"])
                t = (raw - lo["raw"]) / span
                return float(
                    float(lo["actual"])
                    + t * (float(hi["actual"]) - float(lo["actual"]))
                )
    # No table: legacy linear fallback (pre-#440 behavior).
    if raw <= 0:
        return 1.0
    return 1.0 + (raw / 255.0) * 8.9
