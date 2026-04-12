# Shared Frontend Runtime Contract

**Date:** 2026-04-11
**Status:** Draft for discussion
**Issue:** `#643`
**Based on:** `#641`, `#642`
**Base commit:** `f0e78cc0ea0fcfbafdadbb4a20167ba0bc110d6a`

## Objective

Define a strict frontend contract so:

- `v2` main and LCD consume one shared runtime
- layouts differ only in presentation and composition
- audio, scope, commands, capability gating, and connection lifecycle do not fork by mounted component path

## Why this contract is needed

Current `origin/main` already has shared pieces:

- one app bootstrap
- shared stores
- `state-adapter`
- `command-bus`
- shared sidebars

But `#641` showed that runtime ownership still leaks into presentation:

- WS channels opened by rendering components
- `audioManager` used directly in UI components
- direct `sendCommand(...)` in leaf components
- direct backend `fetch(...)` in layout components
- duplicated protocol parsing in UI surfaces

That is enough to cause layout-dependent regressions even with one backend and one WS API.

## Target architecture

The frontend should be split into four layers.

### 1. Runtime layer

Owns all stateful side effects:

- HTTP bootstrap
- control WS lifecycle
- scope/audio-scope WS lifecycle
- audio WS lifecycle
- browser playback lifecycle
- TX microphone lifecycle
- reconnect logic
- capability normalization
- command dispatch
- optimistic state updates

Examples of modules that belong here:

- `app runtime shell`
- `audio controller`
- `scope controller`
- `control controller`
- shared stores

### 2. Adapter layer

Pure functions mapping runtime state into semantic view models.

Responsibilities:

- derive panel/view props
- normalize per-radio/runtime quirks into stable semantic values
- expose layout-independent callbacks supplied by runtime/controllers

This is where "what does the UI mean?" lives, but not "how does it talk to the backend?".

### 3. Semantic UI layer

Presentation components for radio concepts, not transport details.

Examples:

- VFO display
- RX audio controls
- TX controls
- meter panel
- memory panel
- scope surface

These components render view models and call provided callbacks.

### 4. Layout layer

Composes semantic UI into concrete screens:

- standard desktop
- LCD desktop
- mobile

Layouts may decide placement, visibility, grouping, and composition.
Layouts must not own runtime side effects.

## Ownership rules

### Runtime owns

- `WebSocket` creation and teardown
- endpoint paths like `/api/v1/ws`, `/api/v1/audio`, `/api/v1/scope`, `/api/v1/audio-scope`
- `audioManager` or its replacement
- browser `AudioContext` / decoder lifecycle
- protocol parsing for binary frames
- backend HTTP commands
- optimistic patches to shared state

### Adapters own

- mapping `ServerState + Capabilities + UiState -> semantic props`
- capability-based visibility decisions that affect behavior
- semantic labels and normalized enums used by more than one layout

### Presentation/layout owns

- markup
- CSS/theme classes
- panel composition
- local ephemeral UI state that does not affect shared behavior
  - popover open/close
  - drag reorder of panel positions
  - temporary expanded/collapsed UI state

## Allowed imports and forbidden imports

### Allowed in presentational components

- adapter-derived prop types
- stateless formatting helpers
- semantic callback props
- theme tokens/styles
- purely visual child components

### Forbidden in presentational components

- `$lib/transport/ws-client`
- `sendCommand(...)`
- `getChannel(...)`
- `$lib/audio/audio-manager`
- direct `fetch(...)` to backend endpoints
- binary protocol parsers for scope/audio frames
- capability stores when the check changes behavior rather than just visibility

## Invariants

These must hold after migration.

### Invariant 1

There is exactly one RX playback path for all layouts.

Consequence:

- `LIVE` in standard and LCD must route through the same audio controller
- codec negotiation, WS subscription, decoding, volume, and mute logic are layout-independent

### Invariant 2

There is exactly one scope ownership path per scope type.

Consequence:

- hardware scope and audio FFT are mounted by runtime/controller ownership
- layouts only choose whether and where to render the resulting view surface

### Invariant 3

`scope=false + audio=true` is a first-class supported state.

Consequence:

- absence of hardware scope must never alter audio behavior
- LCD fallback and standard layout selection are presentation concerns, not audio runtime concerns

### Invariant 4

Capability gating for behavior happens before presentation.

Consequence:

- panels should not independently decide whether backend behavior exists
- adapters/runtime expose stable booleans like `hasLiveAudio`, `hasHardwareScope`, `hasTx`

### Invariant 5

Mounted component choice must not change transport ownership.

Consequence:

- swapping layouts cannot change which WS is connected
- mounting/unmounting a visual scope surface cannot be the thing that starts or stops the underlying scope stream

## Proposed runtime shape

## `FrontendRuntime`

A single runtime shell should expose:

- `state`
- `capabilities`
- `connectionStatus`
- `audioState`
- `scopeState`
- `actions`

### `actions`

Runtime-level actions should include:

- tuning actions
- mode/filter actions
- TX/PTT actions
- RX audio monitor actions
- scope actions
- system actions

These are the only callbacks adapters/layouts should receive.

## Proposed controller split

### `controlController`

- owns `/api/v1/ws`
- sends commands
- applies optimistic updates

### `audioController`

- owns `/api/v1/audio`
- owns browser playback and TX mic lifecycle
- exposes monitor mode / volume / mute / tx-audio actions

### `scopeController`

- owns `/api/v1/scope` and `/api/v1/audio-scope`
- parses binary frames once
- exposes normalized scope models

### `systemController`

- owns power/connect/disconnect/eibi HTTP actions

## Migration principles

### Principle 1

Move ownership before moving visuals.

Do not rewrite layouts first. First extract transport/audio/command ownership into runtime/controllers.

### Principle 2

Keep adapters pure.

If logic needs network, timers, browser APIs, or shared stores with side effects, it is not adapter logic.

### Principle 3

Replace direct imports with injected callbacks or view models.

If a panel currently imports `sendCommand`, `audioManager`, or `getChannel`, that is a migration target.

### Principle 4

Migrate by behavior slice, not by file tree.

Preferred order:

1. audio ownership
2. scope ownership
3. system/backend HTTP actions
4. remaining direct command dispatch

### Principle 5

Guardrails must enforce the contract.

After migration, lint/tests should fail when presentational components import forbidden runtime modules.

## Anti-drift rules for model-generated changes

Any future change must answer:

1. Which layer owns this behavior?
2. Does this component need side effects, or only a view model?
3. If a new layout is added, would this logic fork?

If the answer implies layout-dependent behavior, the change belongs in runtime/controllers or adapters, not in a panel/layout component.

## Out of scope

This contract does not define:

- skin/theme/token architecture
- component composition flexibility across skins

That belongs in `#646`.

## Provisional conclusion

The codebase does not need a second frontend rewrite. It needs strict completion of the architecture it already started:

- one runtime shell
- one controller-owned side-effect layer
- pure adapters
- presentational panels/layouts only

That is the minimum contract required to keep `v2`, LCD, and future skins behaviorally identical while still allowing radically different presentation.
