"""Re-export shim for backwards compatibility.

Canonical location: rigplane.audio._usb_resolve
Do not add new symbols here -- add them at the canonical location.

This file uses the sys.modules-alias pattern: importing this shim
makes ``rigplane.usb_audio_resolve`` literally the same module object as
``rigplane.audio._usb_resolve``. This preserves attribute walks (incl.
stdlib names not in ``__all__``) and monkeypatch targets.

The two import lines below are BOTH load-bearing -- do not remove
either:

* ``from rigplane.audio._usb_resolve import *`` -- static-analysis adapter.
* ``sys.modules[__name__] = _canonical`` -- the runtime invariant.
"""

import sys

from rigplane.audio._usb_resolve import *  # noqa: F401, F403
import rigplane.audio._usb_resolve as _canonical

sys.modules[__name__] = _canonical
