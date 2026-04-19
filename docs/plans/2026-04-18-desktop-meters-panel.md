# Desktop Bottom-Dock Redesign — Unified Meters Dashboard

**Date:** 2026-04-18
**Status:** Design proposal (no code changes)
**Author:** UX/UI design pass
**Scope:** `desktop-v2` skin only (amber-lcd and mobile skins untouched)

---

## 1. Context

The desktop bottom dock (`frontend/src/components-v2/layout/RadioLayout.svelte`
lines 254–298) currently renders three cards: an RX1 summary
(`receiver-summary-card-main`), an RX2 summary or an audio FFT scope
(`audio-scope-dock-card` → `AudioSpectrumPanel`), and a `DockMeterPanel`
showing S/SWR/Po with a radio-button toggle. The VFO header already shows
frequency, mode, filter, and a full-width S-meter for both receivers in
~156 px at the top of the layout, so the two summary cards are pure
duplication and the meter panel is undersized and incomplete (no ALC, no
Id/Vd, no TEMP, no peak-hold, no capability gating). The IC-7610 exposes
S, Po, SWR, ALC, COMP, Vd, Id via 0x15-family commands
(`src/icom_lan/commands/meters.py`), all already surfaced in runtime state
(`frontend/src/lib/types/state.ts` lines 103–108: `compMeter`, `vdMeter`,
`idMeter`, `powerMeter`, `swrMeter`, `alcMeter`). The dock must become a
proper TX-telemetry and station-health dashboard — TX metering is
life-safety adjacent (SWR spikes, ALC overdrive, final-PA protection) and
must be legible at desk distance without squinting.

**Correction to the brief (from user).** The widget in the current dock
(`AudioSpectrumPanel`) is a **combined instrument**, not just an AF FFT.
It renders, overlaid on a single canvas:
1. AF FFT spectrum (receive audio frequency content).
2. RX filter passband shape (bandwidth + shoulders).
3. PBT (passband tuning) shift indicator.
4. For radios that support them (e.g. FTX-1): notch and contour filter
   indicators.

This composite widget is a deliberate design, and it must be preserved
as-is. No decomposition into separate panels. The decision below is
about **where the combined widget lives**, not what it shows.

---

## 2. Meter Inventory

Source field names are from `RadioState` in
`frontend/src/lib/types/state.ts`. Availability rows reflect IC-7610
(primary target) and a generic "other radio" column that describes the
capability-gated fallback behavior.

| Meter | Unit | Source | State field | IC-7610 | Other radios | Idle (RX) | Active (TX) |
|-------|------|--------|-------------|---------|--------------|-----------|-------------|
| **S** | S-units + dB over S9 | RX | `sValue` (main), `subSValue` | yes | yes (universal) | live, primary | dimmed (not relevant) |
| **Po** | W (0–100 %) | TX | `powerMeter` | yes | usually yes | zero / dim | live, primary |
| **SWR** | ratio (1.0–∞) | TX | `swrMeter` | yes | usually yes | zero / dim | live, **alarm when > 2.0** |
| **ALC** | % of limit | TX | `alcMeter` | yes | usually yes | zero / dim | live, **warn when in red zone** |
| **COMP** | dB compression | TX (SSB) | `compMeter` | yes (SSB only) | varies | zero / dim | live **only when compressor on** (`compressorOn`) |
| **Id** | A drain current | TX | `idMeter` | yes | mid/high-end only | zero / dim | live, informational |
| **Vd** | V drain voltage | TX | `vdMeter` | yes | mid/high-end only | **always live** (shows ≈13.8 V on RX too) | live |
| **TEMP** | relative 0–100 | shared | *(not in state yet — see open question Q4)* | available over 0x15 on many rigs, **not exposed by IC-7610 CI-V** | varies | — | — |

**Normalization.** Raw values 0–255 are already normalized via
`meter-utils.ts` (`normalize`, `formatSMeter`, `formatSwr`,
`formatPowerWatts`, `formatAlc`). COMP/Id/Vd need formatters added
(`formatCompDb`, `formatAmps`, `formatVolts`) — belongs in that same file.

**Capability gating.** A meter tile is shown only when its state field
is defined (`!== undefined`) AND, for COMP, when `compressorOn === true`.
Radios that don't report Id/Vd simply hide those tiles; the grid
re-flows. No "N/A" placeholders — absent meters disappear.

---

## 3. Layout Proposal

### Strategy

Replace the three-card dock with **one full-width `MetersDockPanel`**
that always shows all capability-available meters simultaneously as a
horizontal grid of tiles. No more source-selector toggle — this is a
dashboard, not a single-reading panel. The audio FFT scope moves (see
§4).

### Dimensions

- Dock height: **144 px** total (up from 112 px).
  - +32 px buys us two-line tiles: big value on top, proper label + bar
    below. Current 112 px is cramped even for the truncated S/Po/SWR
    triad.
  - This is ≈9 % of a 1440 × 900 laptop screen — still modest relative
    to the spectrum plot which owns the middle.
- Horizontal padding: 12 px (matches `.bottom-dock` existing
  `gap: 12px`).
- Tile grid: `display: grid; grid-template-columns: repeat(auto-fit,
  minmax(132px, 1fr)); gap: 8px;` — tiles self-size down to 132 px min,
  typically 6 tiles fit at 1440 px width at ≈220 px each.
- Tile internal padding: 10 px top/bottom, 12 px left/right.

### Priority / ordering

Tiles render in fixed priority order so muscle memory survives
capability changes. Left → right:

1. **Po** (TX primary)
2. **SWR** (TX safety)
3. **ALC** (TX correctness)
4. **COMP** (SSB only, compressor on)
5. **Id** (PA health)
6. **Vd** (PSU health)
7. **S** (optional duplicate — see §8)
8. **TEMP** (if ever exposed)

### Dual-RX vs single-RX

The meters are station-level, not per-receiver — SWR/Po/ALC/Id/Vd apply
to the single PA regardless of dual watch. So the dock is identical for
single- and dual-RX radios. (The top VFO header already handles
dual-RX.) No second row of tiles for RX2.

### ASCII wireframe — IC-7610, TX active

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  STATION METERS                                                       TX ●             │  ← 20px title row
├────────────┬────────────┬────────────┬────────────┬────────────┬────────────┬──────────┤
│   Po       │   SWR      │   ALC      │   COMP     │   Id       │   Vd       │   S      │
│  78 W      │  1.3       │  42 %      │  6 dB      │  15.2 A    │  13.8 V    │  —       │
│  ▓▓▓▓▓▓▓░░ │  ▓▓▓░░░░░░ │  ▓▓▓▓▓░░░ │  ▓▓▓░░░░░░ │  ▓▓▓▓░░░░ │  ▓▓▓▓▓▓▓▓ │          │
│  peak 82W  │  peak 1.5  │  peak 55%  │            │            │            │          │
└────────────┴────────────┴────────────┴────────────┴────────────┴────────────┴──────────┘
   ← 144 px tall, full-width, ~220 px per tile at 1440 px wide →
```

### ASCII wireframe — IC-7610, RX idle (no TX)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  STATION METERS                                                       RX               │
├────────────┬────────────┬────────────┬────────────┬────────────┬────────────┬──────────┤
│   Po       │   SWR      │   ALC      │   COMP     │   Id       │   Vd       │   S      │
│  —         │  —         │  —         │  —         │  —         │  13.8 V    │  S7      │
│  (dimmed)  │  (dimmed)  │  (dimmed)  │  (dimmed)  │  (dimmed)  │  ▓▓▓▓▓▓▓▓ │ ▓▓▓▓░░░░ │
│            │            │            │            │            │            │          │
└────────────┴────────────┴────────────┴────────────┴────────────┴────────────┴──────────┘
```

### Tile anatomy

```
┌─ tile ─────────────┐
│ Po        peak 82W │  ← label (11px) + peak readout (9px, right)
│ 78 W               │  ← value (22px, Roboto Mono, weight 700)
│ ▓▓▓▓▓▓▓░░░░░░░░░ │  ← horizontal bar, 6px tall, gradient from --v2-meter-*-fill
└────────────────────┘
```

---

## 4. Audio-scope / filter-curve integration

**Decision: move `AudioSpectrumPanel` (the combined AF-FFT + passband +
PBT + notch/contour widget — see §1 correction) out of the dock into the
right sidebar as a collapsible panel below the existing DSP controls.**
The widget is preserved intact. Argument:

- The dock's new job (meters dashboard) demands full width and visual
  unity. Splitting it with a scope breaks the "one glance, one truth"
  read of station telemetry.
- The combined widget is diagnostic/tuning-assist, not ever-present;
  operators open it when chasing a signal or setting up a filter, then
  often collapse it. Sidebar-collapsible matches that usage pattern.
- Right sidebar already hosts `DspPanel` / `TxPanel` / `RxAudioPanel` —
  a widget that shows AF content + filter shape + PBT + notch/contour
  belongs with DSP/audio, not wedged between RX1 and the meters.
- Only the mount point changes — no modification to
  `AudioSpectrumPanel.svelte` itself. Notch/contour overlays for FTX-1
  continue to function unchanged.

The separate RX filter-bandwidth summary in `FilterPanel` on the left
sidebar (the small trapezoid + "Filter: 3200 Hz" readout) stays put —
this is a *different* widget from `AudioSpectrumPanel` and was never in
the dock.

Rejected alternatives:

- *Keep the combined widget in the dock alongside meters* — kills the
  dashboard read, forces meters into a narrow strip.
- *Move to VFO header* — header is already 156 px tall and dense; adding
  a canvas widget here steals vertical space from the spectrum.

---

## 5. States

| State | Trigger | Visual |
|-------|---------|--------|
| **Idle (RX)** | `txActive === false` | TX-only tiles dim to `opacity: 0.35`, bars show `0`, values show `—`. S-meter and Vd stay fully lit. TX indicator shows `RX` in muted color. |
| **Pre-TX (PTT armed)** | `pttArmed && !txActive` (50–200 ms window) | Brief `border: 1px solid var(--v2-accent-yellow)` pulse on Po/SWR/ALC tiles. Signals "about to transmit." Optional — may be cut if runtime doesn't expose `pttArmed`. |
| **TX active** | `txActive === true` | TX-only tiles fully lit (`opacity: 1`). Peak-hold overlays appear. S-meter dims to 0.35. Top-right status chip shows `TX ●` in `--v2-accent-red` with pulsing dot. |
| **TX fault** | `swrMeter > 2.0` OR `alcMeter > 0.9` | The offending tile's border becomes `--v2-accent-red`, value text turns `--v2-accent-red-alt`, tile gains subtle `box-shadow: 0 0 6px var(--v2-accent-red)`. No modal, no blocking — hams are adults. |
| **Capability missing** | `state.<meter> === undefined` at mount | Tile not rendered. Grid re-flows. |
| **Compressor off** | `compressorOn !== true` | COMP tile not rendered. |
| **Power-off** | `runtime.radioPowerOn === false` | Whole dock hidden by the existing `power-off-overlay` (no change). |

---

## 6. Visual language

### Typography

| Element | Size | Weight | Font | Color token |
|---------|------|--------|------|-------------|
| Tile value | 22 px | 700 | `Roboto Mono` | `--v2-text-white` (active) / `--v2-text-muted` (idle) |
| Tile unit suffix (W, dB, A) | 12 px | 500 | `Roboto Mono` | `--v2-text-secondary` |
| Tile label (Po, SWR, …) | 11 px | 700, letter-spacing 0.12 em | `Roboto Mono` | `--v2-text-light` |
| Peak-hold readout | 9 px | 600 | `Roboto Mono` | `--v2-text-dim` |
| Panel title "STATION METERS" | 11 px | 700, letter-spacing 0.18 em | `Roboto Mono` | `--v2-text-light` |

Current dock uses 8–11 px labels; we standardize on 11 px for labels and
22 px for values. No label below 9 px anywhere.

### Colors

Reuse existing meter gradients:

- Po → `--v2-meter-power-fill` / `-track`
- SWR → `--v2-meter-swr-fill` / `-track` (built-in red zone past 2.0)
- ALC → `--v2-meter-alc-fill` / `-track`
- S → `--v2-meter-s-fill` / `-track`
- COMP → new token `--v2-meter-comp-fill` — propose same green ramp as
  SWR's safe region, `linear-gradient(90deg, #1f7a4a 0%, #4ed37b 100%)`
- Id → new token `--v2-meter-id-fill` — amber, `linear-gradient(90deg,
  #8a6a14 0%, #f2cf4a 100%)`
- Vd → new token `--v2-meter-vd-fill` — blue-cyan, `linear-gradient(90deg,
  #1a5a6d 0%, #7cfce5 100%)`

Tile background: `var(--v2-bg-card)` with `1px solid var(--v2-border)`.
On fault: border swaps to `--v2-accent-red`.

### Peak-hold indicators

SWR, Po, ALC get a 2-second peak-hold:

- Small inverted triangle marker on the bar at peak position, color
  `--v2-accent-yellow`.
- Peak numeric value printed top-right of tile in 9 px
  (`peak 82 W`).
- Peak decays linearly to current value over 2 s after last update ≥
  current.
- Double-click tile → reset peak immediately.

Id, Vd, COMP don't need peak-hold (steady-state readings).

---

## 7. Interaction

| Gesture | Action |
|---------|--------|
| **Click tile** | No-op by default (meters are read-only). Avoids accidental modal spawning during TX. |
| **Double-click tile** | Reset peak-hold (for Po/SWR/ALC tiles only). |
| **Long-press (500 ms) / right-click tile** | Open small popover with: peak value, time since peak, option to toggle between "instantaneous" and "1-s averaged" display. Popover is deferred — can ship without it (Issue 4). |
| **Keyboard** | Dock is not focus-reachable by default. Consider `Tab` stop on the panel title only, with `Enter` to reset all peaks. Deferred. |
| **Hover** | Tile border lifts from `--v2-border` to `--v2-border-soft`; no other effect. |

No source-selector radio group (`S/SWR/Po` buttons in current
`DockMeterPanel`) — deliberately removed. All meters always visible.

---

## 8. Integration with top VFO header

### Removed from dock

1. `receiver-summary-card-main` — RX1 freq/mode/filter/S-meter. **Remove entirely.** Duplicates `VfoPanel` in `VfoHeader`.
2. `receiver-summary-card-sub` — RX2 equivalent. **Remove entirely.**
3. `DockMeterPanel` (S/SWR/Po toggle variant). **Replace** with new `MetersDockPanel`.
4. `audio-scope-dock-card` (the `AudioSpectrumPanel` slot). **Move** to right sidebar (see §4).

### S-meter in the new dock — yes, keep it

Even though VfoHeader has a full-width LinearSMeter, include a
small **S tile** at the far right of the meters dock for two reasons:

- During TX the VfoHeader S-meter is frozen / not relevant. The dock S
  tile fills in the "current RX signal context" role at a glance.
- Symmetry: operators expect to see S alongside Po/SWR. Physical rigs
  put them on the same multimeter.

The S tile in the dock is secondary (smaller visual weight via
`opacity: 0.85` when TX inactive, the VfoHeader one is primary).

### Net change per RadioLayout.svelte

- Lines 254–298 (bottom-dock section) shrink from 3 card types + meter
  panel to **one** `<MetersDockPanel />`.
- Audio-scope mount migrates to `RightSidebar.svelte`.

---

## 9. Atomic implementation issues

Break into four GitHub issues, each ≤3 files and ≤200 LOC.

### Issue A — Add `MetersDockPanel` component with core tiles (Po, SWR, ALC, S)

**Title:** `feat(ui): add MetersDockPanel with Po/SWR/ALC/S tiles`
**Files (3):**
- `frontend/src/components-v2/panels/MetersDockPanel.svelte` (new)
- `frontend/src/components-v2/panels/meter-utils.ts` (edit — add `formatAmps`, `formatVolts`, `formatCompDb`, peak-hold helper)
- `frontend/src/components-v2/panels/__tests__/MetersDockPanel.test.ts` (new)

**Scope:** render tiles, capability-gate by `!== undefined`, basic bars. No peak-hold yet. Uses existing tokens only.
**LOC budget:** ~180.

### Issue B — Replace bottom-dock in RadioLayout + remove duplicates

**Title:** `refactor(ui): replace bottom-dock summary cards with MetersDockPanel`
**Files (2):**
- `frontend/src/components-v2/layout/RadioLayout.svelte` (edit — lines 254–298 and associated CSS)
- `frontend/src/components-v2/layout/RightSidebar.svelte` (edit — mount `AudioSpectrumPanel` as collapsible)

**Scope:** wire the new panel, delete receiver-summary-card markup and styles, migrate audio scope to right sidebar.
**LOC budget:** ~140 (mostly deletions).

### Issue C — Add Id/Vd/COMP tiles + capability gating

**Title:** `feat(ui): add Id/Vd/COMP tiles with capability gating to MetersDockPanel`
**Files (2):**
- `frontend/src/components-v2/panels/MetersDockPanel.svelte` (edit)
- `frontend/src/components-v2/theme/tokens.css` (edit — add `--v2-meter-id-fill`, `--v2-meter-vd-fill`, `--v2-meter-comp-fill`)

**Scope:** extend the tile set; COMP gated on `compressorOn`.
**LOC budget:** ~120.

### Issue D — Add peak-hold + fault highlighting

**Title:** `feat(ui): add peak-hold and SWR/ALC fault highlighting to MetersDockPanel`
**Files (2):**
- `frontend/src/components-v2/panels/MetersDockPanel.svelte` (edit)
- `frontend/src/components-v2/panels/meter-utils.ts` (edit — peak-hold decay logic + tests)

**Scope:** 2-s peak decay for Po/SWR/ALC, SWR > 2.0 red border, ALC > 0.9 red border, double-click reset.
**LOC budget:** ~150.

**Ordering:** A → B → C → D. After B the visible UI is already improved (no duplication, cleaner dock); C and D add polish without blocking.

---

## 10. Open questions

- **Q1 — S tile in dock: keep or cut?** §8 argues keep. If the user
  feels it's still duplication given the VfoHeader meter, we drop it
  and the 6-tile grid becomes cleaner at narrow widths.
- **Q2 — Pre-TX yellow pulse.** Requires `pttArmed` or similar in
  runtime state. Does the WS protocol actually emit an event between
  PTT down and TX confirmed? If not, drop the state entirely (no
  polling hack worth it).
- **Q3 — Peak-hold reset gesture.** Double-click per tile vs. single
  global "reset peaks" button in the panel header? Pro-reset-button:
  one click clears all. Pro-double-click: per-meter control. Lean
  toward double-click to match physical-rig muscle memory
  (tap-the-needle-back-to-zero).
- **Q4 — TEMP meter exposure.** Is IC-7610 PA temp reachable via any
  CI-V subcommand we're not using, or is it truly controller-only? If
  we can add it, the 7-tile grid lights up a useful warning for
  contest/DX operating. Needs backend investigation, out of scope for
  this frontend plan.
- **Q5 — Audio-scope panel collapsed-by-default?** Proposal: yes,
  collapsed on first render; user opens it when debugging audio. Saves
  right-sidebar scroll.
- **Q6 — Tile minimum width on very narrow displays.** At <1100 px the
  grid will wrap to two rows of 3–4 tiles. Is that acceptable for
  desktop-v2 (which isn't supposed to be responsive to mobile sizes
  anyway), or do we force a single-row scroll?
- **Q7 — Does removing `receiver-summary-card-*` break any test
  selectors or Playwright flows?** Grep shows no external refs, but
  confirm in Issue B.

---

## Appendix — Token additions summary

To be added to `frontend/src/components-v2/theme/tokens.css`:

```css
--v2-meter-comp-fill: linear-gradient(90deg, #1f7a4a 0%, #4ed37b 100%);
--v2-meter-comp-track: linear-gradient(90deg, rgba(31,122,74,0.3) 0%, rgba(78,211,123,0.2) 100%);
--v2-meter-id-fill:   linear-gradient(90deg, #8a6a14 0%, #f2cf4a 100%);
--v2-meter-id-track:  linear-gradient(90deg, rgba(138,106,20,0.3) 0%, rgba(242,207,74,0.2) 100%);
--v2-meter-vd-fill:   linear-gradient(90deg, #1a5a6d 0%, #7cfce5 100%);
--v2-meter-vd-track:  linear-gradient(90deg, rgba(26,90,109,0.3) 0%, rgba(124,252,229,0.2) 100%);
--v2-meter-fault-border: var(--v2-accent-red);
--v2-meter-fault-glow:   0 0 6px rgba(255, 32, 32, 0.45);
```
