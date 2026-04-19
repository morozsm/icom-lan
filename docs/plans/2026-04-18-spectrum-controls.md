# Spectrum Toolbar Ergonomics — Design Plan

**Date:** 2026-04-18
**Scope:** Desktop skin (`RadioLayout.svelte` center column). Mobile spectrum is #812 — out of scope.
**Owner files:**
- `frontend/src/components/spectrum/SpectrumToolbar.svelte`
- `frontend/src/components/spectrum/spectrum-toolbar-logic.ts`
- `frontend/src/components-v2/layout/VfoHeader.svelte`

---

## 1. Problem statement

The current desktop spectrum toolbar packs ~16 controls into a single 28 px dense row at 10 px monospace. There is no visual grouping beyond thin 1 px separators at 16 px height, no color differentiation between "display setting" vs "radio state" vs "action", and cryptic 3-char labels (`CTR`, `FIX`, `S-C`, `S-F`, `SPD`, `FST`) that are unreadable to new operators and still slow for pros. The VFO header's bridge column (132 px, center) has vertical headroom and — on wide dual layouts — the MAIN/SUB VfoPanels themselves have horizontal real estate that is currently unused above the frequency display.

**Design goal:** reduce toolbar cognitive load from "wall of beige tokens" to four immediately-recognisable groups, while surfacing purely informational state (current receiver, DUAL on/off, current SPAN value) to the VFO header where it belongs.

---

## 2. Inventory — every control on the spectrum toolbar

| # | Control | Type | Purpose | Frequency | Affects |
|---|---------|------|---------|-----------|---------|
| 1 | `STEP ◀ / value / ▶` | stepper + value | Tuning step cycle (shared with VFO encoder) | **tuning (constant)** | radio state (indirect — mouse-wheel on VFO) |
| 2 | `AVG` | toggle | Enable/disable spectrum averaging (client-side) | view (set-and-forget) | display only |
| 3 | `PEAK` | toggle | Enable/disable peak-hold overlay (client-side) | view (set-and-forget) | display only |
| 4 | `BRT − / value / +` | stepper | Waterfall intensity ±30 | view (rarely) | display only (client) |
| 5 | `REF − / value / +` | stepper | Scope reference level ±30 dB (radio setting) | tuning (sometimes) | radio scope data |
| 6 | `CTR` | radio-segment | Scope mode 0 — CENTER (±span around VFO) | ops | radio scope mode |
| 7 | `FIX` | radio-segment | Scope mode 1 — FIXED (fixed lower/upper edges) | ops | radio scope mode |
| 8 | `S-C` | radio-segment | Scope mode 2 — SCROLL-CENTER | rare | radio scope mode |
| 9 | `S-F` | radio-segment | Scope mode 3 — SCROLL-FIXED | rare | radio scope mode |
| 10 | `EDGE 1..4` | radio-segment (conditional) | Edge preset for FIX / S-F only | ops (when in FIX) | radio scope edges |
| 11 | `SPAN ◀ / value / ▶` | stepper (conditional) | ±2.5k..±500k, CTR/S-C only | **tuning (often)** | radio scope data |
| 12 | `SPD ◀ / value / ▶` | stepper | Sweep speed FST / MID / SLO | ops (rare) | radio scope data |
| 13 | `HOLD` | toggle | Freeze waterfall | rare | radio scope data |
| 14 | `DUAL` | toggle | Dual-scope on/off (MAIN + SUB simultaneously) | set-and-forget | radio scope state |
| 15 | `MAIN / SUB` | momentary | Switch which receiver drives scope | ops | radio scope state |
| 16 | `⚙` | button-popover | Scope settings popover (ATT, VBW, expand) | rare | radio scope data |
| 17 | `Classic / Thermal / Gray` | dropdown | Waterfall palette | set-and-forget | display only |
| 18 | `BANDS` | toggle | Band-plan overlay | set-and-forget | display only |
| 19 | `▾` (layers) | button-popover | Layer/region picker + EiBi launcher | set-and-forget | display only |
| 20 | `⛶ / ✕` | momentary | Toggle fullscreen spectrum | ops | layout |

**Decoding the cryptic labels** (Icom-standard terms from IC-7610 manual, not inventable):

- **CTR** = *Center* mode. VFO stays centred, span expands symmetrically.
- **FIX** = *Fixed* mode. Fixed lower/upper edges, one of four EDGE presets.
- **S-C** = *Scroll-Center*. Centred, but scope scrolls when tuning outside the window rather than re-centering each tick.
- **S-F** = *Scroll-Fixed*. Like FIX, but when tuning past the upper edge the window shifts forward (auto-advancing fixed window).
- **SPD / FST / MID / SLO** = sweep speed. FST/MID/SLO already expanded. **SPD → SPEED** is a trivial clarity win.
- **BRT** = *Brightness* (waterfall palette gain).
- **REF** = *Reference level*, in dB, for the scope amplitude axis.

These Icom abbreviations are muscle-memory for existing operators, so we keep them as primary labels but expand via tooltip, and rename **SPD → SPEED** (same width at this size — 5 chars fits in 34 px).

---

## 3. Categories

Six logical groups, ordered by frequency of use (left-to-right on the toolbar):

| Group | Controls | Tint |
|-------|----------|------|
| **A. Tuning** | `STEP` | none (leftmost, highest-priority, needs visual weight) |
| **B. Scope mode** | `CTR FIX S-C S-F`, `EDGE` (conditional) | `rgba(0,212,255,0.03)` cyan wash — "radio state" |
| **C. Scope data** | `SPAN`, `SPEED`, `HOLD`, `REF` | `rgba(0,212,255,0.03)` cyan wash — "radio state" (same as B) |
| **D. Display** | `AVG`, `PEAK`, `BRT`, palette dropdown, `BANDS+▾` | `rgba(255,255,255,0.02)` neutral wash — "client-only" |
| **E. Settings** | `⚙` | none |
| **F. Actions** | fullscreen | none (rightmost, pushed by spacer) |

**Why this split:** the most important ergonomic signal is *does this change the radio or only my view?* Cyan wash for scope-state (B+C) matches the existing accent for `.active` buttons and tells the operator "this affects the rig". Neutral wash for display (D) says "harmless, experiment freely". Tuning (A) gets no wash because it already has the `auto-step` amber badge providing visual weight, and placing it leftmost with breathing room reinforces its always-active status.

**Why merge B and C visually** rather than separating them: the distinction between "pick a mode" and "tune the mode's parameters" is real, but on a 28 px row two cyan blocks separated by a 1 px divider communicates "this cluster is scope state" more cleanly than three alternating tints.

---

## 4. Proposed toolbar layout

```
┌───────────────────────────────────────────────── SPECTRUM TOOLBAR 28px ───────────────────────────────────────────────────┐
│  [◀ STEP 1kHz ▶]║  CTR  FIX  S-C  S-F  │ EDGE 1 2 3 4  │ [◀ SPAN ±25k ▶] [◀ SPEED MID ▶] HOLD │ REF − 0 +  ║ AVG  PEAK │ BRT − 0 + │ Classic▾ │ BANDS ▾ ║ ⚙ ════════════════spacer═══════ ⛶ │
│   ~110px        ║   ↑ group B: SCOPE MODE ↑    ║   ↑ group C: SCOPE DATA ↑              ║  ↑ group D: DISPLAY ↑        ║                                         │
│   Tuning                 cyan wash rgba(0,212,255,.03)                                       neutral wash rgba(255,255,255,.02)                                   │
│                                                                                                                                                                   │
│   ║ = 2px group boundary (separator becomes 2px + 6px margin)                                                                                                     │
│   │ = 1px in-group sub-separator (4px margin — keeps EDGE visually adjacent to scope-mode without merging)                                                        │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Pixel budget at 1440 px viewport** (center column ≈ 960 px with sidebars):

| Segment | Width |
|---------|------:|
| STEP triplet | 110 |
| group separator | 8 |
| scope-mode quad (CTR FIX S-C S-F) | 128 |
| sub-sep + EDGE 1..4 (conditional, 92 px when shown) | 96 |
| group separator | 8 |
| SPAN triplet (conditional) | 110 |
| SPEED triplet | 110 |
| HOLD | 42 |
| sub-sep | 6 |
| REF triplet | 88 |
| group separator | 8 |
| AVG PEAK | 76 |
| sub-sep | 6 |
| BRT triplet | 88 |
| sub-sep | 6 |
| palette dropdown | 78 |
| sub-sep | 6 |
| BANDS+▾ | 68 |
| group separator | 8 |
| ⚙ | 22 |
| flex spacer | rest |
| ⛶ | 22 |
| **TOTAL (non-conditional)** | **~910 px** |

At 1280 px center column (~800 px), ~110 px overflows — handled in §7.

---

## 5. Move-out plan

### 5a. Move to VFO header

| Control | Why | New home |
|---------|-----|----------|
| `DUAL` toggle | Pure scope visibility state; belongs alongside SPLIT / DUAL-WATCH which already live in VFO bridge | `VfoHeader.svelte` bridge stack (below `VfoOps`, above SPLIT row) |
| `MAIN/SUB` scope receiver selector | Informational + switches which VFO *drives the scope*; redundant with the visual ACTIVE/STANDBY pill already on each VfoPanel | `VfoHeader.svelte` bridge stack — as a tiny two-pill indicator **"SCOPE: ▣ MAIN  ▢ SUB"** clickable |
| Current **SPAN label** (read-only mirror) | Operators reading the VFO header already look there for bandwidth context | VfoPanel badge row, right side of main VFO header only (not both) |

### 5b. Move to scope settings ⚙ popover

- Palette dropdown (`Classic / Thermal / Gray`) — set-and-forget, no business being in the hot row.
- `BANDS` layer dropdown region selector (`US / R1 / R2 / R3`) — already inside the popover conceptually; keep the BANDS toggle on the toolbar but move region chooser into ⚙.
- `HOLD` — stays on toolbar (it's operational, though rare).

### 5c. Keyboard shortcuts only (power users, no UI)

- `[` / `]` — decrement/increment SPAN.
- `-` / `+` — decrement/increment REF level (`+` chosen over `=` to avoid colliding with the existing VFO-equalize shortcut in the runtime keyboard profile).
- `Shift+H` — toggle HOLD.
- `Shift+F` — toggle fast scroll (FST).
- `Shift+D` — toggle DUAL scope.
These are registered through `KeyboardHandler.svelte`; document in `shortcut-hints.ts`.

### 5d. Stays on toolbar

Everything in §3 groups A, B, C (minus DUAL + MAIN/SUB), D, E, F.

---

## 6. VFO header impact

`VfoHeader.svelte` currently has three regions: `main`, `bridge` (132 px center column), `sub`. The bridge stack is vertical: `VfoOps` → gap → SPLIT row → SPEAK. We have ~60 px of vertical slack in the bridge between `VfoOps` and the SPLIT row at current `--vfo-bridge-width: 132px`.

**Add a new `scope-status` stack item between `VfoOps` and the SPLIT row** (only when `hasCapability('scope')`):

```
┌─ bridge 132px ─┐
│   VfoOps       │  ← unchanged
│                │
│ ┌─ SCOPE ─┐    │  ← NEW block
│ │[▣M][ S] │    │     two micro-pills, 42×18 each, click = switchReceiver
│ │  DUAL   │    │     smaller second row: DUAL toggle (48×16) with cyan accent when on
│ │±25k MID │    │     read-only SPAN + SPEED digest, 7px monospace
│ └─────────┘    │
│                │
│ SPLIT ...      │  ← unchanged
│ SPEAK          │  ← unchanged
└────────────────┘
```

Visual spec for the new block:
- Border-top: `1px solid var(--v2-vfo-header-border)` — matches SPLIT row.
- Title row: 7 px uppercase "SCOPE", `letter-spacing: 0.1em`, color `var(--v2-text-muted)` — matches SPLIT title.
- Pills: 18 px tall, cyan-bordered when active (reuses `.toolbar-btn.active` tokens).
- In single-receiver mode (no `hasDualReceiver()`): only the DUAL row is hidden; the SPAN/SPEED digest still shows. MAIN/SUB pills are hidden (nothing to switch).
- Width: fits existing 132 px bridge. No change to `--vfo-bridge-width`.

**Responsive consideration:** the existing `@media (max-width: 1024px)` collapses the bridge onto its own row and flips `.vfo-ops` to horizontal. The new block inherits this — in collapsed mode it lives inline with VfoOps on the horizontal row. That's acceptable because on narrow screens there's less space pressure on the spectrum toolbar anyway.

**Does not break dual-receiver:** no grid-area changes. Nothing is added to MAIN/SUB VfoPanels. The SPAN-label badge proposed in §5a is deferred to a later issue — flagged in §10 as open question.

---

## 7. Visual spec

| Property | Value |
|----------|-------|
| Toolbar height | **32 px** (↑ from 28) — one extra vertical pixel pays for better separator visibility and 11 px font |
| Base font | `11 px` Roboto Mono (↑ from 10) — numeric readability tested; 10 px is below comfortable small-cap threshold |
| Group separator | `2px` wide, `var(--panel-border)`, full 20 px height, `margin: 0 6px` |
| In-group sub-separator | `1px` wide, `var(--panel-border)` alpha 0.5, 14 px height, `margin: 0 4px` |
| Group B+C wash | `rgba(0, 212, 255, 0.03)` — applied to group container `background` |
| Group D wash | `rgba(255, 255, 255, 0.02)` |
| Active button (unchanged) | cyan `#00d4ff` text + `rgba(0,212,255,0.1)` bg + `rgba(0,212,255,0.3)` border |
| Label vs value weight | labels `500`, values `600` — replaces current uniform `400` for scanning |
| Min touch target | 22×22 (unchanged — desktop only) |
| Button gap within group | 3 px (↑ from 2 — breathes at 11 px font) |

---

## 8. Responsive behavior

At **≤1280 px** center column (`container-query`: `@container spectrum (max-width: 800px)` on toolbar container):

**Overflow priority (last to collapse first — i.e. stays visible longest):**
1. STEP (never collapses)
2. Scope-mode quad (never collapses — it IS the scope)
3. SPAN (never collapses — it's *the* primary scope tuning knob)
4. fullscreen (stays — one-click escape)
5. ⚙ (stays — accesses overflow)
6. AVG / PEAK (collapse into ⚙ popover first)
7. BRT (collapse into ⚙)
8. REF (collapse into ⚙)
9. SPEED, HOLD (collapse into ⚙)
10. EDGE (never visible outside FIX/S-F, so not a budget issue)
11. Palette dropdown (collapse into ⚙)
12. BANDS+▾ (collapse into ⚙ — dropdown itself is already a popover, becomes a submenu)

**Strategy:** rather than a `More…` button, use the existing `⚙` popover as the overflow target. Add a `overflowed: boolean[]` CSS-driven state; the popover shows duplicates of whatever the container-query CSS has hidden. This keeps logic simple: no JS measurement.

At **≤1024 px** (tablet), the whole spectrum panel already rearranges — out of scope here, covered by #812.

---

## 9. Interaction notes

**Tooltips** (`title=` on hover, shown after 500 ms by browser):

| Label | Tooltip text |
|-------|--------------|
| STEP | "Tuning step — click cycles up, right-click cycles down. A = auto-step follows band" |
| AVG | "Spectrum averaging (client-side display only)" |
| PEAK | "Peak hold overlay (client-side display only)" |
| BRT | "Waterfall brightness (palette gain, display only)" |
| REF | "Scope reference level in dB — radio setting" |
| CTR | "Scope mode: CENTER — VFO centered in window" |
| FIX | "Scope mode: FIXED edges — choose EDGE preset 1–4" |
| S-C | "Scope mode: SCROLL-CENTER — window scrolls instead of recentering" |
| S-F | "Scope mode: SCROLL-FIXED — fixed window auto-advances" |
| EDGE 1..4 | "Edge preset N — configure in scope settings ⚙" |
| SPAN | "Scope span ±freq (CTR and S-C modes only)" |
| SPEED | "Scope sweep speed: FST fastest / MID / SLO slowest" |
| HOLD | "Freeze scope waterfall — release to resume" |
| ⚙ | "Scope settings (ATT, VBW, expand, overflowed controls)" |
| ⛶ | "Toggle fullscreen spectrum (F)" |

**Do not** expand the on-button labels themselves. `CTR/FIX/S-C/S-F` are reproducing the Icom front-panel labels and operators with any prior IC-7xxx experience expect them. Changing `SPD → SPEED` is the only label edit (4 chars saved elsewhere buys it).

**Cursor affordance:** stepper buttons `◀ ▶` get `cursor: ew-resize` on hover to signal "scrubable" (future: add `<wheel>` on stepper-container to cycle).

---

## 10. Atomic implementation issues

Each ≤3 files, ≤200 LOC, TDD (pure logic in `*-logic.ts`, test first).

### Issue #A — Toolbar grouping, separators, visual spec
- Files: `SpectrumToolbar.svelte`, `spectrum-toolbar-logic.ts` (label constants), `__tests__/spectrum-toolbar-logic.test.ts`
- Scope: wrap groups in `.toolbar-group-b` / `.toolbar-group-c` / `.toolbar-group-d` containers with the wash backgrounds; 2 px vs 1 px separator classes; height bump 28 → 32; font 10 → 11; `SPD → SPEED` label; weight 500/600 split.
- No new behavior. Snapshot test only.
- LOC: ~80.

### Issue #B — Tooltips + keyboard shortcuts
- Files: `SpectrumToolbar.svelte`, `KeyboardHandler.svelte`, `shortcut-hints.ts`
- Scope: add `title=` to every button per §9 table; register `[`, `]`, `-`, `=`, `H`, `D`, `F` in KeyboardHandler; update shortcut-hints registry.
- Tests: `keyboard-map.ts` pure-fn tests for new bindings.
- LOC: ~120.

### Issue #C — Move DUAL + MAIN/SUB + SPAN/SPEED digest to VfoHeader bridge
- Files: `VfoHeader.svelte`, `SpectrumToolbar.svelte` (remove DUAL + MAIN/SUB block), `__tests__/vfo-header.test.ts`
- Scope: add `ScopeStatus` subcomponent (inline or new file — inline keeps file count at 2); wire `scopeControls` from `radio.current` into VfoHeader via new prop; remove moved blocks from toolbar; adjust responsive CSS for ≤1024 px bridge-horizontal mode.
- **Gotcha:** VfoHeader currently doesn't know about `scopeControls`. Pass as prop from `RadioLayout.svelte` (NOT imported directly — preserves `components-v2/layout/` purity per CLAUDE.md frontend layering rule).
- LOC: ~180.

### Issue #D (stretch — optional) — Overflow via ⚙ popover at narrow widths
- Files: `SpectrumToolbar.svelte`, `ScopeSettingsPopover.svelte`
- Scope: container-query CSS hides overflow-eligible groups below 800 px; popover renders the same controls conditionally.
- LOC: ~150.
- Defer if #A–#C land cleanly and 1440 px+ feedback is positive; narrow widths are a smaller segment of usage.

**Recommended order:** A → B → C → (D). Each ships independently; A is pure visual and reviewable fastest, C is highest-value but depends on A's group container markup.

---

## 11. Open questions

1. **SPAN-label mirror on VfoPanel (§5a last row).** Does adding a "±25k" pill to the main VFO's badge row clutter the frequency display, or is it useful passive readout? Recommend A/B with two radio operators before committing. Out of scope for the three atomic issues above.
2. **Palette dropdown — keep on toolbar or move to ⚙?** Operators who switch palettes do so maybe once per session. Moving it saves 78 px but some users visually reach for it. Default: **keep on toolbar for now**; revisit if #A user-tests reveal nobody uses it.
3. **EDGE preset editing.** Currently EDGE 1..4 is select-only; configuration of each edge's low/high lives in ⚙ popover (presumed — to verify). If not, that's a separate issue.
4. **DUAL scope semantics when MAIN/SUB is in VFO bridge.** In current toolbar, `MAIN/SUB` button is a *scope-source* selector. After move, is there a risk of confusion with the *active-receiver* ACTIVE/STANDBY already shown on each VfoPanel? Consider labelling the bridge pills explicitly `SCOPE SRC` to disambiguate.
5. **Container-query support.** We rely on `@container` (baseline in modern Chromium/Firefox/Safari). Confirm the spectrum panel has `container-type: inline-size` set or add it. If project targets pre-2023 browsers, fall back to JS measurement — unlikely given Svelte 5 baseline.
6. **Mobile skin.** #812 owns mobile. This plan's VFO-bridge-move (Issue #C) MUST be verified against `MobileRadioLayout.svelte` so the bridge doesn't explode in the mobile layout — add that as a regression-check line-item when #C lands.

---

## 12. Non-goals

- No changes to waterfall renderer or canvas logic.
- No new commands in `commands/` or CI-V protocol work.
- No new abstractions beyond the `ScopeStatus` bridge subcomponent.
- No behavioural changes to what each button does — every control maps 1:1 to current handlers.
- Color scheme tokens stay as-is; only adding two new alpha washes.
