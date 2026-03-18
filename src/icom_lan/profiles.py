"""Radio profile and capability matrix for runtime routing and guards.

All profiles are loaded from TOML rig files in the ``rigs/`` directory.
There are **no** hardcoded profiles — adding a new radio means adding one
TOML file with zero Python changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "RadioProfile",
    "get_radio_profile",
    "resolve_radio_profile",
]

logger = logging.getLogger(__name__)


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


@dataclass(frozen=True, slots=True)
class BandInfo:
    """Amateur band definition for UI band selector."""

    name: str
    start: int  # Hz
    end: int  # Hz
    default: int  # Hz — default tuning frequency
    bsr_code: int | None = None  # Band Stack Register code for CI-V 0x1A 0x01


@dataclass(frozen=True, slots=True)
class FreqRangeInfo:
    """Frequency range with optional band plan."""

    start: int  # Hz
    end: int  # Hz
    label: str
    bands: tuple[BandInfo, ...] = ()


@dataclass(frozen=True, slots=True)
class RadioProfile:
    """Runtime radio profile used by command routing and capability checks."""

    id: str
    model: str
    civ_addr: int
    receiver_count: int
    capabilities: frozenset[str]
    cmd29_routes: frozenset[tuple[int, int | None]]
    vfo_main_code: int | None = None
    vfo_sub_code: int | None = None
    vfo_swap_code: int | None = None
    vfo_scheme: str = "main_sub"
    has_lan: bool = False
    freq_ranges: tuple[FreqRangeInfo, ...] = ()
    modes: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()
    att_values: tuple[int, ...] | None = None
    pre_values: tuple[int, ...] | None = None
    agc_modes: tuple[int, ...] | None = None
    agc_labels: dict[str, str] | None = None
    data_mode_count: int = 0
    data_mode_labels: dict[str, str] | None = None
    protocol_type: str = "civ"
    controls: dict[str, dict] | None = None
    meter_calibrations: dict[str, list[dict]] | None = None
    rules: tuple[dict, ...] = ()

    def supports_capability(self, capability: str) -> bool:
        return capability in self.capabilities

    def supports_receiver(self, receiver: int) -> bool:
        return 0 <= receiver < self.receiver_count

    def supports_cmd29(self, command: int, sub: int | None = None) -> bool:
        return (command, sub) in self.cmd29_routes or (
            command,
            None,
        ) in self.cmd29_routes


# ── TOML-driven profile registry ──────────────────────────────────

# Lazy-loaded on first access.  Populated from rigs/*.toml.
_profiles: dict[str, RadioProfile] | None = None
_by_normalized: dict[str, RadioProfile] = {}
_by_id: dict[str, RadioProfile] = {}
_by_civ_addr: dict[int, RadioProfile] = {}

# Search paths for rig TOML files (first existing directory wins).
_RIG_DIRS: list[Path] = [
    Path(__file__).resolve().parent.parent.parent / "rigs",  # dev: repo root/rigs/
    Path(__file__).resolve().parent / "rigs",                 # installed: package/rigs/
]


def _ensure_loaded() -> dict[str, RadioProfile]:
    """Load TOML rig profiles on first access (lazy init)."""
    global _profiles, _by_normalized, _by_id, _by_civ_addr

    if _profiles is not None:
        return _profiles

    # Import here to avoid circular imports
    from .rig_loader import discover_rigs

    _profiles = {}
    _by_normalized = {}
    _by_id = {}
    _by_civ_addr = {}

    for rig_dir in _RIG_DIRS:
        if rig_dir.is_dir():
            rigs = discover_rigs(rig_dir)
            for model, rig_config in rigs.items():
                profile = rig_config.to_profile()
                _profiles[model] = profile
                _by_normalized[_normalize(model)] = profile
                _by_id[_normalize(profile.id)] = profile
                _by_civ_addr.setdefault(profile.civ_addr, profile)
            if rigs:
                logger.debug(
                    "Loaded %d rig profiles from %s: %s",
                    len(rigs),
                    rig_dir,
                    ", ".join(sorted(rigs.keys())),
                )
                break  # use first directory that has rigs

    if not _profiles:
        logger.warning(
            "No rig TOML profiles found in search paths: %s",
            [str(p) for p in _RIG_DIRS],
        )

    return _profiles


def get_radio_profile(name_or_id: str) -> RadioProfile:
    """Return a profile by model name or profile id."""
    _ensure_loaded()
    key = _normalize(name_or_id)
    profile = _by_id.get(key) or _by_normalized.get(key)
    if profile is None:
        known = ", ".join(sorted(_ensure_loaded().keys()))
        raise KeyError(f"Unknown radio profile {name_or_id!r}. Known models: {known}")
    return profile


def resolve_radio_profile(
    *,
    profile: RadioProfile | str | None = None,
    model: str | None = None,
    radio_addr: int | None = None,
) -> RadioProfile:
    """Resolve runtime profile from explicit profile/model or CI-V address."""
    _ensure_loaded()
    if isinstance(profile, RadioProfile):
        return profile
    if isinstance(profile, str) and profile.strip():
        return get_radio_profile(profile)
    if isinstance(model, str) and model.strip():
        return get_radio_profile(model)
    if radio_addr is not None and radio_addr in _by_civ_addr:
        return _by_civ_addr[radio_addr]
    # Default fallback — first profile with has_lan=True, or first available
    profiles = _ensure_loaded()
    for p in profiles.values():
        if p.has_lan:
            return p
    if profiles:
        return next(iter(profiles.values()))
    raise KeyError("No rig profiles loaded — check rigs/ directory")


def reload_profiles() -> None:
    """Force reload of TOML profiles (useful for tests)."""
    global _profiles
    _profiles = None
    _ensure_loaded()
