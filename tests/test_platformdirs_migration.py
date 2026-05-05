"""Tests for rigplane._platformdirs_migration.

The migration helper copies the contents of v1.x ``icom-lan`` platformdirs
into v2.x ``rigplane`` platformdirs so existing users keep their logs and
configuration on first start of v2.0.0.
"""

from __future__ import annotations

from pathlib import Path

import platformdirs
import pytest

from rigplane import _platformdirs_migration as mig
from rigplane._platformdirs_migration import (
    _SENTINEL_FILENAME,
    migrate_legacy_platformdirs,
)


@pytest.fixture
def fake_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect every platformdirs.user_*_path call to a tmp_path subtree.

    Each app gets its own subdirectory keyed by app name, e.g.
    ``tmp_path/cache/icom-lan`` vs ``tmp_path/cache/rigplane``.
    """
    cache_root = tmp_path / "cache"
    config_root = tmp_path / "config"
    log_root = tmp_path / "log"
    state_root = tmp_path / "state"

    monkeypatch.setattr(
        platformdirs,
        "user_cache_path",
        lambda app: cache_root / app,
    )
    monkeypatch.setattr(
        platformdirs,
        "user_config_path",
        lambda app: config_root / app,
    )
    monkeypatch.setattr(
        platformdirs,
        "user_log_path",
        lambda app: log_root / app,
    )
    monkeypatch.setattr(
        platformdirs,
        "user_state_path",
        lambda app: state_root / app,
    )
    # Reset in-process guard so each test gets a fresh run.
    mig.__reset_for_tests()
    return tmp_path


def test_legacy_dir_with_files_migrates_into_new_dir(fake_dirs: Path) -> None:
    legacy_cache = fake_dirs / "cache" / "icom-lan"
    legacy_cache.mkdir(parents=True)
    (legacy_cache / "app.log").write_text("legacy log", encoding="utf-8")
    sub = legacy_cache / "logs"
    sub.mkdir()
    (sub / "rigplane.log").write_text("nested log", encoding="utf-8")

    migrate_legacy_platformdirs()

    new_cache = fake_dirs / "cache" / "rigplane"
    assert (new_cache / "app.log").read_text(encoding="utf-8") == "legacy log"
    assert (new_cache / "logs" / "rigplane.log").read_text(
        encoding="utf-8"
    ) == "nested log"
    assert (new_cache / _SENTINEL_FILENAME).exists()


def test_existing_new_files_are_not_overwritten(fake_dirs: Path) -> None:
    legacy_cfg = fake_dirs / "config" / "icom-lan"
    legacy_cfg.mkdir(parents=True)
    (legacy_cfg / "settings.json").write_text("legacy settings", encoding="utf-8")
    (legacy_cfg / "fresh.json").write_text("legacy fresh", encoding="utf-8")

    new_cfg = fake_dirs / "config" / "rigplane"
    new_cfg.mkdir(parents=True)
    (new_cfg / "settings.json").write_text("new settings", encoding="utf-8")

    migrate_legacy_platformdirs()

    # Existing new-side file is preserved (collision: don't overwrite).
    assert (new_cfg / "settings.json").read_text(encoding="utf-8") == "new settings"
    # Non-conflicting legacy file is migrated.
    assert (new_cfg / "fresh.json").read_text(encoding="utf-8") == "legacy fresh"
    # Sentinel was still written so this dir won't be revisited.
    assert (new_cfg / _SENTINEL_FILENAME).exists()


def test_no_legacy_dir_is_a_quiet_noop(fake_dirs: Path) -> None:
    # No legacy dirs exist anywhere.
    migrate_legacy_platformdirs()

    # No new dirs should have been created either — nothing to copy means
    # nothing to do.
    assert not (fake_dirs / "cache" / "rigplane").exists()
    assert not (fake_dirs / "config" / "rigplane").exists()
    assert not (fake_dirs / "log" / "rigplane").exists()
    assert not (fake_dirs / "state" / "rigplane").exists()


def test_second_call_in_same_process_is_a_noop(fake_dirs: Path) -> None:
    legacy_cache = fake_dirs / "cache" / "icom-lan"
    legacy_cache.mkdir(parents=True)
    (legacy_cache / "first.log").write_text("first", encoding="utf-8")

    migrate_legacy_platformdirs()
    new_cache = fake_dirs / "cache" / "rigplane"
    assert (new_cache / "first.log").exists()

    # Drop a fresh file into legacy AFTER the first migration.
    (legacy_cache / "second.log").write_text("second", encoding="utf-8")
    migrate_legacy_platformdirs()

    # Second call short-circuits via the in-process flag, so the
    # newly added legacy file is NOT copied over.
    assert not (new_cache / "second.log").exists()


def test_sentinel_short_circuits_per_directory(fake_dirs: Path) -> None:
    # Pre-create the new dir with a sentinel — simulating a prior process
    # that already migrated. Even with new content in legacy, this dir is
    # skipped at the per-directory level.
    legacy_state = fake_dirs / "state" / "icom-lan"
    legacy_state.mkdir(parents=True)
    (legacy_state / "should-not-copy.txt").write_text("nope", encoding="utf-8")

    new_state = fake_dirs / "state" / "rigplane"
    new_state.mkdir(parents=True)
    (new_state / _SENTINEL_FILENAME).write_text("done", encoding="utf-8")

    migrate_legacy_platformdirs()

    assert not (new_state / "should-not-copy.txt").exists()


def test_function_never_raises_on_io_error(
    fake_dirs: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_cache = fake_dirs / "cache" / "icom-lan"
    legacy_cache.mkdir(parents=True)
    (legacy_cache / "broken.log").write_text("data", encoding="utf-8")

    # Force an exception inside the migration loop.
    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated permission failure")

    monkeypatch.setattr("shutil.copy2", boom)
    monkeypatch.setattr("shutil.copytree", boom)

    # Must NOT raise.
    migrate_legacy_platformdirs()


def test_legacy_path_that_is_a_file_not_dir_is_skipped(fake_dirs: Path) -> None:
    # If something weird made the legacy path a regular file, the migration
    # must not crash and must not try to migrate it.
    legacy_cache_parent = fake_dirs / "cache"
    legacy_cache_parent.mkdir(parents=True)
    legacy_cache = legacy_cache_parent / "icom-lan"
    legacy_cache.write_text("not a dir", encoding="utf-8")

    migrate_legacy_platformdirs()

    new_cache = fake_dirs / "cache" / "rigplane"
    # No new dir created because there was nothing to migrate.
    assert not new_cache.exists()
