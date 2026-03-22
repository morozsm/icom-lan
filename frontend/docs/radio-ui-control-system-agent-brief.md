# Radio UI Control System — Agent Brief

Short working brief for any agent implementing UI controls/styles in `frontend/`.

## Goal
Build a coherent **Radio UI Control System** for the v2 frontend.

This is **not just a button library**. It is a design system for:
- discrete controls (buttons, badges, segmented selectors)
- selection controls
- value controls (sliders / knobs / bipolar)
- panel chrome
- display controls

## Approved workflow
**DO NOT** add new control APIs directly into the library first.

Use this flow:
1. Prototype on the existing demo page (`ControlButtonDemo.svelte` or successor lab page)
2. Compare variants visually
3. Get approval
4. Extract to library
5. Integrate into real UI

Order is always:
**demo -> review -> library -> production**

## Current approved button families
These four are the current foundation:
1. **Dot** — flat button with colored dot indicator
2. **Fill** — flat button with colored fill + subtle colored glow
3. **Hardware** — skeuomorphic button with indicator accents (dot / left edge / bottom edge)
4. **Hardware Plain + Warm Glow** — skeuomorphic plain button with warm incandescent-style glow

## Important semantic rule
Separate **semantic role** from **visual family**.

Example:
- `status-toggle` is a semantic role
- Dot / Fill / Hardware Plain are visual families

Do not hard-bind a semantic role to exactly one visual component forever.
A theme or design mapping may render the same semantic role using different approved families.

## Current visual decisions
- Warm glow is preferred over white glow for the radio aesthetic
- Hardware default row should remain natural / unlit unless explicitly styled otherwise
- Dot indicator should glow in its own color, not inherit warm border glow
- Keep glow subtle; avoid overly bright borders
- Edge indicators allowed: **left** and **bottom**
- Edge-sides / right-edge styles are currently rejected

## Naming direction
Prefer system-oriented naming, not ad-hoc local names.
Use terms like:
- `DotButton`
- `FillButton`
- `HardwareButton`
- `HardwarePlainButton`
- `SegmentedControl`
- `StatusToggle`
- `PanelHeader`
- `ValueControl`

Avoid naming that bakes in one narrow use-case.

## Theming direction
All visual constants should move toward tokens.
Use CSS custom properties / tokens instead of hardcoded values.
Themes should eventually be able to change:
- glow character
- indicator sizes
- border intensity
- gradient surfaces
- contrast / density

Current direction:
- tokens first
- themes second

## Scope boundaries
Do **not** try to make every UI element "look like a button".
Use the same visual language, but preserve control semantics.

Different semantic control roles / families:
- status indicators (display-only)
- status toggles (sustained on/off state)
- action buttons (momentary commands without sustained state)
- selector controls
- continuous value controls
- structural/container controls
- display controls

## Migration strategy
Work one family at a time.
Recommended order:
1. discrete/button-like controls
2. selectors
3. value controls
4. panel chrome
5. displays/meters

## Existing demo policy
Do not delete the current demo page.
It is now the working review surface for control experiments.

## Important constraints for implementation
- Minimize premature abstraction
- Extract only after visual approval
- Keep APIs small and obvious
- Prefer shared tokens over duplicated CSS
- Preserve existing functionality and keyboard behavior
- Do not silently change approved visuals

## GitHub linkage
This work should be tied back to the UI epic(s), especially:
- **#265** epic: Web UI redesign — capability-driven radio panel
- **#318** idea: Extract control kit as standalone Svelte 5 component library

Any follow-up implementation issue should reference the relevant epic.
