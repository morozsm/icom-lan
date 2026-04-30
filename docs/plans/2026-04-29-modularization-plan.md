# Internal Modularization — Phase 2 Architecture & Migration Plan

**Date:** 2026-04-30
**Branch:** `refactor/modularization-discovery`
**Brief:** [`/Users/moroz/Projects/icom-lan-research/2026-04-29-internal-modularization-orchestrator.md`](../../) (out of repo)
**Discovery doc:** [`./2026-04-29-modularization-discovery.md`](./2026-04-29-modularization-discovery.md)
**Status:** ready for maintainer review — Phase 3 (issue creation) cannot start without sign-off

---

## 0. Inputs already locked (do not relitigate)

The discovery doc closed Phase 1 with four explicit maintainer decisions
that this plan encodes verbatim:

1. **Silent re-export shims** with grep-able header (template in §5).
2. **`import-linter`** is the boundary tool. Integrate in Phase 4
   *after* the bulk-move steps, *before* the final import cleanup.
3. **43 private-path leaks across 15 test files** are covered by shims
   in this effort. Phase 3 must file follow-up issue
   `[Followup] Migrate tests off private internal imports` tagged
   `followup-after-modularization`.
4. **`icom-lan-pro` coordination = three-tier validation**:
   end-of-Phase-2 paper check (this doc, §9) → Phase 4 smoke-imports
   per `audio/` or `dsp/` PR → Phase 5 full downstream test suite as
   the definition-of-done marker.

---

## 1. Final layer structure

### 1.1 Directory tree

```
src/icom_lan/
├── __init__.py        # Tier 1 / Tier 2 PEP 562 lazy loader (rewires LAZY_MAP at end)
├── __main__.py        # python -m icom_lan entrypoint (kept top-level for discoverability)
├── core/              # foundational: types, exceptions, transport, contracts
├── commands/          # CI-V command builders + commander (existing dir, expanded)
├── profiles/          # rig profiles + TOML loader
├── audio/             # audio subsystem (existing dir, expanded)
├── scope/             # scope/waterfall frame assembly + render
├── dsp/               # pure DSP nodes + pipeline (existing dir, untouched)
├── runtime/           # IcomRadio + state + mixins + pollers + sync wrapper
├── backends/          # factory + per-radio assembly (existing dir, expanded with discovery)
├── web/               # WebSocket+HTTP server (existing dir, untouched)
├── rigctld/           # Hamlib NET rigctld TCP server (existing dir, untouched)
└── cli/               # CLI + python -m entry helpers
```

11 layers. The five new directories (`core/`, `profiles/`, `runtime/`,
`scope/`, `cli/`) are introduced by this work; the six existing ones
(`audio/`, `backends/`, `commands/`, `dsp/`, `rigctld/`, `web/`) are
expanded.

### 1.2 Layer charters (one paragraph each)

- **`core/`** — Foundational layer with no internal dependencies.
  Holds the wire-protocol primitives, base types, and the abstract
  Radio Protocol that downstream consumers (`icom-lan-pro`) treat as
  the stable contract. Depends on nothing in `icom_lan`. Anyone may
  import from `core`.
- **`commands/`** — CI-V command builders and the high-level
  commander queue. Encodes/decodes wire bytes; does not own state.
  Depends only on `core`.
- **`profiles/`** — Rig profiles, capability matrices, and the
  TOML rig-config loader. Depends on `core` and `commands`.
- **`audio/`** — End-to-end audio subsystem: backend protocol,
  PortAudio/Fake implementations, codecs, transcoder, audio bridge,
  bus, FFT scope, recovery on reconnect, and platform USB resolution.
  Depends on `core`. Its `audio.backend` and `audio.dsp` paths are
  the icom-lan-pro contract.
- **`scope/`** — Spectrum/waterfall frame assembly and rendering.
  Depends on `core`.
- **`dsp/`** — Pure real-time DSP pipeline (nodes, resampler, tap
  registry). Has no internal dependencies (independent layer).
- **`runtime/`** — High-level radio orchestration: `IcomRadio` and
  its mixins, state cache, state queries, pollers, command queue,
  audio recovery, sync-wrapper, and runtime helpers. Depends on
  `core`, `commands`, `profiles`, `audio`, `scope`.
- **`backends/`** — Factory for assembling concrete radio
  implementations from typed configs; per-radio adapters
  (IC-705/7300/7610/9700, Yaesu CAT) and the multi-protocol
  discovery utility. Depends on `core`, `commands`, `profiles`,
  `audio`, `runtime`.
- **`web/`** — WebSocket + HTTP server for the icom-lan Web UI.
  Depends on `core`, `commands`, `profiles`, `audio`, `scope`, `dsp`,
  `runtime`, and (transitionally — see §3.3) `backends`.
- **`rigctld/`** — Hamlib NET rigctld-compatible TCP server.
  Depends on `core`, `commands`, `runtime`.
- **`cli/`** — Command-line entrypoints. Depends on
  `core`, `commands`, `profiles`, `audio`, `scope`, `runtime`,
  `backends`, `web`, `rigctld`.

### 1.3 Deviations from the brief's skeleton

The brief's §"Target end state" sketches a structure where
`backends/` lives *inside* `core/`. The discovery data refutes this:
`backends/` collectively imports 17 non-backends modules including
`audio.usb_driver`, `commands`, `profiles`, `radio`, `radio_state`,
`audio_bus`, etc. (Phase 1 §6 + §8 surface this directly.) A layer
that imports from `runtime` cannot live inside `core` (which by rule
imports nothing internal). **`backends/` is a layer above `runtime/`,
not a sibling of `core`'s primitives.**

Other consequential deviations and the data behind them:

- **`runtime` depends on `audio` and `scope`** (the brief had
  runtime depending only on core/commands/profiles). Justification:
  `_audio_runtime_mixin` and `_scope_runtime` are runtime mixins on
  the IcomRadio class; they pull in audio backends and scope
  rendering at construction. Documented in discovery §3.
- **`audio → scope` allowed** — `audio_fft_scope` legitimately needs
  `scope` types to assemble a panadapter from PCM. Single-edge
  dependency, no cycle.
- **`radio_protocol` lives in `core/`** even though static analysis
  shows it imports `audio_bus` and `scope`. Both imports are inside
  `if TYPE_CHECKING:` blocks (verified at line 57 of the current
  file) and never execute at import time. Phase 4 declares them as
  named `ignore_imports` exceptions in the import-linter contract;
  Phase 5 may file a separate followup to refactor them out using
  `from __future__ import annotations` + string annotations.
- **`web → backends` is provisional**, owned by a tracked followup.
  `web/web_startup.py` directly instantiates
  `backends.yaesu_cat.poller`/`radio` rather than going through
  `backends.factory`. Phase 3 files
  `[Followup] Refactor web_startup to use backends.factory` tagged
  `followup-after-modularization`. Until then the import-linter
  contract has a single named ignore for this transitional edge.

---

## 2. Public API surface per layer

### 2.1 Top-level `icom_lan/__init__.py` — preserved verbatim

The Tier 1 / Tier 2 PEP 562 lazy-loader is migration-INVARIANT. The
60 names in the current `__all__` continue to exist at the top-level
import path after every step. The `_LAZY_MAP` target tuples are
rewritten only in the final cleanup step (see §4 Step 13); during the
bulk-move steps the LAZY_MAP keeps pointing at the *old* paths and
reaches the new home transparently through re-export shims. The
maintainer can therefore review intermediate PRs without worrying
about Tier 2 attribute resolution.

The full Tier 1 + Tier 2 `__all__` is in
[`./discovery-artifacts/init-snapshot.md`](./discovery-artifacts/init-snapshot.md);
this plan does not change a single name in it.

### 2.2 New `__init__.py` `__all__` per layer

These are *internal* contracts — not part of the top-level public API
— but they define what other layers may import through the layer's
front door. Anything not listed is internal to the layer and must be
imported via its full module path.

- **`core/__init__.py`**: re-exports the existing top-level core
  surface — `Mode`, `AudioCodec`, `BreakInMode`, all `*Capable`
  Protocols (via `radio_protocol`), all exception types, `RadioState`,
  `VfoSlotState`, `YaesuStateExtension`, `BandStackRegister`,
  `MemoryChannel`, `ScopeFixedEdge`. Plus transport primitives
  (`UdpTransport`, `Authenticator`, `parse_packet`, …) that other
  layers currently import from `icom_lan.transport`/`icom_lan.civ`/
  `icom_lan.protocol`/`icom_lan.auth`.
- **`commands/__init__.py`**: existing `CommandMap`, `CommandSpec`,
  plus `IcomCommander`, `Priority`. (Tier 2 lazy in top-level,
  preserved.)
- **`profiles/__init__.py`**: `RadioProfile`, `load_profile_toml`,
  helpers from `rig_loader`.
- **`audio/__init__.py`**: existing entries (preserved) +
  `AudioBus`, `AudioAnalyzer`, `AudioBridge`, `AudioFftScope`,
  `_audio_codecs` helpers (kept private), `usb_audio_resolve` helper.
  The `audio.backend` and `audio.dsp` submodule paths used by
  icom-lan-pro stay exactly as they are.
- **`scope/__init__.py`**: `ScopeFrame`, `assemble_scope_frame`,
  `render_scope_image`.
- **`dsp/__init__.py`**: untouched (existing public API stays).
- **`runtime/__init__.py`**: `IcomRadio`, `SyncIcomRadio` (`sync`
  wrapper), `AudioRecoveryState`, plus mixin types as needed. Many
  `_*` private modules in this layer are imported by tests via
  private paths (43 cases) — those are addressed by SHIMS at the
  old top-level paths, NOT by re-exports through this `__init__.py`.
- **`backends/__init__.py`**: `BackendConfig`, `LanBackendConfig`,
  `SerialBackendConfig`, `YaesuCatBackendConfig`, `create_radio` —
  exactly the existing surface — plus `discover` helper from
  `discovery.py`.
- **`web/__init__.py`**: untouched (no web changes).
- **`rigctld/__init__.py`**: untouched.
- **`cli/__init__.py`**: `main` function (or whatever the cli entry
  callable is); `__main__.py` either lives at top level (preferred —
  see §4 Step 12 rationale) or moves into `cli/`.

The above is a planning sketch; per-step PR descriptions in §4
nail down the exact `__all__` for each `__init__.py` as that step
ships.

---

## 3. Allowed-imports matrix

### 3.1 The matrix

`✓` allowed; `—` forbidden; `(t)` allowed but only with named
`ignore_imports` exceptions for transitional violations.

|             | core | commands | profiles | audio | scope | dsp | runtime | backends | web | rigctld | cli |
|---          |:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **core**    | —   | —   | —   | —   | —   | —   | —   | —   | —   | —   | —   |
| **commands**| ✓   | —   | —   | —   | —   | —   | —   | —   | —   | —   | —   |
| **profiles**| ✓   | ✓   | —   | —   | —   | —   | —   | —   | —   | —   | —   |
| **audio**   | ✓   | —   | —   | —   | ✓   | —   | —   | —   | —   | —   | —   |
| **scope**   | ✓   | —   | —   | —   | —   | —   | —   | —   | —   | —   | —   |
| **dsp**     | ✓   | —   | —   | —   | —   | —   | —   | —   | —   | —   | —   |
| **runtime** | ✓   | ✓   | ✓   | ✓   | ✓   | —   | —   | —   | —   | —   | —   |
| **backends**| ✓   | ✓   | ✓   | ✓   | —   | —   | ✓   | —   | —   | —   | —   |
| **web**     | ✓   | ✓   | ✓   | ✓   | ✓   | ✓   | ✓   | (t) | —   | —   | —   |
| **rigctld** | ✓   | ✓   | —   | —   | —   | —   | ✓   | —   | —   | —   | —   |
| **cli**     | ✓   | ✓   | ✓   | ✓   | ✓   | —   | ✓   | ✓   | ✓   | ✓   | —   |

Read **rows depend on columns**: e.g. `runtime` depends on `core`,
`commands`, `profiles`, `audio`, `scope`. Diagonal is `—` because no
layer "depends on itself" in import-linter's `layers` contract sense
(intra-layer imports are unconstrained).

### 3.2 Notable rules

- `core` imports nothing internal. `_optional_deps`, every "core"
  module, and the contract trio (`radio_protocol`, `radio_state`,
  `_state_cache`) form a self-contained leaf cluster (verified
  empirically against the discovery data; see §4 Step 1 acceptance
  criteria).
- `dsp` is independent of the rest (depends on `core` only for
  `_optional_deps` numpy/scipy detection). `audio` depends on `dsp`
  for the optional pipeline path inside `audio.dsp`.
- `commands` does not import `runtime` — command builders are pure;
  they take bytes and return bytes. `IcomCommander`'s queue is
  `commands` only because the queue lives there for `Priority` and
  `_QueueItem` types.

### 3.3 Named exceptions (explicit `ignore_imports`)

import-linter contracts will declare:

```ini
ignore_imports =
    icom_lan.radio_protocol -> icom_lan.audio_bus     ; TYPE_CHECKING only
    icom_lan.radio_protocol -> icom_lan.scope         ; TYPE_CHECKING only
    icom_lan.web.web_startup -> icom_lan.backends.yaesu_cat.poller   ; transitional, see followup
    icom_lan.web.web_startup -> icom_lan.backends.yaesu_cat.radio    ; transitional, see followup
```

The first two are stable exceptions (TYPE_CHECKING is a real Python
mechanism, not a temporary state). The bottom two are transitional;
when the followup PR replaces direct instantiation with
`backends.factory`, the ignores are removed.

---

## 4. Migration steps

13 steps total. Each step is **one PR**, with multiple atomic commits
inside (move-files commit → add-shims commit → optional
update-imports commit, per the §5 commit policy). Step ordering is
strictly linear; later steps depend on earlier ones for the new
layer directories to exist.

Per-step LOC estimates use existing file sizes and exclude
mechanical re-export shims (per brief's §"Non-negotiables" 6).
Targets are PRs ≤500 LOC of moved code; estimates beyond that flag
the step for finer-grained splitting in Phase 3 issue authoring.

| # | Description | Files moved | Approx. LOC moved | Shim files |
|---:|---|---:|---:|---:|
| 1 | Skeleton: empty new package dirs | 0 | ~50 (new `__init__.py`s) | 0 |
| 2 | Move `core` foundationals (types, exceptions, auth, transport, civ, protocol, capabilities, env_config, _optional_deps) | 9 | ~800 (split if >500) | 9 |
| 3 | Move `core` contract trio + transport primitives (radio_protocol, radio_state, _state_cache, _queue_pressure, _bounded_queue) | 5 | ~400 | 5 |
| 4 | Move `commands` top-level (commander, command_map, command_spec) | 3 | ~300 | 3 |
| 5 | Move `profiles` (profiles, rig_loader) | 2 | ~250 | 2 |
| 6 | Move `scope` (scope, scope_render) | 2 | ~200 | 2 |
| 7 | Move `audio` top-level (audio_*, _audio_codecs, _audio_transcoder, _bridge_metrics, _bridge_state, usb_audio_resolve) | 9 | ~700 (likely split into 7a + 7b) | 9 |
| 8 | Move `runtime` part 1: radio + state + helpers (radio, radio_state_snapshot, radio_initial_state, radio_reconnect, radios, ic705, _state_queries) | 7 | ~600 (likely split) | 7 |
| 9 | Move `runtime` part 2: mixins (_audio_runtime_mixin, _dual_rx_runtime, _scope_runtime, _shared_state_runtime, _runtime_protocols) | 5 | ~400 | 5 |
| 10 | Move `runtime` part 3: pollers + control + sync wrapper (_poller_types, _civ_rx, _connection_state, _control_phase, sync, profiles_runtime, meter_cal, cw_auto_tuner, startup_checks, proxy, _audio_recovery) | 11 | ~700 (likely split) | 11 |
| 11 | Move `discovery.py` → `backends/discovery.py` | 1 | ~150 | 1 |
| 12 | Move `cli.py` → `cli/` (decide `__main__.py` per §4 below) | 1–2 | ~250 | 1–2 |
| 13 | Add `import-linter` to dev deps + `.importlinter` config + CI hook + clean up LAZY_MAP target tuples to canonical paths | 0 | ~60 (config + LAZY_MAP) | 0 |

**Estimated PRs after splitting oversize:** **15** (steps 2, 7, 8, 10
each likely split into a + b based on actual LOC at execution time).

### 4.1 Step-by-step detail

The per-step prompt for each Phase 4 sub-agent will follow the
template in the brief's §"Phase 4". Below: scope, dependencies, and
the verification gate for each step.

#### Step 1 — Skeleton

- **Scope:** create empty packages `core/`, `profiles/`, `runtime/`,
  `scope/`, `cli/`. Each gets a stub `__init__.py` with a docstring
  pointing at the relevant `LAYER.md` (LAYER.md files come in
  Phase 5; the docstring placeholder is fine).
- **Acceptance:** `tests/` collect 5210; `mypy src/` clean; `ruff
  check` clean. No imports change yet.

#### Step 2 — `core` foundationals

- **Scope:** move 9 files (`types`, `exceptions`, `auth`,
  `transport`, `civ`, `protocol`, `capabilities`, `env_config`,
  `_optional_deps`) to `core/`. Add 9 re-export shims at the old
  top-level paths.
- **Pre-condition:** Step 1 merged.
- **Acceptance:** every existing import path works; tests pass;
  `_optional_deps` has zero `from icom_lan` imports (verified via
  the discovery script as a CI check).
- **Risk:** transport.py is the largest file (~500+ LOC). If the
  step exceeds 500 LOC of moved code, **split** into:
  - **2a:** small core foundationals (5 files)
  - **2b:** transport + civ + protocol (3 files)

#### Step 3 — `core` contract trio + transport primitives

- **Scope:** move `radio_protocol`, `radio_state`, `_state_cache`,
  `_queue_pressure`, `_bounded_queue` to `core/`.
- **Pre-condition:** Steps 1–2 merged.
- **Acceptance:** `from icom_lan import Radio` (and all 32 other
  Tier 1 names) still works; PEP 562 lazy resolution still works
  for all 28 Tier 2 names (smoke check below in §6).

#### Step 4 — `commands` top-level

- **Scope:** move `commander`, `command_map`, `command_spec` into
  `commands/`. Re-export shims preserve the public Tier 2 names
  `IcomCommander`, `Priority`.

#### Step 5 — `profiles`

- **Scope:** move `profiles.py`, `rig_loader.py` into `profiles/`.
- **Risk pre-mitigation:** the function-local cycle-breaker at
  `profiles.py:266` (`profiles → rig_loader`) MUST be preserved
  verbatim. Do NOT "clean up" the deferred import. Same for the
  top-level `rig_loader → profiles` import.

#### Step 6 — `scope`

- **Scope:** move `scope.py`, `scope_render.py` into `scope/`. Tiny
  step.

#### Step 7 — `audio` top-level (likely split 7a/7b)

- **Scope:** move 9 audio top-level files into `audio/` as
  submodules: `audio/analyzer.py`, `audio/bridge.py`, `audio/bus.py`,
  `audio/fft_scope.py`, `audio/_codecs.py`, `audio/_transcoder.py`,
  `audio/_bridge_metrics.py`, `audio/_bridge_state.py`,
  `audio/_usb_resolve.py`. **`audio.backend` and `audio.dsp`
  paths are NOT moved.**
- **Acceptance:** the 5 icom-lan-pro import paths
  (`icom_lan.audio.backend` ×19, `icom_lan.dsp.pipeline` ×4,
  `icom_lan.dsp.nodes.base` ×3, `icom_lan.dsp.exceptions` ×2,
  `icom_lan.audio.dsp` ×1) are explicitly tested via
  smoke-import (`python -c "from icom_lan.audio.backend import …"`)
  before the PR is merged. **Three-tier validation Step 1 fires
  here.**

#### Step 8 — `runtime` part 1 (radio + state)

- **Scope:** move `radio.py` (the big one), `radio_state_snapshot`,
  `radio_initial_state`, `radio_reconnect`, `radios`, `ic705`,
  `_state_queries` into `runtime/`. Likely split into 8a/8b on
  size.
- **Risk:** `radio.py` is the centerpiece. Many tests reach into it.
  Re-export shim at `icom_lan/radio.py` is critical.

#### Step 9 — `runtime` part 2 (mixins)

- **Scope:** move 5 mixin files into `runtime/`. Mixins are
  internal-only; shims at old `_*_mixin.py` paths cover the
  test-suite private-path imports.

#### Step 10 — `runtime` part 3 (pollers + control + sync + helpers)

- **Scope:** move 11 files including `_civ_rx`, `_connection_state`,
  `_control_phase`, `sync`, `profiles_runtime`, `meter_cal`,
  `cw_auto_tuner`, `startup_checks`, `proxy`, `_audio_recovery`,
  `_poller_types` into `runtime/`. Likely split into 10a/10b.

#### Step 11 — `discovery → backends/`

- **Scope:** move `discovery.py` into `backends/discovery.py`. The
  function `discover_backends()` (or whatever the public entrypoint
  is named) gets re-exported from `backends/__init__.py`.

#### Step 12 — `cli`

- **Scope:** move `cli.py` into `cli/cli.py` or `cli/__init__.py`.
  **Decision needed in this step's PR:** does `__main__.py` move
  too, or stay top-level? Recommendation: keep `__main__.py` at
  top level for `python -m icom_lan` discoverability, with one
  line `from icom_lan.cli import main; main()`. State this
  decision in the PR description; small change, not a separate
  step.

#### Step 13 — `import-linter` integration + LAZY_MAP cleanup

- **Scope:** add `import-linter` to a `[dependency-groups] dev` group
  (NOT to `[project] dependencies`); commit `.importlinter` with the
  matrix from §3 + the named exceptions from §3.3; wire `lint-imports`
  into CI; rewrite `_LAZY_MAP` target tuples in
  `icom_lan/__init__.py` and `icom_lan/audio/__init__.py` to point
  to canonical (post-migration) paths; verify all 28 Tier 2 lazy
  names still resolve via the smoke check in §6.
- **No source-code moves.** This is the closing tooling step.

### 4.2 Step dependencies

```
Step 1 (skeleton) → Step 2 (core foundationals) → Step 3 (core contracts)
                                                 ↓
                              ┌─────────────────┴─────────────────┐
                              ↓                                   ↓
                     Step 4 (commands)                      Step 6 (scope)
                              ↓                                   ↓
                     Step 5 (profiles)                            ↓
                              ↓                                   ↓
                              └─────────────────┬─────────────────┘
                                                ↓
                                       Step 7 (audio)
                                                ↓
                            Step 8 (runtime: radio+state)
                                                ↓
                            Step 9 (runtime: mixins)
                                                ↓
                            Step 10 (runtime: pollers+control)
                                                ↓
                            Step 11 (discovery → backends)
                                                ↓
                                       Step 12 (cli)
                                                ↓
                            Step 13 (import-linter + LAZY_MAP cleanup)
```

The per-issue Phase 3 metadata uses
`blocked-by: <previous-issue-number>` to encode this graph.

---

## 5. Re-export shim policy

### 5.1 Shim file template

Every old top-level path becomes a shim file. **Verbatim template
agreed with the maintainer:**

```python
# Re-export shim for backwards compatibility.
# Canonical location: icom_lan.<new_layer>.<module>
# Do not add new symbols here — add them at the canonical location.
from icom_lan.<new_layer>.<module> import *  # noqa: F401, F403
```

The header is a grep-able marker (`grep -rn "Re-export shim"
src/icom_lan/`) and a signal to PR reviewers: do not edit by hand,
file edits go to the canonical location.

### 5.2 Why silent (no `DeprecationWarning`)

- `pyproject.toml` does not set `filterwarnings = ["error"]`, so a
  warning would not fail tests — but with 43+ private-path leaks and
  ~5210 tests, output would become a noise carpet that obscures real
  failures.
- `DeprecationWarning` is meaningful only with a deprecation horizon.
  This codebase has none planned: the maintainer is solo, the
  downstream `icom-lan-pro` consumes the public paths, shims cost
  one line. There is nothing to ramp down to.
- Warnings on private paths (`_connection_state`, `_civ_rx`, …)
  punish users who explicitly used a private API knowing the risk.
  Out-of-band guidance, not in-band.

### 5.3 Atomic-commit interpretation

The brief's non-negotiable #7 says each *commit* moves files OR adds
shims OR updates imports — never multiple categories in one commit.
This is interpreted as: **one PR per migration step, multiple atomic
commits within**:

1. Commit 1 — `refactor(modularization-stepN): move <files> to <layer>` — pure file relocation; tests fail intentionally.
2. Commit 2 — `refactor(modularization-stepN): add re-export shims for <files>` — restores compatibility; tests pass again.
3. Commit 3 (optional) — `refactor(modularization-stepN): update internal imports to canonical paths` — updates first-party `from .` imports to point at the new locations. Skipped if Step 13 will do the global cleanup.

This keeps `git log --follow <file>` informative for archaeology
without inflating the PR count.

### 5.4 LAZY_MAP is migration-INVARIANT

Critical for sub-agent guidance: the `_LAZY_MAP` in
`icom_lan/__init__.py` and `icom_lan/audio/__init__.py` keeps pointing
at the **OLD** paths during every migration step except Step 13. The
re-export shims handle the resolution. **Do NOT update LAZY_MAP per
move**; it creates a coordination headache and risks breaking lazy
resolution mid-flight. Step 13 rewrites it once, in bulk, after every
file is in its canonical home.

---

## 6. Risk mitigation per step

This table maps the 9 risks from discovery §9 onto migration steps
and states the per-step mitigation.

| Risk (from discovery §9) | Mitigations baked into the plan |
|---|---|
| **R1** — PEP 562 lazy-loader invisible to linter | Step 13 rewrites LAZY_MAP. Every Phase 4 PR's acceptance criteria includes a *Tier 2 smoke check*: `python -c "import icom_lan; [getattr(icom_lan, n) for n in icom_lan._LAZY_MAP]"` (and the analogous for `icom_lan.audio`). |
| **R2** — 43 private-path test leaks | Each step that moves a file referenced by tests via private path adds a shim at the old path (the §5.1 template). The shim's `from … import *` re-exports the same names; tests imports work unchanged. Phase 3 follow-up issue tracks the test-side migration. |
| **R3** — function-local imports as cycle workarounds | Step 5 (`profiles → rig_loader` at line 266) and Step 8/9 (`web.server → web_routing/startup` — out of scope of these steps but the import points are in `web/` which is untouched) preserve the deferred-import pattern verbatim. **Sub-agent guidance: if a `tests/` failure complains about ImportError on `rig_loader`, restore the function-local import; do not "fix" it.** |
| **R4** — 44 untested-by-direct-import modules | Every step's acceptance criteria runs the FULL pytest suite (per brief), not just module-targeted tests. This is non-negotiable. |
| **R5** — Dynamic imports (`serial_civ_link.py:362`, `web/rtc.py:49`) | Step 13's import-linter contract has explicit `ignore_imports` for the resolved targets (verified in Phase 4 by reading the call sites). |
| **R6** — Package-flat means no enforcement until structure is in place | Step 13 (NOT earlier) introduces import-linter to CI. Steps 1–12 run *without* boundary enforcement; their acceptance is pytest + mypy + ruff only. |
| **R7** — `_optional_deps.py` foundation-tier | Step 2 places it in `core/`; pre-step verification confirms it has zero `from icom_lan` imports (already verified empirically — see §1.3 footnote). |
| **R8** — `__main__.py` placement | Step 12 keeps it top-level (rationale in §4.1 Step 12). |
| **R9** — `ARCHITECTURE.md` stale | Phase 5 work (this plan does not touch ARCHITECTURE.md). |

---

## 7. Rollback plan

Per the brief's §"Phase 2 item 7": each merged step is independently
revertable. If a regression surfaces post-merge:

1. **`git revert <merge-commit-sha>`** of the offending PR. Push to
   `main`. CI confirms green.
2. File a regression issue against the reverted PR's number (label:
   `regression`, `modularization`).
3. Replan the step: identify the cause (wrong shim, missed
   dependency, test file using a private path that was overlooked),
   adjust the per-step acceptance criteria, and redo the step in a
   fresh PR.
4. Subsequent steps blocked until the redo merges (per the dependency
   chain in §4.2).

A revert is cheap because each step's PR is bounded ≤500 LOC moved
+ shims + maybe internal-import updates. There is no "rollback the
whole modularization" plan — that would be a 13-PR cascade and is
explicitly NOT supported. The smallest unit of rollback is one step.

---

## 8. Tooling integration plan

### 8.1 What gets added

- **`import-linter`** under a `[dependency-groups] dev` group in
  `pyproject.toml`, so it is installed by `uv sync --all-extras` in
  contributor and CI environments but is NOT a runtime dependency.
  This avoids polluting end-user installs.
- **`.importlinter`** at repo root with the matrix from §3 + the
  named exceptions from §3.3.
- **CI step**: a job that runs `uv run lint-imports`. (Cleaner than
  `uvx --with-editable . --from import-linter lint-imports` per
  discovery §8 caveat — the dev-deps approach declares the intent and
  the package shows up in `uv.lock`.)
- **Optional pre-commit hook**: deferred to a follow-up issue. The
  official `import-linter` pre-commit hook does not handle `uv`
  workflows cleanly (per discovery §8); CI-only enforcement is
  sufficient for this effort.

### 8.2 When (the sequencing — which the brief is right about)

**Step 13** of the migration plan introduces import-linter — *after*
every file has moved to its canonical location, *before* Phase 5
documentation polish. Reasons (from discovery §8):

- The package is currently flat. Adding import-linter before file
  moves means the contract has to enumerate ~56 per-file exceptions,
  which is as tedious as the migration itself and provides no
  guidance.
- Adding import-linter at the FIRST move would block every
  intermediate step on non-canonical edges that the partial
  structure surfaces.
- Adding it at Step 13, after the dust has settled, lets the tool
  do what it is good at: police drift in steady state.

### 8.3 What the contract looks like

Single `[importlinter:contract:layers]` block; the layer ordering is
linear from top (most-dependent) to bottom (foundational), with `|`
between siblings that genuinely do not import each other:

```ini
[importlinter]
root_packages =
    icom_lan

[importlinter:contract:layers]
name = icom-lan layered architecture
type = layers
layers =
    icom_lan.cli
    icom_lan.web | icom_lan.rigctld
    icom_lan.backends
    icom_lan.runtime
    icom_lan.profiles | icom_lan.audio
    icom_lan.commands | icom_lan.scope | icom_lan.dsp
    icom_lan.core
ignore_imports =
    icom_lan.radio_protocol -> icom_lan.audio_bus
    icom_lan.radio_protocol -> icom_lan.scope
    icom_lan.web.web_startup -> icom_lan.backends.yaesu_cat.poller
    icom_lan.web.web_startup -> icom_lan.backends.yaesu_cat.radio
```

Sibling-rank verification (none of these layers imports any of its
siblings — verified via the discovery import graph):

- `web` ⊥ `rigctld`: neither imports the other; an explicit
  `independence` contract was used in Agent C's draft and may be
  retained as a second contract for belt-and-braces.
- `profiles` ⊥ `audio`: no edges either direction.
- `commands` ⊥ `scope` ⊥ `dsp`: pairwise independent (each depends
  only on `core`).

Required ordering rationale (each row depends only on layers below
it):

- `runtime` requires `profiles, audio, commands, scope, core`.
- `profiles` requires `commands, core` → above `commands`.
- `audio` requires `scope, dsp, core` → above `scope` and `dsp`.
- `backends` requires `runtime, profiles, audio, commands, core`.

This contract is finalized in Step 13's PR; the discovery-artifacts
`importlinter-config-draft.ini` is its starting point but uses a
slightly different (split-into-multiple-`forbidden`-contracts) form
that worked for the flat layout. Once layers are physical, the
single `layers` contract above plus the four `ignore_imports`
exceptions is sufficient.

---

## 9. icom-lan-pro paper validation

Discovery §6 enumerated the 5 import paths × 8 files × 29 occurrences
that `icom-lan-pro` uses. Walking each path against the proposed
shim plan:

| icom-lan-pro path | Occurrences | Plan disposition | Shim needed? |
|---|---:|---|---|
| `icom_lan.audio.backend` | 19 | Path is INSIDE `audio/` (existing). Step 7 moves only top-level audio files; `audio/backend.py` is untouched. | No — path stable. |
| `icom_lan.dsp.pipeline` | 4 | Path is INSIDE `dsp/` (existing). `dsp/` is untouched in the entire plan. | No — path stable. |
| `icom_lan.dsp.nodes.base` | 3 | Inside `dsp/nodes/`. Untouched. | No. |
| `icom_lan.dsp.exceptions` | 2 | Inside `dsp/`. Untouched. | No. |
| `icom_lan.audio.dsp` | 1 | Inside `audio/` (existing). Step 7 leaves it alone. | No. |

**Result: ALL 29 icom-lan-pro import sites survive the migration
without requiring a single shim, because every path is already inside
an existing subpackage that this plan does not relocate.**

This is the result the discovery doc predicted ("the single best
piece of news"), now confirmed by walking the actual plan. Phase 4
sub-agents executing Steps 7 and 8 must include the icom-lan-pro
smoke-import in their PR acceptance — Tier 2 of the maintainer's
three-tier validation:

```bash
# Run from /Users/moroz/Projects/icom-lan-pro after an audio/ or dsp/ PR merges:
uv run python -c "
from icom_lan.audio import backend, dsp
from icom_lan.dsp import pipeline, exceptions
from icom_lan.dsp.nodes import base
print('icom-lan-pro import contract: OK')
"
```

---

## 10. Maintainer review checklist

The Phase 1 doc's §10 listed 4 decisions; all are encoded above. This
section is what the maintainer reviews before signing off Phase 2:

- [ ] Layer structure (§1) — particularly the `backends`-as-its-own-layer deviation from the brief.
- [ ] Allowed-imports matrix (§3) — and the four named exceptions in §3.3.
- [ ] First three migration steps in detail (§4.1 Steps 1–3).
- [ ] Shim policy implementation: the verbatim header template (§5.1) and the LAZY_MAP-INVARIANT rule (§5.4).
- [ ] icom-lan-pro paper-validation outcome (§9).
- [ ] Two follow-up issues to be filed in Phase 3:
  - [ ] `[Followup] Migrate tests off private internal imports` (`followup-after-modularization`).
  - [ ] `[Followup] Refactor web_startup to use backends.factory` (`followup-after-modularization`).

**Stop-and-ask triggers from the brief — actively flagged for
maintainer attention:**

- Final structure differs significantly from the brief skeleton.
  **YES.** `backends` is its own top-level layer rather than nested
  under `core`. Deviation rationale in §1.3 (empirical: backends
  imports from runtime, audio, commands, profiles).
- Allowed-imports rule forces a behavior change. **NO** — every
  import that exists today either stays a legal edge under the
  matrix or has a named exception (§3.3). No code is restructured
  for boundary compliance during this effort.
- A re-export shim is infeasible. **NO** — every old path becomes a
  one-liner shim. No name clashes detected; verified by walking the
  60 names in `__all__` against the proposed canonical-path map.

---

## 11. What this plan deliberately does NOT include

Per the brief's §"What this work is NOT":

- ❌ Splitting `icom_lan` into multiple PyPI packages.
- ❌ Renaming `icom_lan` or any public class.
- ❌ Touching `icom-lan-pro` source.
- ❌ Adding new tests of new behavior.
- ❌ Refactoring `radio_protocol` to remove `audio_bus` / `scope`
  TYPE_CHECKING imports — out of scope; followup-eligible.
- ❌ Refactoring `web_startup` to go through `backends.factory` — out
  of scope; followup created in Phase 3.
- ❌ Migrating tests off private-path imports — out of scope;
  followup created in Phase 3.

Phase 5 (Integration & Sign-off) handles `LAYER.md` charters and
`ARCHITECTURE.md` refresh. Phase 3 (Issue Creation) is the next
phase after this plan is approved.
