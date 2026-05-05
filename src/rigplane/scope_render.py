"""Re-export shim for backwards compatibility.

Canonical location: rigplane.scope.render
Do not add new symbols here — add them at the canonical location.

This file uses the sys.modules-alias pattern: importing this shim
makes ``rigplane.scope_render`` literally the same module object as
``rigplane.scope.render``. This preserves attribute walks (incl.
stdlib names not in ``__all__``) and monkeypatch targets.

The two import lines below are BOTH load-bearing — do not remove
either:

* ``from rigplane.scope.render import *`` — static-analysis adapter.
* ``sys.modules[__name__] = _canonical`` — the runtime invariant.
"""

import sys

from rigplane.scope.render import *  # noqa: F401, F403
import rigplane.scope.render as _canonical

sys.modules[__name__] = _canonical
