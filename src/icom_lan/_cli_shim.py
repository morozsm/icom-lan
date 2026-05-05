"""Entry point shim — ``icom-lan`` is a deprecated alias for ``rigplane``.

When the user invokes ``icom-lan <args>``, this prints a deprecation
notice once to stderr, then forwards to the canonical ``rigplane`` CLI.
"""

from __future__ import annotations

import sys


def main() -> None:
    """Forward to :func:`rigplane.cli.main` after a deprecation notice."""
    print(
        "DeprecationWarning: `icom-lan` is deprecated and will be removed "
        "in a future release. Use `rigplane` instead.",
        file=sys.stderr,
    )
    from rigplane.cli import main as _rigplane_main

    _rigplane_main()
