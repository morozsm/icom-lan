# Radio UI Theme Mapping Note

## Purpose
Define the model for **theme mapping** in the Radio UI Control System.

Theme mapping answers this question:

> Given a semantic role, which visual family should render it in this theme?

**Status (as of #343):** A minimal first-pass mapping model is now implemented in
`src/lib/Button/roleMapping.ts` and validated in the control-lab demo.
This note doubles as the architecture reference for that implementation.

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

## Mapping shape (implemented)

```typescript
// src/lib/Button/roleMapping.ts
interface RoleMapping {
  name: string;
  statusToggle: VisualFamily;   // how to render status-toggle controls
  actionButton: VisualFamily;   // how to render action-button controls
}
type VisualFamily = 'fill' | 'dot' | 'hardware-plain' | 'hardware';
```

Exported from `$lib/Button`.

## Preset mappings (implemented)

| Name | status-toggle | action-button | Notes |
|---|---|---|---|
| `default` | `fill` | `fill` | Recommended post-StatusBadge default |
| `hardware` | `hardware-plain` | `hardware-plain` | Vintage incandescent / skeuomorphic |
| `minimal` | `dot` | `dot` | Low visual weight, compact |
| `mixed` | `fill` | `dot` | Different families per role — clearest semantic proof |

The **mixed** preset is most architecturally significant: it proves the role split is real by
assigning distinct visual families to `status-toggle` and `action-button` simultaneously.

## Demo proof (implemented)

`ControlButtonDemo.svelte` → "Theme Mapping Proof" section:
- preset selector row (4 buttons)
- renders `statusToggleButtons` via `activeMapping.statusToggle`
- renders `actionButtons` via `activeMapping.actionButton`
- switches live on preset selection

No production panels were changed.

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
The mapping shape is now real but a runtime theme system is not.

Until a runtime theme system is needed:
- new controls use the `default` mapping (Fill for toggle, Fill for action) unless a specific design calls otherwise
- the mapping shape in `roleMapping.ts` is the authoritative definition of "which families are valid"
- avoid per-component `if theme === ...` branches — if theme switching is needed, thread the `RoleMapping` via context

Example:
- it is fine to use `FillButton` as the current default candidate for a status-toggle migration
- it is **not** fine to encode the architecture as if Fill were the only valid future rendering

---

## What is intentionally deferred

| Item | Why deferred |
|---|---|
| Runtime theme switching in production panels | Demo proof is sufficient; no production need yet |
| Per-theme semantic wrapper components (`VintageStatusToggle` etc.) | Component proliferation without benefit |
| `hardware` preset with per-button indicator/color sub-config | Requires richer `RoleMapping` shape; wait for real hardware theme |
| Token-layer integration | Separate concern from role→family mapping |
| `selector` and `value-control` in the mapping | Not button-family controls; extend shape when needed |

## Suggested future issue areas
Theme mapping will likely need follow-up work in these areas:
1. ~~role-to-family mapping rules~~ — **done (#343)**
2. ~~demo/control-lab theme preview support~~ — **done (#343)**
3. token packs per theme
4. semantic wrapper strategy vs direct primitive usage
5. production panel context/store for active mapping
6. migration safety for switching family mappings later

---

## Summary
Theme mapping is the mechanism that keeps the Radio UI Control System flexible.

It preserves this distinction:
- **semantic role** = meaning / behavior
- **visual family** = rendering choice
- **theme** = policy for choosing and styling the family

That separation should be protected now, even before the full mapping system is implemented.
