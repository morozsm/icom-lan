"""Re-export shim for backwards compatibility.

Canonical location: rigplane.audio._bridge_state
Do not add new symbols here -- add them at the canonical location.

This file uses the sys.modules-alias pattern: importing this shim
makes ``rigplane._bridge_state`` literally the same module object as
``rigplane.audio._bridge_state``. This preserves attribute walks (incl.
stdlib names not in ``__all__``) and monkeypatch targets.

The two import lines below are BOTH load-bearing -- do not remove
either:

* ``from rigplane.audio._bridge_state import *`` -- static-analysis adapter.
* ``sys.modules[__name__] = _canonical`` -- the runtime invariant.
"""

import sys

from rigplane.audio._bridge_state import *  # noqa: F401, F403
import rigplane.audio._bridge_state as _canonical

sys.modules[__name__] = _canonical
