# Radio UI Theme Mapping Note

## Purpose
Define the future direction for **theme mapping** in the Radio UI Control System.

Theme mapping answers this question:

> Given a semantic role, which visual family should render it in this theme?

This note is intentionally architectural / planning-oriented.
It does not require full implementation yet.

---

## Core idea
A semantic role should not be permanently tied to one visual family.

Examples:
- a `status-toggle` may render as Fill in one theme
- the same `status-toggle` may render as Dot or HardwarePlain in another theme
- an `action-button` may render differently again depending on density, contrast, or hardware aesthetic

So theme mapping is conceptually:

**semantic role -> visual family -> tokens/styles**

---

## Current roles relevant to theme mapping
- `status-indicator`
- `status-toggle`
- `action-button`
- `selector`
- `value-control`

## Current visual families relevant to theme mapping
- `FillButton`
- `DotButton`
- `HardwareButton`
- `HardwarePlainButton`
- future families as needed

---

## Example mapping model

Illustrative examples only:

### Theme: default-modern
- `status-toggle` -> Fill
- `action-button` -> HardwarePlain
- `status-indicator` -> StatusIndicator tokens (modern)

### Theme: minimal-lab
- `status-toggle` -> Dot
- `action-button` -> Fill
- `status-indicator` -> flat compact chips

### Theme: vintage-radio
- `status-toggle` -> HardwarePlain
- `action-button` -> HardwarePlain or Hardware
- `status-indicator` -> warmer, lower-contrast indicator tokens

The exact mapping does not need to be implemented yet.
The important point is to preserve the possibility.

---

## What should NOT happen

### 1. Hard-coding semantic roles to one family forever
Bad example:
- assuming `status-toggle === FillButton`

### 2. Solving theme differences by duplicating semantic components
Bad example:
- `VintageStatusToggle`
- `MinimalStatusToggle`
- `BlueStatusToggle`

### 3. Forcing visual mapping through ad-hoc per-component conditionals
Theme mapping should not become scattered `if theme === ...` branches across unrelated components.

---

## Recommended direction

Theme mapping should eventually live in a dedicated layer that decides, for a semantic role:
1. which visual family to use
2. which token set to apply
3. which density/size adjustments are appropriate

This layer may eventually be implemented through:
- theme config objects
- role-to-family maps
- CSS data-theme + token overrides
- lightweight wrapper components
- or a hybrid of the above

The exact implementation can wait until more families stabilize.

---

## Immediate practical rule
Until theme mapping is fully implemented:
- document the semantic role clearly
- avoid making assumptions that block remapping later
- use the current best visual candidate without claiming it is permanently canonical

Example:
- it is fine to use `FillButton` as the current default visual candidate for a status-toggle migration
- it is **not** fine to encode the architecture as if Fill were the only valid future rendering

---

## Suggested future issue areas
Theme mapping will likely need follow-up work in these areas:
1. role-to-family mapping rules
2. token packs per theme
3. demo/control-lab theme preview support
4. semantic wrapper strategy vs direct primitive usage
5. migration safety for switching family mappings later

---

## Summary
Theme mapping is the mechanism that keeps the Radio UI Control System flexible.

It preserves this distinction:
- **semantic role** = meaning / behavior
- **visual family** = rendering choice
- **theme** = policy for choosing and styling the family

That separation should be protected now, even before the full mapping system is implemented.
