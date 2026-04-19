# LCD Layout Redesign v2 — Full Reboot

**Status:** Design spike — NO code changes.
**Author:** Design agent, 2026-04-19.
**Supersedes intent of:** `docs/plans/2026-04-19-lcd-layout-redesign.md` and `docs/plans/2026-04-19-lcd-layout-fixup.md` (incremental patches on top of the #844 scaffold).
**Target file (when implementation starts):** `frontend/src/components-v2/panels/lcd/AmberLcdDisplay.svelte` and siblings.
**Out of scope of this document:** no `.svelte`, `.ts`, `.css` edits. This is a written design spike only.

---

## 1. User feedback + screenshot analysis

### 1.1 Verbatim user complaint (2026-04-19)

> "LCD — плохо. layout самого индикатора — говно. Все еще перекрываются значения, все еще полно свободного места снизу. Полагаю, имеет смысл ПОЛНОСТЬЮ изменить layout самого LCD экрана. Возможно сделать несколько вариантов и выбрать лучший. Для этого нужно отдельный агент, с нужным дизайн скиллом, может дать ему картинку, и объяснить, что как.. Может из интернета найти индикаторы ЖКИ Elektraft, older ICOMs, etc..."

Translated: LCD is bad. Indicator layout is garbage. Values still overlap, bottom half is still empty. Redesign fully. Produce multiple variants.

### 1.2 Concrete defects visible in the 2026-04-19 screenshot

| # | Defect | Root cause (code-level) |
|---|--------|-------------------------|
| D1 | VFO A digits `7.143.0` visually clip into `LSB 1` / `40m` badges | DSEG7 digit advance-width is fixed; even with the 3-column subgrid (#860), when column 2 shrinks below the digit string's natural width `overflow:hidden` crops the LSD rather than reflowing. Result: digits appear to hit the badges at narrow widths. |
| D2 | VFO B `7.188.000` is permanently demoted (50% smaller, dim, 70% vertical scale meter) | `.lcd-meter-sub { transform: scaleY(0.7); opacity: 0.6 }` + `AmberFrequency size="small"`. #845 ("VFO-B peer promotion") was parked; nothing in the current grid reserves peer-sized real estate. |
| D3 | Status row clogged: 20+ tokens wrap onto 2 lines on dual-RX | Single flex-wrap row with no priority/zoning. Every capability-gated chip sits in the same bucket. |
| D4 | Filter trapezoid sits in middle; a ~40–60 px amber strip is empty below it on tall viewports | `align-content: start` on the grid + `minmax(0,120px)` cap on `filter` track. Extra vertical space is unused. |
| D5 | Contrast picker (#877) lives under the display in a separate control-strip — fine for desktop, but on mobile the init was regressed (#877 P2 comment). Not a layout problem of the LCD itself, but affects vertical budget. |
| D6 | No visible memory / recent-QSY slot (#862) or telemetry strip (#837) — despite the empty bottom half. |

### 1.3 Diagnosis

The existing grid (#844 scaffold + #860 freq-subgrid + #871 fixup) is **incrementally patched** around an outgrown mental model: "VFO A is the hero, VFO B is a footnote, indicators are one long strip, everything else is a full-width row." This worked for a single-RX IC-7300-style layout but has failed to scale for IC-7610 (dual-RX first-class) and for radios with rich status token sets (FTX-1, IC-7610 PROC/DIGI-SEL/IP+/ATU).

A full redesign needs to abandon three assumptions:

1. "Indicator row is global." — It should be **zoned per VFO**, with only truly global flags (TX, SPLIT, LOCK) at the top.
2. "VFO B is secondary." — On dual-RX radios (IC-7610, TS-990S, FTDX101) both receivers are **peers**. The active receiver is signaled by **ink-alpha / border-weight**, never by font size.
3. "Filter viz is one full-width row." — It can be **per-VFO** in a dual-cockpit, or **consolidated below meters** as a dedicated widget zone.

---

## 2. Reference research

### 2.1 Elecraft K3 / K3S / KX3

- Two-tier monochrome VFD: **upper 8-digit 7-segment (VFO A)**, **lower 13-segment dot-matrix (VFO B / text / menu)**.
- VFO A is always the "active TX" anchor. VFO B row doubles as scrolling text for menu labels.
- **Right-side icon cluster** (RIT/XIT/SPLIT/ATU/PRE/ATT/NB/NR) sits in a narrow column, not a top strip.
- **S-meter is horizontal bar above the digits**.
- Takeaway: "icon column on the right, meter on top, digits in the middle" gives digits the **widest stable real estate** and keeps the icon row from competing with digits for width.
- Source: [Elecraft K3 Owner's Manual](https://ftp.elecraft.com/K3/Manuals%20Downloads/E740107%20K3%20Owner's%20man%20D10.pdf), [K3S Programmer's Reference](https://ftp.elecraft.com/KX2/Manuals%20Downloads/K3S&K3&KX3&KX2%20Pgmrs%20Ref,%20G5.pdf).

### 2.2 Icom IC-756PRO / IC-756PROIII / IC-746PRO

- **TFT color** (not true amber LCD — the "amber" is our skin convention), but the PRO layout is the visual vocabulary the user expects.
- Upper half: **spectrum scope (±12.5/25/50/100 kHz)**; lower half: VFO digits, dual frequency readout, mode, filter width, multi-meter.
- Status icons are grouped into **top-left (RX path: PRE/ATT/AGC)**, **top-right (mode+filter)**, **bottom (notch/NR/NB/TBW)**. Zoning, not a single strip.
- Dual-watch/sub-receiver shows VFO B as a **smaller line below VFO A** but same digit style — demotion is by size, not by crop.
- Source: [IC-756PRO Instruction Manual](https://www.qrzcq.com/pub/RADIO_MANUALS/ICOM/ICOM--IC-756ProII-user-manual.pdf), [IC-746PRO LCD image](https://www.universal-radio.com/catalog/hamhf/0074lcd.html).

### 2.3 Icom IC-7300

- Single 4.3" TFT. **Top 60% = spectrum + waterfall**; bottom 40% = digits, mode, filter, S-meter bar, indicators zoned along outer edges.
- Indicators clustered into **"RX front-end" (top-left)** and **"DSP" (bottom-right)**; mode/filter always right of digits.
- No dual-RX — single VFO is the only hero.
- Takeaway: 60/40 vertical split works when a spectrum widget exists. Our analog is the AF scope.

### 2.4 Kenwood TS-990S

- **Dual-display** hardware: 7" main + 3.5" sub. The sub is dedicated to VFO B.
- Main shows band scope, waterfall, dual frequency readouts, S-meter, RIT/XIT.
- Sub shows **VFO B freq + AF spectrum + filter shape** — effectively the widget our `AmberAfScope` is modeled on.
- Takeaway: the AS-990S treats dual-RX as **two cockpits side-by-side**, each with its own digits + meter + scope. This is the reference for "Variant B — Dual Cockpit" below.
- Source: [TS-990S Dual Display](https://www.kenwood.com/sg/com/amateur/ts-990s/dual_display.html), [TS-990S brochure](https://www.kenwood.com/usa/com/support/pdf/TS-990S.pdf).

### 2.5 Yaesu FTDX101D / MP

- 7" TFT with user-selectable layout: MAIN only, MAIN/SUB stacked, MAIN/SUB side-by-side (two sub-modes).
- Dual independent scopes (one per receiver), 3DSS + waterfall.
- Takeaway: explicit **layout presets** let the operator choose cockpit shape. If we expose a small set of presets, we don't have to pick a single winner.
- Source: [FTDX101D Operation Manual](https://www.manualslib.com/manual/1600745/Yaesu-Ftdx101d.html).

### 2.6 Vintage bonus — Icom IC-781 / Yaesu FT-1000MP

- Large segmented VFDs with **generous whitespace** around digits. Indicators were **ghost-etched** into the bezel, lighting up only when active — hence the "token-cascade alpha ghost/inactive/active" metaphor we already use.
- Takeaway: our `--lcd-alpha-ghost` idea is correct; the variants just need to deploy it more aggressively so the bottom half isn't blank, it's **ghost-etched labels waiting to light up**.

---

## 3. Three variants

Terminology:
- **Cell** = CSS grid area.
- **Zone** = a named region that may contain multiple cells.
- ASCII wireframes use 12 columns × rows, `·` = empty (ghost-etched), `█` = active ink, `▒` = inactive ink.

### 3.1 Variant A — **"Elecraft Column"** (icons on the right rail)

**Premise:** push all capability-gated tokens into a narrow right-rail column; digits + scope get a wide left column. Solves D1 (digit collision — digits never compete with badges for horizontal room) and D3 (status row is vertical, scrolling-tolerant).

#### Single-RX wireframe

```
┌────────────────────────────────────────────────┬──────────┐
│ [TX]  [SPLIT]  [LOCK]            CLOCK 14:32  │ MODE LSB │ ← row 1 global
├────────────────────────────────────────────────┼──────────┤
│                                                │ FILT 2.4 │
│   A   7 . 1 4 3 . 0 0 0   Hz                   │ BAND 40m │
│                                                │          │
│                                                │ PRE IPO  │
│                                                │ ATT ·    │
├────────────────────────────────────────────────┤ ATU ·    │
│  S ▓▓▓▓▓▓░░░░░   +20dB                  [S]   │ NB  ·    │
├────────────────────────────────────────────────┤ NR  ·    │
│                                                │ NOTCH·   │
│  ╱‾‾‾‾‾‾‾‾╲   AF SCOPE + FILTER SHAPE          │ ANF ·    │
│ ╱          ╲  IF-shift · PBT · contour · notch │ AGC MID  │
│                                                │ RFG 255  │
│                                                │ SQL ·    │
│                                                │ RIT ·    │
│                                                │ VOX ·    │
└────────────────────────────────────────────────┴──────────┘
```

#### Dual-RX wireframe

```
┌────────────────────────────────────────────────┬──────────┐
│ [TX]  [SPLIT A→B]  [LOCK]        CLOCK 14:32  │ MODE LSB │
├────────────────────────────────────────────────┼──────────┤
│  ►A   7 . 1 4 3 . 0 0 0   Hz   40m  LSB 1     │ FILT 2.4 │
│   B   7 . 1 8 8 . 0 0 0   Hz   40m  LSB       │ BAND 40m │
├────────────────────────────────────────────────┤          │
│  Sa ▓▓▓▓▓▓░░░░  S9+20                  [S]   │ PRE / ATT│
│  Sb ▓▓░░░░░░░░  S3                            │ NB / NR  │
├────────────────────────────────────────────────┤ NOTCH/ANF│
│                                                │ AGC MID  │
│  AF SCOPE (active RX) + FILTER SHAPE            │ RFG/SQL  │
│                                                │ RIT/VOX  │
└────────────────────────────────────────────────┴──────────┘
```

#### CSS grid pseudocode

```css
.lcd-screen {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140px;
  grid-template-rows:
    28px                /* global-ind */
    auto                /* vfo-stack (A, B stacked; B collapses on single-RX) */
    minmax(48px, 72px)  /* meter-stack */
    minmax(0, 1fr);     /* scope (fills remaining height — kills D4 empty strip) */
  grid-template-areas:
    "global-ind  right-rail"
    "vfo-stack   right-rail"
    "meter-stack right-rail"
    "scope       right-rail";
}
```

**Rationale / trade-offs:**
- ✅ Solves D1 completely: digits own column 1, zero badges in their row.
- ✅ Solves D4: scope cell is `1fr` — absorbs all extra height.
- ✅ Solves D3: right rail wraps indicators vertically, each gets a fixed slot.
- ⚠️ Visually unfamiliar to Icom users — "Icom operators expect mode/filter *next to* digits, not in a rail."
- ⚠️ Right rail takes 140 px that could go to the scope.
- ⚠️ VFO B still stacked under VFO A (peer-by-alpha, not peer-by-position). Only half-fixes D2.

**Files affected:** `AmberLcdDisplay.svelte` (grid rewrite), new `AmberRightRail.svelte` (extracts all status chips), `AmberVfoLine.svelte` (shared single-line freq+band+mode component used by both A and B). Delete the flex `.lcd-ind-row`.

---

### 3.2 Variant B — **"Dual Cockpit"** (two-column, TS-990S-style)

**Premise:** on dual-RX, split the screen into two **equal columns**, each a complete cockpit: freq, meter, mode/filter/band badges, per-VFO indicators (NB, NR, NOTCH, ANF). Global indicators (TX, SPLIT, LOCK, ATU, VOX, PROC) go top. Scope spans both columns at bottom. On single-RX, column B collapses and column A stretches full-width.

#### Single-RX wireframe

```
┌────────────────────────────────────────────────────────────┐
│ [TX] [VOX] [PROC 5] [ATU] [SPLIT] [LOCK]        14:32      │ ← global
├────────────────────────────────────────────────────────────┤
│  ►A   7 . 1 4 3 . 0 0 0   Hz                               │
│                                         40m   LSB 2.4     │
├────────────────────────────────────────────────────────────┤
│  S ▓▓▓▓▓▓░░░░░░  S9+20                         [S|PO|SWR] │
├────────────────────────────────────────────────────────────┤
│  PRE AMP1   ATT ·   NB 3   NR 5   NOTCH ·   ANF ·          │ ← per-RX row
│  AGC MID    RFG 255  SQL ·   RIT +120 Hz                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   AF SCOPE  + FILTER SHAPE + PBT + NOTCH + CONTOUR         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### Dual-RX wireframe

```
┌────────────────────────────────────────────────────────────┐
│ [TX] [VOX] [PROC 5] [ATU] [SPLIT A→B] [LOCK]    14:32      │
├──────────────────────────────┬─────────────────────────────┤
│  ►A  7 . 1 4 3 . 0 0 0       │   B  7 . 1 8 8 . 0 0 0      │
│      40m  LSB 2.4            │      40m  LSB 2.4           │
├──────────────────────────────┼─────────────────────────────┤
│  Sa ▓▓▓▓▓░░░░  +20     [S]  │   Sb ▓▓░░░░░  S3      [S]   │
├──────────────────────────────┼─────────────────────────────┤
│ PRE AMP1  ATT ·  NB 3        │  PRE ·  ATT 6  NB ·         │
│ NR 5  NOTCH·  ANF·  AGC MID  │  NR ·  NOTCH·  ANF·  AGC F  │
├──────────────────────────────┴─────────────────────────────┤
│                                                            │
│        AF SCOPE (active RX) — spans full width             │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### CSS grid pseudocode

```css
.lcd-screen {
  display: grid;
  grid-template-columns: minmax(0, 1fr);          /* single-RX */
  grid-template-rows:
    28px        /* global */
    auto        /* vfo */
    44px        /* meter */
    auto        /* per-rx indicators */
    minmax(0, 1fr); /* scope */
  grid-template-areas:
    "global"
    "vfo-a"
    "meter-a"
    "ind-a"
    "scope";
}
.lcd-screen.dual {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  grid-template-areas:
    "global   global"
    "vfo-a    vfo-b"
    "meter-a  meter-b"
    "ind-a    ind-b"
    "scope    scope";
}
```

**Rationale / trade-offs:**
- ✅ Solves D2 cleanly: VFO B is a true peer. Active receiver indicated by border-weight and the `►` glyph plus `--lcd-alpha-active` on the header; inactive by `--lcd-alpha-inactive`. Font size is identical.
- ✅ Solves D3: per-VFO chips go into their own column; global chips get their own small row — no more 20-item flex-wrap.
- ✅ Solves D4: scope gets `1fr` and spans full width.
- ✅ Solves D1: each column is `minmax(0,1fr)`, digits have their own cell, mode/band go **below** digits (not beside), zero overlap risk.
- ✅ Solves D5/D6 indirectly: extracting per-RX chips makes room for memory/telemetry above the scope (new optional `aux` row).
- ⚠️ On narrow viewports (<720 px) two cockpits collide. Needs a container query to collapse to stacked-single at `< ~640 px`.
- ⚠️ Per-RX indicators duplicate some chips that are actually radio-global on IC-7610 (e.g. ATU is global, NB is per-RX). Need an **indicator taxonomy** (see §7 Q1).
- ⚠️ Scope is still single (active RX only). Dual-scope is a later enhancement.

**Files affected:** `AmberLcdDisplay.svelte` (grid), new `AmberCockpit.svelte` (reusable freq+meter+ind block, takes `which: 'A'|'B'`), new `AmberGlobalInd.svelte` (top strip), new `AmberPerVfoInd.svelte`. Retire `.lcd-vfo-sub`, `.lcd-meter-sub`. `AmberAfScope` unchanged.

---

### 3.3 Variant C — **"Modern Icom"** (scope dominant, 60/40 split)

**Premise:** IC-7300 / FTDX101 style. Top 55–60% of the LCD is a **big AF scope + filter+PBT+notch visualization** (the skin's whole reason for existing on radios without an RF scope). Bottom 40–45% is a data strip: VFO A+B digits, meters, zoned indicators. Mirror the IC-7300's visual hierarchy.

#### Single-RX wireframe

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│                                                            │
│          AF SCOPE + WATERFALL TRACE + FILTER SHAPE         │
│          (IF shift marker · notch marker · PBT)             │
│                                                            │
│                                                            │
├────────────────────────────────────────────────────────────┤
│ [TX] [VOX] [PROC] [ATU] [SPLIT] [LOCK]   [PRE][ATT][AGC]  │ ← indicator strip
├────────────────────────────────────────────────────────────┤
│ ►A  7 . 1 4 3 . 0 0 0                   40m  LSB  2.4 kHz │
├────────────────────────────────────────────────────────────┤
│  S ▓▓▓▓▓▓░░░░░░  +20         [S|PO|SWR|ALC|COMP]          │
├────────────────────────────────────────────────────────────┤
│ NB3  NR5  NOTCH·  ANF·  CONT·  RFG255  SQL·  RIT+120      │ ← DSP row
└────────────────────────────────────────────────────────────┘
```

#### Dual-RX wireframe

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│          AF SCOPE (active RX, large)                       │
│          — caller can toggle split-scope later             │
│                                                            │
├────────────────────────────────────────────────────────────┤
│ [TX] [VOX] [PROC] [ATU] [SPLIT A→B] [LOCK]  [PRE][ATT][AGC]│
├──────────────────────────────┬─────────────────────────────┤
│ ►A  7 . 1 4 3 . 0 0 0        │  B  7 . 1 8 8 . 0 0 0       │
│     40m  LSB  2.4            │     40m  LSB  2.4           │
├──────────────────────────────┼─────────────────────────────┤
│ Sa ▓▓▓▓▓░░░░  +20      [S]  │ Sb ▓▓░░░░░░  S3        [S]  │
├──────────────────────────────┴─────────────────────────────┤
│ NB3  NR5  NOTCH·  ANF·  CONT·  RFG255  SQL·  RIT+120      │
└────────────────────────────────────────────────────────────┘
```

#### CSS grid pseudocode

```css
.lcd-screen {
  display: grid;
  grid-template-rows:
    minmax(0, 1.2fr)   /* scope dominates */
    28px                /* global + front-end indicator strip */
    52px                /* vfo line(s) */
    44px                /* meter */
    28px;               /* dsp strip */
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas:
    "scope"
    "ind-global"
    "vfo"
    "meter"
    "ind-dsp";
}
.lcd-screen.dual {
  /* vfo + meter rows become 2-col */
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  grid-template-areas:
    "scope      scope"
    "ind-global ind-global"
    "vfo-a      vfo-b"
    "meter-a    meter-b"
    "ind-dsp    ind-dsp";
}
```

**Rationale / trade-offs:**
- ✅ Solves D4 hardest: scope is the **largest** cell; bottom-empty-space problem inverts (bottom is now packed).
- ✅ Solves D1: VFO row is its own row with mode+band pushed to the right edge via `justify-content: space-between` and the digits in the flex-grow child — same pattern as #860 but with more horizontal breathing room because there's nothing stacked vertically alongside.
- ✅ Solves D3: two indicator strips (global + DSP) with clear semantic zones.
- ⚠️ Only half-fixes D2: VFO B is a peer only on dual-RX (good), but on single-RX VFO B row simply doesn't exist, so no regression.
- ⚠️ On short viewports (<480 px tall, e.g. mobile landscape), the 1.2fr scope steals digit readability. Needs a **scope-collapse breakpoint**.
- ⚠️ The user complaint was "bottom half empty" — this variant puts everything at the bottom. If the scope is not available (no `hasAudioFft()`), the scope cell becomes a big empty amber field. Needs a **scope fallback** (ghost-etched graticule + "AUDIO FFT UNAVAILABLE" label in ghost alpha).

**Files affected:** `AmberLcdDisplay.svelte` (grid rewrite), `AmberAfScope.svelte` (`compact={false}` default, add `fallback` slot), new `AmberIndicatorStrip.svelte` with `zone: 'global' | 'dsp' | 'frontend'` prop. `AmberFrequency` unchanged.

---

## 4. Recommendation

**Recommend Variant B ("Dual Cockpit") with a Variant-C scope fallback posture.**

### Why B wins

1. **Dual-RX is first-class** for the project's reference radio (IC-7610) and for TS-990S / FTDX101 class targets. Variant A and C both leave VFO B in a degraded slot; only B treats it as a peer, directly resolving the user's D2 complaint.
2. **Indicator zoning per-VFO** is the most honest mapping of the state model: `main.nbActive`, `sub.nbActive`, `main.agcMode`, `sub.agcMode` are already separate fields in `radioState`. The current single strip collapses that into one, losing information; Variant B restores it visually.
3. **Capability cascade stays clean.** Each cockpit renders only chips supported by its receiver's capabilities. A single-RX radio shows exactly one cockpit — full width, no wasted columns, D4 solved by `scope: 1fr`. A dual-RX radio shows two — no reflow of peer cells (same win the #844 plan §9.1 P2 was after, but achieved by peer columns instead of fixed row heights).
4. **Svelte 5 + token cascade friendly.** `AmberCockpit` is a single reusable component that takes `which: 'A' | 'B'` and `active: boolean`; the token `--lcd-alpha-{active,inactive,ghost}` already drives every ink decision — B just deploys it at cockpit granularity instead of element granularity.
5. **ESLint `no-restricted-imports` unaffected.** `AmberCockpit` lives in `panels/lcd/`, receives all state via props (from the existing `toXxxProps` adapters), and imports nothing from `$lib/transport` or `$lib/audio/audio-manager`. Layering preserved.
6. **Variant-C ideas survive as knobs, not a fork.** We can give the scope `1fr` on the row-track and let it absorb bottom space (picks up C's biggest win), without committing to a scope-dominated layout that breaks when FFT is unavailable.

### Why not A

The right-rail idea is architecturally clean, but it (a) **costs 140 px of horizontal budget** on every viewport, including narrow mobile, and (b) **looks un-Icom**. The skin's purpose is "radio-console-feeling fallback"; the rail makes it feel like a debug HUD.

### Why not C (as headline)

C solves the empty-bottom complaint by inverting it, but it **penalizes radios without `hasAudioFft()`** (a scope-shaped empty). It's also a single-hero layout — VFO B is still compact. Borrow its "scope = 1fr" row idea into B; don't adopt C wholesale.

---

## 5. Atomic implementation plan

Each issue is a single atomic PR, ≤3 files, ≤200 LOC. Sequence is **strict**; each depends on the previous one landing first.

### PR1 — `refactor(#NEW1): extract AmberCockpit component (behavior-preserving)`

- New file: `frontend/src/components-v2/panels/lcd/AmberCockpit.svelte`
- Accepts props: `which: 'A' | 'B'`, `active: boolean`, `freqHz`, `mode`, `filter`, `band`, `sValue`, `meterSource`, `txActive`, `indicators: {nb, nr, notch, anf, pre, att, agcLabel, rfgActive, sqlActive, ritOffset|null}`.
- Renders existing VFO-A visuals at first; the `which === 'B' && !active` branch matches today's compact sub.
- `AmberLcdDisplay.svelte` swaps its VFO A + VFO B blocks to `<AmberCockpit>` twice but uses the same old grid-template-areas.
- **Gate:** zero visual regression on single-RX; dual-RX looks identical to today.
- Files: 2 (new component + display). LOC: ~180.

### PR2 — `feat(#NEW2): dual-cockpit grid — VFO B as peer (replaces scope of parked #845)`

- `AmberLcdDisplay.svelte`: replace the single-column / dual-column grid-templates with the Variant B grid from §3.2. VFO B cockpit now uses `active={activeVfo === 'B'}` and renders at full size with alpha-dimmed tokens when inactive.
- Delete `.lcd-vfo-sub`, `.lcd-meter-sub` CSS (the `scaleY(0.7)` + `opacity: 0.6` demotion).
- Adjust `AmberCockpit` to render identical sizing regardless of `active`; only ink alpha changes.
- **Gate:** single-RX unchanged (cockpit = col-span-all); dual-RX both VFOs same size; screenshot in both `active === 'A'` and `active === 'SUB'` states.
- Files: 2. LOC: ~150 net (mostly deletion).
- **Makes parked #845 obsolete.** Close #845 with a pointer.

### PR3 — `refactor(#NEW3): per-VFO indicator zone + global indicator strip`

- New file: `AmberIndStrip.svelte` with prop `zone: 'global' | 'perVfo'` and `tokens: IndToken[]`.
- `AmberCockpit` uses `<AmberIndStrip zone="perVfo">` in its own row.
- `AmberLcdDisplay` uses `<AmberIndStrip zone="global">` at the top row (TX/VOX/PROC/ATU/SPLIT/LOCK only).
- Indicator taxonomy table lives at the top of `AmberIndStrip.svelte` as a typed const (answer to §7 Q1).
- **Gate:** token total count unchanged; visual wrap-lines reduced from 2 → 1 per zone at 1280 px viewport.
- Files: 3. LOC: ~180.
- **Makes the legacy `.lcd-ind-row` flex-wrap obsolete.** Delete it in this PR.

### PR4 — `feat(#NEW4): scope track fills remaining height (absorbs D4 empty amber)`

- `AmberLcdDisplay.svelte` grid `grid-template-rows` last track `minmax(0, 1fr)` for the `scope` area (currently `minmax(0, 120px)`).
- `AmberAfScope.svelte`: add `compact={false}` default path that draws graticule + filter trapezoid scaled to full cell.
- Ghost fallback: when `!hasAudioFft()`, render `AmberFilterGhost.svelte` (graticule + filter shape only, no live data, label "AUDIO FFT UNAVAILABLE" at `--lcd-alpha-ghost`).
- **Gate:** on tall viewports (>800 px) no amber strip below the scope; on short viewports (<500 px) the scope still gets ≥80 px.
- Files: 3. LOC: ~160.
- **Addresses #862's memory-slot premise too:** with the scope now `1fr`, a future memory row can be inserted above the scope without shoving content down.

### PR5 — `feat(#NEW5): mobile container-query collapse + telemetry reserve`

- Container query on `.lcd-screen`: `@container (max-width: 640px)` flips dual-cockpit grid back to stacked single-cockpit with VFO B as a compact one-liner (explicit, not `scaleY(0.7)`).
- Reserve a slim `aux` row (height `0` by default, `auto` when `hasCapability('telemetry')`, addressing #837) between `ind-dsp`/`meter` and `scope`.
- **Gate:** mobile viewport (375 × 667) no horizontal scroll; dual-RX degrades to single-column stacked gracefully.
- Files: 1–2. LOC: ~100.
- **Partially resolves #862 / #837** — they become trivial follow-ups (fill the reserved `aux` row).

### Obsolete vs survivable queue items

| Issue | Status after this plan | Reason |
|-------|------------------------|-------|
| #845 (VFO-B peer promotion) | **Obsolete — close** | PR2 delivers the promotion by grid redesign. |
| #846 (specific indicator reorg, if same) | Likely **obsolete** | Subsumed by PR3 zoning. Confirm with user in Q3. |
| #862 (memory / recent-QSY slot) | **Survivable** | PR5 reserves the `aux` row; #862 fills it. |
| #837 (telemetry VD/TEMP/ID) | **Survivable** | Same `aux` row mechanism. |
| #835 (filter-viz wide mode) | **Obsolete** | Scope is always wide now. Close. |
| #877 (contrast in control-strip) | **Unchanged** | Lives below LCD in a separate strip; this redesign is inside the LCD only. |

---

## 6. Migration from current state

Current state, in file terms:
- `#844` scaffolded the grid (`grid-template-areas: indicators / meter-a / vfo-a / pb / filter`).
- `#860` added a 3-col subgrid inside `.lcd-vfo-main` to stop digit/badge collision (partial fix; D1 remnants visible).
- `#871` capped the `filter` track at `minmax(0, 120px)` + `align-content: start` (creates D4 empty amber).
- `#877` moved contrast control **outside** the LCD into the sidebar control-strip.

### Migration steps

1. **PR1 — Cockpit extraction.** Keep the current grid. Just reorganize VFO A + B into a shared component. No visual change. Safe, easy to revert.
2. **PR2 — Grid swap.** The `indicators / meter-a / vfo-a / pb / filter` template is replaced by Variant B's `global / vfo-? / meter-? / ind-? / scope`. The `pb` row is absorbed into each cockpit's own RIT offset display (cockpits own their RIT because RIT is per-receiver on IC-7610).
3. **PR3 — Indicator split.** The legacy `.lcd-ind-row` flex strip becomes `AmberIndStrip zone="global"` (6–8 chips max) + two per-cockpit `AmberIndStrip zone="perVfo"` (8–12 chips each, depending on capabilities).
4. **PR4 — Scope grows.** The `minmax(0, 120px)` filter track becomes `minmax(0, 1fr)` scope track. The `align-content: start` stays, but with a `1fr` track there's no residual space to align. D4 resolved.
5. **PR5 — Responsive + reserves.** Adds container query and `aux` row. No change to desktop visuals unless telemetry/memory is enabled.

### Rollback plan

Each PR is independently revertable. PR1–5 all live in `AmberLcdDisplay.svelte` + sibling components under `panels/lcd/`; no upstream wiring (`state-adapter`, `runtime`, stores) changes, so reverting is pure UI.

### Risks

- **Snapshot tests** on VFO rendering (if any exist under `frontend/tests/`) will break at PR1 if they assert on DOM structure. Audit first.
- **#877 mobile contrast regression** is orthogonal — do not try to fix it inside this plan.
- **Capability flag coverage** — per-VFO indicator zoning assumes `radioState.main.nbActive` and `radioState.sub.nbActive` both exist. For radios where NB is global (not per-RX), the same value would render in both cockpits — potentially confusing. Mitigate with the indicator taxonomy const (PR3).

---

## 7. Open questions

1. **Indicator taxonomy — global vs per-VFO.** For each of TX, VOX, PROC, ATT, PRE, DIGI-SEL, IP+, ATU, NB, NR, NOTCH, ANF, AGC, RFG, SQL, RIT, SPLIT, LOCK, DATA, CONT — is it **radio-global** (one value) or **per-receiver** (two values)? Proposal: global = {TX, VOX, PROC, ATU, SPLIT, LOCK}; per-RX = everything else. Confirm for IC-7610.
2. **VFO B SPLIT direction.** When `splitActive`, do we show `SPLIT A→B` (direction of TX) as a global chip, or mark VFO B's cockpit with a "TX" tag? Proposal: global chip `SPLIT`, plus a small `TX` marker on whichever cockpit is the TX VFO.
3. **Is #846 the same as our PR3 indicator zoning?** If yes, close #846 as duplicate. If no, describe what #846 wanted that PR3 misses.
4. **Scope fallback text.** When `!hasAudioFft()`, what do we show? Options: (a) ghost graticule + "AUDIO FFT UNAVAILABLE"; (b) ghost graticule + filter-shape trapezoid only, no label; (c) collapse the scope row to `0`, let indicators breathe vertically. Proposal: (b) — filter shape is still useful without FFT data.
5. **Container query breakpoint.** 640 px was picked by eyeball. Is there an existing breakpoint token in the codebase (`skins/` / `lib/ui/tokens`) we should reuse?
6. **RIT ownership.** Current code treats RIT as a single global state (`ritXit.ritActive`). On IC-7610 RIT is per-receiver (at least for main vs sub dial offset). Does `radioState.main.rit` / `radioState.sub.rit` exist in the state shape, or is RIT still modeled as global? If global, we keep RIT in the global strip; if per-RX, each cockpit owns it. This changes PR2/PR3 scope.
7. **Meter B source.** Today VFO B meter is hard-coded to `S` (S-meter). Should the B cockpit gain its own PO/SWR/ALC cycle button during split-TX? Proposal: no — during TX, the TX-VFO cockpit's meter switches to PO/SWR/ALC; the other cockpit shows S or blanks.
8. **Filter readout placement.** Variant B wireframe puts filter width as `LSB 2.4` inside the badge row. The existing `toFilterProps` adapter has more (IF-shift, contour). Does the user want a **textual filter readout** in the cockpit (e.g. "SHIFT -120 Hz"), or is the scope's visual notch/shift marker enough? Proposal: scope-only.
9. **`compact` prop on AmberAfScope.** Currently forced `compact`. After PR4, `compact={false}` by default. Do we keep `compact` as a prop for any other caller? Grep shows only `AmberLcdDisplay` uses it — safe to drop.
10. **Skin-wide audit.** This plan changes `amber-lcd` only. `desktop-v2` and `mobile` skins reuse `AmberCockpit` / `AmberIndStrip`? Proposal: yes, but that's a separate spike — flag for a follow-up plan if the user wants consistency.

---

## Sources (references)

- [Elecraft K3 Owner's Manual (PDF)](https://ftp.elecraft.com/K3/Manuals%20Downloads/E740107%20K3%20Owner's%20man%20D10.pdf)
- [Elecraft K3S/K3/KX3/KX2 Programmer's Reference Rev. G5 (PDF)](https://ftp.elecraft.com/KX2/Manuals%20Downloads/K3S&K3&KX3&KX2%20Pgmrs%20Ref,%20G5.pdf)
- [K3S Transceiver — Elecraft product page](https://elecraft.com/products/k3s-transceiver)
- [Icom IC-756ProII Instruction Manual (PDF)](https://www.qrzcq.com/pub/RADIO_MANUALS/ICOM/ICOM--IC-756ProII-user-manual.pdf)
- [Icom IC-746PRO LCD photo — Universal Radio](https://www.universal-radio.com/catalog/hamhf/0074lcd.html)
- [Icom IC-756 screen — Universal Radio](https://www.universal-radio.com/catalog/hamhf/756scrn.html)
- [Kenwood TS-990S dual display](https://www.kenwood.com/sg/com/amateur/ts-990s/dual_display.html)
- [Kenwood TS-990S brochure (PDF)](https://www.kenwood.com/usa/com/support/pdf/TS-990S.pdf)
- [Yaesu FTDX101D Operation Manual — ManualsLib](https://www.manualslib.com/manual/1600745/Yaesu-Ftdx101d.html)
- [Yaesu FTDX-101D — DX Engineering](https://www.dxengineering.com/parts/ysu-ftdx-101d)
