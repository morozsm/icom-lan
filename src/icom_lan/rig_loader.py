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
        # Receiver
        "audio",
        "dual_rx",
        "dual_watch",
        "af_level",
        "rf_gain",
        "squelch",
        # RF front end
        "attenuator",
        "preamp",
        "digisel",
        "ip_plus",
        # Antenna
        "antenna",
        "rx_antenna",
        # DSP / Noise
        "nb",
        "nr",
        "notch",
        "apf",
        "twin_peak",
        # Filter
        "pbt",
        "filter_width",
        "filter_shape",
        # TX
        "tx",
        "split",
        "vox",
        "compressor",
        "monitor",
        "drive_gain",
        "ssb_tx_bw",
        # CW
        "cw",
        "break_in",
        # RIT / XIT
        "rit",
        "xit",
        # Tuner
        "tuner",
        # Metering
        "meters",
        # Scope
        "scope",
        # Tone
        "repeater_tone",
        "tsql",
        # Data
        "data_mode",
        # System
        "power_control",
        "dial_lock",
        "scan",
        "bsr",
        "main_sub_tracking",
    }
)

VALID_VFO_SCHEMES = {"ab", "main_sub", "ab_shared", "single"}
VALID_PROTOCOL_TYPES = {"civ", "kenwood_cat", "yaesu_cat"}
VALID_CONTROL_STYLES = {"toggle", "stepped", "selector", "toggle_and_level", "level_is_toggle"}
VALID_RULE_KINDS = {"mutex", "disables", "requires", "value_limit"}

_REQUIRED_SECTIONS = ("radio", "capabilities", "modes", "filters", "vfo")
_REQUIRED_RADIO_FIELDS = ("id", "model", "receiver_count", "has_lan", "has_wifi")


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
    default_baud: int
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
    att_values: tuple[int, ...] | None
    pre_values: tuple[int, ...] | None
    agc_modes: tuple[int, ...] | None
    agc_labels: dict[str, str] | None
    filter_width_min: int = 50
    filter_width_max: int = 9999
    data_mode_count: int = 0
    data_mode_labels: dict[str, str] | None = None
    protocol_type: str = "civ"
    protocol_address: int | None = None
    protocol_baud: int | None = None
    controls: dict[str, dict] | None = None
    meter_calibrations: dict[str, list[dict]] | None = None
    meter_redlines: dict[str, int] | None = None
    rules: tuple[dict, ...] = ()

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
                        bsr_code=b.get("bsr_code"),
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
            vfo_scheme=self.vfo_scheme,
            has_lan=self.has_lan,
            freq_ranges=ranges,
            modes=tuple(self.modes),
            filters=tuple(self.filters),
            filter_width_min=self.filter_width_min,
            filter_width_max=self.filter_width_max,
            att_values=self.att_values,
            pre_values=self.pre_values,
            agc_modes=self.agc_modes,
            agc_labels=self.agc_labels,
            data_mode_count=self.data_mode_count,
            data_mode_labels=self.data_mode_labels,
            protocol_type=self.protocol_type,
            controls=self.controls,
            meter_calibrations=self.meter_calibrations,
            rules=self.rules,
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
    for field_name in _REQUIRED_RADIO_FIELDS:
        if field_name not in radio:
            raise RigLoadError(
                f"{filename}: missing required field [radio].{field_name}"
            )

    # civ_addr is optional (default 0 for non-civ radios); validate range if present
    if "civ_addr" in radio:
        civ_addr = radio["civ_addr"]
        if not (0x00 <= civ_addr <= 0xFF):
            raise RigLoadError(
                f"{filename}: [radio].civ_addr = {civ_addr} out of range 0x00–0xFF"
            )
    else:
        civ_addr = 0

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
    filter_section = data["filters"]
    filters = filter_section.get("list", [])
    if not filters:
        raise RigLoadError(f"{filename}: [filters].list must not be empty")
    filter_width_min = int(filter_section.get("width_min_hz", 50))
    filter_width_max = int(filter_section.get("width_max_hz", 9999))

    # Parse [protocol] (optional)
    proto_section = data.get("protocol", {})
    protocol_type = proto_section.get("type", "civ")
    if protocol_type not in VALID_PROTOCOL_TYPES:
        raise RigLoadError(
            f"{filename}: [protocol].type must be one of {VALID_PROTOCOL_TYPES}, "
            f"got {protocol_type!r}"
        )
    protocol_address = proto_section.get("address")
    protocol_baud = proto_section.get("baud")

    # Parse commands (optional for non-civ protocols)
    commands: dict[str, tuple[int, ...]] = {}
    if "commands" in data:
        commands_raw = dict(data["commands"])
        overrides = commands_raw.pop("overrides", {})
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
    vfo_swap_val = tuple(vfo["swap"]) if "swap" in vfo else None

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

    # Parse attenuator/preamp/agc (optional sections)
    att_section = data.get("attenuator", {})
    att_values = tuple(att_section["values"]) if "values" in att_section else None

    pre_section = data.get("preamp", {})
    pre_values = tuple(pre_section["values"]) if "values" in pre_section else None

    agc_section = data.get("agc", {})
    agc_modes = tuple(agc_section["modes"]) if "modes" in agc_section else None
    agc_labels = dict(agc_section["labels"]) if "labels" in agc_section else None

    # Parse [data_mode] (optional)
    # If data_mode is in features but no [data_mode] section, default to 1 mode (OFF/DATA)
    data_mode_section = data.get("data_mode", {})
    has_data_mode_feature = "data_mode" in features
    if data_mode_section:
        data_mode_count = int(data_mode_section.get("count", 0))
        data_mode_labels = dict(data_mode_section["labels"]) if "labels" in data_mode_section else None
    elif has_data_mode_feature:
        data_mode_count = 1
        data_mode_labels = {"0": "OFF", "1": "DATA"}
    else:
        data_mode_count = 0
        data_mode_labels = None

    # Parse [controls] (optional)
    controls_raw = data.get("controls")
    controls: dict[str, dict] | None = None
    if controls_raw is not None:
        controls = {}
        for ctrl_name, ctrl_data in controls_raw.items():
            if isinstance(ctrl_data, dict):
                style = ctrl_data.get("style")
                if style is not None and style not in VALID_CONTROL_STYLES:
                    raise RigLoadError(
                        f"{filename}: [controls.{ctrl_name}].style must be one of "
                        f"{VALID_CONTROL_STYLES}, got {style!r}"
                    )
                controls[ctrl_name] = dict(ctrl_data)

    # Parse [meters] (optional)
    meters_raw = data.get("meters")
    meter_calibrations: dict[str, list[dict]] | None = None
    meter_redlines: dict[str, int] | None = None
    if meters_raw is not None:
        meter_calibrations = {}
        meter_redlines = {}
        for meter_name, meter_data in meters_raw.items():
            if isinstance(meter_data, dict):
                if "calibration" in meter_data:
                    meter_calibrations[meter_name] = list(meter_data["calibration"])
                if "redline_raw" in meter_data:
                    meter_redlines[meter_name] = meter_data["redline_raw"]
        if not meter_calibrations:
            meter_calibrations = None
        if not meter_redlines:
            meter_redlines = None

    # Parse [[rules]] (optional)
    rules_raw = data.get("rules", [])
    rules: list[dict] = []
    for rule in rules_raw:
        kind = rule.get("kind")
        if kind not in VALID_RULE_KINDS:
            raise RigLoadError(
                f"{filename}: rule kind must be one of {VALID_RULE_KINDS}, "
                f"got {kind!r}"
            )
        rules.append(dict(rule))

    return RigConfig(
        id=radio["id"],
        model=radio["model"],
        civ_addr=civ_addr,
        receiver_count=radio["receiver_count"],
        has_lan=radio["has_lan"],
        has_wifi=radio["has_wifi"],
        default_baud=radio.get("default_baud", 19200),
        capabilities=tuple(features),
        modes=tuple(modes),
        filters=tuple(filters),
        filter_width_min=filter_width_min,
        filter_width_max=filter_width_max,
        vfo_scheme=scheme,
        vfo_main_select=vfo_main,
        vfo_sub_select=vfo_sub,
        vfo_swap=vfo_swap_val,
        freq_ranges=tuple(freq_ranges_data),
        commands=commands,
        cmd29_routes=tuple(cmd29_routes),
        spectrum=spectrum,
        att_values=att_values,
        pre_values=pre_values,
        agc_modes=agc_modes,
        agc_labels=agc_labels,
        data_mode_count=data_mode_count,
        data_mode_labels=data_mode_labels,
        protocol_type=protocol_type,
        protocol_address=protocol_address,
        protocol_baud=protocol_baud,
        controls=controls,
        meter_calibrations=meter_calibrations,
        meter_redlines=meter_redlines,
        rules=tuple(rules),
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
