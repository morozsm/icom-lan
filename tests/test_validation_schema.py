"""Schema tests for the real-radio validation matrix contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rigplane.validation import (
    CheckStatus,
    FailureDomain,
    MatrixTemplate,
    SchemaValidationError,
    ValidationArtifact,
    validate_artifact_dict,
    validate_template_dict,
)

_FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def _load_json(name: str) -> object:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def test_valid_template_fixture_builds_matrix_template() -> None:
    template = validate_template_dict(_load_json("validation_template_ic7300.json"))
    assert isinstance(template, MatrixTemplate)
    assert template.radio.model == "IC-7300"
    assert template.radio.profile_id == "ic7300"
    assert any(entry.check_id == "tuner.tune" for entry in template.entries)


def test_invalid_capability_tag_raises() -> None:
    data = _load_json("validation_template_ic7300.json")
    assert isinstance(data, dict)
    entries = data["entries"]
    assert isinstance(entries, list)
    entries[0]["capability"] = "not_a_real_capability"
    with pytest.raises(SchemaValidationError):
        validate_template_dict(data)


def test_mixed_artifact_fixture_validates() -> None:
    artifact = validate_artifact_dict(_load_json("validation_artifact_mixed.json"))
    assert isinstance(artifact, ValidationArtifact)
    statuses = {check.status for level in artifact.levels for check in level.checks}
    assert CheckStatus.PASS in statuses
    assert CheckStatus.FAIL in statuses
    assert CheckStatus.UNSUPPORTED in statuses


def test_reverse_sync_fail_fixture_carries_readback_domain() -> None:
    artifact = validate_artifact_dict(
        _load_json("validation_artifact_reverse_sync_fail.json")
    )
    reverse_sync = [
        check
        for level in artifact.levels
        for check in level.checks
        if check.check_id == "freq.reverse_sync"
    ]
    assert len(reverse_sync) == 1
    check = reverse_sync[0]
    assert check.status is CheckStatus.FAIL
    assert check.failure_domain is FailureDomain.READBACK


def test_fail_without_failure_domain_raises() -> None:
    data = {
        "schema_version": 1,
        "tool": "rigplane-validation-matrix",
        "mode": "hardware",
        "core_version": "2.5.1",
        "radio": {"model": "IC-7300", "profile_id": "ic7300"},
        "transport": {"backend": "lan"},
        "safety": {"tx_allowed": False, "tuner_allowed": False},
        "levels": [
            {
                "level": 2,
                "checks": [
                    {
                        "check_id": "freq.write",
                        "capability": "",
                        "level": 2,
                        "status": "fail",
                        "declaration": "supported",
                        "summary": "Failed without a domain.",
                    }
                ],
            }
        ],
        "metadata": {},
    }
    with pytest.raises(SchemaValidationError):
        validate_artifact_dict(data)
