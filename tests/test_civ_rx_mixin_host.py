"""Focused tests for _CivRxMixin host coupling.

These tests exercise small pieces of the CI-V RX mixin against a minimal
fake host, so that accidental removal of required attributes is more likely
to surface as a runtime failure rather than only at type-check time.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from icom_lan._civ_rx import _CivRxMixin
from icom_lan.exceptions import ConnectionError


@dataclass
class _DummyTracker:
    """Minimal stub for CivRequestTracker used by _advance_civ_generation."""

    generation: int = 0
    last_error: Exception | None = None

    def advance_generation(self, error: Exception) -> int:
        self.last_error = error
        self.generation += 1
        return self.generation


class _FakeCivHost(_CivRxMixin):
    """Minimal host implementing just enough for targeted mixin tests."""

    def __init__(self) -> None:
        self._civ_request_tracker = _DummyTracker()
        self._civ_epoch = self._civ_request_tracker.generation
        self._civ_transport = object()


class TestCivRxMixinHost:
    """Tests for small pieces of _CivRxMixin against a fake host."""

    def test_advance_civ_generation_updates_epoch_and_uses_tracker(self) -> None:
        host = _FakeCivHost()
        assert host._civ_epoch == 0
        tracker = host._civ_request_tracker

        host._advance_civ_generation("unit-test")

        assert host._civ_epoch == 1
        assert tracker.last_error is not None
        assert "unit-test" in str(tracker.last_error)

    def test_ensure_civ_runtime_raises_when_no_transport(self) -> None:
        host = _FakeCivHost()
        host._civ_transport = None

        with pytest.raises(ConnectionError, match="Not connected to radio"):
            host._ensure_civ_runtime()

