"""TOML rig config loader — parse, validate, and build runtime objects."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .command_map import CommandMap
from .profiles import BandInfo, FreqRangeInfo, RadioProfile

__all__ = ["RigConfig", "RigLoadError", "load_rig", "discover_rigs"]

KNOWN_CAPABILITIES = frozenset(
    {
        "audio",
        "scope",
        "dual_rx",
        "meters",
        "tx",
        "cw",
        "attenuator",
        "preamp",
        "rf_gain",
        "af_level",
        "squelch",
        "nb",
        "nr",
        "digisel",
        "ip_plus",
    }
)

VALID_VFO_SCHEMES = {"ab", "main_sub"}

_REQUIRED_SECTIONS = ("radio", "capabilities", "modes", "filters", "vfo", "commands")
_REQUIRED_RADIO_FIELDS = ("id", "model", "civ_addr", "receiver_count", "has_lan", "has_wifi")


class RigLoadError(Exception):
    """Raised when a rig TOML file is invalid or malformed."""


@dataclass(frozen=True, slots=True)
class RigConfig:
    """Parsed rig configuration from a TOML file."""

    id: str
    model: str
    civ_addr: int
    receiver_count: int
    has_lan: bool
    has_wifi: bool
    capabilities: tuple[str, ...]
    modes: tuple[str, ...]
    filters: tuple[str, ...]
    vfo_scheme: str
    vfo_main_select: tuple[int, ...] | None
    vfo_sub_select: tuple[int, ...] | None
    vfo_swap: tuple[int, ...] | None
    freq_ranges: tuple[dict, ...]
    commands: dict[str, tuple[int, ...]]
    cmd29_routes: tuple[tuple[int, int | None], ...]
    spectrum: dict[str, int] | None

    def to_profile(self) -> RadioProfile:
        """Build a ``RadioProfile`` from this config."""
        vfo_main = self.vfo_main_select[0] if self.vfo_main_select else None
        vfo_sub = self.vfo_sub_select[0] if self.vfo_sub_select else None
        vfo_swap = self.vfo_swap[0] if self.vfo_swap else None

        ranges = tuple(
            FreqRangeInfo(
                start=r["start_hz"],
                end=r["end_hz"],
                label=r["label"],
                bands=tuple(
                    BandInfo(
                        name=b["name"],
                        start=b["start_hz"],
                        end=b["end_hz"],
                        default=b["default_hz"],
                    )
                    for b in r.get("bands", ())
                ),
            )
            for r in self.freq_ranges
        )

        return RadioProfile(
            id=self.id,
            model=self.model,
            civ_addr=self.civ_addr,
            receiver_count=self.receiver_count,
            capabilities=frozenset(self.capabilities),
            cmd29_routes=frozenset(self.cmd29_routes),
            vfo_main_code=vfo_main,
            vfo_sub_code=vfo_sub,
            vfo_swap_code=vfo_swap,
            freq_ranges=ranges,
            modes=tuple(self.modes),
            filters=tuple(self.filters),
        )

    def to_command_map(self) -> CommandMap:
        """Build a ``CommandMap`` from this config's commands."""
        return CommandMap(self.commands)


def load_rig(path: Path) -> RigConfig:
    """Load and validate a rig TOML file.

    Args:
        path: Path to the ``.toml`` file.

    Returns:
        Parsed and validated ``RigConfig``.

    Raises:
        RigLoadError: If the file is missing, unparseable, or invalid.
    """
    filename = path.name

    if not path.exists():
        raise RigLoadError(f"{filename}: file not found: {path}")

    try:
        raw = path.read_bytes()
        data = tomllib.loads(raw.decode())
    except Exception as exc:
        raise RigLoadError(f"{filename}: failed to parse TOML: {exc}") from exc

    # Validate required sections
    for section in _REQUIRED_SECTIONS:
        if section not in data:
            raise RigLoadError(f"{filename}: missing required section [{section}]")

    # Validate [radio]
    radio = data["radio"]
    for field in _REQUIRED_RADIO_FIELDS:
        if field not in radio:
            raise RigLoadError(
                f"{filename}: missing required field [radio].{field}"
            )

    civ_addr = radio["civ_addr"]
    if not (0x00 <= civ_addr <= 0xFF):
        raise RigLoadError(
            f"{filename}: [radio].civ_addr = {civ_addr} out of range 0x00–0xFF"
        )

    # Validate [capabilities]
    features = data["capabilities"].get("features", [])
    if not features:
        raise RigLoadError(f"{filename}: [capabilities].features must not be empty")
    for cap in features:
        if cap not in KNOWN_CAPABILITIES:
            raise RigLoadError(
                f"{filename}: unknown capability {cap!r}. "
                f"Known: {sorted(KNOWN_CAPABILITIES)}"
            )

    # Validate [vfo]
    vfo = data["vfo"]
    scheme = vfo.get("scheme", "")
    if scheme not in VALID_VFO_SCHEMES:
        raise RigLoadError(
            f"{filename}: [vfo].scheme must be one of {VALID_VFO_SCHEMES}, "
            f"got {scheme!r}"
        )

    # Validate [modes]
    modes = data["modes"].get("list", [])
    if not modes:
        raise RigLoadError(f"{filename}: [modes].list must not be empty")

    # Validate [filters]
    filters = data["filters"].get("list", [])
    if not filters:
        raise RigLoadError(f"{filename}: [filters].list must not be empty")

    # Parse commands
    commands_raw = data["commands"]
    overrides = commands_raw.pop("overrides", {})
    commands: dict[str, tuple[int, ...]] = {}
    for key, value in commands_raw.items():
        if isinstance(value, list):
            commands[key] = tuple(value)
    # Apply overrides
    for key, value in overrides.items():
        if isinstance(value, list):
            commands[key] = tuple(value)

    # Parse freq_ranges
    freq_ranges_data = data.get("freq_ranges", {}).get("ranges", [])

    # Parse VFO bytes
    vfo_main = tuple(vfo["main_select"]) if "main_select" in vfo else None
    vfo_sub = tuple(vfo["sub_select"]) if "sub_select" in vfo else None
    vfo_swap = tuple(vfo["swap"]) if "swap" in vfo else None

    # Parse cmd29 routes
    cmd29_raw = data.get("cmd29", {}).get("routes", [])
    cmd29_routes: list[tuple[int, int | None]] = []
    for entry in cmd29_raw:
        if len(entry) == 1:
            cmd29_routes.append((entry[0], None))
        elif len(entry) == 2:
            cmd29_routes.append((entry[0], entry[1]))

    # Parse spectrum
    spectrum = data.get("spectrum")

    return RigConfig(
        id=radio["id"],
        model=radio["model"],
        civ_addr=civ_addr,
        receiver_count=radio["receiver_count"],
        has_lan=radio["has_lan"],
        has_wifi=radio["has_wifi"],
        capabilities=tuple(features),
        modes=tuple(modes),
        filters=tuple(filters),
        vfo_scheme=scheme,
        vfo_main_select=vfo_main,
        vfo_sub_select=vfo_sub,
        vfo_swap=vfo_swap,
        freq_ranges=tuple(freq_ranges_data),
        commands=commands,
        cmd29_routes=tuple(cmd29_routes),
        spectrum=spectrum,
    )


def discover_rigs(directory: Path) -> dict[str, RigConfig]:
    """Discover and load all rig TOML files in a directory.

    Files starting with underscore are ignored (e.g. ``_schema.md``,
    ``_template.toml``).

    Returns:
        Dict mapping model name to ``RigConfig``.
    """
    rigs: dict[str, RigConfig] = {}
    if not directory.is_dir():
        return rigs

    for path in sorted(directory.glob("*.toml")):
        if path.name.startswith("_"):
            continue
        rig = load_rig(path)
        rigs[rig.model] = rig

    return rigs
