"""SWR calibration tests — TOML data + ``interpolate_swr`` algorithm.

Covers issue #1173 (P3-01): every Icom rig in the matrix ships a
piecewise-linear SWR calibration table in ``[[meters.swr.calibration]]``
and ``MetersCapable.get_swr`` returns the calibrated ratio.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from icom_lan.meter_cal import interpolate_swr
from icom_lan.rig_loader import load_rig

RIGS_DIR = Path(__file__).resolve().parent.parent / "rigs"


# Per R1 research — anchor points each rig's TOML must publish.
# Format: rig filename → list of (raw, expected_swr_ratio).
EXPECTED_ANCHORS: dict[str, list[tuple[int, float]]] = {
    "ic7610.toml": [
        (0, 1.0),
        (48, 1.5),
        (80, 2.0),
        (120, 3.0),
        (255, 6.0),  # IC-7610-specific top endpoint (wfview IC-7610.rig).
    ],
    "ic7300.toml": [
        (0, 1.0),
        (48, 1.5),
        (80, 2.0),
        (120, 3.0),
        (240, 6.0),
    ],
    "ic705.toml": [
        (0, 1.0),
        (48, 1.5),
        (80, 2.0),
        (120, 3.0),
        (240, 6.0),
    ],
    "ic9700.toml": [
        (0, 1.0),
        (48, 1.5),
        (80, 2.0),
        (120, 3.0),
        (240, 6.0),
    ],
}


@pytest.mark.parametrize("rig_file", list(EXPECTED_ANCHORS))
def test_toml_has_swr_calibration_block(rig_file: str) -> None:
    """Every Icom rig must ship ``[[meters.swr.calibration]]``."""
    rig = load_rig(RIGS_DIR / rig_file)
    assert rig.meter_calibrations is not None
    assert "swr" in rig.meter_calibrations


@pytest.mark.parametrize("rig_file", list(EXPECTED_ANCHORS))
def test_toml_swr_anchor_count(rig_file: str) -> None:
    rig = load_rig(RIGS_DIR / rig_file)
    pts = rig.meter_calibrations["swr"]
    assert len(pts) == len(EXPECTED_ANCHORS[rig_file])


@pytest.mark.parametrize(
    "rig_file,raw,expected",
    [
        (rig_file, raw, expected)
        for rig_file, anchors in EXPECTED_ANCHORS.items()
        for raw, expected in anchors
    ],
)
def test_anchor_round_trip(rig_file: str, raw: int, expected: float) -> None:
    """Interpolating a raw value at an anchor returns the anchor's SWR."""
    rig = load_rig(RIGS_DIR / rig_file)
    swr = interpolate_swr(raw, rig.meter_calibrations)
    assert swr == pytest.approx(expected)


@pytest.mark.parametrize("rig_file", list(EXPECTED_ANCHORS))
def test_midpoint_interpolation(rig_file: str) -> None:
    """Midpoint between two anchors returns the linear midpoint SWR.

    Picks the (48, 1.5) → (80, 2.0) leg because it's identical across
    every Icom rig and gives a clean answer at raw=64.
    """
    rig = load_rig(RIGS_DIR / rig_file)
    swr = interpolate_swr(64, rig.meter_calibrations)
    # 1.5 + (64 - 48) / (80 - 48) * (2.0 - 1.5) = 1.5 + 16/32 * 0.5 = 1.75
    assert swr == pytest.approx(1.75)


def test_interpolate_swr_clamps_below_first_anchor() -> None:
    points = [{"raw": 10, "actual": 1.2}, {"raw": 200, "actual": 5.0}]
    assert interpolate_swr(0, {"swr": points}) == pytest.approx(1.2)


def test_interpolate_swr_clamps_above_last_anchor() -> None:
    points = [{"raw": 10, "actual": 1.2}, {"raw": 200, "actual": 5.0}]
    assert interpolate_swr(255, {"swr": points}) == pytest.approx(5.0)


def test_interpolate_swr_no_table_falls_back_to_legacy_linear() -> None:
    """Without a ``swr`` table the legacy mapping is preserved."""
    # raw=0 → 1.0 (special-cased)
    assert interpolate_swr(0, None) == pytest.approx(1.0)
    # raw=255 → 1.0 + 1.0 * 8.9 = 9.9
    assert interpolate_swr(255, None) == pytest.approx(9.9)


def test_interpolate_swr_empty_calibrations_uses_legacy() -> None:
    assert interpolate_swr(0, {}) == pytest.approx(1.0)


def test_interpolate_swr_yaesu_path_unchanged() -> None:
    """Regression guard: FTX-1 still resolves through the same helper."""
    rig = load_rig(RIGS_DIR / "ftx1.toml")
    # Anchors in ftx1.toml — sanity check the first one to confirm the
    # Yaesu backend continues to use the same shared algorithm after
    # being switched to ``meter_cal.interpolate_swr`` in #1173.
    pts = rig.meter_calibrations["swr"]
    first = pts[0]
    swr = interpolate_swr(first["raw"], rig.meter_calibrations)
    assert swr == pytest.approx(first["actual"])
