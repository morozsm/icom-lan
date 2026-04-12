# Frontend Runtime Unification Migration Plan

**Date:** 2026-04-11
**Status:** Draft
**Issue:** `#645`
**Depends on:** `#641`, `#642`, `#643`, `#644`, `#646`
**Base commit:** `f0e78cc0ea0fcfbafdadbb4a20167ba0bc110d6a`

## Executive summary

The frontend does not need a big-bang rewrite. It needs controlled completion of an architecture that already partially exists.

Current state:

- one app bootstrap
- one shared store layer
- one `state-adapter`
- one `command-bus`
- LCD already expressed as a layout branch inside `v2`

Current problem:

- runtime ownership still leaks into layout and leaf components
- audio/scope/command behavior can still depend on mounted component path
- parity is not enforced by tests or architecture guardrails

Therefore the migration strategy should be:

1. instrument and prove the current failure mode
2. add anti-drift guardrails
3. centralize runtime ownership
4. formalize presentation boundaries
5. migrate one layout at a time
6. cut over only after parity checks exist

## Confirmed findings

From `#641`:

- LCD is not a separate frontend in current `origin/main`; it is a layout branch within `v2`
- runtime side effects still leak into UI components
- duplicated protocol parsing and direct transport access still exist

From `#642`:

- audio transport success is not enough to prove playback success
- plausible failure points include:
  - suspended `AudioContext`
  - missing usable `AudioDecoder`
  - codec normalization mismatch, especially 8-bit PCM -> web PCM16
- next step should be instrumentation, not speculative fixes

From `#643`:

- frontend needs one runtime shell and controller-owned side-effect layer
- layouts and panels must become presentation-only

From `#646`:

- theme, skin, and layout variant must be separate concepts
- presentation flexibility should come from tokens, semantic renderers, and composition
- none of them may own runtime behavior

From `#644`:

- parity must be defined by behavior slices, not visual similarity
- the critical regression scenario is `scope=false + audio=true`

## Final target state

The final frontend shape should be:

- one shared runtime shell
- controller-owned transport/audio/scope/system behavior
- pure adapters
- semantic components
- skins/themes/layout variants above the semantic layer
- parity coverage around capability scenarios and critical flows

## What must happen first

### First priority

Make the system observable and anti-drift safe before moving behavior.

That means:

- diagnostic instrumentation for the current RX audio failure
- architectural guardrails against new direct transport imports in presentation components

### Second priority

Move ownership of side effects, not visuals.

The first migration work should extract:

- audio ownership
- scope ownership
- system HTTP ownership

### Third priority

After runtime ownership is centralized, migrate layouts onto the new contract one by one.

## What should not change early

During early phases, do **not**:

- redesign the UI
- rewrite both layouts at once
- mix skin/theme work into transport ownership changes
- change backend protocol unless instrumentation proves it is necessary
- move every component into a new directory structure up front

Early phases should preserve user-visible behavior as much as possible.

## Recommended phase sequence

The placeholder implementation phases are directionally correct and should be kept, with one important clarification:

- diagnostic instrumentation belongs at the very start of Phase 0

## Phase 0 — Guardrails + diagnostics

Issue anchor: `#647`

Objectives:

- add minimal diagnostic instrumentation for RX playback failures
- add forbidden-import guardrails for presentation components
- define temporary ownership exceptions explicitly

Outputs:

- logs that classify current LCD audio failure
- lint/test guardrails preventing new `sendCommand`, `getChannel`, `audioManager`, and backend `fetch` imports in presentational UI

Rollback risk:

- very low

### Why Phase 0 exists

Without diagnostics, we may refactor around the wrong root cause.
Without guardrails, model-generated changes can keep reintroducing the same leak.

## Phase 1 — Shared runtime shell and adapter boundary

Issue anchor: `#648`

Objectives:

- introduce a formal `FrontendRuntime` boundary
- define controller/action interfaces
- ensure layouts receive runtime-backed semantic props/callbacks rather than reaching into transports

Outputs:

- runtime shell scaffold
- injected runtime/actions interface
- presentation components no longer need direct runtime imports for newly migrated slices

Rollback risk:

- low if behavior slices are migrated incrementally

## Phase 2 — Centralize audio and scope ownership

Issue anchor: `#649`

Objectives:

- move `/api/v1/audio`, `/api/v1/scope`, `/api/v1/audio-scope` ownership into controllers
- move binary frame parsing out of presentation components
- unify RX/TX audio lifecycle ownership

Outputs:

- one audio controller
- one scope controller per scope type
- no direct `getChannel(...)` usage in scope-rendering surfaces
- no direct `audioManager` usage in presentation components

Rollback risk:

- medium
- mitigated by instrumentation and scenario-B parity checks

## Phase 3 — Semantic presentation layer

Issue anchor: `#650`

Objectives:

- formalize semantic component contracts
- separate semantic components from primitives
- create skin/theme-ready presentation boundaries

Outputs:

- semantic component APIs
- initial skin registry pattern
- layout slots/composition contract

Rollback risk:

- low to medium
- mostly structural if runtime ownership is already centralized

## Phase 4 — Migrate standard V2 onto unified architecture

Issue anchor: `#651`

Objectives:

- move the standard desktop layout onto the new runtime/presentation contract

Outputs:

- standard layout consuming only semantic props/actions
- no direct transport ownership in standard layout/panels

Rollback risk:

- medium
- mitigated by keeping LCD untouched during this phase

## Phase 5 — Migrate LCD onto unified architecture

Issue anchor: `#652`

Objectives:

- move LCD layout and LCD renderers onto the same contract
- remove remaining LCD-only runtime ownership

Outputs:

- LCD expressed as skin/layout over shared runtime
- `scope=false + audio=true` explicitly validated

Rollback risk:

- medium to high
- this is where the current bug class is most likely to surface

## Phase 6 — Cutover and remove obsolete paths

Issue anchor: `#653`

Objectives:

- make unified architecture the only production path
- delete superseded transport ownership code and temporary compatibility layers

Outputs:

- one default runtime path
- cleaned legacy code
- cutover checklist completed

Rollback risk:

- medium
- should only happen after parity matrix acceptance checks pass

## Implementation backlog mapping

The existing issue set is mostly correct:

- `#647` keep, but explicitly include diagnostic instrumentation
- `#648` keep
- `#649` keep
- `#650` keep
- `#651` keep
- `#652` keep
- `#653` keep

No renumbering or major backlog reshuffle is necessary at this stage.

## Evidence gates between phases

These should block progression.

### Gate after Phase 0

- current RX playback failure classified with evidence
- forbidden-import guardrails active

### Gate after Phase 2

- one controller-owned audio path exists
- one controller-owned scope path exists
- no remaining presentation-owned WS connections for migrated slices

### Gate after Phase 3

- semantic component contracts are stable enough for both standard and LCD

### Gate before Phase 6 cutover

- parity checks for all four capability scenarios exist
- Scenario B (`scope=false + audio=true`) explicitly passes
- manual hardware validation completed on affected radio class

## Relationship between runtime and presentation architecture

The migration has two independent but coordinated goals:

### Runtime goal

Make behavior single-owned and layout-independent.

### Presentation goal

Make visuals extensible without behavior forks.

The runtime work must happen first.
Presentation flexibility only becomes safe after runtime ownership is fixed.

## Main risks

### Risk 1

Fixing the current audio symptom by ad hoc patching the visible LCD path.

Effect:

- symptom may disappear temporarily
- architecture drift gets worse

### Risk 2

Trying to introduce the full skin/theme system before centralizing runtime ownership.

Effect:

- visual flexibility increases while correctness decreases

### Risk 3

Judging parity by screenshots or layout similarity.

Effect:

- behavior regressions slip through

## Immediate next step

The next concrete execution step should be:

- Phase 0 diagnostic instrumentation patch for RX playback

Reason:

- it directly resolves the highest-uncertainty finding from `#642`
- it is low-risk
- it informs whether later migration must include a codec fix, browser playback fix, or both

## Provisional conclusion

The existing implementation backlog is valid. It only needs to be interpreted as a disciplined migration story:

- diagnose
- guard
- centralize ownership
- formalize semantic presentation
- migrate one layout at a time
- cut over only after behavior parity is proven
