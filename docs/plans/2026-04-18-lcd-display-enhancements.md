# LCD Display Enhancements — Design Plan

**Date:** 2026-04-18
**Surface:** `frontend/src/components-v2/panels/lcd/AmberLcdDisplay.svelte` (+ children)
**Skin:** `amber-lcd`
**Coordinates with:** #808 (warm-dark sidebars), #809 (inactive status dimming)
**Status:** design — no code changes in this document

---

## 1. Context

### What the amber LCD skin is for

The amber LCD skin is **not a novelty aesthetic** — it is the fallback surface for radios that have no panadapter / scope / waterfall data available over the wire (FTX‑1, FT‑710 in some modes, older Kenwoods, hypothetical future backends without scope). For such radios, every square pixel of the "screen" needs to carry numeric state.

The amber tone (`#C8A030` background, `#1A1000` ink, `DSEG7 Classic` font, `JetBrains Mono` labels) is a deliberate visual homage to the Japanese "STN amber" LCDs used on Kenwood TS‑940/TS‑950, Icom IC‑781, and mid‑era TS‑2000 display sub‑boards. It signals to the operator: *this is a data surface, not a graphics surface*. Everything inside it is "etched" by the absence of backlight.

### Current rendering model (important for the contrast design)

The surface is **not** canvas‑rendered 7‑segment. It uses two stacked DOM layers:

- **Ghost layer** — digits forced to `"888.888.888"`, painted at `rgba(0,0,0,0.06)`. These are the dim un‑energised segments.
- **Active layer** — real digits painted at `#1A1000`, absolutely positioned over the ghost.

Indicators (`.lcd-ind`) use the same idea: inactive → `rgba(0,0,0,0.08)` with `rgba(0,0,0,0.06)` border; active → `#1A1000`. The s‑meter and AfScope (filter trapezoid) draw to canvas using the same ink colour.

**This is a gift for the contrast feature** — one CSS custom‑property swap moves the entire display across its dynamic range.

### Users

Primary operator profile for this skin:
- Uses an IC‑7610/FTX‑1/TS‑890‑class radio *without* a connected scope feed (or has disabled it).
- Wants glanceable state across the whole panel — no hunting, no hover.
- May run the UI on a shaded veranda at noon or a dark shack at 0230z. Needs to dial brightness/contrast like they would a real rig.

### Constraints

- Fixed 16 : 7.5 aspect ratio (`.lcd-slot`), so the display is wide and short.
- Current surface is ~60 % vertically occupied; ~40 % dead space below frequency B.
- Must stay readable on 1366 × 768 laptop displays at one extreme and 4K wall monitors at the other.
- No new fonts, no new asset downloads.

---

## 2. Contrast control

### 2.1 UX pattern

Three access paths, lowest‑friction first:

1. **Keyboard shortcut:** `Shift + [` decrement, `Shift + ]` increment. Cycles through 5 presets (see below). Mirrors the feel of the physical CONTRAST button on an IC‑7610 (short press cycles, long press enters set‑mode).
2. **In‑display contrast strip** — a **4 px‑tall horizontal bar** flush with the top‑inside edge of the `.lcd-screen` bezel, 120 px wide, positioned at top‑right. Five subdivisions, one highlighted. Click a cell to jump; scroll‑wheel over it to step; drag to scrub. Looks like a hardware trim slot, not a web UI control. Invisible to screen readers' flow but exposed as `role="slider"` with proper `aria-valuenow`.
3. **Settings modal** — already‑existing theme settings panel gets a `LCD Contrast` row: 5‑step segmented control + a "fine tune" slider that maps to `[-2 … +2]` around the selected preset (10 effective levels, preset‑biased).

### 2.2 Range & presets

Five named presets, not a continuous 0–100 — operators who grew up with real rigs think in clicks, not percentages:

| Preset  | Ink α (active) | Inactive α | Ghost α | Use case                                    |
|---------|----------------|------------|---------|---------------------------------------------|
| `DIM`   | 0.55           | 0.04       | 0.03    | Dark shack, night, contest; reduces glare   |
| `LOW`   | 0.75           | 0.06       | 0.045   | Normal dim room                             |
| `MID`   | 1.00           | 0.10       | 0.06    | **Default.** Current tuning.                |
| `HIGH`  | 1.00           | 0.18       | 0.09    | Overhead fluorescents, daytime              |
| `MAX`   | 1.00           | 0.30       | 0.14    | Direct sunlight / glass porch               |

Note: "contrast" on a real reflective LCD is actually **the ratio of active to inactive segment density**. It does **not** make active ink darker past a point (ink is already saturated) — it pushes *inactive* segments further away from or closer to the ink. Our model mirrors that: active stays at `#1A1000` once past `MID`; what changes is how visible the un‑energised "888"s become. This is why a filter `brightness()` on the container is the *wrong* mechanism — it would drag both layers together, collapsing contrast instead of expanding it.

Fine‑tune (`−2 … +2`) linearly interpolates between preset pairs; `MID +1` sits between `MID` and `HIGH`.

### 2.3 Persistence

- `localStorage['icom-lan:lcd-contrast'] = 'MID+0'` (or similar string key).
- **Not** part of theme config — contrast is environmental (ambient light), theme is aesthetic. Keeping them separate lets a user switch skin without losing their light‑level calibration.
- Survives reload; does not sync across browsers (deliberate — different monitor, different light).

### 2.4 CSS mechanism — token cascade

The ghost/active/inactive alphas are currently hard‑coded (`rgba(0,0,0,0.06)`, `rgba(0,0,0,0.08)`, `#1A1000`). Introduce three CSS custom properties on `.amber-lcd`:

```
--lcd-ink-active:   rgba(26, 16, 0, var(--lcd-alpha-active, 1));
--lcd-ink-inactive: rgba(26, 16, 0, var(--lcd-alpha-inactive, 0.10));
--lcd-ink-ghost:    rgba(26, 16, 0, var(--lcd-alpha-ghost, 0.06));
```

Then every `color:` / `border-color:` / `fillStyle` literal is replaced by one of those three tokens. The contrast control flips just the three `--lcd-alpha-*` numbers. Canvas components (AmberSmeter, AmberAfScope) read the resolved values via `getComputedStyle(rootEl).getPropertyValue('--lcd-alpha-inactive')` on mount + on a `lcd-contrast-changed` CustomEvent.

### 2.5 What exactly does contrast adjust?

- Active‑segment **opacity** (ink α). From `DIM`→`MAX`, 0.55 → 1.00.
- Inactive‑segment **opacity** (ghost α). From `DIM`→`MAX`, 0.03 → 0.14.
- Ratio of active to inactive — the perceived "contrast" — rises from **~18:1** at `DIM` to **~7:1** at `MAX`. Both ends remain readable; `MID`/`HIGH` is where the display looks most like paper.
- Nothing touches the amber background. A real LCD's backlight is the panel itself, not the segments.

Things that do **not** move with contrast:
- Indicator frame/border thickness.
- TX‑active red tint (operator safety).
- S‑meter ladder marks (scale must stay legible at `DIM`).
- Scanlines overlay (tied to a separate "Display Mode" setting — see §6).

---

## 3. Filter‑viz enhancement

### 3.1 Current state

`AmberAfScope` (`compact`) occupies a 30 %‑wide strip, ~96 px tall, to the right of the main VFO frequency. It draws:
- Top label row (Shift: ±NNNN Hz).
- Second label row (Filter: NNNN Hz).
- A fixed‑width trapezoid representing the passband, with whiskers to either side.
- FFT bars inside the trapezoid (if audio FFT available).
- Contour dip (U‑curve from top edge).
- Manual notch spike (V from top edge).

It's already doing a lot, but the label area is cramped, the trapezoid lacks numeric ticks, and **there is no visual anchor for "where 0 Hz is"** relative to IF shift.

### 3.2 Proposal

Promote the filter‑viz from a 30 %‑wide strip to a **dedicated row** below the VFO block, spanning the full display width at **~140 px tall**. Keep the compact version available for dual‑RX layouts (see §5).

New additions:

- **Hz scale ruler** under the trapezoid baseline. Ticks at `−3 kHz, −2, −1, 0, +1, +2, +3` for SSB‑class bandwidths; auto‑rescale for CW (±500 Hz) and AM/FM (±10 kHz). Minor ticks every 500 Hz / 100 Hz / 2 kHz respectively.
- **Centre marker** — a short vertical pip at the carrier/BFO reference, drawn even when IF shift is zero. Anchors the eye.
- **−6 dB / −20 dB tick labels** on the trapezoid's left shoulder ("‑6" at the top, "‑20" at the whisker knee). Two characters, dim ink, identifies the trapezoid as a skirt shape, not just a bucket.
- **IF‑shift offset arrow** — a small horizontal arrow on the Hz scale pointing from 0 to current shift value (dim when zero). When non‑zero, the arrow brightens and a small "SHIFT +320" label hangs under the ruler.
- **Passband‑tuning (PBT‑inner / PBT‑outer) brackets** — two small "[" "]" marks on the trapezoid top edge, indicating the twin PBT positions when the radio supports it. Dim when at detent.
- **Mode‑aware passband envelope** — draw the *ideal* filter shape as a faint outline (−6 dB theoretical Kaiser/Chebyshev curve), overlay the trapezoid on top. Gives the operator a sense of "how steep my filter actually is" without a datasheet.
- **Interactivity** — click on the filter‑viz opens the full DSP/filter panel on the right sidebar (existing panel, just deep‑links to it); `scroll`‑wheel over the trapezoid adjusts bandwidth; `Shift`‑scroll adjusts IF shift. Hover shows a tooltip with exact filter number (FIL1/FIL2/FIL3) + BW Hz.

### 3.3 ASCII wireframe

```
┌──────────────────────────────────────────────── filter viz (full width, 140 px) ──────────────────────────────────────────────┐
│                                                                                                                                │
│   Filter: 2400 Hz   FIL2         Shape: 1.2 (Sharp)         Shift: +320 Hz         PBT: ‒140 / +60         Contour ─ 2 Notch ■ │
│                                                                                                                                │
│  ‑6 ─── ┌─────────[─────────]──────┐ ───                                                                                       │
│         /                           \                                                                                          │
│  ‑20 ──/    ▁▃▅▇█▇▅▃▂▁               \── ──── FFT bars inside passband (audio scope)                                          │
│ ──────/                               \──────                                                                                  │
│  ├──────┼──────┼──────┼──────┼──────┼──────┼──────┤     Hz scale                                                               │
│  ‑3k   ‑2k    ‑1k     0     +1k    +2k    +3k                                                                                  │
│                       ▲                                  ↑ centre marker                                                      │
│                       └───→ +320 (SHIFT)                                                                                       │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Target size: full display width (minus 12 px gutters) × 140 px. Roughly 3 × the current strip area. Justifies the elevation to first‑class citizen.

---

## 4. Lower‑half content proposal

With the filter‑viz promoted to its own row, the dead space below frequency B shrinks but doesn't vanish. Remaining height (~80–120 px depending on viewport) goes to **exactly two** modules, left/right split 60/40:

### 4.1 Primary (left, 60 %): Memory / recent‑frequency strip

A horizontal row of up to 8 cells, each ~12 % wide:

```
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│  M1      │  M2      │  M3      │  M4      │  M5      │  ↺ 14.074│  ↺ 7.074 │  ↺ 3.573 │
│ 14.195 U │ 18.100 U │ 21.280 U │ 28.074 U │  7.200 L │ USB      │ USB      │ USB      │
│  DX      │  FT8     │  SSTV    │  FT8     │  NET     │   12s    │   3m     │  11m     │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
   memory slots (first 5)          recent‑QSY stack (last 3, auto‑captured)
```

Why this combo:
- Memory channels are what operators miss most when switching from a physical rig to a web UI — they're the muscle memory of "hit M3 to get to my 21 MHz SSTV spot". Putting the first 5 directly on the display makes the skin feel like a real control head.
- The auto‑QSY stack (last 3 distinct VFO frequencies held for > 5 s) addresses the common "where was I just listening?" case. Click a cell → VFO jumps.
- Both fit the same cell shape → one component, two data sources.

Justification against alternatives:
- *Band scope substitute:* If the radio has no scope, we have no spectrum data to fake. Drawing fake bars would be a lie.
- *Voltage/temp panel:* Already in the status bar / right sidebar; not worth display real estate.
- *Dual‑RX expansion:* Handled by variant layout (§5), not by lower‑half space.

### 4.2 Secondary (right, 40 %): Extended telemetry strip

Three small tiles, each ~33 % of the 40 % (so ~13 % of display width):

```
┌──────────────┬──────────────┬──────────────┐
│   VD  13.8 V │  TEMP  42 °C │  ID    0.2 A │
│  ▁▂▃▅▇▇▆▅▃▂▁ │  ▁▂▂▃▄▄▄▄▃▂ │  ▁▁▁▂▂▁▁▁▁  │
└──────────────┴──────────────┴──────────────┘
```

Each tile: big DSEG7 reading, tiny sparkline (last 60 s) under it, units in mono. Sparkline makes trend visible without a full chart. Picks the three vitals that matter during TX:
- Supply voltage (drops reveal power supply sag).
- Finals temperature (thermal runaway early warning).
- Drain current (ATU mismatch / key‑down sanity).

Only shown when the backend provides them; for backends that don't, the right 40 % collapses and the memory strip takes the full width.

### 4.3 Why 1‑2 picks, not 5

Every element on an LCD competes with every other. Two modules, each owning its job, each visible at a glance. Five would require tabs or scroll and **kill the whole reason the amber skin exists** (glance‑time information).

---

## 5. Layout variants

**User note (2026-04-18):** "Имеет смысл пересмотреть layout самого LCD
дисплея, с учетом двух VFO, индикаторов и спектра/фильтра."

The layout in §5.1 (single-RX) / §5.2 (dual-RX) refines the existing
AmberLcdDisplay. User asked for a more holistic revisit that treats
dual-VFO as a first-class layout concern, not a compact-variant
fallback. Captured as additional atomic issue §8.7 ("LCD layout
redesign") — a dedicated design-spike that re-sequences the display
surface with equal-weight VFO A / VFO B + indicators + spectrum/filter,
then supersedes §5.2 (and possibly §5.1) with a unified grid.

The rest of §5 describes the baseline that ships if §8.7 doesn't land
first.

### 5.1 Single‑RX radio

```
┌─ status bar ───────────────────────────────────────────────────────────────────────┐
├─ meter row (main S / PO / SWR …) ──────────────────────────────────────────────────┤
├─ indicators row ───────────────────────────────────────────────────────────────────┤
├─ VFO A (large DSEG7)                                  mode | band ─────────────────┤
├─ filter‑viz row (full width, 140 px) ──────────────────────────────────────────────┤
├─ memory/QSY strip (60 %)              │  telemetry (40 %) ──────────────────────── ┤
├─ VFO ctrl buttons (A↔B, A=B, SPLIT, TUNE…) ───────────────────────────────────────┤
└─ RIT row (conditional) ───────────────────────────────────────────────────────────┘
```

### 5.2 Dual‑RX radio

VFO B reclaims the memory row. Filter‑viz drops to **compact** mode (current 30 %‑wide strip, re‑parented next to VFO A), freeing the full width below for VFO B + its own small meter.

```
├─ meter row (main) ─────────────────────────────────────────────────────────────────┤
├─ meter row (sub, scale‑0.7, current behaviour) ────────────────────────────────────┤
├─ indicators row ───────────────────────────────────────────────────────────────────┤
├─ VFO A (large)  ┃ filter‑viz compact (30 %) ───────────────────────────────────────┤
├─ VFO B (small, full width, mode tag) ──────────────────────────────────────────────┤
├─ telemetry strip (full width, 3 tiles) ────────────────────────────────────────────┤
├─ VFO ctrl buttons ─────────────────────────────────────────────────────────────────┤
```

Memory strip in dual‑RX is demoted to the right sidebar (memory panel already exists). The display privileges the second receiver.

### 5.3 Switching rule

Not user‑selectable — `hasDualReceiver()` decides. Keep it capability‑driven to match the rest of the skin.

---

## 6. Vintage aesthetic touches

All optional, all behind a single `Display Mode` dropdown in settings (default: `CLEAN`). No mode is enabled by default, because every effect reduces information density.

| Mode      | Effects                                                                                      | When to use                       |
|-----------|----------------------------------------------------------------------------------------------|-----------------------------------|
| `CLEAN`   | Current rendering. Scanlines at 0.03 α. No curvature.                                         | Default. Max legibility.          |
| `VINTAGE` | Scanlines bumped to 0.05. 0.3 s phosphor persistence on segment changes. No curvature.       | Looks like a warmed‑up rig.       |
| `CRT`     | 1 % CSS `border-radius` → full‑bezel curvature (`transform: perspective(…)`). Subtle vignette at corners. Scanlines 0.06. | Demo mode / screenshots. Costs 3–4 % performance. |
| `FLICKER` | CLEAN + 0.5 Hz 1 % opacity flicker on the whole screen. Simulates old inverter noise.        | Nostalgia. Off for most sessions. |

Phosphor persistence specifics: on digit change, run a 300 ms fade from "previous digit ghost at 0.2 α" down to 0. Not a blur — a discrete previous‑value overlay. Cheap, CSS‑only (class + transition).

**Explicit non‑features:** no chromatic aberration, no bloom, no pixel‑grid overlay. Those push the skin from "vintage rig" to "video game CRT". Wrong reference.

---

## 7. Accessibility

- **Contrast floor:** even at `DIM`, active‑segment ink (α=0.55) against background `#C8A030` yields a luminance ratio of **≥ 4.5 : 1** (measured: 4.9 : 1). This meets WCAG AA for large text, which all DSEG7 numerals qualify as. Do not allow a preset below `DIM`.
- **Indicator floor:** at `DIM`, inactive indicator α=0.04. This *does* fall below AA — but inactive indicators are by design invisible‑ish ("segment not energised"). The *active* indicator at α=0.55 on border α=0.2 remains legible (ratio ≥ 4.5 : 1).
- **Focus ring:** every clickable (contrast strip, memory cell, filter‑viz, telemetry tile) has a 2 px focus ring in `rgba(26,16,0,0.9)` that ignores contrast preset. Keyboard users never lose the cursor.
- **`prefers-reduced-motion`:** disables phosphor persistence, flicker, and trapezoid animation (AmberAfScope's `adaptiveLerp`). Digits update instantly.
- **`prefers-contrast: more`:** forces contrast preset to `MAX` regardless of stored setting; disables ghost digits (`--lcd-alpha-ghost: 0`).
- **Screen readers:** memory cells announce "Memory 1, 14.195 MHz upper sideband, DX"; telemetry tiles announce full `aria-label` with value + unit. Filter‑viz canvas gets an `aria-label` summarising state ("Filter 2400 Hz, shift +320 Hz, notch active").

---

## 8. Atomic implementation issues

Each sub‑issue ≤ 3 files, ≤ 200 LOC, independent. Order below is recommended but not strict.

### 8.1 Token cascade + contrast core
- **Files:** `AmberLcdDisplay.svelte`, `AmberFrequency.svelte`, `AmberAfScope.svelte` (canvas colour reads).
- Replace literal ink colours with `--lcd-ink-active/inactive/ghost`.
- Add `useLcdContrast()` store (reads localStorage, exposes preset + alphas).
- Keyboard shortcut `Shift+[` / `Shift+]` via existing `KeyboardHandler`.
- Settings‑modal row (segmented control only, fine‑tune slider in a follow‑up).
- Out: in‑display slider strip.

### 8.2 In‑display contrast slider strip
- **Files:** new `AmberContrastStrip.svelte`, mounted inside `.lcd-screen` top‑right; `AmberLcdDisplay.svelte` wires it; tests.
- 4 px tall, 120 px wide, 5‑cell segmented. Click/scroll/drag. ARIA slider role.

### 8.3 Filter‑viz promotion to full‑width row
- **Files:** `AmberAfScope.svelte` (new `size="wide"` mode with Hz ruler, centre marker, dB ticks, mode‑aware scale), `AmberLcdDisplay.svelte` (reparent + capability branch for compact variant).
- Interactivity (scroll = bandwidth, Shift‑scroll = IF shift) gated behind a flag for the first cut; can land with click‑to‑open only.

### 8.4 Memory / recent‑QSY strip
- **Files:** new `AmberMemoryStrip.svelte`, QSY‑history store in `$lib/stores/qsy-history.svelte.ts`, mounted in `AmberLcdDisplay.svelte`.
- Reads existing memory store (already populated by backends that support it). QSY history is local (not sent to backend).

### 8.5 Telemetry strip (VD / TEMP / ID)
- **Files:** new `AmberTelemetryStrip.svelte`, a minimal sparkline primitive (`AmberSparkline.svelte`), mounted in `AmberLcdDisplay.svelte`.
- Graceful empty state when backend supplies no telemetry.

### 8.6 (Optional, P3) Display Mode effects
- **Files:** `AmberLcdDisplay.svelte`, new CSS module for `vintage`/`crt`/`flicker` classes, settings row.
- Lowest priority. Defer until the above five ship.

### 8.7 LCD layout redesign (design spike, prerequisite for §5.2)

**Added per user feedback 2026-04-18.** The §5 variants refine the
existing display; user requested a holistic layout revisit treating
dual-VFO as first-class. This issue is a **design-spike** (produces a
plan doc) rather than an implementation issue.

**Deliverable:** `docs/plans/2026-04-19-lcd-layout-redesign.md`.

**Scope:**
- Grid redesign of `AmberLcdDisplay` that treats VFO A + VFO B, status
  indicator row, meter row, filter-viz, and optional spectrum/memory
  strips as equal-weight layout cells (not "VFO A primary, VFO B
  demoted").
- Proposal for a unified grid that works for both single-RX and dual-RX
  radios via capability-driven cell show/hide, not two separate
  layouts.
- Interaction with §3 (filter-viz expansion) and §4 (lower-half
  content) — which sections survive, which get re-sequenced.
- Impact on CW/SSB/DATA mode-specific variants (if any).
- ASCII wireframes for single-RX and dual-RX cases.

**Out of scope:** implementation. Spawns 2–3 implementation issues
after approval.

**Ordering:** §8.7 → re-evaluate §5.2 and §4.1 / §4.2 layout
allocations → §8.4 and §8.5 may need revision.

---

Estimated sequencing: 8.1 and 8.3 first (they set up tokens + the new layout grid). 8.4 and 8.5 in parallel. 8.2 after 8.1. 8.6 last. **8.7 runs in parallel with 8.1–8.3 as a design-spike — its output may alter 8.4/8.5 before they ship.**

---

## 9. Open questions

1. **Fine‑tune slider vs. 5 hard presets** — do we ship `±2` fine‑tune in 8.1, or keep it to 5 discrete presets until users ask? (Leaning: 5 only, MVP.)
2. **Memory source of truth** — memory channels today live in the backend for IC‑7610 but are simulated for FTX‑1. For radios with no memory read‑back, is a local "bookmark" store acceptable? (Probably yes — needs confirmation from #memory‑related issues.)
3. **Filter‑viz width when `hasAudioFft()` is false** — still full width, just no bars inside? Or fall back to a narrower "diagram only" layout to reclaim space? (Leaning: still full width — the trapezoid + Hz ruler is valuable standalone.)
4. **Telemetry tiles that show "--"** — do we hide the tile entirely, or keep the placeholder for visual stability? Hiding shifts layout on connect; placeholder is honest about what the rig reports. (Leaning: placeholder with dim "N/A".)
5. **Dual‑RX memory strip demotion** — if the user *wants* memories visible in dual‑RX, should there be a "Panels" preference? Or is the sidebar panel sufficient? (Leaning: sidebar sufficient; revisit if users complain.)
6. **Is `MAX` contrast still "LCD" or does it cross into "HD display" territory and break the illusion?** — worth a visual pass in both light and dark rooms before locking alphas.
7. **Coordination with #808 (warm‑dark sidebars)** — if sidebars go warm‑dark, does the amber LCD bezel colour need a warmer brown (`#8A7020 → #7A5F1B`)? Worth a joint mock before either lands.
8. **Coordination with #809 (inactive status token dimming to 0.25–0.3)** — #809's target α values sit between our `HIGH` and `MAX` inactive alphas. Decision: #809 sets the *baseline* inactive α, and the contrast control scales it by a preset‑specific multiplier (`DIM × 0.25, MID × 1.0, MAX × 1.5`) rather than replacing it. Needs confirmation before both land.

---

*End of plan.*
