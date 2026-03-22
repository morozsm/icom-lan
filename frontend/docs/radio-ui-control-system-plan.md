# Radio UI Control System — Plan

> Status note: the first production migration phase from legacy `StatusBadge` into the Radio UI Control System is now complete in `TxPanel`, `VfoPanel`, `DspPanel`, and `RitXitPanel`. The related semantic-split docs and migration issues were completed alongside that implementation. This document remains the architecture/migration reference for broader follow-up control-system work.

## Purpose
Define the target design-system direction for the v2 frontend and the migration path from current ad-hoc controls to a coherent reusable control system.

---

## 1. Summary

The frontend already has the beginnings of a reusable control layer, but it is split across:
- control-button CSS patterns
- segmented buttons
- badges/status controls
- value controls
- panel-level container styles
- display controls

The goal is to evolve this into a **Radio UI Control System**.

This is broader than a button library.

It should cover:
1. discrete action/toggle controls
2. selectors
3. continuous value controls
4. panel/container chrome
5. display controls
6. theming/tokens

---

## 2. Working process

### Approved workflow
For new controls, use:

1. prototype on demo page
2. compare variants
3. approve visual + behavior
4. extract to library
5. integrate in production UI

**Rule:**
Do not promote experimental controls into the library before approval.

### Control lifecycle
A control can move through these statuses:
- **Exploration** — demo-only
- **Candidate** — visually close, API becoming clear
- **Library** — extracted, tokenized, reusable
- **Production** — used in actual panels/layout

---

## 3. Current approved button families

### 3.1 Dot
Flat control with left-side colored dot indicator.

Use cases:
- small action toggles
- state indicators that remain button-like
- compact controls where color identity matters

### 3.2 Fill
Flat control with filled color state and subtle colored glow.

Use cases:
- stronger state emphasis
- mode-like toggles
- actions where a fully lit state reads better than a tiny indicator

### 3.3 Hardware
Skeuomorphic control with indicator accents.
Approved accents:
- left edge
- bottom edge
- colored dot

Rejected / currently not preferred:
- edge-sides
- right-edge variants

### 3.4 Hardware Plain + Warm Glow
Skeuomorphic plain control without color accents, using subtle warm glow.

Use cases:
- incandescent / radio-panel feel
- controls where state should feel illuminated rather than color-coded

---

## 4. Visual rules already agreed

- Prefer **warm glow** over cold white glow for radio feel
- Keep glow subtle; avoid flashy/neon borders
- Hardware default row should stay natural unless a glow style is explicitly requested
- Dot indicator keeps its own color glow; border glow should not leak into the dot
- Fill buttons should use the same border/glow intensity profile as warm-glow buttons, but tinted in the indicator color
- Edge accents should remain minimal and purposeful

---

## 5. Inventory of current v2 controls

### 5.1 Discrete / button-like controls
- `StatusBadge.svelte`
- `SegmentedButton.svelte`
- `AttenuatorControl.svelte`
- `ThemePicker.svelte`
- button patterns inside panel actions
- new `src/lib/Button/*`

### 5.2 Selection controls
- `BandSelector.svelte`
- `SegmentedButton.svelte`
- `AttenuatorControl.svelte`
- `ThemePicker.svelte`

### 5.3 Continuous value controls
- `ValueControl.svelte`
- `Slider.svelte`
- `BipolarSlider.svelte`
- `value-control/HBarRenderer.svelte`
- `value-control/BipolarRenderer.svelte`
- `value-control/KnobRenderer.svelte`

### 5.4 Structural / container controls
- `CollapsiblePanel.svelte`
- panel section wrappers in left/right sidebars
- `VfoHeader.svelte`
- `StatusBar.svelte`

### 5.5 Display controls
- `FrequencyDisplay.svelte`
- `FrequencyDisplayInteractive.svelte`
- meters/gauges in `components-v2/meters/*`
- VFO-related displays

---

## 6. Proposed taxonomy

### 6.1 Action / Toggle family
For direct interaction and on/off state.

Candidates:
- `DotButton`
- `FillButton`
- `HardwareButton`
- `HardwarePlainButton`
- semantic role: `status-toggle`
- semantic role: `action-button`

Important distinction:
- `StatusToggle` should be treated as a **semantic role** first
- its visual realization may vary by theme / variant mapping
- do not assume `StatusToggle` must permanently equal `FillButton`
- `ActionButton` should also be treated as a semantic role first: a momentary command without sustained on/off state
- do not rush to create a dedicated `ActionButton.svelte` primitive before enough concrete examples stabilize the API

### 6.2 Selector family
For one-of-many or grouped selection.

Candidates:
- `SegmentedControl`
- `BandSelector`
- `AttenuatorSelector`
- `ThemeSelector`

### 6.3 Value family
For continuous or stepped numeric control.

Candidates:
- `LinearValueControl`
- `BipolarValueControl`
- `KnobControl`

### 6.4 Container / chrome family
For grouping and hierarchy.

Candidates:
- `Panel`
- `CollapsiblePanel`
- `PanelHeader`
- `SidebarSection`

### 6.5 Display family
For readouts and instrument-like visualization.

Candidates:
- `FrequencyDisplay`
- `NumericReadout`
- `StatusReadout`
- `Meter`
- `Gauge`

---

## 7. Naming guidelines

Use names based on role, not implementation accident.

Prefer:
- `SegmentedControl` over narrow one-off names
- `StatusToggle` over badge-specific naming if it becomes interactive by default
- `PanelHeader` over local panel-specific class names
- `KnobControl` rather than renderer terminology when promoted to public API

Keep renderers/internal pieces internal where possible.

---

## 8. Token strategy

### 8.1 Tokens should own
- dimensions
- radius
- spacing
- glow intensity
- border strength
- indicator size
- gradients
- semantic colors
- hardware surface treatment

### 8.2 Themes should be able to alter
- warm vs cooler illumination
- indicator scale
- surface contrast
- density / compactness
- chrome strength
- brightness balance for day/night variants

### 8.3 Avoid
- scattering magic numbers back into component-local CSS
- per-component theme hacks
- creating component APIs to compensate for missing tokens

---

## 9. Recommended migration phases

### Phase 1 — discrete controls
Target:
- `StatusBadge`
- `SegmentedButton`
- `AttenuatorControl`
- `ThemePicker`
- possibly `BandSelector`

Goal:
establish stable control primitives and selector patterns.

### Phase 2 — selector controls
Target:
- `BandSelector`
- richer grouped selectors
- panel-level choice controls

Goal:
standardize grouped selection behavior and layout.

### Phase 3 — value controls
Target:
- `ValueControl`
- `Slider`
- `BipolarSlider`
- knob renderer system

Goal:
align visual language without destroying the semantics of continuous controls.

### Phase 4 — panel chrome
Target:
- `CollapsiblePanel`
- panel headers
- sidebar sections
- status bar chrome

Goal:
make containers belong to the same system.

### Phase 5 — displays / meters
Target:
- frequency display family
- gauges
- meters

Goal:
establish a consistent instrument/display language.

---

## 10. What should be tested on the demo page

For each candidate control, demo should show:
- idle / hover / active / disabled if relevant
- compact vs standard if relevant
- multiple colors if color is part of the API
- real radio labels, not generic lorem labels only
- side-by-side comparisons if exploring variants

The demo page should act as a **control lab**, not just a showcase.

---

## 11. Suggested GitHub issue structure

### Existing anchor issues
- **#265** — epic: Web UI redesign — capability-driven radio panel
- **#318** — idea: Extract control kit as standalone Svelte 5 component library
- **#316** — button indicator styles work already related to the new language
- **#326** — skinnable ValueControl (important later for value family)

### Recommended new issues
1. **feat(v2): Formalize Radio UI Control System docs + workflow**
2. **feat(v2): Migrate StatusBadge into approved control system**
3. **feat(v2): Refactor SegmentedButton into selector-family primitive**
4. **feat(v2): Unify AttenuatorControl and BandSelector under selector patterns**
5. **feat(v2): Build themed panel header / collapsible chrome system**
6. **feat(v2): Align ValueControl family with control-system tokens**

All should reference #265.
Library-specific work should also reference #318.
ValueControl theming/styling should reference #326.

---

## 12. Immediate next recommended task

Best next candidate after buttons:

### Option A — `StatusBadge`
Why:
- already visually close to button language
- widely used in action/toggle contexts
- relatively constrained migration

### Option B — `SegmentedButton`
Why:
- central selector primitive
- reused across many panels
- strong leverage for system consistency

**Recommendation:** do `StatusBadge` first, then `SegmentedButton`.

---

## 13. Definition of done for a control promoted into library

A control is ready for library promotion when:
- visual variant has been approved on demo page
- API is small and understandable
- hardcoded styling is replaced with tokens where appropriate
- naming matches the design-system taxonomy
- keyboard/accessibility behavior is preserved
- at least basic test coverage exists if the project already tests that family

---

## 14. Final principle

This project should evolve toward a **Radio UI Control System**, not a pile of one-off styled widgets.

The system should feel:
- instrument-like
- coherent
- themeable
- reusable
- conservative in API design
- experimentally validated before promotion
