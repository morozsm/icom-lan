# Radio UI Semantic Roles and API Note

## Purpose
Capture the naming and API conventions for **semantic roles** in the Radio UI Control System.

This note exists to prevent a common failure mode:
confusing a control's **meaning** with its **visual family**.

---

## Core principle
Separate:

- **semantic role** — what the control means / how it behaves
- **visual family** — how the control is rendered in a given theme or design language

Example:
- `status-toggle` = semantic role
- `FillButton` / `DotButton` / `HardwarePlainButton` = visual families

A semantic role must not be permanently hard-bound to one visual family unless there is a strong reason.

---

## Approved semantic roles (current)

### 1. `status-indicator`
Read-only display status.

Characteristics:
- non-interactive
- no click handler
- no sustained user-controlled state transitions
- display-only

Examples:
- TX ACTIVE / TX IDLE
- compact VFO mode/filter/status chips

Recommended primitive:
- `StatusIndicator`

---

### 2. `status-toggle`
Interactive control with sustained on/off state.

Characteristics:
- clickable / keyboard-interactive
- user toggles a persistent state
- active/inactive state matters semantically

Examples:
- VOX
- MON
- COMP
- RIT
- XIT
- NB
- ATU

Important:
- `status-toggle` is a semantic role, not a fixed component name
- current visual candidates may include Fill / Dot / HardwarePlain depending on theme

---

### 3. `action-button`
Momentary command-style control.

Characteristics:
- clickable / keyboard-interactive
- performs an action, command, or reset
- does **not** represent a sustained on/off state
- may have transient pressed/busy feedback, but not persistent active semantics by default

Examples:
- CLEAR
- TUNE
- CW Auto Tune (current `DspPanel` wiring is command-style, not sustained state)
- RESET
- CENTER

Important:
- do not classify these as status indicators
- do not classify these as sustained toggles unless the behavior truly warrants it

---

### 4. `selector`
Choice among options.

Characteristics:
- one-of-many or grouped selection
- may be segmented, menu-based, grid-based, etc.

Examples:
- SegmentedButton / future SegmentedControl
- BandSelector
- AttenuatorControl
- ThemePicker

---

### 5. `value-control`
Continuous or stepped numeric control.

Characteristics:
- adjusts a value across a range
- often drag/wheel/step-based
- not button semantics

Examples:
- Slider
- BipolarSlider
- Knob-based controls
- ValueControl renderers

---

## Naming guidance

### Use role names for semantics
Prefer terms like:
- `StatusIndicator`
- `StatusToggle` (only if/when a semantic wrapper is genuinely useful)
- `ActionButton` (same caveat)
- `SegmentedControl`
- `ValueControl`

### Use family names for rendering primitives
Prefer terms like:
- `DotButton`
- `FillButton`
- `HardwareButton`
- `HardwarePlainButton`

### Avoid
- using visual-family names as if they define the semantic role
- naming a semantic concept after the first visual candidate that happened to work
- keeping legacy ambiguous names once a split is understood

---

## API guidance

### Semantic wrappers should be introduced only when they add value
Do **not** create a semantic wrapper component just because the name sounds nice.

Create a semantic wrapper only when at least one of these is true:
1. it encapsulates behavior beyond a bare visual family
2. it stabilizes a repeated semantic usage pattern
3. it protects the app from theme-mapping churn
4. it improves code readability materially

### Otherwise
Keep the semantic role documented, and use existing visual primitives until the API naturally stabilizes.

This means:
- `StatusIndicator` is already justified as a dedicated primitive
- `StatusToggle` may still remain a documented role before becoming a dedicated component
- `ActionButton` may remain a documented role before becoming a dedicated component

---

## Recommended relationship between roles and families

Think in two layers:

### Layer 1 — semantic role
What is this control doing?
- status-indicator
- status-toggle
- action-button
- selector
- value-control

### Layer 2 — visual family
How should that role be rendered in this theme?
- fill
- dot
- hardware
- hardware-plain
- future families

---

## Practical rule for agents
When implementing or migrating controls:
1. classify the semantic role first
2. choose or prototype a visual family second
3. only then decide whether a dedicated library primitive is warranted

Never reverse this order.
