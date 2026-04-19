# LCD Twin-Skin Implementation Plan

**Status:** ✅ approved 2026-04-19 — atomic issues to be created from §10.

## User decisions (2026-04-19)

1. Default variant on upgrade: **`lcd-cockpit`** (Variant B).
2. Switcher UI: **dropdown in StatusBar** (scalable to N skins).
3. Legacy `amber-lcd` alias: **keep indefinitely** — route to `lcd-cockpit`. No scheduled removal.
4. v2 §7 carryover (indicator taxonomy / RIT / meter B): **agent-level defaults** per atomic PR — per-VFO indicators on cockpit, per-VFO RIT, meter B follows current TX VFO.
5. C-PR4 waterfall: **no real waterfall** — dimmed running-max line only.
6. C-PR6 fallback (AF FFT unavailable): **option (b)** — ghost graticule + filter shape, no error label.
7. Outer wrapper: **single `LcdLayout.svelte`** with `variant` prop.
8. Legacy `skins/amber-lcd/` dir: keep until cleanup-PR.

---

**Author:** design agent.
**Builds on:** `docs/plans/2026-04-19-lcd-layout-redesign-v2.md` (the "v2 plan" — full wireframes, references, rationale for Variants A/B/C).
**Scope:** no code changes. Markdown planning only.

> This plan assumes the reader has skimmed v2 plan §3 (wireframes for Variants B and C) and §4 (rationale). It deliberately does **not** repeat those artifacts.

---

## 1. Decision context

The v2 plan recommended Variant B ("Dual Cockpit", TS-990S-style) over A and C. After review (2026-04-19) the user decided to **ship both B and C as separate selectable LCD skins** rather than pick one. Why:

1. **Different operating modes favor different layouts.** Operators running split / dual-RX (contesting, DX pileups) get the most value from B's peer cockpits. Operators running single-RX with AF-FFT want the IC-7300-style scope-dominated C.
2. **Neither pure B nor pure C is clearly universal.**
   - B penalizes single-RX single-RX single-scope operators: the per-VFO indicator zoning is overkill, and the bottom scope still has to share priority with a fat per-VFO chip row.
   - C penalizes dual-RX: VFO B lives in a thin bottom strip, not a peer cockpit (v2 plan §3.3, dual-RX wireframe confirms this).
3. **Shared primitives make the cost low.** `AmberFrequency`, `AmberAfScope`, `LcdContrastControl`, the `--lcd-alpha-*` cascade, and the warm theme are all used by both. The fork is small — two layout `.svelte` files plus cockpit/strip components that each variant owns.
4. **Skin registry already supports enumerable choice** (`SkinId` union in `frontend/src/skins/registry.ts`). Adding entries is cheap; the only real UX question is the switcher affordance.
5. **Reduces bikeshed risk.** Shipping both avoids having to relitigate "B vs C" per release. Each skin can evolve on its own cadence.

Out of scope for twin-skins: Variant A ("Elecraft Column", right rail). We drop it entirely — it was ruled out in v2 plan §4, and nothing changes that analysis.

---

## 2. Skin taxonomy + naming

### 2.1 Final skin IDs

| Skin ID            | Based on          | Description                                                        |
|--------------------|-------------------|--------------------------------------------------------------------|
| `lcd-cockpit`      | Variant B         | TS-990S-style dual-cockpit — two peer VFOs, per-VFO indicator zones |
| `lcd-scope`        | Variant C         | IC-7300-style scope-dominant — 60/40 top/bottom, big AF scope       |
| `amber-lcd`        | legacy (#844)     | Current scaffold. **Deprecated alias** → maps to `lcd-cockpit`.    |

Rationale:
- `lcd-cockpit` > `lcd-dual`: "dual" lies on single-RX radios (one cockpit shown). "Cockpit" names the layout philosophy (per-VFO zones).
- `lcd-scope` > `lcd-modern`: "modern" is a marketing word; "scope" names the load-bearing visual feature. When AF-FFT is unavailable the skin degrades; users should know scope is the headline.
- Keep `amber-lcd` as a **legacy alias only** during one release. Inside `loadSkin`, route `amber-lcd` to the `lcd-cockpit` loader. Remove the alias after two releases.

### 2.2 SkinId type change

```ts
// frontend/src/skins/registry.ts
export type SkinId = 'desktop-v2' | 'lcd-cockpit' | 'lcd-scope' | 'mobile';

// transitional: recognize legacy value, map on load
export type PersistedSkinId = SkinId | 'amber-lcd';
```

---

## 3. Shared infrastructure

Decision table — per primitive, shared vs forked.

| Primitive / file                                                                         | Status   | Notes |
|------------------------------------------------------------------------------------------|----------|-------|
| `panels/lcd/LcdContrastControl.svelte` (extracted by #877)                                | SHARED   | Lives outside the LCD surface (sidebar control-strip). Both skins reuse unchanged. |
| `theme/lcd-warm.css` (from #808)                                                          | SHARED   | Warm palette. Both skins set `data-theme="lcd-warm"` in their wrapper. |
| `--lcd-alpha-active / --lcd-alpha-inactive / --lcd-alpha-ghost` token cascade              | SHARED   | Both variants rely on it heavily; cockpit active/inactive styling and scope-ghost fallback. |
| `panels/lcd/AmberFrequency.svelte` (digit primitive)                                      | SHARED   | Used by both. Variant B uses size=lg for both cockpits; Variant C uses size=lg for A, size=md for B line. |
| `panels/lcd/AmberAfScope.svelte` (AF+passband+PBT widget)                                  | SHARED   | Both use it. Variant B calls with `compact={false}` filling remaining height; Variant C calls with a `dominant` variant that maximizes graticule + adds waterfall trace. Add `mode: 'compact' \| 'fill' \| 'dominant'` prop rather than forking. |
| `panels/lcd/VfoControlPanel.svelte` (sidebar soft-buttons)                                 | SHARED   | Sidebar widget, not inside the LCD surface. Both skins keep it in `content-right`. |
| `components-v2/layout/LcdLayout.svelte` (current outer layout with sidebars + strip)        | SHARED   | This file stays as the **outer chrome**. It renders `<StatusBar>`, sidebars, control strip, and a slot for the LCD surface itself. |
| `panels/lcd/AmberLcdDisplay.svelte` (current inner surface)                                | FORKED   | Split into `AmberLcdCockpitDisplay.svelte` (B) and `AmberLcdScopeDisplay.svelte` (C). |
| `panels/lcd/AmberCockpit.svelte` (new, from v2 plan PR1)                                   | SHARED   | Variant B uses two. Variant C uses one `AmberCockpit` for A, a compact `AmberVfoLine` for B. |
| `panels/lcd/AmberIndStrip.svelte` (new, from v2 plan PR3)                                  | SHARED   | `zone: 'global' \| 'perVfo' \| 'dsp' \| 'frontend'` prop. B uses `global`+`perVfo`; C uses `global`+`frontend`+`dsp`. |

**Net effect:** ~90% of LCD code is shared. The fork is the grid template and the outer `AmberLcd*Display.svelte` wrapper (plus C's extra `AmberVfoLine.svelte` compact renderer for its sub-VFO slot).

---

## 4. Skin registry changes

### 4.1 `frontend/src/skins/registry.ts`

- Extend `SkinId` (see §2.2).
- Extend `SKIN_LOADERS` with two new entries:
  ```ts
  'lcd-cockpit': () => import('./lcd-cockpit/LcdCockpitSkin.svelte'),
  'lcd-scope':   () => import('./lcd-scope/LcdScopeSkin.svelte'),
  ```
- Keep `'amber-lcd'` loader pointing at `lcd-cockpit/LcdCockpitSkin.svelte` during deprecation window.

### 4.2 `resolveSkinId()` default

Current rule (registry.ts:37): `hasAnyScope ? 'desktop-v2' : 'amber-lcd'`. Rewrite:

- `isMobile` → `mobile` (unchanged).
- `layoutPreference === 'standard'` → `desktop-v2` (unchanged).
- `layoutPreference === 'lcd'` → the **last-used LCD variant** from localStorage (`icom-lan-lcd-variant`, default `lcd-cockpit`).
- `layoutPreference === 'lcd-cockpit'` / `'lcd-scope'` → explicit choice.
- Auto: `hasAnyScope ? 'desktop-v2' : 'lcd-cockpit'` (default LCD = cockpit; reason: dual-RX IC-7610 is the reference radio).

### 4.3 UI switcher

Current: `StatusBar.svelte` has a STD/LCD cycle button (2-state toggle on `layoutPreference`).

Options:
1. **Extend to 3-way cycle** (STD → LCD-cockpit → LCD-scope → STD). Simple, but the current button only exposes one label; a 3-state cycle needs three labels.
2. **Dropdown menu** in the status bar: "Layout: Standard | LCD Cockpit | LCD Scope". Clearer.
3. **STD/LCD toggle unchanged + LCD sub-switcher inside LCD skin.** A tiny toggle inside each LCD skin's status strip (or the `lcd-control-strip`, next to the contrast picker) flips between the two LCD variants.

**Proposal: Option 3.** Keeps the global STD/LCD toggle familiar. Puts the cockpit/scope choice where the user is already looking at LCD (inside the skin). The sub-switcher is a small pill `COCKPIT / SCOPE` in the control strip, persisting to `localStorage['icom-lan-lcd-variant']`.

---

## 5. Migration from current `amber-lcd`

Existing users have `localStorage.icom-lan-skin === 'amber-lcd'` (or the equivalent `layoutPreference === 'lcd'`).

Mapping:
- Legacy `'amber-lcd'` → `'lcd-cockpit'`.
- New persisted key `icom-lan-lcd-variant`: if unset, default `'lcd-cockpit'` (the rationale: the current `amber-lcd` is closest to a stacked cockpit already; users complaining about VFO B demotion want peer cockpits — B delivers; C would be a more disruptive surprise on first boot).
- On first boot after upgrade, show a **one-shot toast**: "LCD skin now has two variants. Switch anytime in the control strip." (1 release only; wire via a version-gate key `icom-lan-skin-migrated-0.18`.)

The `amber-lcd` loader alias stays until v0.19; after that, remove the union member and the loader entry.

---

## 6. Variant B atomic PRs

Ported from v2 plan §5, renamed for the new skin ID. **No content changes** — only skin-id substitutions.

| # | Title | Files | LOC |
|---|-------|-------|-----|
| B-PR1 | `refactor(#NEW-B1): extract AmberCockpit component (behavior-preserving)` | new `panels/lcd/AmberCockpit.svelte`, edit `AmberLcdDisplay.svelte` | ~180 |
| B-PR2 | `feat(#NEW-B2): dual-cockpit grid — VFO B as peer` | edit `AmberLcdDisplay.svelte` (→ `AmberLcdCockpitDisplay.svelte` at this PR), edit `AmberCockpit.svelte` | ~150 |
| B-PR3 | `refactor(#NEW-B3): per-VFO indicator zone + global indicator strip` | new `AmberIndStrip.svelte`, edit cockpit + display | ~180 |
| B-PR4 | `feat(#NEW-B4): scope track fills remaining height (D4 fix)` | edit display, edit `AmberAfScope.svelte`, new `AmberFilterGhost.svelte` | ~160 |
| B-PR5 | `feat(#NEW-B5): mobile container-query collapse + telemetry reserve` | edit display, maybe edit `AmberCockpit` | ~100 |

See v2 plan §5 for gate definitions and rationale. Each PR is ≤3 files, ≤200 LOC. Strict sequence: B-PR1 → B-PR2 → … → B-PR5.

---

## 7. Variant C atomic PRs (NEW)

C's scope is smaller than B's because it gets to reuse `AmberCockpit` / `AmberIndStrip` / `AmberAfScope` once B has landed. C depends on **B-PR1, B-PR3, B-PR4** but not B-PR2 or B-PR5.

| # | Title | Files | LOC |
|---|-------|-------|-----|
| C-PR1 | `feat(#NEW-C1): add lcd-scope skin wrapper + registry entry` | new `skins/lcd-scope/LcdScopeSkin.svelte`, edit `skins/registry.ts`, new `layout/LcdScopeLayout.svelte` (thin — reuses outer chrome pattern from `LcdLayout.svelte`) | ~120 |
| C-PR2 | `feat(#NEW-C2): scope-dominant grid (60/40) for single-RX` | new `panels/lcd/AmberLcdScopeDisplay.svelte` (CSS grid per v2 plan §3.3), reuse `AmberCockpit` for A, new `AmberVfoLine.svelte` (compact one-liner for sub-VFO — not needed on single-RX) | ~190 |
| C-PR3 | `feat(#NEW-C3): scope-variant dual-RX — sub-VFO compact line` | edit `AmberLcdScopeDisplay.svelte`, edit `AmberVfoLine.svelte`. B-cockpit becomes a sub-line under the scope on dual-RX (v2 plan §3.3 dual-RX wireframe). | ~150 |
| C-PR4 | `feat(#NEW-C4): dominant-scope mode for AmberAfScope` | edit `AmberAfScope.svelte` — add `mode: 'compact' \| 'fill' \| 'dominant'` prop; `dominant` adds a dim waterfall trace and a larger graticule. | ~130 |
| C-PR5 | `feat(#NEW-C5): indicator strips — zone='frontend' \| 'dsp'` | edit `AmberIndStrip.svelte` taxonomy const to add the two new zones, wire into `AmberLcdScopeDisplay` | ~90 |
| C-PR6 | `feat(#NEW-C6): scope-fallback (no AF-FFT) — ghost graticule + filter shape` | edit `AmberFilterGhost.svelte` (from B-PR4) + display wrapper; degrade the big scope cell to graticule-only when `!hasAudioFft()` | ~100 |

All PRs ≤3 files, ≤200 LOC.

---

## 8. Execution order

**Phase 0 — shared switcher groundwork (before B or C):**
- S-PR1: `feat(#NEW-S1): expand SkinId to include lcd-cockpit + lcd-scope, add legacy alias`. Edits `registry.ts` only. Both new loaders point at `amber-lcd/LcdSkin.svelte` temporarily until B-PR2 / C-PR1 exist. No visual change.
- S-PR2: `feat(#NEW-S2): LCD variant sub-switcher in control strip`. Adds the COCKPIT/SCOPE pill next to `LcdContrastControl` in `LcdLayout.svelte`. Until both variants exist, pill is non-functional or hidden behind a feature flag (`VITE_LCD_TWIN=1`).

**Phase 1 — Variant B (critical path, blocks C on shared primitives):**
- B-PR1 through B-PR5 sequentially. After B-PR3 lands (`AmberIndStrip` exists) and B-PR4 lands (`AmberFilterGhost` exists), C can start in parallel.

**Phase 2 — Variant C (parallel from B-PR4 onward):**
- C-PR1 can start once S-PR1 lands (registry entry) and B-PR1 lands (`AmberCockpit` exists).
- C-PR2–C-PR6 sequentially.

**Phase 3 — cleanup:**
- CL-PR1: remove `amber-lcd` alias from `SkinId` (after v0.19 release).
- CL-PR2: delete the migration one-shot toast code.

Why not fully parallel B and C from day one: C reuses `AmberCockpit` (B-PR1), `AmberIndStrip` (B-PR3), and `AmberFilterGhost` (B-PR4). Trying to build C's equivalents in parallel duplicates work and risks merge conflicts. Serial-with-overlap is lower total wall time.

---

## 9. File-conflict matrix

Shared files each PR touches. `R` = reads/depends on; `W` = writes/edits.

| File                                        | S-PR1 | S-PR2 | B-PR1 | B-PR2 | B-PR3 | B-PR4 | B-PR5 | C-PR1 | C-PR2 | C-PR3 | C-PR4 | C-PR5 | C-PR6 |
|---------------------------------------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `skins/registry.ts`                         | W  |     |     |     |     |     |     | W  |     |     |     |     |     |
| `components-v2/layout/LcdLayout.svelte`      |     | W  |     |     |     |     |     |     |     |     |     |     |     |
| `panels/lcd/AmberLcdDisplay.svelte` → `...CockpitDisplay` |     |     | W  | W  | W  | W  | W  |     |     |     |     |     |     |
| `panels/lcd/AmberLcdScopeDisplay.svelte`    |     |     |     |     |     |     |     |     | W  | W  |     |     | W  |
| `panels/lcd/AmberCockpit.svelte`            |     |     | W  | W  | W  |     |     |     | R  |     |     |     |     |
| `panels/lcd/AmberIndStrip.svelte`           |     |     |     |     | W  |     |     |     | R  |     |     | W  |     |
| `panels/lcd/AmberAfScope.svelte`            |     |     |     |     |     | W  |     |     | R  | R  | W  |     | R  |
| `panels/lcd/AmberFilterGhost.svelte`        |     |     |     |     |     | W  |     |     |     |     |     |     | W  |
| `panels/lcd/AmberVfoLine.svelte`            |     |     |     |     |     |     |     |     | W  | W  |     |     |     |
| `skins/lcd-cockpit/LcdCockpitSkin.svelte`   |     |     |     |     |     |     |     |     |     |     |     |     |     |
| `skins/lcd-scope/LcdScopeSkin.svelte`       |     |     |     |     |     |     |     | W  |     |     |     |     |     |

**Key observations:**
- After B-PR4 lands, C-PRs touch **disjoint** files from remaining B-PRs (B-PR5 only touches the cockpit display; C touches scope display + scope-only siblings). Parallel work is safe.
- `AmberAfScope.svelte` is the only file with a possible race — B-PR4 edits it, then C-PR4 edits it. Serialize: C-PR4 must merge after B-PR4.
- `AmberIndStrip.svelte`: B-PR3 creates it; C-PR5 extends its zone enum. Serialize.
- Registry and `LcdLayout.svelte` outer chrome are edited only by Phase-0 PRs — no conflicts with variant PRs.

---

## 10. Issues to create

Suggested GitHub issue titles (all `frontend, lcd, design-spike` labels):

1. **#NEW-S1: LCD twin-skins — register `lcd-cockpit` + `lcd-scope` skin IDs (Phase 0)**
2. **#NEW-S2: LCD twin-skins — variant sub-switcher pill in control strip**
3. **#NEW-B1: LCD cockpit — extract `AmberCockpit` component (behavior-preserving)**
4. **#NEW-B2: LCD cockpit — dual-cockpit grid, VFO B as peer (closes #845)**
5. **#NEW-B3: LCD cockpit — per-VFO indicator zones + global strip**
6. **#NEW-B4: LCD cockpit — scope track fills remaining height (fixes D4 empty amber)**
7. **#NEW-B5: LCD cockpit — mobile container-query collapse + telemetry aux row**
8. **#NEW-C1: LCD scope — skin wrapper + registry plumbing**
9. **#NEW-C2: LCD scope — 60/40 scope-dominant grid (single-RX)**
10. **#NEW-C3: LCD scope — dual-RX compact sub-VFO line under scope**
11. **#NEW-C4: LCD scope — `AmberAfScope` dominant mode with waterfall trace**
12. **#NEW-C5: LCD scope — indicator strip zones (`frontend`, `dsp`)**
13. **#NEW-C6: LCD scope — AF-FFT unavailable fallback (ghost graticule + filter shape)**

13 issues total. Group under an epic **"LCD twin-skin redesign (v0.18)"** with the B-PRs and C-PRs as sub-issues.

---

## 11. Sunset queue

Issues that become obsolete or need reassessment once the twin-skin plan lands:

| Issue | Action | Reason |
|-------|--------|--------|
| #845 (VFO-B peer promotion) | **Close** after B-PR2 lands | Delivered by B-PR2 grid redesign. v2 plan already marked this obsolete. |
| #846 (status row 4 bays) | **Close** after B-PR3 lands | Superseded by B-PR3's per-VFO zoning. If #846 wanted something specific beyond zoning, capture as a follow-up issue. |
| #862 (memory / recent-QSY aux row) | **Keep, reassess** after B-PR5 | B-PR5 reserves the `aux` row; #862 fills it. Not obsolete — deferred. |
| #835 (filter-viz wide mode) | **Close** after B-PR4 lands | Scope is always wide in both skins post-B-PR4/C-PR4. |
| #836 (filter-viz something related) | **Reassess** — the v2 plan pairs #835/#836 but didn't specify #836 distinctly. Need issue body review before deciding. |
| #837 (telemetry VD/TEMP/ID strip) | **Keep, reassess** after B-PR5 | Same `aux` row mechanism; becomes trivial follow-up. |
| #877 (contrast in control-strip) | **Unchanged** | Lives outside LCD surface; both skins reuse. |

See v2 plan §5 for the obsolete/survivable rationale, unchanged here except for #836 which is flagged for body review (I didn't open it during this spike).

---

## 12. Open questions for user

1. **Default LCD variant on upgrade.** Recommend `lcd-cockpit` (closest to current layout; dual-RX reference radio). Confirm, or prefer `lcd-scope` since it is most visually different and "showcases" the redesign?
2. **Switcher UI placement.** Option-3 proposal (sub-switcher pill in control strip). Alternative: promote to a 3-state cycle in StatusBar (STD → COCKPIT → SCOPE). Preference?
3. **Legacy alias duration.** One release (remove in v0.19) or two (remove in v0.20)? One is cleaner; two is kinder to users who only upgrade occasionally.
4. **Are v2 plan §7 open questions still open?** Specifically Q1 (indicator taxonomy global vs per-VFO), Q6 (RIT ownership per-VFO), Q7 (meter B source during TX) — these answers apply to both skins. Please answer in the epic issue.
5. **C-PR4 waterfall trace.** v2 plan §3.3 mentions "waterfall trace" inside the dominant scope. Is that a genuine waterfall (2D time-history), or just a dimmer running-max line on top of the FFT? If waterfall, this is a larger LOC than 130 and needs its own spike.
6. **C-PR6 fallback behavior.** Three options in v2 plan §7 Q4: (a) ghost graticule + label "AUDIO FFT UNAVAILABLE", (b) ghost graticule + filter-shape only no label, (c) collapse the scope row. On `lcd-scope` skin, (c) breaks the whole premise of the skin. Proposal: (b) + a small ghost label. Confirm?
7. **Shared wrapper for outer chrome?** `LcdLayout.svelte` currently wraps the display. We can keep a single `LcdLayout` and have it render `<AmberLcdCockpitDisplay>` or `<AmberLcdScopeDisplay>` based on `persistedLcdVariant`, OR we can fork into `LcdCockpitLayout.svelte` / `LcdScopeLayout.svelte`. Proposal: **single `LcdLayout`** that takes a `variant` prop — less duplication. Confirm?
8. **Should we delete `amber-lcd` directory** (`skins/amber-lcd/LcdSkin.svelte`) at Phase-0, or leave it as the target of the legacy alias until cleanup? Proposal: leave it, alias-route it through the registry map, delete in CL-PR1.
