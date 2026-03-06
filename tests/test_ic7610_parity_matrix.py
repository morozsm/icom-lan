from __future__ import annotations

import importlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs/parity/ic7610_command_matrix.json"
WFVIEW_RIG_PATH = ROOT / "references/wfview/rigs/IC-7610.rig"
PROJECT_DOC_PATH = ROOT / "docs/PROJECT.md"
PARITY_README_PATH = ROOT / "docs/parity/README.md"
ALLOWED_STATUSES = {"implemented", "partial", "missing"}


def _load_matrix() -> dict[str, object]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _parse_wfview_rig() -> dict[int, dict[str, object]]:
    text = WFVIEW_RIG_PATH.read_text(encoding="utf-8")
    commands: dict[int, dict[str, object]] = {}
    for match in re.finditer(r"^Commands\\(\d+)\\Type=(.+)$", text, flags=re.MULTILINE):
        command_id = int(match.group(1))
        commands[command_id] = {"name": match.group(2)}
    for key in ("String", "Command29", "GetCommand", "SetCommand", "Admin"):
        pattern = re.compile(rf"^Commands\\(\d+)\\{key}=(.+)$", flags=re.MULTILINE)
        for match in pattern.finditer(text):
            command_id = int(match.group(1))
            value = match.group(2)
            if key == "String":
                parsed: object = value
            else:
                parsed = value.lower() == "true"
            commands.setdefault(command_id, {})[key.lower()] = parsed
    return commands


def _resolve_symbol(symbol_ref: str) -> object:
    module_name, _, qualname = symbol_ref.partition(":")
    if not module_name or not qualname:
        raise AssertionError(f"Invalid runtime symbol reference: {symbol_ref!r}")
    module = importlib.import_module(module_name)
    target: object = module
    for part in qualname.split("."):
        target = getattr(target, part)
    return target


def _assert_pattern_refs_exist(pattern_refs: list[str]) -> None:
    for pattern_ref in pattern_refs:
        rel_path, _, pattern = pattern_ref.partition("::")
        if not rel_path or not pattern:
            raise AssertionError(f"Invalid pattern reference: {pattern_ref!r}")
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        if re.search(pattern, text, flags=re.MULTILINE) is None:
            raise AssertionError(
                f"Pattern {pattern!r} not found in {rel_path}"
            )


def test_ic7610_parity_matrix_matches_wfview_reference() -> None:
    matrix = _load_matrix()
    commands = matrix["commands"]
    rig_commands = _parse_wfview_rig()

    assert matrix["radio_model"] == "IC-7610"
    assert matrix["reference"]["wfview_rig"] == "references/wfview/rigs/IC-7610.rig"
    assert len(commands) == len(rig_commands) == 134

    seen_ids: set[int] = set()
    for entry in commands:
        command_id = entry["id"]
        seen_ids.add(command_id)
        rig_entry = rig_commands[command_id]
        assert entry["name"] == rig_entry["name"]
        assert entry["wire"] == rig_entry["string"]
        assert entry["command29"] == rig_entry["command29"]
        assert entry["get"] == rig_entry["getcommand"]
        assert entry["set"] == rig_entry["setcommand"]
        assert entry["admin"] == rig_entry["admin"]

    assert seen_ids == set(range(1, 135))


def test_ic7610_parity_matrix_statuses_and_family_counts_are_consistent() -> None:
    matrix = _load_matrix()
    commands = matrix["commands"]
    families = matrix["families"]

    status_totals = {status: 0 for status in ALLOWED_STATUSES}
    family_totals = {
        family_key: {status: 0 for status in ALLOWED_STATUSES}
        for family_key in families
    }

    for entry in commands:
        status = entry["status"]
        family = entry["family"]
        assert status in ALLOWED_STATUSES
        assert family in families
        status_totals[status] += 1
        family_totals[family][status] += 1

    assert status_totals == matrix["status_totals"]
    for family_key, totals in family_totals.items():
        assert totals == families[family_key]["counts"]


def test_ic7610_parity_matrix_supported_entries_have_real_evidence() -> None:
    matrix = _load_matrix()

    for entry in matrix["commands"]:
        status = entry["status"]
        runtime_symbols = entry.get("runtime_symbols", [])
        test_patterns = entry.get("test_patterns", [])
        notes = entry.get("notes", "")

        if status == "implemented":
            assert runtime_symbols, f"implemented command #{entry['id']} lacks runtime evidence"
            assert test_patterns, f"implemented command #{entry['id']} lacks test evidence"
        if status == "partial":
            assert notes, f"partial command #{entry['id']} needs a note"
            assert runtime_symbols or test_patterns, (
                f"partial command #{entry['id']} lacks runtime/test evidence"
            )

        for symbol_ref in runtime_symbols:
            _resolve_symbol(symbol_ref)
        _assert_pattern_refs_exist(test_patterns)


def test_project_doc_parity_summary_matches_matrix() -> None:
    matrix = _load_matrix()
    project_doc = PROJECT_DOC_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"IC-7610 parity matrix \(issue #139, 2026-03-06\): "
        r"(?P<implemented>\d+) implemented, "
        r"(?P<partial>\d+) partial, "
        r"(?P<missing>\d+) missing",
        project_doc,
    )
    assert match is not None, "docs/PROJECT.md is missing the parity summary line"
    assert {
        "implemented": int(match.group("implemented")),
        "partial": int(match.group("partial")),
        "missing": int(match.group("missing")),
    } == matrix["status_totals"]


def test_parity_docs_and_integration_profile_are_explicit() -> None:
    matrix = _load_matrix()
    parity_readme = PARITY_README_PATH.read_text(encoding="utf-8")
    project_doc = PROJECT_DOC_PATH.read_text(encoding="utf-8")
    integration_conftest = (ROOT / "tests/integration/conftest.py").read_text(
        encoding="utf-8"
    )
    marked_files = {
        "tests/integration/test_media_scope_integration.py": (
            ROOT / "tests/integration/test_media_scope_integration.py"
        ).read_text(encoding="utf-8"),
        "tests/integration/test_controls_extended_integration.py": (
            ROOT / "tests/integration/test_controls_extended_integration.py"
        ).read_text(encoding="utf-8"),
    }

    assert matrix["families"]["baseline_core"]["owner_issue"] is None
    assert "baseline_core` -> pre-M4 baseline (no open issue owner)" in parity_readme
    assert 'integration and ic7610_parity' in parity_readme
    assert 'integration and ic7610_parity' in project_doc
    assert "ic7610_parity:" in integration_conftest
    assert any("pytest.mark.ic7610_parity" in text for text in marked_files.values())
