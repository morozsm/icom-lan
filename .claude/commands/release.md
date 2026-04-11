# Release icom-lan

Automate the full release process. Argument: `$ARGUMENTS` — one of `patch`, `minor`, `major`, or an explicit version like `0.15.0`.

User-facing messages in Russian. Code/commit/release text in English.

---

## Step 1 — Determine target version

Read the current version from `pyproject.toml` (`version = "..."` under `[project]`).
Also read `src/icom_lan/__init__.py` (`__version__ = "..."`).

If versions differ, note both — they will be synced to the new version.
Use `pyproject.toml` as the authoritative current version.

If `$ARGUMENTS` is empty, ask the user: patch / minor / major / explicit version.
If `$ARGUMENTS` is `patch`, `minor`, or `major`, compute automatically.
If `$ARGUMENTS` looks like a version (digits and dots), use it directly.

Show: "Releasing vX.Y.Z (current: vA.B.C)" and ask for confirmation.

## Step 2 — Pre-flight checks

Run each check. STOP on first failure with a clear error message.

```bash
# 2a. Clean working tree
git status --porcelain
```
Non-empty (except RELEASE_NOTES.md) → stop, tell user to commit/stash.

```bash
# 2b. On main branch
git branch --show-current
```
Not `main` → warn and ask confirmation.

```bash
# 2c. Tests
uv run pytest tests/ -q --tb=short --ignore=tests/integration
```
Failures → stop.

```bash
# 2d. Lint
uv run ruff check src/ tests/
```
Failures → stop.

```bash
# 2e. Type check
uv run mypy src/
```
Failures → stop.

```bash
# 2f. Regression check
```
Run `/regression-check`. Any regression → stop. Write results to `.claude/workflow/regression.md`.

```bash
# 2g. No open FAILED issues
```
Check `.claude/queue/history.json` for recent FAILED entries with no resolution. Warn if found.

Report "All pre-flight checks passed" and continue.

## Step 3 — Bump version

Edit these files (use Edit tool, not sed):

1. `pyproject.toml` — `version = "OLD"` → `version = "NEW"`
2. `src/icom_lan/__init__.py` — `__version__ = "OLD"` → `__version__ = "NEW"`
3. `CLAUDE.md` — `| **Version** | OLD |` → `| **Version** | NEW |` (if present)

Show diffs, confirm with user.

## Step 4 — Update CHANGELOG.md

Read `CHANGELOG.md`. Find `## [Unreleased]` section (ends at next `## [` heading).

If the section has no content (no bullets under any sub-headers): ask user whether to
continue with empty changelog or stop to add entries.

Otherwise:
1. Keep `## [Unreleased]` header (empty) at the top
2. Insert new section below it: `## [NEW_VERSION] — YYYY-MM-DD` with today's date,
   followed by all content that was under `[Unreleased]`
3. Update footer links at the bottom of the file:
   - `[Unreleased]:` → compare `vNEW_VERSION...HEAD`
   - Add `[NEW_VERSION]:` → compare `vPREV_VERSION...vNEW_VERSION`
   - Get PREV_VERSION from: `git tag --list 'v*' --sort=-version:refname | head -1`

Show the resulting CHANGELOG section, confirm with user.

## Step 5 — Generate RELEASE_NOTES.md

Collect git log since previous tag:
```bash
git log vPREV_VERSION..HEAD --oneline --no-merges
```

Generate `RELEASE_NOTES.md` with this structure:

```markdown
# icom-lan NEW_VERSION

**Release date:** Month Day, Year

## Highlights

[2-3 sentence overview from changelog entries]

## What's New

[Reformat changelog Added/Changed/Fixed/Docs into readable sections]

## Breaking Changes

[From changelog, or "None."]

## Install / Upgrade

\`\`\`bash
pip install icom-lan==NEW_VERSION
# or upgrade:
pip install --upgrade icom-lan
\`\`\`

## Commits

[Git log summary, max 30 lines]
```

Show preview, confirm with user.

## Step 6 — Commit

Stage exactly: `pyproject.toml`, `src/icom_lan/__init__.py`, `CHANGELOG.md`,
`RELEASE_NOTES.md`, and `CLAUDE.md` if modified.

```bash
git commit -m "chore: release vNEW_VERSION"
```

Show diff summary, ask for explicit confirmation before committing.

## Step 7 — Tag

```bash
git tag -a vNEW_VERSION -m "Release NEW_VERSION"
```

Ask for confirmation before running.

## Step 8 — Push

```bash
git push && git push --tags
```

Ask for confirmation. If push fails, stop — do NOT proceed to GitHub release.

## Step 9 — Create GitHub release

```bash
gh release create vNEW_VERSION --notes-file RELEASE_NOTES.md --title "NEW_VERSION"
```

Ask for confirmation. Print the release URL on success.

## Step 10 — Update metrics

Update `.claude/metrics.json`:
- Increment `releases_count`
- Set `last_release_version` to `"NEW_VERSION"`

Save release summary to `.claude/workflow/release-notes.md`:
- Version, date, highlights, commit count

## Step 11 — Summary

```
Release vNEW_VERSION complete!

  pyproject.toml + __init__.py: NEW_VERSION
  CHANGELOG.md: updated
  RELEASE_NOTES.md: generated
  Git tag: vNEW_VERSION
  GitHub release: [URL]

CI will now:
  - Publish to PyPI (publish.yml)
  - Deploy docs (docs.yml)

Monitor: https://github.com/morozsm/icom-lan/actions
```

## Error recovery

If any step after commit fails (tag/push/release), do NOT roll back.
Show the user the manual commands to complete from where it stopped.
