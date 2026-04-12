# Presentation Architecture For Skins, Themes, And Layout Variants

**Date:** 2026-04-11
**Status:** Draft for discussion
**Issue:** `#646`
**Depends on:** `#643`
**Base commit:** `f0e78cc0ea0fcfbafdadbb4a20167ba0bc110d6a`

## Objective

Define the ideal presentation architecture above the shared runtime so the app can support:

- standard `v2`
- LCD
- future skins
- small theme changes
- larger component-level visual swaps

without reintroducing logic drift.

## Core definitions

### Runtime

The stateful side-effect layer:

- backend transport
- audio/scope lifecycle
- commands
- capability normalization
- optimistic updates

Runtime must be presentation-agnostic.

### View-model adapter

A pure mapping layer:

- runtime state -> semantic UI props
- runtime actions -> semantic callbacks

Adapters know what the UI means, but not how it looks.

### Semantic component

A component representing a radio concept with stable behavior contract.

Examples:

- `VfoDisplay`
- `RxAudioControl`
- `ScopeSurface`
- `MeterPanel`
- `TxControl`

Semantic components receive semantic props and callbacks only.

### Primitive component

A low-level visual building block with no radio semantics.

Examples:

- button
- segmented control
- gauge
- card
- label/value row
- LED indicator

### Theme

A token set for colors, typography, spacing, shadows, borders, motion.

Theme changes appearance without changing component identity or layout structure.

### Skin

A mapping from semantic components to concrete visual implementations.

Examples:

- `industrial-v2`
- `amber-lcd`
- future `rack`, `retro`, `minimal`, `touch`

A skin may swap component internals, but must preserve semantic component contracts.

### Layout variant

A screen composition over semantic components.

Examples:

- desktop standard
- desktop LCD
- mobile
- compact monitor

Layout variants choose placement and grouping, not runtime behavior.

## Recommended layering

Dependency direction should be one-way:

`runtime -> adapters -> semantic components -> skin implementations -> primitives -> theme tokens`

And separately:

`layout variant -> semantic components`

Important:

- runtime must not import skins/themes/layouts
- themes must not know about runtime
- skin implementations must not talk to runtime directly
- layout variants must compose semantic components, not transports

## The three presentation knobs

These should be first-class and separate.

### 1. Theme = token switch

Use theme when only visual language changes:

- colors
- font families
- spacing scale
- border radius
- shadows
- animation style

Theme should be mostly CSS variables and token objects.

### 2. Skin = semantic renderer switch

Use skin when the same radio concept needs a different visual implementation:

- classic seven-segment frequency vs industrial frequency strip
- analog S-meter vs LCD bar meter
- hardware-style buttons vs flat touch controls

Skin swaps renderers, not behavior contracts.

### 3. Layout variant = composition switch

Use layout variants when the same semantic components need different arrangement:

- sidebars vs stacked mobile panels
- LCD center panel vs wide spectrum center panel
- docked meters vs embedded meters

Layout variants decide:

- which semantic components appear
- where they appear
- in which slot/group they appear

They must not decide:

- how to connect to backend transports
- how to decode audio
- how to dispatch commands

## Semantic component contract

Each semantic component should expose:

- semantic props only
- semantic callbacks only
- no transport knowledge
- no backend endpoint knowledge
- no concrete skin assumptions

Example:

`RxAudioControl` should receive:

- `monitorMode`
- `hasLiveAudio`
- `level`
- `onMonitorModeChange`
- `onLevelChange`

It should not know:

- `audioManager`
- `/api/v1/audio`
- codec names
- `sendCommand(...)`

## Skin architecture

Each skin should provide a component registry for semantic components.

Example shape:

- `skins/industrial-v2/registry.ts`
- `skins/amber-lcd/registry.ts`

Each registry maps semantic component ids to concrete implementations.

Example:

- `VfoDisplay -> IndustrialVfoDisplay`
- `MeterPanel -> NeedleMeterPanel`
- `RxAudioControl -> HardwareRxAudioPanel`

Another skin might map:

- `VfoDisplay -> AmberFrequencyDisplay`
- `MeterPanel -> AmberMeterStrip`
- `RxAudioControl -> LcdAudioStrip`

The semantic API stays the same.

## Primitive architecture

Primitives should be reusable visual building blocks, not "business logic widgets".

Good primitives:

- `ControlButton`
- `SegmentedControl`
- `Gauge`
- `Knob`
- `PanelFrame`
- `StatusPill`

Bad primitives:

- `WsAwareButton`
- `ScopeConnectedIndicator` that reads transport state itself
- `PttButton` that imports `audioManager`

## Slots and composition

Layouts should compose semantic components via named slots/zones.

Recommended slot model:

- `header`
- `leftRail`
- `centerPrimary`
- `centerSecondary`
- `rightRail`
- `bottomDock`
- `overlay`

Each layout variant assigns semantic components into these slots.

This keeps composition flexible without inventing new runtime paths.

## How standard V2 and LCD should differ in the target system

### Standard desktop

- skin: `industrial-v2`
- theme: one of the current token themes
- layout: `desktop-standard`

Composition:

- `centerPrimary` -> `HardwareScopeSurface`
- `header` -> `VfoHeader`
- `leftRail` -> semantic control groups
- `rightRail` -> semantic audio/DSP/TX groups
- `bottomDock` -> compact summaries/meters

### LCD desktop

- skin: `amber-lcd`
- theme: LCD token theme
- layout: `desktop-lcd`

Composition:

- `centerPrimary` -> `LcdReceiverDisplay`
- `centerSecondary` -> optional semantic scope surface if available
- same semantic sidebars or LCD-specific semantic groups

Important:

Both layouts still consume the same:

- `RxAudioControl` behavior contract
- `ScopeSurface` runtime data
- `TxControl` callbacks
- capability-derived view models

## Extension points that should be first-class

These are worth designing for explicitly.

### First-class

- theme tokens
- skin registry
- layout slot composition
- semantic component variants
- renderer swapping for meters/frequency/status blocks

### Deliberately not first-class

- per-skin transport ownership
- per-layout command dispatch
- per-component capability policy
- per-skin codec or audio lifecycle decisions

If an extension point can fork behavior, it belongs below the presentation layer or should be forbidden.

## Suggested directory model

One reasonable end state:

- `frontend/src/runtime/`
- `frontend/src/adapters/`
- `frontend/src/semantic/`
- `frontend/src/skins/<skin-id>/`
- `frontend/src/primitives/`
- `frontend/src/themes/`
- `frontend/src/layouts/`

Meaning:

- `runtime/` side effects and controllers
- `adapters/` pure mappers
- `semantic/` stable radio concepts
- `skins/` concrete renderers
- `primitives/` reusable low-level visuals
- `themes/` tokens
- `layouts/` screen composition

## Anti-patterns to avoid

### Anti-pattern 1

Skin components importing runtime modules directly.

That turns skins into hidden behavior forks.

### Anti-pattern 2

Theme objects containing behavior flags.

Theme is for tokens, not feature semantics.

### Anti-pattern 3

Layout deciding transport ownership based on whether a panel is mounted.

This is the current source of drift around scope/audio ownership.

### Anti-pattern 4

"Flexible" components that accept both semantic props and backend-specific escape hatches.

That destroys the semantic boundary over time.

### Anti-pattern 5

Treating LCD as a special-case app instead of a skin/layout expression over shared runtime.

## Design principles

### Principle 1

Optimize for correctness before flexibility.

The architecture should make the wrong thing hard.

### Principle 2

Different visuals should reuse the same semantics.

If two skins need different behavior contracts, the semantic component boundary is wrong.

### Principle 3

Presentation extensibility should come from composition, not from conditional logic spread across components.

### Principle 4

Model-assisted development needs hard boundaries.

If a future model can solve a UI request by importing `sendCommand(...)` into a panel, the architecture is not strict enough.

## Provisional conclusion

The ideal frontend is not "one mega theme system". It is a layered system with three independent presentation controls:

- theme changes tokens
- skin changes semantic renderers
- layout variant changes composition

All three sit on top of one shared runtime and one semantic contract. That is the only shape that gives both visual freedom and behavioral stability.
