# Release Readiness

## v0.6.6 — Released 2026-02-26 ✅

All gates passed:
- Full test suite: 869 passed, 78 skipped, 1 xpassed
- Lint: ruff check clean
- Docs build: mkdocs OK
- CI: all matrix jobs green (3.11/3.12/3.13)
- Real-radio validation (IC-7610): CAT + PTT stable
- Manual QA: WSJT-X with --wsjtx-compat confirmed working
- Published: GitHub release + PyPI

## Post-release TODO
- [x] Close completed issues (#16, #17, #18, #32)
- [x] Update open issue status (#19, #20, #21, #22)
- [x] Add WSJT-X setup guide (docs/guide/wsjtx-setup.md)
- [ ] Golden protocol response suite (#20) — next sprint
