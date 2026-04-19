# UI refinements — consolidated execution plan

**Date:** 2026-04-18
**Scope:** executes the 5 design spikes (#813–#817) + 9 already-created atomic issues (#804–#812) for UI refinements across Desktop, LCD, Mobile skins.
**Source plans:**
- [`2026-04-18-desktop-meters-panel.md`](./2026-04-18-desktop-meters-panel.md)
- [`2026-04-18-receiver-activation.md`](./2026-04-18-receiver-activation.md)
- [`2026-04-18-spectrum-controls.md`](./2026-04-18-spectrum-controls.md)
- [`2026-04-18-lcd-display-enhancements.md`](./2026-04-18-lcd-display-enhancements.md)
- [`2026-04-18-mobile-ia.md`](./2026-04-18-mobile-ia.md)

Approved by user 2026-04-18 with these corrections:
- **#813 meters:** `AudioSpectrumPanel` is a combined widget (AF FFT + passband + PBT + notch/contour for FTX-1). Preserve intact when moving.
- **#814 activation:** downscoped from hybrid (D) to single M/S control (B). No freq-click activation. + cross-cutting tooltip/typography audit for all buttons (new Issue E).
- **#816 LCD:** add holistic layout redesign spike (new Issue 8.7) that treats dual-VFO as first-class.

---

## 1. Full atomic issue inventory (25 issues)

### Already created (9 issues, #804–#812)
| # | Area | Title |
|---|---|---|
| #804 | Desktop | idle vs disabled for VFO ops |
| #805 | Desktop | ON/OFF → single power toggle |
| #806 | Desktop | remove BAR indicator |
| #807 | Desktop | move settings gear into StatusBar |
| #808 | LCD | warm-dark theme |
| #809 | LCD | dim inactive status tokens |
| #810 | Global | auto-collapse mode-specific panels |
| #811 | Mobile | MAIN/SUB → segmented control |
| #812 | Mobile | BRT/REF → gear menu |

### Derived from spike plans (16 new issues, IDs TBD)

**Meters panel (4):**
- M-A: `feat(ui): add MetersDockPanel with Po/SWR/ALC/S tiles` — new component, ~180 LOC
- M-B: `refactor(ui): replace bottom-dock summary cards with MetersDockPanel` — migrate combined AudioSpectrumPanel (AF FFT+passband+PBT+notch/contour) to right sidebar as collapsible, ~140 LOC
- M-C: `feat(ui): add Id/Vd/COMP tiles with capability gating` — ~120 LOC
- M-D: `feat(ui): add peak-hold + SWR/ALC fault highlighting` — ~150 LOC

**Receiver activation (5, was 4, one added):**
- Act-A: `refactor(ui): remove panel-wide click-to-activate + STANDBY/ACTIVE pill` — downscoped, ~25 LOC
- Act-B: `feat(ui): add ActiveReceiverToggle segmented control` — ~140 LOC
- Act-C: `style(ui): strengthen active/inactive VFO panel treatment` — ~50 LOC
- Act-D: `feat(ui): keyboard bindings m, Shift+M, Shift+S for active receiver` — ~80 LOC
- Act-E: `chore(ui): button discoverability audit — typography + tooltips` (NEW, cross-cutting) — ~120 LOC

**Spectrum controls (3):**
- Spec-A: `style(ui): spectrum toolbar grouping + separators + visual spec` — ~80 LOC
- Spec-B: `feat(ui): spectrum toolbar tooltips + keyboard shortcuts` — ~120 LOC
- Spec-C: `refactor(ui): move DUAL/MAIN-SUB/SPAN-SPEED digest to VfoHeader bridge` — ~180 LOC
- (Spec-D stretch — deferred)

**LCD enhancements (7):**
- LCD-8.1: `refactor(ui): LCD token cascade + contrast core` — ~150 LOC
- LCD-8.2: `feat(ui): LCD in-display contrast slider strip` — ~100 LOC
- LCD-8.3: `feat(ui): LCD filter-viz wide mode with Hz ruler + markers` — ~180 LOC
- LCD-8.4: `feat(ui): LCD memory/recent-QSY strip` — ~160 LOC
- LCD-8.5: `feat(ui): LCD telemetry strip (VD/TEMP/ID + sparkline)` — ~140 LOC
- LCD-8.6: `feat(ui): LCD Display Mode effects (scanlines, phosphor) [P3]` — ~120 LOC
- LCD-8.7: `design: LCD layout redesign with dual-VFO first-class` (NEW, design-spike) — produces `docs/plans/2026-04-19-lcd-layout-redesign.md`

**Mobile IA (5):**
- Mob-10.1: `feat(ui/mobile): chip-scroll IA + ESSENTIALS panel` — ~180 LOC
- Mob-10.2: `feat(ui/mobile): persistent guarded PTT FAB` — ~150 LOC
- Mob-10.3: `refactor(ui/mobile): MORE → SETUP (rare config only)` — ~100 LOC
- Mob-10.4: `feat(ui/mobile): promote RIT/XIT to first-class chip` — ~60 LOC
- Mob-10.5: `chore(ui/mobile): landscape PTT guard parity` — ~40 LOC

**Total: 9 existing + 16 new = 25 atomic issues.**

---

## 2. File-touch matrix (conflict analysis)

Key shared files and which issues touch them. Issues listed together **cannot run concurrently** on the same branch.

| File | Issues |
|---|---|
| `VfoHeader.svelte` | Act-B, Spec-C, #806 |
| `VfoPanel.svelte` | Act-A, Act-C, Act-E |
| `VfoOps.svelte` | Act-B, Act-E |
| `SpectrumToolbar.svelte` | Spec-A, Spec-B, Spec-C |
| `RadioLayout.svelte` | M-B, #807, Spec-C (props) |
| `StatusBar.svelte` | #805, #807 |
| `MetersDockPanel.svelte` | M-A, M-C, M-D |
| `meter-utils.ts` | M-A, M-D |
| `AmberLcdDisplay.svelte` | LCD-8.1, 8.2, 8.3, 8.4, 8.5, 8.6, #809 |
| `AmberAfScope.svelte` | LCD-8.1, 8.3 |
| `AmberFrequency.svelte` | LCD-8.1 |
| `MobileRadioLayout.svelte` | Mob-10.1–10.5, #811, #812 |
| `command-bus.ts` | Act-D |
| `keyboard-map.ts` | Act-D, Spec-B |
| `KeyboardHandler.svelte` | Spec-B |
| `CollapsiblePanel.svelte` | #810 |
| `theme/` tokens | #808, Act-C, M-C |

**Conflict hotspots:**
- `AmberLcdDisplay.svelte` — 7 LCD issues touch it → **strictly sequential** within LCD track.
- `MobileRadioLayout.svelte` — 7 mobile issues touch it → **strictly sequential** within Mobile track.
- `VfoHeader.svelte` — Act-B and Spec-C both modify props; Act-B must ship first so Spec-C reuses the prop pattern.
- `VfoPanel.svelte` — Act-A removes old affordance; Act-C polishes; Act-E adds tooltips. Order: A → C → E.
- `SpectrumToolbar.svelte` — 3 spectrum issues touch it → sequential: A → B → C.
- `StatusBar.svelte` — #805 and #807 both modify. Bundle or serialize.

---

## 3. Wave plan for parallel execution

Each wave = set of issues that can run concurrently by **different agents on different worktrees** without file-level merge conflict.

### Wave 1 — 6 parallel, independent files
| Issue | Files | Why safe |
|---|---|---|
| #807 | StatusBar, RadioLayout | isolated — moves gear |
| Act-A | VfoPanel (removal only) | removal-only, isolated |
| Spec-A | SpectrumToolbar, spectrum-toolbar-logic | isolated in toolbar |
| LCD-8.1 | AmberLcdDisplay, AmberFrequency, AmberAfScope | foundation for all LCD |
| Mob-10.1 | MobileRadioLayout, new EssentialsPanel, new chip-bar | foundation for all Mobile |
| M-A | MetersDockPanel (new), meter-utils | new file, isolated |

Prerequisite: #807 before #805 (StatusBar ordering), optional. Or bundle.

### Wave 2 — 6 parallel, after Wave 1
| Issue | Depends on | Files |
|---|---|---|
| #805 | #807 | StatusBar (sequential with #807) |
| Act-B | — | new ActiveReceiverToggle, VfoOps, VfoHeader |
| Spec-B | Spec-A | SpectrumToolbar, KeyboardHandler, shortcut-hints |
| LCD-8.3 | LCD-8.1 (tokens) | AmberAfScope, AmberLcdDisplay |
| Mob-10.2 | Mob-10.1 | MobileRadioLayout, new PttFab |
| M-B | M-A | RadioLayout, RightSidebar (moves combined AudioSpectrumPanel) |

After Wave 2: dock duplication gone, PTT FAB shipped, filter-viz expanded, mobile chip-scroll shipped, contrast control core landed, active-receiver M/S toggle live. Major visible wins.

### Wave 3 — 5 parallel, after Wave 2
| Issue | Depends on | Files |
|---|---|---|
| Act-C | Act-A | VfoPanel, tokens |
| Spec-C | Act-B (VfoHeader prop pattern), Spec-B | VfoHeader, SpectrumToolbar |
| LCD-8.2 | LCD-8.1 | new AmberContrastStrip, AmberLcdDisplay |
| Mob-10.3 | Mob-10.1 | MobileRadioLayout |
| M-C | M-A | MetersDockPanel, tokens |

### Wave 4 — 5 parallel
| Issue | Depends on | Files |
|---|---|---|
| Act-D | Act-B | keyboard-map, command-bus, test |
| Act-E | Act-A, Act-C | VfoPanel, VfoOps, VfoHeader (tooltip-only) |
| LCD-8.4 | LCD-8.1 | new AmberMemoryStrip, qsy-history store, AmberLcdDisplay |
| Mob-10.4 | Mob-10.1 | MobileRadioLayout, RitXitPanel |
| M-D | M-A | MetersDockPanel, meter-utils |

Conflict: Act-E touches VfoPanel (= Act-C). Serialize inside VFO track: A→C→E.
So actually Act-E stays in Wave 5.

### Wave 5 — parallel
| Issue | Depends on | Files |
|---|---|---|
| Act-E | Act-C | VfoPanel, VfoOps, VfoHeader |
| LCD-8.5 | LCD-8.1 | new AmberTelemetryStrip, AmberSparkline, AmberLcdDisplay |
| Mob-10.5 | Mob-10.1 | MobileRadioLayout |

### Wave 6 — design spike + polish
| Issue | Files |
|---|---|
| LCD-8.7 | produces new plan doc `docs/plans/2026-04-19-lcd-layout-redesign.md` |
| LCD-8.6 | AmberLcdDisplay, new CSS module |

### Cross-wave parallel (can start any time, totally isolated)
- #806 (remove BAR) — VfoHeader but trivial; bundle with Act-B.
- #808 (LCD theme) — new theme files; prerequisite for LCD-8.6 if overlaps; otherwise independent.
- #809 (dim inactive tokens) — AmberLcdDisplay; conflicts with LCD track → run as part of Wave 1 or serialized before LCD-8.1.
- #810 (auto-collapse panels) — CollapsiblePanel + call sites; independent. Any wave.
- #811 (MAIN/SUB segmented mobile) — depends on Act-B's `toActiveReceiverProps` adapter. Run after Wave 2.
- #812 (BRT/REF gear) — spectrum/mobile bridge; after Mob-10.1.
- #804 (idle vs disabled) — VfoOps styling; run before Act-E tooltip audit.

---

## 4. Recommended execution sequence

**6 waves × ~5 issues each = ~30 agent-hours of implementation if run 5-wide concurrently.**

Each wave uses `worktree` isolation so 5 agents run in parallel without stepping on each other's branches.

Per issue, the standard pipeline applies: EXPLORE → PLAN (if >20 LOC or protocol touch) → EXECUTE → REGCHECK → REVIEW → TEST → PR.

**Suggested concrete rollout:**

1. **Approve this execution plan.**
2. **Create the 16 new GitHub issues** under the two existing epics (#818 implementation, #819 spikes).
3. **Start Wave 1** (6 agents in parallel via `/solve-issue` invocations in separate worktrees).
4. On each agent completion: merge PR, kick off next-wave issue that depended on it.
5. **Design-spike LCD-8.7** runs in parallel with Wave 1 by a high-effort opus agent (like the current 5 spikes), producing a new plan doc.

---

## 5. Epic structure update

### Epic #818 (atomic implementation) gets 22 sub-issues:
- Original 9 (#804–#812) stay.
- +13 new implementation issues: M-A…D, Act-A…E, Spec-A…C, LCD-8.1…8.6, Mob-10.1…10.5.

### Epic #819 (design spikes) gets 1 new child:
- +LCD-8.7 (layout redesign spike), after the original 5 spike plans.

*(Remaining LCD and Mobile items LCD-8.6 [optional P3] and Mob-10.5 [landscape parity] are P3/P2 respectively.)*

---

## 6. Open questions — user input needed before issue creation

1. **OK to create all 16 new issues at once?** Or batch by wave?
2. **Worktree isolation per agent** — confirmed supported by current harness?
3. **Design-spike LCD-8.7** — spawn another opus agent now, or park until first wave lands?
4. **Priorities** — any issues you want bumped to P0?
5. **Act-E tooltip audit** — limited to VFO area in first cut, or extend to StatusBar + spectrum toolbar + rest of desktop in same issue (likely overflows 3-file guardrail — then split)?
6. **Test plan** — each issue gets unit tests per guardrails; do we want a Playwright E2E regression pass after each wave?
