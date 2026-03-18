"""Naming parity: every TOML command name must exist in commands.py and radio.py.

Part of epic #295 — TOML as single source of truth for command naming.
"""

import importlib
import inspect
import tomllib
from pathlib import Path

import pytest

RIGS_DIR = Path(__file__).parent.parent / "rigs"

# Some TOML commands intentionally map to a different radio.py method
# (higher-level abstraction).  These are exempted from the direct-name check.
_COMPOUND_COMMANDS: dict[str, str] = {
    # TOML name → radio.py method name
    "ptt_on": "set_ptt",
    "ptt_off": "set_ptt",
    "power_on": "set_powerstat",
    "power_off": "set_powerstat",
    "scope_on": "enable_scope",
    "scope_off": "disable_scope",
    "scope_data_output": "enable_scope",
    "set_dual_watch_on": "set_dual_watch",
    "set_dual_watch_off": "set_dual_watch",
}


def _ci_v_toml_files() -> list[Path]:
    """Return TOML files with populated CI-V command sections."""
    result = []
    for p in sorted(RIGS_DIR.glob("*.toml")):
        with open(p, "rb") as f:
            data = tomllib.load(f)
        cmds = data.get("commands", {})
        # Skip if commands section is empty or only has sub-tables / comments
        if any(isinstance(v, list) for v in cmds.values()):
            result.append(p)
    return result


def _not_implemented_names(toml_path: Path) -> set[str]:
    """Return command names flagged with NOT_IMPLEMENTED in the raw TOML text."""
    raw = toml_path.read_text()
    names: set[str] = set()
    for line in raw.splitlines():
        if "NOT_IMPLEMENTED" in line and "=" in line:
            name = line.split("=")[0].strip().lstrip("#").strip()
            if name:
                names.add(name)
    return names


def _active_commands(toml_path: Path) -> list[str]:
    """Return all active (non-NOT_IMPLEMENTED) command names from a TOML file."""
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    not_impl = _not_implemented_names(toml_path)

    names: list[str] = []
    cmds = data.get("commands", {})
    for key, value in cmds.items():
        if key == "overrides":
            # handled separately below
            continue
        if isinstance(value, list) and key not in not_impl:
            names.append(key)

    overrides = cmds.get("overrides", {})
    for key, value in overrides.items():
        if isinstance(value, list) and key not in not_impl:
            names.append(key)

    return names


@pytest.fixture(params=_ci_v_toml_files(), ids=lambda p: p.stem)
def rig_toml(request: pytest.FixtureRequest) -> Path:
    return request.param  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Test 1 — override names must follow get_/set_ convention
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="Pending: epic #295 naming standardization", strict=False)
def test_overrides_have_prefix(rig_toml: Path) -> None:
    """All [commands.overrides] entries must start with get_ or set_."""
    with open(rig_toml, "rb") as f:
        data = tomllib.load(f)

    overrides = data.get("commands", {}).get("overrides", {})
    not_impl = _not_implemented_names(rig_toml)

    bad: list[str] = []
    for key, value in overrides.items():
        if not isinstance(value, list):
            continue
        if key in not_impl:
            continue
        if not (key.startswith("get_") or key.startswith("set_")):
            bad.append(key)

    assert not bad, (
        f"{rig_toml.name}: override command names must start with get_ or set_, "
        f"but these do not: {bad}"
    )


# ---------------------------------------------------------------------------
# Test 2 — every active TOML command must exist in commands.py
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="Pending: epic #295 naming standardization", strict=False)
def test_toml_commands_in_commands_module(rig_toml: Path) -> None:
    """Each active TOML command has a matching function in commands.py."""
    commands_mod = importlib.import_module("icom_lan.commands")
    available = {name for name, _ in inspect.getmembers(commands_mod, inspect.isfunction)}

    missing: list[str] = []
    for cmd in _active_commands(rig_toml):
        if cmd not in available:
            missing.append(cmd)

    assert not missing, (
        f"{rig_toml.name}: commands missing from icom_lan.commands: {missing}"
    )


# ---------------------------------------------------------------------------
# Test 3 — every active TOML command must exist in IcomRadio (or be compound)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="Pending: epic #295 naming standardization", strict=False)
def test_toml_commands_in_radio(rig_toml: Path) -> None:
    """Each active TOML command has a matching method in IcomRadio (or is in _COMPOUND_COMMANDS)."""
    from icom_lan.radio import IcomRadio  # noqa: PLC0415

    radio_methods = {
        name
        for name, _ in inspect.getmembers(IcomRadio, predicate=inspect.isfunction)
    }

    missing: list[str] = []
    for cmd in _active_commands(rig_toml):
        if cmd in _COMPOUND_COMMANDS:
            # Verify the compound target method exists
            target = _COMPOUND_COMMANDS[cmd]
            if target not in radio_methods:
                missing.append(f"{cmd} (compound target '{target}' missing)")
        elif cmd not in radio_methods:
            missing.append(cmd)

    assert not missing, (
        f"{rig_toml.name}: commands missing from IcomRadio: {missing}"
    )
