# LCD Layout Redesign — Design Spike

**Date:** 2026-04-19
**Surface:** `frontend/src/components-v2/panels/lcd/AmberLcdDisplay.svelte`
**Skin:** `amber-lcd` (fallback skin for radios lacking panadapter/scope)
**Prerequisite for:** `2026-04-18-lcd-display-enhancements.md` §5.2 (per §8.7)
**Triggered by user feedback (2026-04-18):**
*"Имеет смысл пересмотреть layout самого LCD дисплея, с учётом двух VFO, индикаторов и спектра/фильтра."*
**Status:** design only — no code changes in this document.

**User clarification (2026-04-19):** "спектр" in the triggering quote
refers to **AF spectrum** (the combined AF FFT + passband + PBT +
notch/contour widget currently in `AmberAfScope`). Confirmed — the LCD
skin is precisely for radios without an RF panadapter, so the only
spectrum on-screen is AF. Resolves open question Q1.

---

## 1. Context — current `AmberLcdDisplay` structure

Read of `AmberLcdDisplay.svelte` (138–270) gives the following vertical stack inside
`.lcd-screen` (flex-column, `gap: 6px`, `padding: 12px 18px`):

| # | Region (class)                 | Height (approx)            | Content                                                                                       |
|---|--------------------------------|----------------------------|-----------------------------------------------------------------------------------------------|
| 1 | `.lcd-meter-row` (main)        | ~28 px                     | `AmberSmeter` + source cycle button (S/PO/SWR/ALC/COMP)                                       |
| 2 | `.lcd-meter-row.lcd-meter-sub` | ~20 px (scaleY 0.7, dim)   | Sub-RX S-meter, dual-RX only, hidden during TX                                                |
| 3 | `.lcd-ind-row`                 | ~24 px, wraps (!)          | 20+ status tokens, 3 hard `<span class="ind-sep">` gutters, flex-wrap                         |
| 4 | `.lcd-vfo-scope-row`           | ~96–110 px                 | VFO A frequency (`AmberFrequency size="large"`) + mode-box + band-box, with scope strip 30 %  |
| 5 | `.lcd-vfo-row.lcd-vfo-sub`     | ~38 px (dual-RX only)      | VFO B frequency (`AmberFrequency size="small"`) + `B` tag + mode                              |
| 6 | `.lcd-vfo-ctrl-row`            | ~24 px                     | A↔B, A=B, DW, SPLIT, XIT, CLR, TUNE, BK-OFF… (wraps)                                          |
| 7 | `.lcd-rit-row`                 | ~20 px (conditional)       | RIT/XIT offset readout                                                                        |

Ink model (important for redesign): two-layer DOM, ghost `"888.888.888"` at
α 0.06 + active digits at α 1.0 absolutely over it. All tokens use
`JetBrains Mono` except the digit blocks which use `DSEG7 Classic`. The
s-meter and `AmberAfScope` render to canvas with the same ink colour.

Capability gates already present:
- `hasDualReceiver()` → rows 2 + 5.
- `hasAudioFft()` → scope strip inside row 4.
- `hasCapability(...)` on ~12 tokens inside row 3.
- `isCwMode` / `hasCapability('break_in')` → BK-OFF button in row 6.

### Current problems (grounded in the file)

1. **VFO B is a second-class citizen.** Row 5 is `.lcd-vfo-sub` — font `small`,
   tag dim, sub-mode α 0.45, no band, no meter tied to it. For a dual-RX
   operator running cross-band split or dual-watch, this is the wrong
   hierarchy.
2. **Row 3 (indicators) is a wall of 20+ tokens** with only three separators.
   At 1366 × 768 it wraps to two or three lines, pushing every row below
   downward and eating VFO space. The `flex-wrap: wrap` on `.lcd-ind-row`
   is a reflow grenade.
3. **Filter-viz is anchored to VFO A's row**, not the display as a whole.
   This makes "promote to full-width" (enhancements §3) a reflow-heavy
   operation: moving the strip out of row 4 requires restructuring row 4
   anyway.
4. **Single-RX and dual-RX share one linear layout with `{#if}` toggles.**
   Every capability flip (enabling DW mid-session, hot-adding sub-RX in a
   future backend) triggers layout reflow of *everything below*.
5. **VFO B has no meter, no band tag, no mode-box parity.** Yet a dual-watch
   operator stares at VFO B's S-meter for split-frequency DX listening.
6. **The VFO control buttons (row 6) cross the display/control boundary.**
   A physical rig's display doesn't carry soft buttons; they belong on the
   bezel (sidebar). They currently eat ~24 px of the vertical budget.

### 16 : 7.5 surface budget

`.lcd-slot` is `aspect-ratio: 16/7.5`. On a 1600 px wide main column, that's
1600 × 750 CSS px. After `.lcd-screen`'s 12 × 2 + 18 × 2 padding and the
4 px `.amber-lcd` outer padding, usable interior is **~1556 × 714 px**.

That is enough. But it is not abundant. Every row must pay rent.

---

## 2. Design principles

Six principles. Each argued briefly; each has a consequence cited downstream.

### P1. Dual-VFO equal weight *by default*, demotion *on capability absence*.

A dual-RX radio's two receivers are not primary/secondary — they are two
independently-tuned DSP chains. The current "VFO A big, VFO B small" is a
UI lie about the hardware. The redesign's default layout reserves equal
horizontal slab area for both VFOs. Single-RX radios collapse VFO B's
slab to zero; the grid's other columns absorb the space deterministically
(no reflow of VFO A's dimensions).

**Consequence:** we need a grid (not a flex-column) so we can collapse a
named cell without re-laying out its neighbours.

### P2. Capability-driven cell hide *without layout reflow*.

Hiding VFO B, the scope strip, the memory strip, or the telemetry strip
must never change the position or size of VFO A, the status row, the
meter, or the filter-viz. Operators already rely on muscle-memory placement.

**Consequence:** the grid must use named `grid-template-areas` and fixed
`grid-template-rows` / `grid-template-columns` in each variant. Hiding a
cell = `visibility: hidden` + the area stays allocated, *or* a variant
switch to a grid definition where the absent cell's row/column has
collapsed to zero and the *remaining* areas have identical absolute
dimensions to the other variant. We choose the second (§3).

### P3. Indicators legible at 2 m — *group*, *separate*, *stabilise*.

Row 3's 20+ tokens must not wrap. Wrapping breaks scan paths. Solution:
**group into four fixed-width bays** (TX / RF-chain / DSP / VFO-state).
Bays are `grid-template-columns` with explicit widths; tokens inside a
bay can ellipsize or hide individually, but the bay's horizontal position
is immutable. Separators (`ind-sep`) become bay borders, not inline
pseudo-spans.

**Consequence:** the status row becomes a 4-column sub-grid. Capability-
absent tokens render as a dim placeholder (`·`) — the bay shape is
preserved.

### P4. Filter-viz is a peer of VFO, not an accessory.

On a scope-less radio, the filter-viz (passband shape + PBT brackets +
notch/contour + AF FFT inside) is the operator's *only* visual
representation of the receive chain. It deserves a named cell with its
own grid row, not "30 % strip pinned to VFO A". Per the combined-widget
note in the task brief, this widget aggregates 4 layers (AF FFT,
passband, PBT, notch/contour). Its vertical budget should be sized for
the worst-case (FTX-1 with all 4 layers visible), not the best-case
(passband only).

**Consequence:** filter-viz gets a dedicated `filter` area, ~120 px tall,
full display width minus gutters. Dual-RX and single-RX share the same
allocation.

### P5. Soft buttons belong on the bezel, not on the screen.

The amber LCD is a *display*. The current row 6 (VFO control buttons)
puts soft buttons *inside the screen*. This:
- Costs ~24 px of screen real estate.
- Mimics a control surface the display itself never had on any real rig.
- Duplicates controls already present in `LeftSidebar` / `RightSidebar`.

Redesign moves A↔B, A=B, DW, SPLIT, XIT, CLR, TUNE, BK-OFF to the
**right sidebar's VFO control panel** (existing panel expanded). The
display surfaces only *state*, never *command entry*.

**Consequence:** row 6 is deleted from the LCD grid. ~24 px freed,
given to the filter-viz cell. The RIT-offset row (currently conditional
row 7) gets folded into VFO A's right-side inline region (PB cell).

### P6. Mode-specific variation is a *content* concern, not a *layout* concern.

CW vs SSB vs DATA can change what the filter-viz draws (CW: ±500 Hz
scale; DATA: wider passband outline), what the meter shows (CW: key-down
current if wired), what the VFO mode-box prints (`CW` vs `CW-R`). But
the grid cells don't move. Layout is invariant under mode change.

**Consequence:** no `{#if mode === 'CW'}` at the grid level. Mode gates
live inside individual components.

---

## 3. Grid proposal — unified 8 × 12 grid

All variants share one grid. Capability gates collapse *rows or columns*,
never move areas.

```
Grid columns:          [ A=left-gutter  1fr  1fr  1fr  1fr  1fr  1fr  1fr  1fr  1fr  1fr  right-gutter ]
                          12 px         —— 12 fluid unit columns ——                                 12 px

Logical column bands:  [ gutter | VFO-A-block (6u) | VFO-B-block (6u) | gutter ]
                                       ←            split 50/50            →
```

### 3.1 Row template (worst case, dual-RX with full enhancements)

```
row-1   status      28 px   [ status-tx | status-rf | status-dsp | status-vfo ]  (4 bays)
row-2   meter-A     28 px   [ meter-A spans VFO-A-block |  meter-B spans VFO-B-block ]
row-3   vfo         72 px   [ vfo-A (freq + mode + band)  |  vfo-B (freq + mode + band) ]
row-4   pb          22 px   [ rit/xit A | offset | . . . | rit/xit B | offset     ]
row-5   filter    120 px   [ filter-viz spans full width, shared between A and B (§5)  ]
row-6   aux        80 px   [ memory strip (7u) | telemetry (5u) ]
```

**Total:** 28 + 28 + 72 + 22 + 120 + 80 = **350 px** of content, plus
6 × `gap: 6px` = 30 px, plus top/bottom padding 24 px → **~404 px**.
Fits inside our ~714 px interior with ~310 px margin for growth.

That 310 px margin is deliberate. It allows:
- Contrast preset `MAX` pushing inactive α to 0.30 (larger visual mass).
- `vfo` row upsized to 96 px on 4K monitors (digit scaling).
- One future row (e.g. CW decode text, RTTY FSK indicator) without a
  redesign.

### 3.2 Single-RX idle

VFO-B-block columns collapse: the grid's second 6u band shrinks to 0u,
leaving a single 12u band. Row heights unchanged. `meter-B`, `vfo-B`
areas disappear (no reflow — the columns underneath them simply do not
exist in this variant).

```
┌──────────────────────────────────────────────── 1556 px ────────────────────────────────────────────────┐
│ [TX VOX PROC]  │  [ATT AMP1 DIGI IP+ ATU]  │  [NB NR CONT NOTCH ANF AGC-M]  │  [RFG SQL RIT SPLIT LOCK] │ row-1 status
├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ S ▁▂▃▄▅▆▇█ 9+20dB                                                                           [S|PO|SWR] │ row-2 meter
├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [A]   14.195.678   USB 2.4k                                                                      [20m] │ row-3 vfo
├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                         │ row-4 pb (empty)
├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────── filter 2.4k  FIL2  Shift +320  PBT −140/+60  Contour 3  Notch ■ ─── AF FFT ─────────────┐│
│ │    ‐6 ┌──[───]──┐                    ▁▃▅▇█▇▅▃▂                                                     ││
│ │ ‐20 ──┘          └──                                                                               ││ row-5 filter
│ │  ├──┼──┼──┼──┼──┼──┤  −3k −2k −1k  0  +1k +2k +3k                                                  ││
│ │                    ▲ (centre)                                                                      ││
│ └────────────────────────────────────────────────────────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [M1 14.195 U DX] [M2 18.100 U FT8] [M3 21.280 SSTV] [M4 28.074 FT8]  │  VD 13.8  TEMP 42  ID 0.2A     │ row-6 aux
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Single-RX TX

Changes vs idle:
- Row 1: `TX` token glows red (`ind-tx` class). `ATU` may switch to
  `TUNE` (blink).
- Row 2 meter auto-source flips S → PO (existing behaviour).
- Row 5 filter-viz dims the AF FFT layer (no useful input), passband
  shape unchanged. This is correct even for SSB (TX sidebands are not
  echo'd through the AF path).
- No grid row moves. No cell resizes. The *content* changes.

```
│ [TX] [VOX] [PROC 6]  │  [ATT AMP1 · · TUNE*]  │  [NB · · · · AGC-M]  │  [· · · SPLIT ·]   │ row-1
│ PO ▁▂▃▄▅▆▇▇▇▇ 75 W                                                        [PO]            │ row-2
│ [A]   14.195.678   USB 2.4k                                             [20m]             │ row-3
│                                                                                            │ row-4
│ filter + dimmed FFT                                                                        │ row-5
│ memories unchanged  │  VD 13.2 TEMP 48 ID 18A                                              │ row-6
```

`*` = blink. `·` = placeholder for absent token (bay width preserved).

### 3.4 Single-RX, mode-specific content notes

Layout invariant. Content deltas only:

| Mode | Filter row scale | Status row delta | VFO mode-box |
|------|------------------|------------------|--------------|
| SSB  | ±3 kHz, minor 500 Hz | NR/NB gates normal | `USB` / `LSB` |
| CW   | ±500 Hz, minor 100 Hz | add `BK` badge if break-in, hide DATA | `CW` / `CW-R` |
| DATA | ±3 kHz, outline shows wide roofing | `DATA` token active | `USB-D` / `LSB-D` |
| AM   | ±10 kHz, minor 2 kHz | hide NR if backend strips it in AM | `AM` |
| FM   | ±15 kHz, minor 5 kHz | squelch token promoted to active bay | `FM` |

### 3.5 Dual-RX idle (default, both receivers listening)

```
┌──────────────────────────── 1556 px ────────────────────────────────────────────────────────────────────┐
│ [TX VOX PROC]  │  [ATT AMP1 DIGI IP+ ATU]  │  [NB NR CONT NOTCH ANF AGC-M]  │  [RFG SQL RIT SPLIT LOCK] │ row-1
├──────────────────────────────────────── 6u ────────────────────┬──────────────────── 6u ────────────────┤
│ S ▁▂▃▄▅▆▇█ 9+20 [S|PO|SWR]                                      │ S ▁▂▃▄ 5 [S]                          │ row-2
├─────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤
│ [A]● 14.195.678   USB 2.4k            [20m]                     │ [B]  7.074.000   USB 2.4k   [40m]     │ row-3
├─────────────────────────────────────────────────────────────────┴───────────────────────────────────────┤
│ (RIT row: empty when both offsets are zero)                                                             │ row-4
├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                filter-viz (shared, active-VFO anchored)                                 │ row-5
├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [M1 … M4]  (4 instead of 5 — memory cell narrower)  │  VD 13.8  TEMP 42  ID 0.2A                        │ row-6
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Key differences vs §3.2:
- VFO-B-block has identical dimensions to VFO-A-block. Same font size
  for frequency, same mode-box, same band-box.
- `[A]●` marker shows which VFO is *active* (receiver-controlled). Moves
  to `[B]●` on swap. This replaces the current "active VFO font-weight"
  hack with an explicit dot.
- Meter-B uses the same `AmberSmeter` widget, not the scaled-0.7
  degraded version. Source is locked to `S` (you cannot change a sub-RX
  meter source; it's an S-meter only).
- Filter-viz is still shared (§5) — a single widget anchored to whichever
  VFO is active.

### 3.6 Dual-RX SPLIT / DUAL-WATCH

Visually identical to §3.5, plus:
- Row 1 `SPLIT` token active (or `DW` token, see §6.2).
- Row 3: the *transmit* VFO gets a small red `TX` pip next to its tag
  (e.g. `[A]   ` is RX, `[B]  TX` means "listening on A, transmitting
  on B" — classic DX split).
- Row 4 pb: if the offset between VFO A and VFO B is small (< 10 kHz,
  "close split"), show `Δ = +2.3 kHz` in row-4. Useful. Disappears for
  cross-band split.

```
│ [TX VOX PROC]  │  [ATT ...]  │  [... AGC]  │  [... SPLIT* ...]                            │ row-1
│ S 9+20    [S|PO|SWR]   │ S 5    [S]                                                        │ row-2
│ [A]● 14.195.678 USB 2.4k [20m]   │ [B]TX 14.197.300 USB 2.4k [20m]                         │ row-3
│ Δ = +1.622 kHz                                                                              │ row-4
│ filter-viz (anchored to active RX)                                                          │ row-5
│ memories │ telemetry                                                                        │ row-6
```

Dual-watch (same-band, shared-filter) variant: row 4 shows `DW` instead
of `Δ`. Row 2's meter-B is now the *same DSP chain* as meter-A
(diversity receiver), so both meter needles track together — a visual
hint that they're coupled.

### 3.7 CW / SSB / DATA in dual-RX

No grid changes. Per-VFO mode-box content differs. The filter-viz is
anchored to the *active* VFO's mode — this means switching A↔B can
rescale the filter-viz x-axis. Acceptable; the scale ticks re-label.

---

## 4. Cell inventory

Every cell, with capability gate and empty-state behaviour. Cells are
named after their `grid-area`.

| Area            | Purpose                                        | Capability required                 | When absent                                                                    |
|-----------------|------------------------------------------------|-------------------------------------|--------------------------------------------------------------------------------|
| `status-tx`     | TX / VOX / PROC bay                            | always present                      | never empty (TX is always shown; VOX/PROC gated inside bay with `·` holder)    |
| `status-rf`     | ATT / AMP / DIGI / IP+ / ATU bay               | per token (`attenuator`, `preamp`, `digisel`, `ip_plus`, `tuner`) | bay always present; individual tokens → `·`                                    |
| `status-dsp`    | NB / NR / CONT / NOTCH / ANF / AGC bay         | per token                           | same                                                                           |
| `status-vfo`    | RFG / SQL / RIT / SPLIT / DATA / LOCK bay      | per token                           | same                                                                           |
| `meter-A`       | Main RX meter + source cycle button            | always                              | never                                                                          |
| `meter-B`       | Sub RX S-meter, full-size                      | `hasDualReceiver()`                 | column collapses; `meter-A` widens to 12u                                      |
| `vfo-A`         | VFO A freq (DSEG7) + mode-box + band-box + active dot | always                       | never                                                                          |
| `vfo-B`         | VFO B freq (DSEG7) + mode-box + band-box + active dot | `hasDualReceiver()`          | column collapses; `vfo-A` widens to 12u                                        |
| `pb-A` / `pb-B` | RIT/XIT offset or close-split Δ                | `rit` or `split`                    | row collapses to 0 px                                                          |
| `filter`        | Full-width filter-viz (AF FFT + passband + PBT + notch/contour) | always | row remains; internal layers gate separately (no AF FFT → outline only)        |
| `memory`        | Memory / recent-QSY strip, 7u wide             | (always; falls back to QSY-only if no backend memories) | row remains; if telemetry also absent, row collapses to 0 px                   |
| `telemetry`     | VD / TEMP / ID tiles, 5u wide                  | backend reports any of VD/TEMP/ID   | 5u column gives width to `memory`; if both memory+telemetry empty, row collapses |

### 4.1 Reflow rules summarised

- Collapsing VFO-B-block does not resize VFO-A-block. Instead, VFO-A-block's
  column span changes from 6u → 12u via a *different grid template*
  selected by `hasDualReceiver()`. Both templates have identical row
  heights, so the vertical position of row-4, row-5, row-6 is byte-for-
  byte equal across variants.
- Collapsing `pb` row (no RIT/XIT active) uses `grid-template-rows`
  with `minmax(0, auto)` on that row. Row-5 filter moves up exactly
  22 px. Acceptable — filter-viz doesn't have absolute positioning
  dependencies elsewhere.
- Collapsing `aux` row (no memories, no telemetry) frees 80 px. We
  *do not* grow the filter row to fill it; the empty space below the
  filter is fine. Operators reading S-meters will notice more growth
  than empty bottom.

---

## 5. Interaction with enhancement plan §3 and §4

The redesign re-sequences §3 and §4 as follows.

### 5.1 Filter-viz wide mode (enhancements §3) — **survives, promoted**

The redesign's row-5 *is* the wide filter-viz. §3's pixel proposals
(Hz ruler, centre marker, `-6` / `-20` dB ticks, IF-shift arrow,
PBT brackets, mode-aware envelope) all land unchanged. The only delta:
§3's compact-variant fallback for dual-RX (30 %-wide strip next to
VFO A) is **deleted**. In the new grid, filter-viz is always full-width,
always shared between A and B. The current "compact scope strip inside
row 4" disappears.

This is a simplification win. §3 previously had to specify both wide
and compact layouts; the redesign forces one.

### 5.2 Memory / recent-QSY strip (enhancements §4.1) — **survives, narrower**

§4.1 planned 8 cells at ~12 % each. In the new grid's `memory` area
(7u out of 12u = ~58 % of display width = ~900 px), we fit **5 cells at
~180 px each** (or 4 cells in dual-RX where telemetry takes 5u and
memory is 7u minus 0u). Cell content unchanged: first 5 memory slots,
or memories + 2 recent QSY in single-RX.

In dual-RX, memory strip is not demoted to the sidebar (which was §4.1's
fallback). It stays on the LCD, just narrower — the user asked us to
treat dual-VFO as first-class, and memories remain part of the glance-
scannable surface.

### 5.3 Telemetry strip VD/TEMP/ID (enhancements §4.2) — **survives, same size**

§4.2's three tiles fit in 5u (~680 px) comfortably — ~220 px per tile,
each with big DSEG7 + sparkline + label. Unchanged.

### 5.4 Items **deprioritised or deleted** by the redesign

- **Dual-RX memory-strip demotion to sidebar** (§4.1 fallback) — deleted.
  Memory strip stays on the LCD in both variants.
- **Scope-strip compact mode for dual-RX** (§3 fallback) — deleted.
  Filter-viz is always full-width.
- **Sub-meter scaleY-0.7 degradation** (current code) — deleted.
  Meter-B is full-size in the new grid.
- **VFO control buttons inside the LCD surface** (current row 6) —
  **moved to right sidebar**. Not lost, just relocated per P5.

---

## 6. Status indicator organisation

Current row 3 has these 20 tokens (in source order, gated by capability):

```
TX VOX PROC    | ATT [AMP1|AMP2|IPO] DIGI-SEL IP+ ATU(or TUNE) | NB NR CONT NOTCH ANF AGC-<mode> | RFG SQL RIT SPLIT DATA LOCK
```

### 6.1 Four-bay grid (new)

```
┌──────────────── status-tx ────┬──────── status-rf ────────┬──────────── status-dsp ──────────┬──────── status-vfo ────────┐
│  TX   VOX   PROC 6            │  ATT   AMP1   DIGI   IP+  │  NB 3   NR 5   CONT   NOTCH      │  RFG   SQL   RIT   SPLIT   │
│                               │  TUNE*                    │  ANF    AGC-MID                  │  DATA  LOCK                │
└───────────────────────────────┴───────────────────────────┴──────────────────────────────────┴────────────────────────────┘
       3u                                3u                             3u                                3u
```

Each bay is a `display: grid; grid-template-columns: repeat(auto-fill, minmax(...))`
inside its 3u slot. Tokens flow left-to-right inside their bay and wrap
*within* the bay only — never across bay boundaries.

Bay widths are **equal (3u each)** rather than content-fit. This gives
consistent horizontal anchors — operators know `AGC` always sits in the
third quarter of row 1. A real-rig analogue: the IC-7610's status line
has fixed regions, not a flex-wrap.

### 6.2 Tokens that move off the LCD to the sidebar

Criteria: low frequency of change + already present in sidebar controls.

| Token     | Reason for demotion                                                              | New home               |
|-----------|----------------------------------------------------------------------------------|------------------------|
| `RFG`     | Always "on" when rf_gain < max; the slider is on the sidebar already.            | Sidebar RF-gain slider |
| `DIGI-SEL`| Rarely toggled; a per-band setting.                                              | Sidebar DSP panel      |
| `IP+`     | Rarely toggled; a preamp companion setting.                                      | Sidebar RF panel       |
| `CONT`    | The contour *level* is visible in filter-viz as the U-curve. Redundant to show as a token. | Deleted from LCD |
| `ANF`     | Notch-class token; keep ANF in the DSP bay *only* if capability present, else hide. | Same                |

After demotion:

- **`status-tx` (3u):** `TX VOX PROC` → unchanged.
- **`status-rf` (3u):** `ATT AMP DIGI IP+ ATU` → `ATT AMP ATU` (3 tokens, DIGI/IP+ → sidebar).
- **`status-dsp` (3u):** `NB NR CONT NOTCH ANF AGC` → `NB NR NOTCH AGC` (4 tokens, CONT → filter-viz only, ANF → inside NOTCH badge).
- **`status-vfo` (3u):** `RFG SQL RIT SPLIT DATA LOCK DW` → `SQL RIT SPLIT DW DATA LOCK` (6 tokens, RFG → sidebar).

Result: **20+ tokens → 16 tokens in 4 equal bays**. Row 1 fits on one
line at 1366 × 768 without wrapping. Below 1366 px the whole LCD skin
already degrades gracefully (it's wide-screen-oriented); no special
case needed.

### 6.3 Visual separators

`.ind-sep` (currently a 1 px dim line) becomes a proper CSS
`border-right` on each bay except the last. Width 1 px, colour
`var(--lcd-ink-ghost)`. Height 100 % of row-1 (not 16 px as currently).
This visually anchors the bays as distinct regions.

### 6.4 `DW` token

The current code does not render a DW indicator (only a DW button).
Add `DW` to the `status-vfo` bay, gated by `hasCapability('dual_rx')` and
reactive to `vfoOps.dualWatch`. This makes the bay a state surface, not
just a label dump.

---

## 7. Typography hierarchy

Existing file uses `font-size: 14px` for indicators, `22px` for the
VFO-A tag, `18px` for mode/band boxes, `16px` for sub-VFO tag, `13px`
for sub-mode, `12px` for RIT label, `11px` for buttons, `10px` for
meter-source button. Inconsistent.

### 7.1 Proposed scale

Seven named tokens, matching CSS custom properties on `.amber-lcd`:

| Token                  | px   | Weight | Usage                                                                     |
|------------------------|------|--------|---------------------------------------------------------------------------|
| `--lcd-font-freq-primary`   | 48   | bold   | VFO A / VFO B DSEG7 digits (single-RX and dual-RX *equal*)           |
| `--lcd-font-mode-box`       | 20   | 700    | Mode-box, band-box (both VFOs)                                       |
| `--lcd-font-vfo-tag`        | 22   | 700    | `[A]`, `[B]` tags — equal size both VFOs                             |
| `--lcd-font-status-ind`     | 14   | 700    | Status row tokens (all four bays)                                    |
| `--lcd-font-meter-label`    | 12   | 600    | Meter scale marks, source button                                     |
| `--lcd-font-pb-offset`      | 16   | 600    | RIT/XIT offset, close-split Δ (DSEG7 mono)                           |
| `--lcd-font-aux-label`      | 11   | 700    | Memory label, telemetry unit, aux-row microcopy                      |

**Key change:** `--lcd-font-freq-primary` is the *same* for VFO A and
VFO B. Per P1, VFO B is not demoted typographically. The *active*
receiver gets the `[A]●` active-dot treatment; inactivity is signalled
by the dot, not by shrinking the digits.

### 7.2 Active vs inactive emphasis (no size change)

When a VFO is inactive, its frequency digits use `--lcd-ink-inactive` at
the active-layer α (respecting contrast preset). Ghost layer unchanged.
Ratio of active-VFO : inactive-VFO ink is ~1 : 0.6 — visible, scannable,
not "shrunken".

This replaces the current "small font = secondary" idiom with an "ink
density = focus" idiom. The latter is closer to how real rigs work
(segments all same size; only the backlit ones are "loud").

### 7.3 Responsive scaling

All tokens listed above are in px. On very small viewports (`.lcd-slot`
narrower than 1100 px), a `@container`-driven multiplier drops them to
80 %. Below 900 px, we'd be outside the skin's target envelope anyway.

---

## 8. Transition plan

Options:

### 8.a Redesign-first, enhancements adapt.

Ship the grid refactor (§9.1) first. Then §8.1–§8.6 of the enhancements
plan each merge into the new grid. Risk: enhancements land later
(2–3 weeks). Reward: enhancements land *correctly sized* into their
final cells — no rework.

### 8.b Enhancements-first, redesign reshuffles.

Land §8.1 (contrast tokens), §8.3 (wide filter-viz), §8.4 (memory),
§8.5 (telemetry) into the *current* layout. Then redesign, breaking all
four. Risk: significant rework in the redesign PR — filter-viz, memory,
telemetry all need their DOM parent changed. Reward: users get the
enhancements a week earlier.

### 8.c Coordinated sequence (**recommended**).

1. **Land redesign scaffold first** (Issue §9.1 below). This is a
   layout-only change: introduces the grid, moves VFO B to peer status,
   moves control buttons to sidebar, splits status row into 4 bays.
   *No* new widgets, *no* new data sources. ≤ 3 files, ≤ 200 LOC.
2. **Land enhancements §8.1 (contrast tokens) in parallel.** This is
   pure CSS-variable plumbing — orthogonal to the grid.
3. **Land filter-viz wide mode (§8.3) on top of the new grid.** The
   new `filter` area is already reserved; §8.3 just fills it. Because
   we deleted the compact variant (§5.1), §8.3 is *simpler* than the
   original plan.
4. **Land memory strip (§8.4) and telemetry strip (§8.5) into the `aux`
   row.** Both already have their cells allocated.
5. **Dual-RX VFO-B promotion (Issue §9.2).** Ship the full-size
   meter-B, full-size vfo-B, active-dot marker.
6. **Status row reorg (Issue §9.3).** Demote tokens to sidebar, add DW
   indicator, bay borders.

Net: one layout PR up-front, five content PRs in sequence. Each ≤ 3
files.

**Recommendation: 8.c.** It respects the existing enhancement plan's
atomicity while preventing downstream rework.

Why not 8.a? 8.a stalls user-visible improvement for weeks.
Why not 8.b? 8.b guarantees churn — every enhancement PR would later
be reworked when the grid changes.

---

## 9. Atomic implementation issues

Three issues. Each ≤ 3 files, ≤ 200 LOC, independent after #9.1 lands.

### Issue 9.1 — LCD grid scaffold

**Title:** refactor(lcd): unified grid with named areas for VFO A/B, status bays, filter, aux

**Files:**
- `frontend/src/components-v2/panels/lcd/AmberLcdDisplay.svelte` (swap flex-column for `grid-template-areas`; introduce `hasDualReceiver` template switch; delete `.lcd-vfo-ctrl-row`; delete `.lcd-rit-row` at top level and fold into `pb-A`/`pb-B` areas).
- `frontend/src/components-v2/layout/LcdLayout.svelte` (no change expected — grid is internal to AmberLcdDisplay; touched only if `.lcd-slot` min-height needs adjustment).
- `frontend/src/components-v2/panels/controls/VfoControlPanel.svelte` (new home for A↔B, A=B, DW, SPLIT, XIT, CLR, TUNE, BK-OFF — *move* buttons, don't duplicate).

**Scope:**
- Introduce grid with two column templates (single-RX 12u, dual-RX 6u+6u).
- Create `grid-area: status-tx | status-rf | status-dsp | status-vfo | meter-A | meter-B | vfo-A | vfo-B | pb-A | pb-B | filter | memory | telemetry` placeholders.
- Move VFO control buttons to right sidebar panel (`VfoControlPanel.svelte`). Delete row 6 from LCD.
- No new visual features. Existing meters, frequencies, indicators render into the new cells unchanged.
- Keep `.lcd-scanlines`, TX-glow, bezel styling untouched.

**Out of scope:** status-bay reorg (§9.3), VFO-B size parity (§9.2), filter-viz promotion (§8.3 in enhancements).

**Estimated LOC:** ~160 (mostly CSS grid definitions, some JSX reshuffling).

### Issue 9.2 — VFO B promotion to peer

**Title:** feat(lcd): VFO B renders at peer size with meter, band, active-dot marker

**Files:**
- `frontend/src/components-v2/panels/lcd/AmberLcdDisplay.svelte` (swap `<AmberFrequency size="small">` for `"large"` for VFO B; add band tag and mode-box in B's cell; add active-dot render).
- `frontend/src/components-v2/panels/lcd/AmberFrequency.svelte` (only if a new `size="peer"` variant differs from `"large"` — ideally not; use `"large"` for both).
- `frontend/src/components-v2/panels/lcd/AmberSmeter.svelte` (delete the 0.7-scale sub-meter styling class; meter-B uses full-size).

**Scope:**
- VFO B uses `--lcd-font-freq-primary` (48 px).
- VFO B gets band-box + mode-box identical to VFO A.
- Active VFO shown via `[A]●` / `[B]●` dot glyph (not font weight, not size).
- Sub-meter rendered full-size in `meter-B` area; source locked to `S`.
- Inactive VFO uses `--lcd-ink-inactive` at current contrast preset's α — no separate dim class.

**Depends on:** #9.1 merged.

**Estimated LOC:** ~120.

### Issue 9.3 — Status row four-bay reorganisation

**Title:** refactor(lcd): status row → four fixed bays, demote low-frequency tokens to sidebar

**Files:**
- `frontend/src/components-v2/panels/lcd/AmberLcdDisplay.svelte` (replace single `.lcd-ind-row` with four `grid-area` bays; remove RFG/DIGI-SEL/IP+/CONT tokens; add `DW` state indicator).
- `frontend/src/components-v2/panels/controls/RfControlPanel.svelte` (surface DIGI-SEL and IP+ controls, since they're no longer in the LCD status row; if panel doesn't exist, create in this PR — still ≤ 3 files).
- `frontend/src/components-v2/panels/controls/DspControlPanel.svelte` (same idea for RFG — if existing, just verify it's surfaced; no work likely needed).

**Scope:**
- Four bays with equal 3u widths.
- Bay separators via `border-right` in `--lcd-ink-ghost`.
- Absent tokens render as `·` placeholder (preserve bay shape).
- Add `DW` indicator to `status-vfo` bay, reactive to `vfoOps.dualWatch`.
- Verify that DIGI-SEL / IP+ / RFG controls are reachable from sidebar (create sidebar rows if missing).

**Depends on:** #9.1 merged.

**Estimated LOC:** ~140.

### (Optional follow-up) Issue 9.4 — pb row (RIT/XIT/Δ)

Could absorb into #9.2 if LOC budget allows. Otherwise a 4th issue:
move RIT/XIT offset into `pb-A` / `pb-B` areas, add close-split Δ
readout when SPLIT is active and |Δ| < 10 kHz. ≤ 80 LOC.

---

## 10. Open questions

1. **Grid template switching vs cell hiding.**
   §3.1 chose "two distinct grid templates (12u vs 6u+6u) with
   identical row heights" over "single template, cells `visibility:hidden`".
   The former is reflow-safe by construction; the latter is simpler but
   leaves `meter-B` etc. occupying space. Confirm before #9.1 lands.

2. **Filter-viz anchoring in dual-RX.**
   The filter-viz follows the *active* VFO. Switching A↔B rescales the
   x-axis. Acceptable? Or should we render *two* filter-viz rows (one
   per VFO) in dual-RX, at half height each? Cost: 60 px of extra
   vertical, plus component duplication. Leaning: single shared,
   anchored to active. User feedback welcome.

3. **Active-dot glyph.**
   `●` vs a small TX-red underline vs a filled tag background. Each
   has different contrast behaviour. Needs a visual pass at `DIM`
   contrast.

4. **Should VFO control buttons (§9.1 move to sidebar) live in a new
   panel or expand the existing `VfoOpsPanel`?**
   Open — depends on current `RightSidebar` layout. If there's no
   dedicated VFO-ops panel, #9.1 creates one; if there is, we just
   surface additional rows.

5. **Close-split Δ threshold.**
   §3.6 proposes showing `Δ = +N kHz` only when |Δ| < 10 kHz. Real
   DX split is often ±5 kHz, but contest CW split can be ±1 kHz.
   10 kHz is a guess; should it be band-aware (wider for VHF, tighter
   for HF CW)? Deferred to post-#9.2.

6. **Mode-specific filter-viz scales — who decides?**
   §3.4 proposed mode→scale mapping in a table. This lives in
   `AmberAfScope.svelte` now. Confirm the enhancements §8.3 issue
   owns the rescale logic, not the grid scaffold (#9.1).

7. **Memory-strip cell count in dual-RX.**
   §5.2 says 4 cells in dual-RX. If telemetry is absent (backend
   doesn't report VD/TEMP/ID), do we grow memory back to 5–6 cells,
   or leave the 4-cell layout for consistency? Leaning: grow
   (capability-driven, respects P2).

8. **Sidebar width impact.**
   Moving VFO control buttons + DIGI-SEL + IP+ + RFG to the right
   sidebar may push its content above 228 px (current
   `grid-template-columns: 228px minmax(0, 1fr) 228px` in
   `LcdLayout.svelte`). Verify scroll vs. widen. Leaning: stay at
   228 px, rely on sidebar scroll (already enabled).

9. **Regression test surface.**
   Grid refactor touches the most-viewed panel in the app. What
   visual-regression capture do we add? Playwright screenshot diffs
   per capability matrix (single-RX idle, single-RX TX, dual-RX
   idle, dual-RX split) × 5 contrast presets = 20 snapshots.
   Reasonable? Or is it overkill — start with 4 and expand on first
   regression?

10. **User quote revisited.**
    The user asked for a holistic revisit that treats VFO A/B,
    indicators, and spectrum/filter as first-class equal-weight
    concerns. This document proposes that. But *"spectrum"* in the
    user's quote — does it mean AF spectrum (what we have on a
    scope-less radio), or RF spectrum (what we'd have if the radio
    had a scope, but then this skin wouldn't be selected)? The
    redesign assumes the former. Confirm with user before #9.1
    lands.

---

*End of design spike. Next step: user review → create issues #9.1 /
#9.2 / #9.3 → sequence per §8.c.*
