"""One-shot migration of v1.x icom-lan platformdirs paths to v2.x rigplane.

When v2.0.0 starts on a host that has v1.x data under ``icom-lan`` paths
(``~/.cache/icom-lan``, ``~/.config/icom-lan``, etc.), copy the contents
to the new ``rigplane`` paths so logs and configuration carry over.
Idempotent — runs once per process; subsequent calls are no-ops.

The legacy paths are left in place (read-only after migration) so users
can manually clean them up. We do NOT delete legacy contents.

Best-effort: any failure (broken FS permissions, missing platformdirs,
etc.) is logged at DEBUG and swallowed so a broken migration cannot
break startup.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Final

import platformdirs

_logger = logging.getLogger("rigplane.platformdirs_migration")
_LEGACY_APP: Final = "icom-lan"
_NEW_APP: Final = "rigplane"
_SENTINEL_FILENAME: Final = ".migrated-from-icom-lan-v1"

_done = False


def __reset_for_tests() -> None:
    """Test-only: reset the in-process flag so a unit test can re-run."""
    global _done
    _done = False


def migrate_legacy_platformdirs() -> None:
    """Copy contents of legacy icom-lan platformdirs to rigplane paths.

    Best-effort: failures are logged at DEBUG and swallowed so a broken
    migration cannot break startup. Idempotent — calling multiple times
    in the same process is a no-op after the first call.
    """
    global _done
    if _done:
        return
    _done = True

    pairs = (
        (
            Path(platformdirs.user_cache_path(_LEGACY_APP)),
            Path(platformdirs.user_cache_path(_NEW_APP)),
        ),
        (
            Path(platformdirs.user_config_path(_LEGACY_APP)),
            Path(platformdirs.user_config_path(_NEW_APP)),
        ),
        (
            Path(platformdirs.user_log_path(_LEGACY_APP)),
            Path(platformdirs.user_log_path(_NEW_APP)),
        ),
        (
            Path(platformdirs.user_state_path(_LEGACY_APP)),
            Path(platformdirs.user_state_path(_NEW_APP)),
        ),
    )

    for legacy, new in pairs:
        try:
            _migrate_one(legacy, new)
        except Exception as exc:  # noqa: BLE001 — best-effort, swallow all
            _logger.debug(
                "platformdirs migration %s -> %s failed: %s",
                legacy,
                new,
                exc,
            )


def _migrate_one(legacy: Path, new: Path) -> None:
    if not legacy.exists() or not legacy.is_dir():
        return
    sentinel = new / _SENTINEL_FILENAME
    if sentinel.exists():
        return  # already migrated this directory
    new.mkdir(parents=True, exist_ok=True)
    for child in legacy.iterdir():
        target = new / child.name
        if target.exists():
            continue  # don't overwrite anything in the new location
        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)
    sentinel.write_text(
        "platformdirs migration from icom-lan v1.x complete\n",
        encoding="utf-8",
    )
