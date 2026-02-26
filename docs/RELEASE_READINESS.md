# Release Readiness (post-PR #31)

Date: 2026-02-26
Scope: CI-V desync fix train + DATA/WSJT-X compatibility hardening

## Current decision

- **Merge:** done ✅
- **Release now:** **no** (per plan)
- **Readiness status:** **almost ready** (needs final manual QA + release notes pass)

## Included changes (high-level)

- CI-V pipeline hardening for reconnect/desync scenarios.
- Rigctld state cache + autonomous poller + circuit breaker.
- DATA mode semantics refinements:
  - `PKTUSB`, `PKTLSB`, `PKTRTTY` handling.
  - no forced DATA-off side effect for unrelated mode changes.
- Commander cancellation safety:
  - cancelled/timed-out client requests no longer execute in background.
- Rigctld reliability updates:
  - poller pause on writes,
  - packet-mode transition hold window,
  - lazy poller lifecycle (start on first client, stop on last).
- WSJT-X compatibility mode (opt-in):
  - `icom-lan serve --wsjtx-compat` pre-warms DATA mode on first client
    when base mode is USB/LSB/RTTY and DATA is off.

## Verification performed

### Automated checks

- Full suite: `869 passed, 78 skipped, 1 xpassed` ✅
- Targeted radio-control suites: `184 passed, 1 xpassed` ✅
- Lint: `ruff check .` ✅
- Docs build: `mkdocs build` ✅ (build succeeds; upstream warning about MkDocs/Material roadmap)

### Real-radio validation (IC-7610)

- CAT stable in USB and DATA modes.
- SSB → PKTUSB transition now deterministic in rigctld tests.
- WSJT-X first-TX latency issue mitigated by `--wsjtx-compat`.
- With DATA already enabled, WSJT-X CAT/PTT path works reliably.

## Remaining pre-release checklist

1. **Manual regression pass** (one final run):
   - WSJT-X: Test CAT/Test PTT from USB (DATA off) with `--wsjtx-compat` ON/OFF.
   - JTDX/JS8Call sanity (connect, freq/mode/PTT toggle).
2. **Docs polish**:
   - add short “Known behavior” note: USB→PKT may incur first-TX delay in some client stacks; use `--wsjtx-compat`.
   - add recommended WSJT-X profile block (Rig/PTT/Mode/Split).
3. **Changelog final pass**:
   - verify Unreleased bullets are grouped and concise.
4. **Versioning/release prep (when approved)**:
   - tag plan, release notes draft, and rollback note.

## Risk notes

- `--wsjtx-compat` intentionally changes radio state (enables DATA) but is **opt-in**.
- No default behavior changes for users who do not pass the flag.
- One `xpassed` test remains in commander suite (non-blocking, known flaky category).
