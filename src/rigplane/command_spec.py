"""Re-export shim for backwards compatibility.

Canonical location: rigplane.commands.command_spec
Do not add new symbols here — add them at the canonical location.

This file uses the sys.modules-alias pattern: importing this shim
makes ``rigplane.command_spec`` literally the same module object as
``rigplane.commands.command_spec``. This preserves attribute walks (incl.
stdlib names not in ``__all__``) and monkeypatch targets.

The two import lines below are BOTH load-bearing — do not remove
either:

* ``from rigplane.commands.command_spec import *`` — static-analysis adapter.
* ``sys.modules[__name__] = _canonical`` — the runtime invariant.
"""

import sys

from rigplane.commands.command_spec import *  # noqa: F401, F403
import rigplane.commands.command_spec as _canonical

sys.modules[__name__] = _canonical
