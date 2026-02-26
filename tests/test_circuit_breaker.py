"""Tests for CircuitBreaker state machine."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from icom_lan.rigctld.circuit_breaker import CircuitBreaker, CircuitState

# A large monotonic offset used wherever we need to simulate elapsed time.
_FAR_FUTURE = time.monotonic() + 3600.0


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_initial_state_is_closed() -> None:
    cb = CircuitBreaker()
    assert cb.state == CircuitState.CLOSED


def test_default_thresholds() -> None:
    cb = CircuitBreaker()
    assert cb.failure_threshold == 3
    assert cb.recovery_timeout == 5.0


def test_custom_thresholds() -> None:
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=10.0)
    assert cb.failure_threshold == 5
    assert cb.recovery_timeout == 10.0


def test_invalid_failure_threshold() -> None:
    with pytest.raises(ValueError):
        CircuitBreaker(failure_threshold=0)


def test_invalid_recovery_timeout() -> None:
    with pytest.raises(ValueError):
        CircuitBreaker(recovery_timeout=0.0)


# ---------------------------------------------------------------------------
# CLOSED → OPEN transition
# ---------------------------------------------------------------------------

def test_allow_request_in_closed_state() -> None:
    cb = CircuitBreaker(failure_threshold=3)
    assert cb.allow_request() is True


def test_closed_state_stays_closed_below_threshold() -> None:
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED


def test_circuit_opens_at_failure_threshold() -> None:
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_circuit_opens_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    cb = CircuitBreaker(failure_threshold=2)
    with caplog.at_level(logging.WARNING, logger="icom_lan.rigctld.circuit_breaker"):
        cb.record_failure()
        cb.record_failure()
    assert any("CLOSED → OPEN" in r.message for r in caplog.records)


def test_allow_request_returns_false_when_open() -> None:
    cb = CircuitBreaker(failure_threshold=1)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


# ---------------------------------------------------------------------------
# OPEN → HALF_OPEN transition (time-based)
# ---------------------------------------------------------------------------

def test_open_state_stays_open_before_timeout() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_open_transitions_to_half_open_after_timeout() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # Simulate time passing beyond recovery_timeout by patching monotonic.
    with patch("icom_lan.rigctld.circuit_breaker.time.monotonic", return_value=_FAR_FUTURE):
        assert cb.state == CircuitState.HALF_OPEN


def test_half_open_allows_request() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)
    cb.record_failure()
    with patch("icom_lan.rigctld.circuit_breaker.time.monotonic", return_value=_FAR_FUTURE):
        assert cb.allow_request() is True


def test_open_to_half_open_logs_info(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)
    cb.record_failure()
    with caplog.at_level(logging.INFO, logger="icom_lan.rigctld.circuit_breaker"):
        with patch("icom_lan.rigctld.circuit_breaker.time.monotonic", return_value=_FAR_FUTURE):
            _ = cb.state  # trigger transition
    assert any("OPEN → HALF_OPEN" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# HALF_OPEN → CLOSED (probe succeeds)
# ---------------------------------------------------------------------------

def test_probe_success_closes_circuit() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)
    cb.record_failure()
    with patch("icom_lan.rigctld.circuit_breaker.time.monotonic", return_value=_FAR_FUTURE):
        _ = cb.state  # trigger HALF_OPEN
        cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_probe_success_resets_failure_counter() -> None:
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    # Circuit is now OPEN; simulate time passing to enter HALF_OPEN.
    with patch("icom_lan.rigctld.circuit_breaker.time.monotonic", return_value=_FAR_FUTURE):
        _ = cb.state  # trigger OPEN → HALF_OPEN
        assert cb._state == CircuitState.HALF_OPEN
        cb.record_success()
    assert cb.consecutive_failures == 0


def test_probe_success_logs_closed(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)
    cb.record_failure()
    with caplog.at_level(logging.INFO, logger="icom_lan.rigctld.circuit_breaker"):
        with patch("icom_lan.rigctld.circuit_breaker.time.monotonic", return_value=_FAR_FUTURE):
            _ = cb.state  # trigger HALF_OPEN
            cb.record_success()
    assert any("→ CLOSED" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# HALF_OPEN → OPEN (probe fails)
# ---------------------------------------------------------------------------

def test_probe_failure_reopens_circuit() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)
    cb.record_failure()
    with patch("icom_lan.rigctld.circuit_breaker.time.monotonic", return_value=_FAR_FUTURE):
        _ = cb.state  # trigger HALF_OPEN
        cb.record_failure()
    # Internal state should be OPEN again (opened_at was reset to _FAR_FUTURE).
    assert cb._state == CircuitState.OPEN


def test_probe_failure_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)
    cb.record_failure()
    with caplog.at_level(logging.WARNING, logger="icom_lan.rigctld.circuit_breaker"):
        with patch("icom_lan.rigctld.circuit_breaker.time.monotonic", return_value=_FAR_FUTURE):
            _ = cb.state  # trigger HALF_OPEN
            cb.record_failure()
    assert any("HALF_OPEN → OPEN" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# CLOSED: success resets failure counter
# ---------------------------------------------------------------------------

def test_success_in_closed_state_resets_counter() -> None:
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.consecutive_failures == 2
    cb.record_success()
    assert cb.consecutive_failures == 0
    assert cb.state == CircuitState.CLOSED


def test_success_after_failures_does_not_log_transition(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """record_success in CLOSED state should NOT log a state transition."""
    import logging
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    with caplog.at_level(logging.INFO, logger="icom_lan.rigctld.circuit_breaker"):
        cb.record_success()
    # No "→ CLOSED" log since we were already CLOSED.
    assert not any("→ CLOSED" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Failure threshold = 1 (edge case)
# ---------------------------------------------------------------------------

def test_threshold_one_opens_on_first_failure() -> None:
    cb = CircuitBreaker(failure_threshold=1)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


# ---------------------------------------------------------------------------
# allow_request idempotency in OPEN state
# ---------------------------------------------------------------------------

def test_allow_request_consistent_in_open_state() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=100.0)
    cb.record_failure()
    for _ in range(5):
        assert cb.allow_request() is False
