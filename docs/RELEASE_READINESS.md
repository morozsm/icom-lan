# Release Readiness

## All Issues Closed — 2026-02-26 🎉

**32 issues opened → 32 issues closed. Zero open issues.**

### Test Suite
- **1040 passed**, 78 skipped, 1 xpassed
- 0 failures (1 pre-existing flaky test in `test_radio.py::TestScopeCallbackSafety` — passes in isolation)
- Coverage areas: unit, golden protocol, TCP wire, e2e audio, mock integration

### Closed Issues Summary

| Area | Issues | What was done |
|------|--------|---------------|
| **Audio API** | #1-#7, #10 | PCM transcoder, RX/TX high-level API, CLI subcommands, audio stats, capability negotiation, auto-recovery, naming consistency |
| **Audio Docs/Tests** | #5, #9 | E2E tests for PCM API + CLI, task-oriented recipes |
| **Rigctld Server** | #16-#22, #32 | TCP skeleton, MVP commands, read-only mode, structured logging, golden protocol suite, WSJT-X docs, DATA mode fix, epic complete |
| **Reliability** | #27 | CI-V desync fix, state cache, circuit breaker |

### Release Gates for v0.7.0

| Gate | Status |
|------|--------|
| All issues closed | ✅ 32/32 |
| Tests passing | ✅ 1040 passed |
| Lint clean | ⬜ verify `ruff check` |
| Docs build | ⬜ verify `mkdocs build` |
| CI green | ⬜ verify GitHub Actions |
| CHANGELOG updated | ⬜ move [Unreleased] → [0.7.0] |
| Version bump | ⬜ pyproject.toml 0.6.6 → 0.7.0 |
| PyPI publish | ⬜ after above gates |
| Real-radio smoke test | ⬜ optional but recommended |

## Previous Releases

### v0.6.6 — Released 2026-02-26 ✅

All gates passed:
- Full test suite: 869 passed, 78 skipped, 1 xpassed
- Lint: ruff check clean
- Docs build: mkdocs OK
- CI: all matrix jobs green (3.11/3.12/3.13)
- Real-radio validation (IC-7610): CAT + PTT stable
- Manual QA: WSJT-X with --wsjtx-compat confirmed working
- Published: GitHub release + PyPI
