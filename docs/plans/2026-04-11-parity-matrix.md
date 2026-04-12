# V2/LCD Parity Matrix And Regression Harness

**Date:** 2026-04-11
**Status:** Draft
**Issue:** `#644`
**Based on:** `#641`, `#642`, `#643`, `#646`
**Base commit:** `f0e78cc0ea0fcfbafdadbb4a20167ba0bc110d6a`

## Objective

Define what "parity" means for standard `v2` and LCD, and which checks must exist before and during migration to the unified architecture.

Parity here means:

- same runtime behavior
- same capability semantics
- same command side effects
- same audio/scope lifecycle behavior

It does **not** mean identical DOM or identical visuals.

## First-class capability scenarios

These capability combinations must be treated as explicit scenarios.

### Scenario A

- hardware scope: yes
- live audio: yes

Expected presentations:

- standard layout available
- LCD layout available
- audio and scope both functional

### Scenario B

- hardware scope: no
- live audio: yes

Expected presentations:

- LCD is a valid first-class layout
- live audio still works exactly as in Scenario A
- lack of scope must not change audio behavior

This is the most important regression scenario for the current problem.

### Scenario C

- hardware scope: yes
- live audio: no

Expected presentations:

- scope still works
- no `LIVE` monitor path is offered
- local AF control still works if radio supports AF

### Scenario D

- hardware scope: no
- live audio: no

Expected presentations:

- LCD remains valid
- no live-audio path
- no scope path
- core tuning / mode / meter / tx behavior still works

## High-risk flows

These are the flows most likely to regress during runtime unification.

### 1. App bootstrap

Check:

- state polling starts
- capabilities load
- control WS connects
- runtime derives the correct semantic availability for scope/audio

### 2. Layout selection

Check:

- `auto` chooses the expected layout from capabilities
- forcing LCD/standard changes presentation only
- switching layout does not change transport ownership

### 3. RX monitor mode transitions

Check:

- `RADIO -> LIVE`
- `LIVE -> MUTE`
- `MUTE -> RADIO`
- `MUTE -> LIVE`

Expected:

- same state transitions in standard and LCD
- same audio controller behavior
- same AF-level semantics

### 4. AF level changes

Check separately:

- AF level change in `RADIO`
- AF level change in `LIVE`

Expected:

- `RADIO` controls radio AF command path
- `LIVE` controls browser playback volume path
- LCD and standard must not disagree about which path is active

### 5. Receiver switching

Check:

- MAIN/SUB active receiver change
- monitor mode preserved correctly
- commands address the intended receiver
- displayed meter/frequency/mode are derived from the same active receiver semantics

### 6. Reconnect / remount

Check:

- control WS reconnect
- audio WS reconnect
- layout remount while runtime remains alive
- runtime rehydrates view models correctly

Expected:

- mounted component path does not decide which transport reconnects

### 7. Scope unavailable while audio remains available

Check:

- capability or runtime state where scope is absent but audio is present

Expected:

- `LIVE` still functions
- no hidden dependency on scope mount state

### 8. PTT / TX interaction with audio

Check:

- entering TX
- leaving TX
- monitor/audio state around TX transitions

Expected:

- same TX audio lifecycle regardless of layout

## Parity matrix

## Scenario A: `scope=true`, `audio=true`

| Flow | Standard V2 | LCD | Automation target |
|---|---|---|---|
| Bootstrap | Pass | Pass | unit + component |
| `LIVE` playback path | Must work | Must work | unit + browser/manual |
| Scope stream | Must work | Optional render variant, same runtime ownership | unit + browser/manual |
| Layout switch | No transport restart due only to layout | Same | browser/manual |
| Receiver switch | Same active receiver semantics | Same | unit + component |

## Scenario B: `scope=false`, `audio=true`

| Flow | Standard V2 | LCD | Automation target |
|---|---|---|---|
| Auto layout choice | LCD fallback or equivalent | Pass | unit |
| `LIVE` playback path | Must work | Must work | unit + browser/manual |
| Scope ownership | Absent | Absent | unit |
| AF level semantics | Same | Same | unit |
| Layout remount | Audio unaffected | Audio unaffected | browser/manual |

## Scenario C: `scope=true`, `audio=false`

| Flow | Standard V2 | LCD | Automation target |
|---|---|---|---|
| `LIVE` option visibility | Hidden | Hidden | component |
| Scope path | Works | Same runtime semantics if rendered | unit + browser/manual |
| AF local control | Works if radio AF exists | Works | unit |

## Scenario D: `scope=false`, `audio=false`

| Flow | Standard V2 | LCD | Automation target |
|---|---|---|---|
| Auto layout choice | LCD fallback or equivalent | Pass | unit |
| `LIVE` option visibility | Hidden | Hidden | component |
| Core radio control flows | Same | Same | unit + component |

## Regression harness strategy

### Layer 1: pure unit tests

Target:

- adapters
- capability resolution
- layout selection logic
- monitor mode derivation
- receiver selection semantics

Good candidates:

- `state-adapter`
- layout mode resolution
- semantic view-model builders

### Layer 2: component tests

Target:

- semantic components
- layout composition decisions
- option visibility
- callback wiring

Good candidates:

- `RxAudioControl`
- `ScopeSurface`
- `VfoDisplay`
- layout wrappers

### Layer 3: controller/runtime tests

Target:

- audio controller
- scope controller
- reconnect behavior
- ownership invariants

Needed especially for:

- `LIVE` start/stop
- ws reconnect
- layout remount while runtime state persists

This layer is currently weak and should be added during migration.

### Layer 4: browser integration tests

Target:

- autoplay/user-gesture interactions
- actual `AudioContext` state
- layout switching in a browser environment
- route through real runtime shell

These should use Playwright with controlled mocks for backend endpoints where possible.

### Layer 5: manual / hardware validation

Still required for:

- real radio codec negotiation
- actual audio output audibility
- hardware scope + audio coexistence
- radio/backend-specific codec combinations

## Current blind spots

These are the important gaps in current automation.

### Blind spot 1

No meaningful tests for `audioManager` RX lifecycle.

Current tests do not prove:

- `/api/v1/audio` connect/start behavior
- reconnect behavior
- first-frame handling

### Blind spot 2

No meaningful tests for Opus decode availability.

Current tests do not prove:

- `AudioDecoder` presence/absence handling
- decoder recreation after error

### Blind spot 3

No tests for mounted-layout independence.

Current tests do not prove:

- transport ownership is unchanged when switching between standard and LCD

### Blind spot 4

No backend tests around codec normalization edge cases.

Current tests do not prove:

- `PCM_1CH_8BIT` path
- u-law decode path end-to-end to browser framing

### Blind spot 5

No automation for browser autoplay/suspended-context failures.

This is exactly the kind of issue that can make "frames arrived" look healthy while playback is dead.

## Acceptance checks before cutover

Before the unified architecture becomes default, the migration should satisfy:

1. Scenario B (`scope=false`, `audio=true`) has explicit automated coverage
2. Layout switching does not restart or re-own transports
3. `LIVE` mode has one tested controller path
4. Receiver switching semantics are identical across layouts
5. At least one manual hardware validation run confirms audio playback on the previously failing class of radio

## Provisional conclusion

The migration should be judged against parity of behavior slices, not against visual similarity.

The most critical regression target is:

- `scope=false + audio=true`

because that is the scenario most likely to reveal whether the architecture is truly unified or only visually similar.
