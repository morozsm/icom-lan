# Receiver Activation UX — Removing the SUB `ACTIVATE` Chip

**Status:** proposal
**Owner:** UX
**Date:** 2026-04-18
**Scope:** desktop-v2 skin primarily; coordination notes for amber-lcd and mobile
**Related:** #811 (mobile MAIN/SUB tabs), #815 (spectrum informational offload)

---

## 1. Context

### 1.1 What "active receiver" means on IC-7610

The IC-7610 is a true dual-receiver radio. Both MAIN and SUB have independent frequency, mode, filter, AGC, AF/RF gain, NR/NB, preamp/attenuator, and S-meter. At any instant exactly one is the **selected / active** receiver; that one is:

- the target of tuning and control-panel edits (AF, RF, RIT, filter, NR/NB…),
- the source of demodulated audio to headphones/speaker (unless Dual-Watch mixing is engaged),
- the receiver displayed as the CI-V "current VFO" (commands 0x07 0xD0 MAIN / 0xD1 SUB in `src/icom_lan/commands/vfo.py`),
- the `state.active` value on the backend runtime (`_dual_rx_runtime.py::_active_receiver_name`).

On the physical radio, the dedicated **M/S button** toggles the active receiver. That's the user's mental model. Our UI must respect it: active-receiver switching is a first-class, single-tap operation, not a buried chip.

Terminology note in `command-bus.ts::makeVfoHandlers`: `onTxVfoChange` is different — it governs which VFO *transmits* in SPLIT, independent of which receives. The two must remain visually distinct.

### 1.2 Current UX (desktop-v2)

`frontend/src/components-v2/layout/VfoHeader.svelte` lays out three columns:

```
[ MAIN VfoPanel ] [ Bridge: VfoOps + SPLIT status + SPEAK ] [ SUB VfoPanel ]
```

Inside each `VfoPanel.svelte`:

- Row 1 header: `VFO MAIN/SUB` label + `ACTIVE | STANDBY` state badge + `BAR` + slot tag.
- Row 2: linear S-meter.
- Row 3: frequency display (color-coded by `receiver`) + RIT offset.
- Row 4: mode / band / filter / status badges strip.

The entire `.panel` element already has `onclick={onVfoClick}` wired to `set_vfo {MAIN|SUB}` in `command-bus.ts` (lines 78–79). So **click-to-activate already works end-to-end**. The "ACTIVATE" interaction the user wants removed is the `STANDBY → ACTIVE` chip in the header — not an extra button the panel itself lacks, but the misleading affordance of what looks like a click-target label.

### 1.3 Problems

1. **Affordance ambiguity.** `STANDBY` looks like a clickable pill (same chrome as header tags). Users click it expecting activation — they *get* it, but only because the whole panel is clickable. The pill duplicates the affordance and misleads about scope.
2. **Asymmetry.** The chip is visually noisy on SUB (where users most often want to activate) and redundant on MAIN (already active by default). Reading ACTIVE on MAIN and STANDBY on SUB adds zero information beyond the color-coded frequency.
3. **No centered M/S control.** The on-radio mental model — one M/S button in the middle — isn't mirrored. Every activation path is "reach to the far side of the header," which is far on a 27" monitor and impossible on keyboard.
4. **`BAR` header tag is meaningless** (separate issue — noted but out of scope).
5. **No keyboard shortcut** for active-receiver toggling, even though `switch_active_vfo` dispatch exists in `makeKeyboardHandlers` (command-bus.ts:872–877) — it's wired but not bound in `DEFAULT_KEYBOARD_CONFIG`.

---

## 2. Activation Model — recommendation: **B (single M/S control)** — downscoped from D per user

**User feedback (2026-04-18):** "Одна кнопка M/S достаточна, как в железном радио.
Важно чтобы по типографике и всплывающим подсказкам было ясно, что она делает.
Равно, как и все другие кнопки, на самом деле..."

Model downscoped from D (hybrid) to **B (segmented control only)**.
Frequency-click activation is dropped. Rationale:
- Mirrors the physical radio exactly — IC-7610 has one M/S toggle, not two
  ways to switch receivers.
- Fewer affordances = less confusion about "which action activates". Users
  who learn the segmented control don't have to also remember the
  click-on-digits shortcut.
- Eliminates the only remaining overloaded-click concern on the frequency
  display (scroll vs click vs drag semantics stay clean).

**Cross-cutting scope expansion (from same user feedback):** typography +
tooltip discoverability must be applied to **all buttons** in the VFO
area (and by extension, the rest of the desktop layout), not just M/S.
See §9 Issue E below. This is a separate concern from activation but
surfaced in the same discussion.

The original 4-model comparison is preserved below for historical
context; the Hybrid (D) analysis is no longer the recommendation.

### 2.0 Model comparison (historical)

We evaluated four models:

| Model | Description | Pros | Cons |
|-------|-------------|------|------|
| A | Click anywhere on VFO block activates | Maximal target, cheap | High accidental-activation risk: mode chip, S-meter, freq-scroll all live inside the block; clicks during tuning bleed into activation |
| B | Dedicated `M↔S` toggle / `ACTIVE: M\|S` segmented control in center column | Mirrors radio's M/S button; single, unambiguous target | Two taps for new users (find center, click); requires a new control |
| C | Activation as side-effect of tuning / changing mode | Zero-UI; "just work" | Violates expectation — users scrub SUB to look, not to steal focus; silent focus theft is hostile for screen-reader users |
| D | **Hybrid**: explicit M↔S segmented control in center column is the primary path; clicking the **frequency display** of a VFO also activates it; other regions of the block are inert for activation | Mirrors physical radio; keeps fast path; avoids accidental clicks; one SR-announceable control | Slightly more layout work; need to unwire `onVfoClick` from the whole panel |

### 2.1 Why D

- **Mirrors the physical radio.** The center column becomes the M/S-button analog. Users who know the 7610 will find it instantly.
- **Keyboard-first.** Single control → single shortcut (`m`), aria-pressed state on a `role="radiogroup"`.
- **Screen-reader friendly.** One control announces "Active receiver — Main, selected" / "Sub, not selected." Currently, clicking an entire panel with no explicit label leaves SR users with "button, VFO MAIN panel" and no idea activation is the outcome.
- **Accidental activation goes away.** The current "click the whole panel" model silently activates when users meant to click the mode chip or scrub the frequency. Frequency-click stays (users who click the digits expect focus), but the meter, badges, header, and dead space no longer trigger activation.
- **Progressive disclosure.** Hovering the active-indicator ring on a panel hints "this side receives"; the center control is the action; the frequency is the express shortcut.

### 2.2 Rejected refinements

- **A pure-B (center only, no freq shortcut).** Rejected because freq-click activation is already a learned gesture; removing it is a regression for existing users.
- **A pure-C (implicit).** Rejected on accessibility grounds — any UI that changes global focus as a side-effect of unrelated actions is a11y-hostile.

---

## 3. Visual Indication of Active State

Current cues:
- Frequency numerals colored by receiver (cyan=MAIN, green=SUB) regardless of active.
- `.panel.active` applies `border-color: var(--receiver-control-border)` + `box-shadow: inset 0 0 0 1px var(--receiver-control-glow)` (VfoPanel.svelte:141–144).
- The `ACTIVE / STANDBY` pill in the header.

### 3.1 Proposal

Remove the header pill. Compensate with three subtle, layered cues:

1. **Active-side glow** (keep + strengthen). Widen the `box-shadow` on `.panel.active` from `inset 1px` to `inset 2px` plus a soft outer halo (`0 0 12px -4px var(--receiver-control-glow)`) so the active panel reads as "lit" at a glance across the room.
2. **Inactive dimming.** Apply `filter: saturate(0.6) brightness(0.85)` to the non-active panel's S-meter and badge strip. The frequency stays at full saturation (it's the primary data), but supporting chrome recedes.
3. **Active-receiver pill in the center column.** A compact segmented control `[ M ][ S ]` (height 18px matching other bridge buttons) with `aria-pressed` and `data-active`. This both signals state and offers the action. Replaces the 2× `ACTIVE/STANDBY` pills with a single shared indicator positioned on the axis of symmetry.

Net: less chrome per panel, one consolidated indicator, stronger "which side is live" read.

### 3.2 Accessibility

- The center control gets `role="radiogroup"`, `aria-label="Active receiver"`; children `role="radio"` with `aria-checked` and `aria-label="Main receiver"` / `"Sub receiver"`.
- Panels no longer expose `role="button"` (since the whole-panel click is removed). The frequency display keeps its existing interactive semantics.
- `aria-live="polite"` region announces "Active receiver: Sub" on change (reuses existing leader-pill infrastructure in `KeyboardHandler.svelte`).

---

## 4. Center Column Contents

Current (dual-rx, `VfoOps.svelte` grid):

```
Row 1:  COPY  | SPLIT
Row 2:  DW    | =
Row 3:  TX-M  | TX-S
Row 4:  SWAP (span 2)
```

Plus below: SPLIT status line, SPEAK button.

### 4.1 Proposed

Add **ACTIVE M↔S segmented control at the top** of the ops grid — it's the most-used dual-rx control on the real radio, so it deserves primacy:

```
Row 1:  [  M  |  S  ]  (span 2, segmented, aria-radiogroup)
Row 2:  COPY  | SPLIT
Row 3:  DW    | =
Row 4:  TX-M  | TX-S
Row 5:  SWAP (span 2)
```

The segmented control is visually distinct (no border, inset, larger font 11px vs 10px) so it reads as a *state indicator* rather than a transient action.

### 4.2 Does activation belong here?

Yes — the whole point of the center column is inter-VFO operations. `M↔S swap`, `A=B copy`, `SPLIT`, `DW`, `TX→M/S`, and now `ACTIVE M/S` are all "between-VFO" actions. Putting activation anywhere else contradicts the user's stated intent ("оставить все управление переключением приемников МЕЖДУ VFO панелями").

### 4.3 What else could go here?

- **Tracking toggle** (MAIN/SUB tracking, CAP_MAIN_SUB_TRACKING) — currently has no UI; natural home is next to DW. *Deferred to a separate issue — not in this scope.*
- **Spectrum-span/center-freq informational readout** (#815) — *not* here. That belongs next to the spectrum. Coordinate: keep the center column for control, push informational offload to the spectrum frame.

Room check: current column is 132px wide and already stacks 7 buttons. Adding a segmented pair on top keeps the column compact because we drop the two per-panel `ACTIVE/STANDBY` pills.

---

## 5. Behavior Map

| User action | Runtime state change | Visual change | Notes |
|---|---|---|---|
| Click `[ M ]` in center segmented control | `patchRadioState({ active: 'MAIN' })` + `sendCommand('set_vfo', {vfo: 'MAIN'})` | MAIN panel glows, SUB desaturates; segmented control flips `aria-pressed` | New handler `onActivateChange('MAIN')` in `command-bus.ts::makeVfoHandlers` |
| Click `[ S ]` in center segmented control | `patchRadioState({ active: 'SUB' })` + `sendCommand('set_vfo', {vfo: 'SUB'})` | mirror of above | Same handler, `'SUB'` arg |
| Click frequency digits on inactive panel | Existing `onFreqChange` path — but we also pre-activate if the panel isn't active | Panel becomes active *then* tuning proceeds | Freq-click already implicitly tunes `activeReceiverParam()`; we make activation explicit to prevent "I scrolled SUB but MAIN changed" bugs |
| Click anywhere else on inactive panel (meter, badges, header) | **nothing** (change from today) | no-op | Explicit: remove `onclick={onVfoClick}` from `.panel` root; retain only on FrequencyDisplayInteractive |
| Click mode chip on inactive panel | activate that panel, then open mode popover | Active flip + mode panel highlight | `focusModePanel(vfo)` already does this; keep |
| Tune with ArrowLeft/Right on inactive panel's freq when focused | tune *that* panel (implicitly activates via freq-click path) | Active flip + tuning | Implicit activation only when the *frequency* is the interaction target |
| Press `m` (new shortcut) | toggle `active` between MAIN/SUB | segmented control flips; panel glow swaps | Existing `switch_active_vfo` action in handler; add binding |
| Press `Shift+M` | Force MAIN active | — | Optional; see §6 |
| Press `Shift+S` | Force SUB active | — | Optional; see §6 |
| `state.active` changes via backend poll (e.g. CAT from front panel) | store update | glow/segmented control follow | Already works — the segmented control is a pure `$derived` view of `state.active` |

---

## 6. Keyboard Shortcuts

Current `DEFAULT_KEYBOARD_CONFIG` has no active-receiver binding, though `switch_active_vfo` dispatch exists (`command-bus.ts::makeKeyboardHandlers:872`).

### 6.1 Add

| Key | Action id | Params | Section | Label |
|---|---|---|---|---|
| `m` | `switch_active_vfo` | — | VFO | Toggle active receiver (MAIN/SUB) |
| `Shift+M` | `set_active_vfo` | `{vfo: 'MAIN'}` | VFO | Activate MAIN |
| `Shift+S` | `set_active_vfo` | `{vfo: 'SUB'}` | VFO | Activate SUB |

`set_active_vfo` is a new action case in `makeKeyboardHandlers.dispatch` that reads `action.params.vfo` and calls `patchRadioState + cmd('set_vfo', {vfo})`.

### 6.2 Rationale

- `m` matches the radio's physical M/S button (single key, muscle-memory).
- Shift variants are explicit (useful for macro pads and screen-readers) and complement Shift-aware bindings already in use.
- Leader sequences are unnecessary — activation is too frequent for a two-keystroke gesture.

### 6.3 Collisions

`m` is currently unbound. `Shift+M` unbound. `Shift+S` unbound. Safe.

---

## 7. Skin Variants

### 7.1 amber-lcd

`LcdLayout.svelte` uses the same VfoHeader composition (verified via grep of `KeyboardHandler` / import trees). The change works verbatim — amber palette keeps the active-glow cue, and the segmented control inherits LCD chrome. One note: amber has no cyan/green distinction, so the glow (`box-shadow`) becomes the *primary* cue. Strengthen it on that skin (amber active border at full opacity, inactive at 40%).

### 7.2 mobile (#811)

Mobile uses MAIN/SUB **tabs**, not side-by-side panels. The segmented control concept is already native to mobile (tabs *are* segmented controls). Coordination with #811:

- The MAIN/SUB tab is the active-receiver selector. No separate control needed.
- Activation = tapping the tab. Matches this proposal's center-segmented semantics at a different scale.
- The freq-click-to-activate shortcut doesn't apply (the inactive panel isn't visible).
- Keyboard shortcuts (`m`, Shift-M, Shift-S) should be honored on tablet/BT-keyboard configs; they flip the tab selection.

Recommendation: #811 should consume the same underlying store state (`state.active`) and emit the same `set_vfo` command as the desktop segmented control. The tabs should read `aria-pressed` from `state.active`.

### 7.3 Cross-skin contract

Define in `state-adapter.ts` a new adapter `toActiveReceiverProps(state)` returning `{ active: 'MAIN' | 'SUB' }`. Skins consume this; their presentation differs (segmented control / tabs / LCD chunk) but state semantics are identical.

---

## 8. Wireframes

### 8.1 Before (current desktop-v2, dual-rx)

```
┌──────────────────────────┬─────────────┬──────────────────────────┐
│ VFO MAIN [ACTIVE] BAR A  │    COPY     │ VFO SUB [STANDBY] BAR B  │
│  ═══ S-METER (main) ═══  │   SPLIT     │  ═══ S-METER (sub)  ═══  │
│  14.074.000  [RIT]       │    DW       │  14.200.000              │
│  USB  A  20M  FIL1  NR   │    =        │  USB  B  20M  FIL1       │
│                          │   TX-M      │                          │
│                          │   TX-S      │                          │
│                          │   SWAP      │                          │
│                          │  ─────      │                          │
│                          │  SPLIT      │                          │
│                          │  RX … TX …  │                          │
│                          │   SPEAK     │                          │
└──────────────────────────┴─────────────┴──────────────────────────┘
   (whole panel clickable — ambiguous)
```

### 8.2 After

```
┌──────────────────────────┬─────────────┬──────────────────────────┐
│ VFO MAIN        [A]      │ [  M │ S  ] │ VFO SUB          [B]     │  ← no ACTIVE/STANDBY pill,
│  ═══ S-METER (main) ═══  │    COPY     │  ··· S-METER (sub, dim)  │    BAR removed (issue out of scope)
│  14.074.000  [RIT]       │   SPLIT     │  14.200.000              │    active = glow on MAIN
│  USB  A  20M  FIL1  NR   │    DW       │  USB  B  20M  FIL1 (dim) │    segmented shows M selected
│                          │    =        │                          │
│                          │   TX-M      │                          │
│                          │   TX-S      │                          │
│                          │   SWAP      │                          │
│                          │   ─────     │                          │
│                          │   SPLIT     │                          │
│                          │   RX … TX … │                          │
│                          │   SPEAK     │                          │
└──────────────────────────┴─────────────┴──────────────────────────┘
   (only freq + mode chip + segmented control activate; rest inert)
```

Active-side glow is rendered as a 2px inset border + soft outer halo in the receiver accent color.

---

## 9. Atomic Implementation Issues

Each is ≤3 files, ≤200 LOC, independently shippable.

### Issue A — Remove panel-wide click-to-activate + STANDBY/ACTIVE pill

**Scope change (from user):** frequency-click activation is dropped.
Issue A is now purely removal — all activation flows through the new M/S
segmented control added by Issue B.

**Files:**
- `frontend/src/components-v2/vfo/VfoPanel.svelte` — drop
  `onclick={onVfoClick}` + `role="button"` from `.panel`; remove the
  `ACTIVE / STANDBY` pill span; keep `isActive` styling.

**LOC:** ~25. (Down from ~60.)

### Issue B — Add `ActiveReceiverToggle` segmented control in VfoOps bridge

**Files:**
- New `frontend/src/components-v2/vfo/ActiveReceiverToggle.svelte` — segmented radiogroup with `role="radiogroup"`, keyboard-friendly.
- `frontend/src/components-v2/vfo/VfoOps.svelte` — add toggle at top of grid, expose `activeVfo` + `onActiveVfoChange` props.
- `frontend/src/components-v2/layout/VfoHeader.svelte` — thread `activeVfo` / `onActiveVfoChange` props from parent; add `toActiveReceiverProps` adapter in `state-adapter.ts`.

**LOC:** ~140.

### Issue C — Strengthen active/inactive visual treatment

**Files:**
- `frontend/src/components-v2/vfo/VfoPanel.svelte` — widen `.panel.active` glow; add `.panel:not(.active)` desaturation to `.panel-meter` and `.control-strip`.
- `frontend/src/styles/*` (tokens) — new `--v2-vfo-panel-glow-outer` token per receiver.

**LOC:** ~50.

### Issue D — Keyboard bindings `m`, `Shift+M`, `Shift+S`

**Files:**
- `frontend/src/components-v2/layout/keyboard-map.ts` — add three bindings to `DEFAULT_KEYBOARD_CONFIG`.
- `frontend/src/components-v2/wiring/command-bus.ts` — add `set_active_vfo` case to `makeKeyboardHandlers.dispatch`.
- `frontend/src/components-v2/layout/__tests__/keyboard-map.test.ts` — bindings + precedence.

**LOC:** ~80.

### Issue E — Button discoverability audit (typography + tooltips)

**Added per user feedback 2026-04-18.** Cross-cutting issue extending the
activation-model discussion: every button in the VFO area and adjacent
controls must be self-explanatory via typography + `title` tooltip.

**Scope:**
- Audit every button inside `VfoHeader.svelte` / `VfoOps.svelte` /
  `VfoPanel.svelte` / center-column (M↔S, SPLIT, DW, TX→M, SPEAK,
  A↔B, A=B, ACTIVE-M/S when added).
- For each: verify label is real English (not abbreviation without
  context), verify `title=` tooltip exists and accurately describes the
  action + current state.
- Standardize tooltip format: `"<action verb> <object> (<current
  state/shortcut>)"` — e.g. `"Swap MAIN and SUB frequencies"`,
  `"Split transmit (off — press to enable)"`.
- Apply same pattern to StatusBar controls (STD, theme, DISCONNECT,
  power toggle, settings gear after #807).
- No behavior change.

**Files:**
- `frontend/src/components-v2/vfo/VfoOps.svelte`
- `frontend/src/components-v2/vfo/VfoPanel.svelte`
- `frontend/src/components-v2/layout/VfoHeader.svelte`

(StatusBar tooltip pass is a separate issue if this one blows past 3
files / 200 LOC.)

**LOC:** ~120.

**Suggested order:** B → A → C → D (B establishes the primary affordance so A can safely remove the old one; C polishes; D layers on).

---

## 10. Open Questions

1. **SPLIT semantics.** When SPLIT is on, IC-7610 semantics tie TX to the inactive VFO. If a user activates SUB while SPLIT is on, does TX follow (SPLIT TX becomes MAIN) or stay pinned? `onTxVfoChange` in command-bus.ts does re-target based on `splitActive`. Confirm desired behavior — proposal: activation should **not** change TX assignment (decoupled controls).
2. **Dual-Watch (DW).** In DW mode, both receivers emit audio mixed. Does "active" still mean anything audibly? It still means "target of tuning and control edits" — visual treatment stays the same, but audio-routing cue (which side is louder / panned) is a separate concern for #815-adjacent work.
3. **Animation.** Should the glow transition have a 150ms ease when `state.active` changes, or snap? Proposal: ease (matches existing 150ms border transition).
4. **LCD skin active color.** Amber-only palette — should inactive freq numerals also desaturate, or stay readable? Proposal: stay full-amber on freq (data-first), dim only chrome.
5. **Mobile keyboard shortcuts.** Should `m` be honored on mobile when a BT keyboard is paired? Coordinate with #811.
6. **"Activation follows tuning" opt-in.** Some contesters might want C-style implicit activation as a pref. Not in v1 — revisit if requested.

---

## Appendix — References

- `frontend/src/components-v2/layout/VfoHeader.svelte`
- `frontend/src/components-v2/vfo/VfoPanel.svelte`
- `frontend/src/components-v2/vfo/VfoOps.svelte`
- `frontend/src/components-v2/wiring/command-bus.ts` (`makeVfoHandlers`, `makeKeyboardHandlers`, `focusModePanel`)
- `frontend/src/components-v2/wiring/state-adapter.ts` (`toVfoProps`)
- `frontend/src/components-v2/layout/KeyboardHandler.svelte`
- `frontend/src/components-v2/layout/keyboard-map.ts` (`DEFAULT_KEYBOARD_CONFIG`)
- `src/icom_lan/commands/vfo.py` (`set_vfo`, codes MAIN=0xD0/SUB=0xD1)
- `src/icom_lan/_dual_rx_runtime.py` (`_active_receiver_name`)
- Related: `docs/plans/2026-04-12-target-frontend-architecture.md`, #811, #815
