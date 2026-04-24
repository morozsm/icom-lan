"""Tests for auth-token redaction in request logging (issue #948)."""

from __future__ import annotations

from icom_lan.web.server import _redact_token_in_path


def test_redact_token_simple() -> None:
    assert _redact_token_in_path("/api/v1/ws?token=secret123") == "/api/v1/ws?token=***"


def test_redact_token_with_other_params_before() -> None:
    assert (
        _redact_token_in_path("/api/v1/ws?foo=1&token=secret&bar=2")
        == "/api/v1/ws?foo=1&token=***&bar=2"
    )


def test_redact_token_with_other_params_after() -> None:
    assert (
        _redact_token_in_path("/api/v1/ws?token=secret&foo=1")
        == "/api/v1/ws?token=***&foo=1"
    )


def test_redact_empty_token_value() -> None:
    assert _redact_token_in_path("/api/v1/ws?token=") == "/api/v1/ws?token=***"


def test_no_token_param_unchanged() -> None:
    assert _redact_token_in_path("/api/v1/ws?foo=bar") == "/api/v1/ws?foo=bar"


def test_no_query_unchanged() -> None:
    assert _redact_token_in_path("/api/v1/ws") == "/api/v1/ws"


def test_token_substring_in_other_param_is_not_redacted() -> None:
    # A param named `mytoken=...` must NOT be redacted — only exact `token`.
    assert _redact_token_in_path("/api/v1/ws?mytoken=abc") == "/api/v1/ws?mytoken=abc"


def test_path_with_token_in_body_but_no_query_unchanged() -> None:
    # The substring `token=` appears in the literal path, not as a query arg.
    # Our guard (`"token=" not in path`) is a fast-path; since there IS
    # `token=` in the literal, we go into the split logic, but without a `?`
    # we return the path as-is.
    assert _redact_token_in_path("/tokens/token=foo") == "/tokens/token=foo"
