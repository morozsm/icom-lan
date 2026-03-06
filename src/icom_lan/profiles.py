"""Radio profile and capability matrix for runtime routing and guards."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "RadioProfile",
    "get_radio_profile",
    "resolve_radio_profile",
]


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


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

    def supports_capability(self, capability: str) -> bool:
        return capability in self.capabilities

    def supports_receiver(self, receiver: int) -> bool:
        return 0 <= receiver < self.receiver_count

    def supports_cmd29(self, command: int, sub: int | None = None) -> bool:
        return (
            (command, sub) in self.cmd29_routes
            or (command, None) in self.cmd29_routes
        )


_DUAL_CAPS = frozenset(
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

_SINGLE_CAPS = frozenset(
    {
        "audio",
        "scope",
        "meters",
        "tx",
        "cw",
        "rf_gain",
        "af_level",
        "squelch",
    }
)

_CMD29_7610 = frozenset(
    {
        (0x11, None),   # ATT
        (0x14, 0x01),   # AF
        (0x14, 0x02),   # RF gain
        (0x14, 0x03),   # SQL
        (0x14, 0x05),   # APF Type Level
        (0x14, 0x06),   # NR Level
        (0x14, 0x07),   # PBT Inner
        (0x14, 0x08),   # PBT Outer
        (0x14, 0x12),   # NB Level
        (0x14, 0x13),   # DIGI-SEL Shift
        (0x15, 0x01),   # S-meter squelch status
        (0x15, 0x05),   # Various squelch
        (0x16, 0x02),   # PREAMP
        (0x16, 0x32),   # Audio Peak Filter
        (0x16, 0x22),   # NB
        (0x16, 0x40),   # NR
        (0x16, 0x41),   # Auto Notch
        (0x16, 0x48),   # Manual Notch
        (0x16, 0x4E),   # DIGI-SEL
        (0x16, 0x4F),   # Twin Peak Filter
        (0x16, 0x56),   # Filter Shape
        (0x16, 0x65),   # IP+
        (0x1A, 0x04),   # AGC Time Constant
        (0x1A, 0x09),   # AF Mute
    }
)

_PROFILES: dict[str, RadioProfile] = {
    "IC-7610": RadioProfile(
        id="icom_ic7610",
        model="IC-7610",
        civ_addr=0x98,
        receiver_count=2,
        capabilities=_DUAL_CAPS,
        cmd29_routes=_CMD29_7610,
        vfo_main_code=0xD0,
        vfo_sub_code=0xD1,
        vfo_swap_code=0xB0,
    ),
    "IC-9700": RadioProfile(
        id="icom_ic9700",
        model="IC-9700",
        civ_addr=0xA2,
        receiver_count=2,
        capabilities=_DUAL_CAPS,
        cmd29_routes=_CMD29_7610,
        vfo_main_code=0xD0,
        vfo_sub_code=0xD1,
        vfo_swap_code=0xB0,
    ),
    "IC-7300": RadioProfile(
        id="icom_ic7300",
        model="IC-7300",
        civ_addr=0x94,
        receiver_count=1,
        capabilities=_SINGLE_CAPS,
        cmd29_routes=frozenset(),
    ),
    "IC-705": RadioProfile(
        id="icom_ic705",
        model="IC-705",
        civ_addr=0xA4,
        receiver_count=1,
        capabilities=_SINGLE_CAPS,
        cmd29_routes=frozenset(),
    ),
}

_PROFILE_BY_NORMALIZED: dict[str, RadioProfile] = {
    _normalize(profile.model): profile for profile in _PROFILES.values()
}
_PROFILE_BY_ID: dict[str, RadioProfile] = {
    _normalize(profile.id): profile for profile in _PROFILES.values()
}
_PROFILE_BY_CIV_ADDR: dict[int, RadioProfile] = {}
for _profile in _PROFILES.values():
    _PROFILE_BY_CIV_ADDR.setdefault(_profile.civ_addr, _profile)


def get_radio_profile(name_or_id: str) -> RadioProfile:
    """Return a profile by model name or profile id."""
    key = _normalize(name_or_id)
    profile = _PROFILE_BY_ID.get(key) or _PROFILE_BY_NORMALIZED.get(key)
    if profile is None:
        known = ", ".join(sorted(_PROFILES.keys()))
        raise KeyError(f"Unknown radio profile {name_or_id!r}. Known models: {known}")
    return profile


def resolve_radio_profile(
    *,
    profile: RadioProfile | str | None = None,
    model: str | None = None,
    radio_addr: int | None = None,
) -> RadioProfile:
    """Resolve runtime profile from explicit profile/model or CI-V address."""
    if isinstance(profile, RadioProfile):
        return profile
    if isinstance(profile, str) and profile.strip():
        return get_radio_profile(profile)
    if isinstance(model, str) and model.strip():
        return get_radio_profile(model)
    if radio_addr is not None and radio_addr in _PROFILE_BY_CIV_ADDR:
        return _PROFILE_BY_CIV_ADDR[radio_addr]
    return _PROFILES["IC-7610"]
