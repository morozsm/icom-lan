"""Radio model presets with CI-V addresses and capabilities.

Reference: wfview rigs/*.rig files.
"""

from dataclasses import dataclass

__all__ = ["RadioModel", "RADIOS"]


@dataclass(frozen=True, slots=True)
class RadioModel:
    """Radio model preset.

    Attributes:
        name: Human-readable model name.
        civ_addr: Default CI-V address.
        receivers: Number of independent receivers.
        has_lan: Whether the radio supports LAN control.
        has_wifi: Whether the radio has built-in WiFi.
    """

    name: str
    civ_addr: int
    receivers: int = 1
    has_lan: bool = True
    has_wifi: bool = False


#: Known Icom radio models with LAN/WiFi support.
RADIOS: dict[str, RadioModel] = {
    "IC-7610": RadioModel(
        name="IC-7610",
        civ_addr=0x98,
        receivers=2,
    ),
    "IC-7300": RadioModel(
        name="IC-7300",
        civ_addr=0x94,
    ),
    "IC-705": RadioModel(
        name="IC-705",
        civ_addr=0xA4,
        has_wifi=True,
    ),
    "IC-9700": RadioModel(
        name="IC-9700",
        civ_addr=0xA2,
        receivers=2,
    ),
    "IC-R8600": RadioModel(
        name="IC-R8600",
        civ_addr=0x96,
    ),
    "IC-7851": RadioModel(
        name="IC-7851",
        civ_addr=0x8E,
        receivers=2,
    ),
}


def _normalize_model_name(model: str) -> str:
    """Normalize model names for flexible lookup."""
    return "".join(ch for ch in model.upper() if ch.isalnum())


_RADIOS_BY_NORMALIZED: dict[str, RadioModel] = {
    _normalize_model_name(name): radio for name, radio in RADIOS.items()
}


def get_civ_addr(model: str) -> int:
    """Look up CI-V address by model name.

    Args:
        model: Model name (e.g. "IC-705", case-insensitive).

    Returns:
        CI-V address byte.

    Raises:
        KeyError: If model not found.
    """
    key = _normalize_model_name(model)
    if key in _RADIOS_BY_NORMALIZED:
        return _RADIOS_BY_NORMALIZED[key].civ_addr
    raise KeyError(f"Unknown radio model: {model}. Known: {', '.join(RADIOS)}")
