"""Band plan registry — load TOML files and serve via REST.

Loads all .toml files from the band-plans/ directory at startup,
indexes segments for fast frequency-range queries.
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default mode colors (hex) — used when TOML doesn't specify a color
MODE_COLORS: dict[str, str] = {
    "cw": "#FF6A00",
    "digital": "#4ADE80",
    "phone": "#60A5FA",
    "beacon": "#FACC15",
    "broadcast": "#C084FC",
    "utility": "#F97316",
    "military": "#EF4444",
    "other": "#9CA3AF",
}

DEFAULT_OPACITY = 0.20


class BandPlanRegistry:
    """Load and query band plan data from TOML files."""

    def __init__(self, band_plans_dir: str | Path | None = None) -> None:
        self._dir = Path(band_plans_dir) if band_plans_dir else None
        self._layers: dict[str, dict[str, Any]] = {}  # layer_name -> meta
        self._segments: list[dict[str, Any]] = []  # flat list, sorted by start

    def load(self, band_plans_dir: str | Path | None = None) -> None:
        """Load all .toml files from the directory."""
        search_dir = Path(band_plans_dir) if band_plans_dir else self._dir
        if search_dir is None:
            logger.warning("band-plan: no directory configured")
            return

        if not search_dir.is_dir():
            logger.warning("band-plan: directory not found: %s", search_dir)
            return

        self._layers.clear()
        self._segments.clear()

        toml_files = sorted(search_dir.glob("*.toml"))
        if not toml_files:
            logger.info("band-plan: no TOML files in %s", search_dir)
            return

        for path in toml_files:
            if path.name.startswith("_"):
                continue  # skip config files
            try:
                self._load_file(path)
            except Exception:
                logger.exception("band-plan: failed to load %s", path.name)

        # Sort all segments by start frequency
        self._segments.sort(key=lambda s: s["start"])
        logger.info(
            "band-plan: loaded %d segments from %d files (%d layers)",
            len(self._segments),
            len(toml_files),
            len(self._layers),
        )

    def _load_file(self, path: Path) -> None:
        """Parse a single TOML band plan file."""
        with open(path, "rb") as f:
            data = tomllib.load(f)

        meta = data.get("meta", {})
        layer = meta.get("layer", path.stem)
        priority = meta.get("priority", 0)

        self._layers[layer] = {
            "name": meta.get("name", path.stem),
            "layer": layer,
            "priority": priority,
            "source": meta.get("source", ""),
            "region": meta.get("region", ""),
            "updated": str(meta.get("updated", "")),
            "file": path.name,
        }

        bands = data.get("band", [])
        for band in bands:
            band_name = band.get("name", "?")
            for seg in band.get("segment", []):
                mode = seg.get("mode", "other")
                self._segments.append(
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "mode": mode,
                        "label": seg.get("label", mode.upper()),
                        "color": seg.get("color", MODE_COLORS.get(mode, "#9CA3AF")),
                        "opacity": seg.get("opacity", DEFAULT_OPACITY),
                        "band": band_name,
                        "layer": layer,
                        "priority": priority,
                        "url": seg.get("url"),
                        "notes": seg.get("notes"),
                        "station": seg.get("station"),
                        "language": seg.get("language"),
                        "schedule": seg.get("schedule"),
                        "license": seg.get("license"),
                    }
                )

    def get_segments(
        self,
        start_hz: int,
        end_hz: int,
        layers: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return segments overlapping the given frequency range.

        Args:
            start_hz: Left edge of the visible spectrum (Hz).
            end_hz: Right edge of the visible spectrum (Hz).
            layers: Optional layer filter (None = all layers).

        Returns:
            List of segment dicts sorted by start frequency.
        """
        result: list[dict[str, Any]] = []
        for seg in self._segments:
            if seg["end"] < start_hz:
                continue
            if seg["start"] > end_hz:
                break  # sorted, no more matches
            if layers and seg["layer"] not in layers:
                continue
            result.append(seg)
        return result

    def get_layers(self) -> list[dict[str, Any]]:
        """Return all loaded layers with metadata."""
        return sorted(
            self._layers.values(),
            key=lambda l: -l.get("priority", 0),
        )

    @property
    def segment_count(self) -> int:
        """Total number of loaded segments."""
        return len(self._segments)
