"""Template tests: every shipped validation template parses and is valid."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rigplane.core.capabilities import KNOWN_CAPABILITIES
from rigplane.validation import validate_template_dict

_TEMPLATES_DIR = (
    Path(__file__).resolve().parents[1] / "docs" / "validation" / "templates"
)


def _template_paths() -> list[Path]:
    return sorted(_TEMPLATES_DIR.glob("*.json"))


def test_templates_dir_has_templates() -> None:
    assert _template_paths(), "expected at least one validation template"


@pytest.mark.parametrize("path", _template_paths(), ids=lambda p: p.stem)
def test_template_parses_and_validates(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    template = validate_template_dict(data)
    for entry in template.entries:
        if entry.capability:
            assert entry.capability in KNOWN_CAPABILITIES
