"""Re-export shim for backwards compatibility.

Canonical location: rigplane.runtime.ic705
Do not add new symbols here — add them at the canonical location.

This file uses the sys.modules-alias pattern: importing this shim
makes ``rigplane.ic705`` literally the same module object as
``rigplane.runtime.ic705``. This preserves attribute walks
(incl. stdlib names not in ``__all__``) and monkeypatch targets.

The two import lines below are BOTH load-bearing — do not remove
either:

* ``from rigplane.runtime.ic705 import *`` — static-analysis adapter.
* ``sys.modules[__name__] = _canonical`` — the runtime invariant.
"""

import sys

from rigplane.runtime.ic705 import *  # noqa: F401, F403
import rigplane.runtime.ic705 as _canonical

sys.modules[__name__] = _canonical
