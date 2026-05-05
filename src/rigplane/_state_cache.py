"""Re-export shim for backwards compatibility.

Canonical location: rigplane.core._state_cache
Do not add new symbols here — add them at the canonical location.

This file uses the sys.modules-alias pattern: importing this shim
makes ``rigplane._state_cache`` literally the same module object as
``rigplane.core._state_cache``. This preserves attribute walks
(incl. stdlib names not in ``__all__``) and monkeypatch targets such
as ``unittest.mock.patch('rigplane._state_cache.…', …)``.

The two import lines below are BOTH load-bearing — do not remove
either:

* ``from rigplane.core._state_cache import *`` — static-analysis
  adapter. Mypy and ruff resolve re-exported names through
  star-imports; they do not model the ``sys.modules`` mutation.
  Without this line, every consumer of
  ``from rigplane._state_cache import X`` triggers ``attr-defined``
  errors. At runtime this populates the temporary module object,
  which is immediately superseded by the swap below.

* ``sys.modules[__name__] = _canonical`` — the runtime invariant.
  Makes ``rigplane._state_cache`` and
  ``rigplane.core._state_cache`` the same module object so
  attribute lookups (including stdlib names imported by the
  canonical module) flow to the canonical module.
"""

import sys

from rigplane.core._state_cache import *  # noqa: F401, F403
import rigplane.core._state_cache as _canonical

sys.modules[__name__] = _canonical
