"""Coverage test for rigctld/__init__.py ImportError fallback path (lines 16-17).

When server.py cannot be imported (e.g. missing dependency), __init__.py
must fall back to an empty __all__ instead of crashing the entire package.
"""

from __future__ import annotations

import importlib
import sys

import pytest


def test_rigctld_init_import_error_sets_empty_all(monkeypatch: pytest.MonkeyPatch) -> None:
    """If RigctldServer import fails, __all__ should be set to []."""
    # Block the server sub-module so the 'from .server import RigctldServer' fails
    monkeypatch.setitem(
        sys.modules,
        "icom_lan.rigctld.server",
        None,  # type: ignore[arg-type]
    )
    # Also remove any already-cached version of the init module
    for key in list(sys.modules.keys()):
        if key == "icom_lan.rigctld":
            monkeypatch.delitem(sys.modules, key)

    # Re-import the __init__; with server blocked, ImportError branch is taken
    import icom_lan.rigctld as rigctld_pkg
    importlib.reload(rigctld_pkg)

    assert rigctld_pkg.__all__ == []

    # Restore: force re-import on next access so other tests are not affected
    importlib.reload(rigctld_pkg)
