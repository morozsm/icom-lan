"""Re-export shim for backwards compatibility.

Canonical location: rigplane.runtime._audio_runtime_mixin
Do not add new symbols here — add them at the canonical location.

This file uses the sys.modules-alias pattern: importing this shim
makes ``rigplane._audio_runtime_mixin`` literally the same module
object as ``rigplane.runtime._audio_runtime_mixin``. This preserves
attribute walks (incl. stdlib names not in ``__all__``) and
monkeypatch targets.

The two import lines below are BOTH load-bearing — do not remove
either:

* ``from rigplane.runtime._audio_runtime_mixin import *`` —
  static-analysis adapter.
* ``sys.modules[__name__] = _canonical`` — the runtime invariant.
"""

import sys

from rigplane.runtime._audio_runtime_mixin import *  # noqa: F401, F403
import rigplane.runtime._audio_runtime_mixin as _canonical

sys.modules[__name__] = _canonical
