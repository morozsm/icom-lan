"""Re-export shim for backwards compatibility.

Canonical location: rigplane.core._bounded_queue
Do not add new symbols here — add them at the canonical location.

This file uses the sys.modules-alias pattern: importing this shim
makes ``rigplane._bounded_queue`` literally the same module object as
``rigplane.core._bounded_queue``. This preserves attribute walks
(incl. stdlib names not in ``__all__``) and monkeypatch targets such
as ``unittest.mock.patch('rigplane._bounded_queue.asyncio.…', …)``.

The two import lines below are BOTH load-bearing — do not remove
either:

* ``from rigplane.core._bounded_queue import *`` — static-analysis
  adapter. Mypy and ruff resolve re-exported names through
  star-imports; they do not model the ``sys.modules`` mutation.
  Without this line, every consumer of
  ``from rigplane._bounded_queue import X`` triggers ``attr-defined``
  errors. At runtime this populates the temporary module object,
  which is immediately superseded by the swap below.

* ``sys.modules[__name__] = _canonical`` — the runtime invariant.
  Makes ``rigplane._bounded_queue`` and
  ``rigplane.core._bounded_queue`` the same module object so
  attribute lookups (including stdlib names imported by the
  canonical module) flow to the canonical module.
"""

import sys

from rigplane.core._bounded_queue import *  # noqa: F401, F403
import rigplane.core._bounded_queue as _canonical

sys.modules[__name__] = _canonical
