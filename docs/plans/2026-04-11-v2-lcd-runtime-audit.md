# V2/LCD Runtime Boundary Audit

**Date:** 2026-04-11
**Status:** Research in progress
**Issue:** `#641`
**Base commit:** `f0e78cc0ea0fcfbafdadbb4a20167ba0bc110d6a` (`origin/main`)

## Goal

Establish whether `v2` main and LCD are truly two presentations over one shared frontend runtime, or whether runtime responsibilities have leaked into layout and leaf components.

## Current topology

### Shared app entrypoint

`frontend/src/App.svelte:24-52` initializes one frontend runtime path for `v2`:

- polls `/api/v1/state` via `startPolling(...)`
- loads `/api/v1/capabilities`
- opens the control WebSocket `/api/v1/ws`
- mounts `RadioLayoutV2` when `uiVersion === 'v2'`

This means LCD is not a separate app in current `origin/main`; it is a layout variant inside `v2`.

### V2 layout split

`frontend/src/components-v2/layout/RadioLayout.svelte:191-195` chooses between:

- `MobileRadioLayout`
- `LcdLayout`
- standard `RadioLayout` content

`frontend/src/components-v2/layout/LcdLayout.svelte:47-67` reuses the same sidebars as standard layout:

- `LeftSidebar`
- `RightSidebar`
- `StatusBar`
- `KeyboardHandler`

Only the center content changes:

- standard layout renders `SpectrumPanel`
- LCD layout renders `AmberLcdDisplay`

### Shared state/command machinery already present

The main shared abstraction is:

- `frontend/src/components-v2/wiring/state-adapter.ts`
- `frontend/src/components-v2/wiring/command-bus.ts`

Example: `RightSidebar.svelte:56-85` derives props through `state-adapter` and binds UI events through `command-bus`. `RxAudioPanel.svelte:8-23` is mostly presentation-only and receives props/callbacks.

This is the right architectural direction, but it is not yet the only path.

## Confirmed boundary violations

### 1. Presentation components still own transport connections

These components open their own WS channels instead of consuming data from a shared runtime/controller:

- `frontend/src/components/spectrum/SpectrumPanel.svelte:310-318`
  Opens `/api/v1/scope` directly with `getChannel('scope')`.
- `frontend/src/components-v2/panels/audio-scope/AudioSpectrumPanel.svelte:55-72`
  Opens `/api/v1/audio-scope` directly with `getChannel('audio-scope')`.
- `frontend/src/components-v2/panels/lcd/AmberLcdDisplay.svelte:145-168`
  Also opens `/api/v1/audio-scope` directly with `getChannel('audio-scope')`.

Consequence: scope/audio-scope lifecycle is tied to which component happens to be mounted, not to one runtime owner.

### 2. Leaf components still dispatch backend commands directly

These components bypass `command-bus` and call `sendCommand(...)` themselves:

- `frontend/src/components/spectrum/SpectrumPanel.svelte:287-298`
  Sends `set_freq` during drag tuning.
- `frontend/src/components-v2/panels/lcd/AmberLcdDisplay.svelte:284`
  Sends `set_tuner_status` directly.
- `frontend/src/components-v2/panels/MemoryPanel.svelte:56-80`
  Sends memory commands directly.

Consequence: behavior can diverge by component even if state derivation is shared.

### 3. TX audio lifecycle is split between command handlers and components

RX audio is controlled in `command-bus`:

- `frontend/src/components-v2/wiring/command-bus.ts:536-581`
  `makeRxAudioHandlers()` owns `audioManager.startRx()`, `stopRx()`, and browser volume updates.

TX audio is not centralized the same way. These presentation/layout components still call `audioManager` directly:

- `frontend/src/components-v2/panels/TxPanel.svelte:55-80`
  Calls `audioManager.startTx()` / `stopTx()` inside PTT logic.
- `frontend/src/components-v2/layout/MobileRadioLayout.svelte:290-297`
  Also calls `audioManager.startTx()` / `stopTx()` directly.

Consequence: RX and TX do not share one consistent ownership model. Mobile and desktop TX can evolve differently.

### 4. Layout/presentation components still own HTTP side effects

These UI components call backend HTTP endpoints directly:

- `frontend/src/components-v2/layout/LcdLayout.svelte:27-38`
  Calls `/api/v1/radio/power`.
- `frontend/src/components-v2/layout/StatusBar.svelte:47-78`
  Calls connect/disconnect and power endpoints.
- `frontend/src/components-v2/layout/StatusBar.svelte:87-108`
  Calls `/api/v1/eibi/identify`.

Consequence: system/runtime actions are not consistently routed through one orchestration layer.

### 5. LCD still contains logic that is not expressed through shared view-models

`frontend/src/components-v2/panels/lcd/AmberLcdDisplay.svelte` contains custom derivation beyond presentation:

- band lookup by frequency: `:38-64`
- active meter source state and cycling: `:87-109`
- LCD-specific DSP activity heuristics: `:111-121`
- AGC label mapping: `:133-140`

Some of this is valid presentation logic, but some of it is semantic UI/view-model logic that should be explicit in adapters if parity across skins matters.

### 6. Scope frame parsing is duplicated across UI surfaces

Equivalent `parseScopeFrame(...)` logic appears in:

- `frontend/src/components-v2/panels/audio-scope/AudioSpectrumPanel.svelte:18-27`
- `frontend/src/components-v2/panels/lcd/AmberLcdDisplay.svelte:27-36`
- `frontend/src/components/spectrum/spectrum-logic.ts`

Consequence: protocol handling is duplicated in presentation surfaces.

## What is actually shared today

The current codebase is not "two separate frontends". It already shares meaningful core pieces:

- one top-level app bootstrap (`App.svelte`)
- one control WS path
- one polling/state store path
- one capabilities store path
- one `state-adapter`
- one `command-bus` for a large portion of controls
- shared sidebars between standard and LCD layouts

So the problem is not lack of any shared architecture. The problem is incomplete enforcement of that architecture.

## Current assessment

The code on `origin/main` is in an intermediate state:

- directionally correct toward shared runtime + presentation adapters
- not yet strict enough to guarantee parity
- still vulnerable to model drift because transport, audio lifecycle, and commands can be reintroduced into UI components

That explains how "same backend" can still produce different behavior by layout or mounted component path.

## Implications for next issues

### For `#642` (audio failure trace)

Need to verify whether LCD audio failure is caused by:

- a capability/UI gating mismatch
- a decode/playback path issue in `audioManager` / `rx-player`
- component-mount ownership of audio/scope side effects
- a browser/user-gesture issue

### For `#643` (target runtime contract)

The target contract should make these ownership rules explicit:

- layouts do not open WS connections
- panels do not import `audioManager`
- panels do not call `sendCommand(...)` directly
- panels do not call backend HTTP endpoints directly
- protocol parsing does not live in rendering components

### For `#646` (presentation architecture)

Need to separate:

- presentation-only formatting/styling logic
- semantic view-model derivation
- runtime transport/command ownership

Without that split, "skin" work will keep reintroducing behavioral forks.

## Provisional conclusion

On current `origin/main`, LCD and standard `v2` are partially unified, but not fully architecture-safe.

The main architectural defect is not that LCD is a separate app; it is that runtime ownership is still distributed across layout and leaf components. That is enough to cause layout-dependent regressions even when backend transport is shared.
