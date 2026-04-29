"""Regression tests for the deprecated aliases in ``icom_lan.commands.levels``.

PR #1174 introduced PEP 562 ``__getattr__`` to emit ``DeprecationWarning`` for
the legacy alias names ``get_power``/``set_power``/``get_sql``/``set_sql``.
Issue #1182 (Codex P2) noted that wildcard import (``from ... import *``) only
iterates module globals (or ``__all__``) and therefore would silently drop the
aliases, leaving ``NameError`` at the call site instead of the intended
deprecation path.

These tests pin the contract:

1. Direct attribute access still resolves the alias and warns (regression guard
   from #1174).
2. Wildcard import via ``__all__`` exposes the aliases as callables and the
   first call still emits ``DeprecationWarning`` (fix for #1182).
"""

from __future__ import annotations

import importlib
import sys
import warnings


def _fresh_levels_module():
    """Reload ``icom_lan.commands.levels`` so ``__getattr__`` re-fires."""
    sys.modules.pop("icom_lan.commands.levels", None)
    return importlib.import_module("icom_lan.commands.levels")


def test_direct_attribute_access_warns_and_resolves() -> None:
    """Regression guard for PR #1174 — direct access still works + warns."""
    levels = _fresh_levels_module()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fn_get_power = levels.get_power  # type: ignore[attr-defined]
        fn_set_power = levels.set_power  # type: ignore[attr-defined]
        fn_get_sql = levels.get_sql  # type: ignore[attr-defined]
        fn_set_sql = levels.set_sql  # type: ignore[attr-defined]

    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    messages = " | ".join(str(w.message) for w in deprecations)
    assert "get_power" in messages
    assert "set_power" in messages
    assert "get_sql" in messages
    assert "set_sql" in messages
    # Aliases resolve to the canonical builders.
    assert fn_get_power is levels.get_rf_power
    assert fn_set_power is levels.set_rf_power
    assert fn_get_sql is levels.get_squelch
    assert fn_set_sql is levels.set_squelch


def test_wildcard_import_exposes_deprecated_aliases() -> None:
    """Fix for #1182 — ``from icom_lan.commands.levels import *`` works."""
    _fresh_levels_module()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        namespace: dict[str, object] = {}
        exec("from icom_lan.commands.levels import *", namespace)

    # All four deprecated aliases must be reachable as callables.
    for name in ("get_power", "set_power", "get_sql", "set_sql"):
        assert name in namespace, f"wildcard import dropped {name!r}"
        assert callable(namespace[name]), f"{name} is not callable after import *"

    # The wildcard import itself must emit a DeprecationWarning per alias.
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    messages = " | ".join(str(w.message) for w in deprecations)
    for name in ("get_power", "set_power", "get_sql", "set_sql"):
        assert name in messages, (
            f"expected DeprecationWarning for {name} during wildcard import; "
            f"got: {messages!r}"
        )


def test_all_lists_canonical_and_deprecated_names() -> None:
    """``__all__`` must explicitly contain the deprecated alias names — that
    is what makes wildcard import iterate them and trigger ``__getattr__``."""
    levels = _fresh_levels_module()
    exported = set(levels.__all__)
    # Deprecated aliases.
    assert {"get_power", "set_power", "get_sql", "set_sql"} <= exported
    # A few canonical builders as a sanity spot-check.
    assert {"get_rf_power", "set_rf_power", "get_squelch", "set_squelch"} <= exported


def test_unknown_attribute_still_raises_attribute_error() -> None:
    """``__getattr__`` only handles known aliases — anything else must raise."""
    levels = _fresh_levels_module()
    try:
        _ = levels.no_such_thing  # type: ignore[attr-defined]
    except AttributeError as exc:
        assert "no_such_thing" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected AttributeError for unknown attribute")
