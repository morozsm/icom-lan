"""Golden-fixture test runner for the rigctld protocol layer.

Loads tests/golden/protocol_golden.json and for each fixture:
  1. parse_line(input)  → RigctldCommand   (or direct cmd from fixture)
  2. handler.execute(cmd) → RigctldResponse  (with AsyncMock radio per mock spec)
  3. format_response(cmd, resp, session) → bytes
  4. Assert exact wire bytes match expected_output (normal mode)
  5. Assert exact wire bytes match extended_output (extended mode, if present)

Fixture fields
--------------
input            : str  — raw text fed to parse_line (mutually exclusive with cmd)
cmd              : dict — direct RigctldCommand spec, bypasses parse_line
expect_parse_error : bool — if true, parse_line must raise ValueError
mock             : dict — radio method mocks:
                      key           → return_value (int/bool/float/list)
                      get_mode_info → [mode_int, filter_or_null]  (special)
                      "<method>__exc" → "ConnectionError"|"TimeoutError"
read_only        : bool — use handler with read_only=True config
expected_output  : str  — normal-mode wire string
extended_output  : str  — extended-mode wire string (optional)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from icom_lan.exceptions import (
    ConnectionError as IcomConnectionError,
    TimeoutError as IcomTimeoutError,
)
from icom_lan.rigctld.contract import (
    ClientSession,
    HamlibError,
    RigctldCommand,
    RigctldConfig,
)
from icom_lan.rigctld.handler import RigctldHandler
from icom_lan.rigctld.protocol import format_error, format_response, parse_line
from icom_lan.types import Mode

# ---------------------------------------------------------------------------
# Load fixtures at module level so parametrize sees them at collection time.
# ---------------------------------------------------------------------------

_FIXTURES_PATH = Path(__file__).parent / "golden" / "protocol_golden.json"
_FIXTURES: list[dict] = json.loads(_FIXTURES_PATH.read_text())


# ---------------------------------------------------------------------------
# Mock-radio builder
# ---------------------------------------------------------------------------

_EXC_MAP: dict[str, Exception] = {
    "ConnectionError": IcomConnectionError("mock connection error"),
    "TimeoutError": IcomTimeoutError("mock timeout"),
}


def _make_mock_radio(mock_spec: dict) -> AsyncMock:
    """Build an AsyncMock radio from a fixture mock-spec dict.

    Keys ending in ``__exc`` set a side_effect instead of a return_value.
    The ``get_mode_info`` key expects a [mode_int, filter_or_null] list which
    is converted to the ``(Mode, int|None)`` tuple the handler expects.
    Level getters (get_s_meter, get_power, get_swr) are set as AsyncMock so
    await in the handler returns the value.
    """
    radio = AsyncMock()
    # Sensible defaults so get_mode doesn't blow up when not explicitly mocked.
    radio.get_data_mode.return_value = False

    _async_level_getters = {"get_s_meter", "get_power", "get_swr"}

    for key, value in mock_spec.items():
        if key.endswith("__exc"):
            method = key[:-5]
            exc = _EXC_MAP[value]
            getattr(radio, method).side_effect = exc
        elif key == "get_mode_info":
            mode_int, filt = value[0], value[1]
            getattr(radio, key).return_value = (Mode(mode_int), filt)
        elif key in _async_level_getters:
            setattr(radio, key, AsyncMock(return_value=value))
        else:
            getattr(radio, key).return_value = value

    return radio


# ---------------------------------------------------------------------------
# Parametrized test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture", _FIXTURES, ids=[f["id"] for f in _FIXTURES])
async def test_golden_protocol(fixture: dict) -> None:
    """Execute one golden fixture end-to-end through parse → handler → format."""
    mock_spec = fixture.get("mock", {})
    radio = _make_mock_radio(mock_spec)
    read_only = fixture.get("read_only", False)
    # cache_ttl=0.0 → cache always expired → deterministic radio calls in tests.
    config = RigctldConfig(read_only=read_only, cache_ttl=0.0)
    # Populate level cache when mock has level getters so get_level returns numeric (not RPRT -4)
    from icom_lan.rigctld.state_cache import StateCache

    cache = StateCache()
    if "get_s_meter" in mock_spec:
        cache.update_s_meter(mock_spec["get_s_meter"])
    if "get_power" in mock_spec:
        cache.update_rf_power(float(mock_spec["get_power"]) / 255.0)
    if "get_swr" in mock_spec:
        raw = mock_spec["get_swr"]
        swr_display = 1.0 + (float(raw) / 255.0) * 4.0
        cache.update_swr(swr_display)
    handler = RigctldHandler(radio, config, cache=cache)

    normal_session = ClientSession()
    extended_session = ClientSession(extended_mode=True)

    # ── Branch 1: parse error expected ──────────────────────────────────────
    if fixture.get("expect_parse_error", False):
        raw = fixture["input"].encode("ascii")
        with pytest.raises(ValueError):
            parse_line(raw)
        # Server translates parse errors to ENIMPL (-4).
        expected_wire = format_error(HamlibError.ENIMPL).decode()
        assert fixture["expected_output"] == expected_wire, (
            f"[{fixture['id']}] parse-error expected_output mismatch"
        )
        return

    # ── Branch 2: direct cmd dict (bypasses parse_line) ─────────────────────
    if "cmd" in fixture:
        cmd_data = fixture["cmd"]
        cmd = RigctldCommand(
            short_cmd=cmd_data["short_cmd"],
            long_cmd=cmd_data["long_cmd"],
            args=tuple(cmd_data.get("args", [])),
            is_set=cmd_data.get("is_set", False),
        )

    # ── Branch 3: normal input through parse_line ────────────────────────────
    else:
        raw = fixture["input"].encode("ascii")
        cmd = parse_line(raw)

    # Execute command through handler.
    resp = await handler.execute(cmd)

    # Normal mode assertion.
    normal_out = format_response(cmd, resp, normal_session).decode("ascii")
    assert normal_out == fixture["expected_output"], (
        f"[{fixture['id']}] normal mode mismatch\n"
        f"  got:      {normal_out!r}\n"
        f"  expected: {fixture['expected_output']!r}"
    )

    # Extended mode assertion (optional).
    if "extended_output" in fixture:
        extended_out = format_response(cmd, resp, extended_session).decode("ascii")
        assert extended_out == fixture["extended_output"], (
            f"[{fixture['id']}] extended mode mismatch\n"
            f"  got:      {extended_out!r}\n"
            f"  expected: {fixture['extended_output']!r}"
        )
