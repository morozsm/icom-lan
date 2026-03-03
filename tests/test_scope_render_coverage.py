"""Additional coverage tests for scope_render.py.

Tests the _require_pillow ImportError path that the main test file
(test_scope_render.py) cannot reach because it skips when Pillow is absent.
"""

from __future__ import annotations

import sys

import pytest


class TestRequirePillowImportError:
    """Test the _require_pillow() ImportError guard."""

    def test_require_pillow_raises_when_pil_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_require_pillow() must raise ImportError with helpful message when PIL absent."""
        # Temporarily shadow PIL in sys.modules to simulate it being uninstalled.
        # Setting the value to None causes Python to raise ImportError on import.
        monkeypatch.setitem(sys.modules, "PIL", None)  # type: ignore[arg-type]

        from icom_lan.scope_render import _require_pillow

        with pytest.raises(ImportError, match="Pillow is required"):
            _require_pillow()

    def test_require_pillow_succeeds_when_pil_installed(self) -> None:
        """_require_pillow() must not raise when PIL is importable."""
        # This import will raise at test-collection time if PIL is not installed,
        # which is the intended behaviour for an optional-dependency guard.
        PIL = pytest.importorskip("PIL")  # noqa: F841

        from icom_lan.scope_render import _require_pillow

        _require_pillow()  # should not raise
