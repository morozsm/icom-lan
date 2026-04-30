# Panel → Adapter Migration Plan

Tracking issue: [#1240](https://github.com/morozsm/icom-lan/issues/1240)
(Tier 2 of #1063; parent #1238).

## Current state

- **18 panels** (Svelte components + 2 helper modules) under
  `frontend/src/components-v2/panels/` still import directly from
  `$lib/stores/*` — verified 2026-04-29 against commit `d48e8705` on `main`.
- This breaks the layering rule from `CLAUDE.md` ("Frontend layering"):
  *panels and layouts must not reach into stores; they must consume props
  from `lib/runtime/adapters/`*.
- ESLint (`no-restricted-imports`) currently bans `$lib/transport/*` and
  `$lib/audio/audio-manager` from panels; tightening to also ban
  `$lib/stores/*` is **out of scope** for this issue (Tier 3).
- Source-of-truth count comes from
  `grep -rln '$lib/stores' src/components-v2/panels/` minus tests
  (`__tests__/` files). Test files are **not** in scope — they exercise the
  store layer directly by design.

### Existing adapters (`frontend/src/lib/runtime/adapters/`)

| File | Purpose |
|------|---------|
| `audio-adapter.ts` | RX audio view-model + handlers (used by `RxAudioPanel`). |
| `panel-adapters.ts` | Per-panel `derive*Props()` / `get*Handlers()` for AGC, Mode, Antenna, RF Front End, RIT/XIT, Scan, Meter, CW, DSP, TX, Filter, Band Selector. |
| `scope-adapter.ts` | Audio-scope WS channel lifecycle + binary-frame parsing. |
| `tx-adapter.ts` | Audio TX lifecycle callbacks for PTT components. |
| `vfo-adapter.ts` | VFO view-model props (frequency / mode / split / RX badges). |

Note: `panel-adapters.ts` already exports a derive-fn for most "capability"
panels in this audit (CW, DSP, Meter, TX, RF Front End, Filter). The panels
have been *partially* migrated — they consume `derive*Props()` for their
state but still call ad-hoc capability helpers (`hasCapability`,
`hasTx`, `getAttValues`, etc.) directly from the store. Closing that
remaining gap is the bulk of this migration.

---

## Cluster inventory

### Cluster A — capabilities-only (8 files)

| File | Stores accessed | Read/Write |
|------|-----------------|------------|
| `AudioRoutingControl.svelte` | `capabilities.svelte` (`receiverLabel`) | read |
| `CwPanel.svelte` | `capabilities.svelte` (`hasCapability`) | read |
| `DspPanel.svelte` | `capabilities.svelte` (`hasCapability`) | read |
| `MeterPanel.svelte` | `capabilities.svelte` (`hasTx`) | read |
| `TxPanel.svelte` | `capabilities.svelte` (`hasTx`, `hasCapability`) | read |
| `RfFrontEnd.svelte` | `capabilities.svelte` (`hasCapability`, `getAttValues`, `getAttLabels`, `getPreValues`, `getPreLabels`) | read |
| `filter-controls.ts` | `capabilities.svelte` (`getControlRange`) | read |
| `meter-utils.ts` | `capabilities.svelte` (`getMeterCalibration`, `getMeterRedline`) | read |

**Adapter status:** *new adapter required.* Today, the existing
`panel-adapters.ts` exposes typed view-model props per panel (it already
calls `runtime.caps` internally), but each of these files **also** reaches
into `capabilities.svelte` for ad-hoc booleans / option lists / numeric
ranges. Two complementary moves:

1. **Move per-panel capability flags into the `derive*Props()` return
   value** (e.g. `CwProps.showBreakIn`, `RfFrontEndProps.attOptions`). Most
   already have a "props.has*" shape — extend it to cover everything the
   panel currently asks for.
2. **Add a thin shared `capabilities-adapter.ts`** for the pieces that
   genuinely don't fit a single panel's view-model: `meter-utils.ts` and
   `filter-controls.ts` are *helper modules* used from many places, so
   exposing `getMeterCalibration` / `getMeterRedline` / `getControlRange`
   via `runtime.caps.*` (already available — these helpers just need to
   accept caps as an argument or read from `runtime.caps`) is enough.
   `receiverLabel`, used by `AudioRoutingControl`, can be inlined into
   the existing audio routing props or moved to the same shared adapter.

**Complexity:** trivial-to-moderate. No state, no writes — pure derived
data. The Svelte panels already use `$derived(...)` against the helpers,
so swapping the import to a runtime adapter is a one-line change per
call site once the adapter exposes the same shape.

**Migration order:** first — lowest risk, unlocks the rest.

---

### Cluster B — radio live state (5 files; was 6 in scout — see note)

| File | Stores accessed | Read/Write |
|------|-----------------|------------|
| `audio-scope/AudioSpectrumPanel.svelte` | `radio.svelte` (`radio.current`), `capabilities.svelte` (`getCapabilities`) | read |
| `MemoryPanel.svelte` | `radio.svelte` (`radio.current`) | read |
| `lcd/AmberScope.svelte` | `radio.svelte`, `capabilities.svelte` (`hasAudioFft`, `hasDualReceiver`, `getCapabilities`, `hasCapability`) | read |
| `lcd/AmberTelemetryStrip.svelte` | `radio.svelte` | read |
| `lcd/VfoControlPanel.svelte` | `radio.svelte`, `capabilities.svelte` (`hasCapability`) | read |

> **Note on AmberCockpit double-listing.** The decomposition scout placed
> `AmberCockpit.svelte` in both this cluster and the qsy-history cluster.
> It is one file with two responsibilities: it reads `radio.current` for
> view-model state (this cluster) **and** it writes to `qsyHistory` from a
> tuning effect (Cluster D). Migrating it requires both adapters to land
> first; it is therefore listed under Cluster D as the merge point and
> excluded from this row to avoid double-counting. Total panel count
> remains 18.

**Adapter status:** *partial.* `vfo-adapter.ts` already covers VFO props,
but no adapter exposes a generic `radio.current`-flavored read (active RX,
freq/mode by slot). Three options:

1. **Extend per-panel adapters** in `panel-adapters.ts` —
   `deriveMemoryPanelProps()`, `deriveAudioSpectrumProps()`,
   `deriveAmberScopeProps()`, `deriveAmberTelemetryProps()`,
   `deriveVfoControlProps()`. Each returns the small slice the panel
   actually needs (e.g. MemoryPanel only needs `{ activeFreqHz, activeMode }`
   for the "store VFO → channel" flow). This keeps panels presentational.
2. **Single shared `radio-state-adapter.ts`** exposing
   `getActiveRx()` / `getRadioSnapshot()`. Rejected — bypasses the
   typed-props convention `panel-adapters.ts` has established.
3. **Combine 1 + the capabilities work from Cluster A.** Recommended:
   the same per-panel `derive*Props()` already consumes `runtime.caps`
   (Cluster A target), so consuming `runtime.state` alongside is the
   identical pattern.

**Complexity:** moderate. Write paths exist (MemoryPanel calls
`runtime.send(...)` for `set_memory_mode` / `memory_to_vfo` /
`memory_write` / `memory_clear`), but those go through the runtime
already — only the *read* of `radio.current` needs adapting.
`AmberCockpit` straddles this and Cluster D — see Cluster D.

**Migration order:** second.

---

### Cluster C — LCD chrome (2 files)

| File | Stores accessed | Read/Write |
|------|-----------------|------------|
| `lcd/LcdContrastControl.svelte` | `lcd-contrast.svelte` (`LCD_CONTRAST_PRESETS`, `applyLcdContrast`, `getLcdContrastPreset`, `setLcdContrastPreset`, `stepLcdContrast`, `LcdContrastPreset` type) | read+write |
| `lcd/LcdDisplayModeControl.svelte` | `lcd-display-mode.svelte` (`LCD_DISPLAY_MODES`, `getLcdDisplayMode`, `setLcdDisplayMode`, `LcdDisplayMode` type) | read+write |

**Adapter status:** *no adapter exists.* Both stores are pure UI-chrome
state (LCD vintage skin), local to the browser, persisted in
`localStorage`. They have no equivalent in `runtime.state` because
nothing in `runtime` cares about LCD contrast or display mode.

Two reasonable shapes:

1. **`lcd-chrome-adapter.ts`** under `lib/runtime/adapters/` exposing a
   thin façade that just re-exports the store API. This satisfies the
   layering rule mechanically but adds a pass-through indirection.
2. **Treat `lib/stores/lcd-*.svelte.ts` as "skin-local UI state" and
   exempt them from the rule.** Move them to
   `frontend/src/skins/amber-lcd/state/` (or similar) and update the
   ESLint rule to ban `$lib/stores/*` while allowing skin-local
   imports.

Recommendation: **(1) for this migration**, with an open question
(see below) whether (2) is the durable answer. (1) is mechanical and
unblocks ESLint tightening; (2) is a separate refactor.

**Complexity:** trivial. Two small files, no derived state.

**Migration order:** third (after Cluster A so the adapter pattern is
settled).

---

### Cluster D — qsy-history (2 files)

| File | Stores accessed | Read/Write |
|------|-----------------|------------|
| `lcd/AmberCockpit.svelte` | `radio.svelte`, `capabilities.svelte`, `qsy-history.svelte` (`qsyHistory.record`) | read (radio, caps) + write (qsyHistory) |
| `lcd/AmberMemoryStrip.svelte` | `qsy-history.svelte` (`qsyHistory.recent`) | read |

**Adapter status:** *no adapter exists.* `qsyHistory` is a small
ring-buffer with two entry points: `record(freq, mode)` (write,
debounced — see issue #836) and `recent` (read, latest 3 reversed). The
write happens from a tuning effect inside `AmberCockpit` whenever
`activeFreqHz` / `activeMode` changes.

Sketch: `qsy-history-adapter.ts` exporting:

```ts
export function deriveQsyRecent(): readonly QsyEntry[]
export function recordQsy(freqHz: number, mode: string): void
```

`AmberCockpit` is the merge point for Cluster B (radio state), Cluster A
(capabilities), and Cluster D (qsy-history). It should migrate **last**,
after the per-panel adapter for it (`deriveAmberCockpitProps` +
`getAmberCockpitHandlers`) is in place. The handler bundle exposes
`onTuningChange(freq, mode) → recordQsy(...)` so the panel never
imports the qsy store.

**Complexity:** moderate. The debounce semantics in `qsyHistory.record`
must be preserved (issue #836). `AmberMemoryStrip` is trivial —
read-only.

**Migration order:** fourth (depends on Cluster A capability flags being
available on `runtime.caps` and Cluster B `radio.current` adapter).

---

### Cluster E — connection (1 file)

| File | Stores accessed | Read/Write |
|------|-----------------|------------|
| `RxAudioPanel.svelte` | `connection.svelte` (`isAudioConnected`), `capabilities.svelte` (`hasDualReceiver`) | read |

**Adapter status:** *partial.* `audio-adapter.ts` already supplies
`deriveRxAudioProps()` / `getRxAudioHandlers()`. The two remaining
direct-store reads (`isAudioConnected`, `hasDualReceiver`) should fold
into `RxAudioProps` — both are derivable from `runtime.audio.connected`
and `runtime.caps.hasDualReceiver` respectively.

**Complexity:** trivial. One panel, two booleans.

**Migration order:** fifth (smallest; can ship anytime once Cluster A
lands `hasDualReceiver` on `runtime.caps`).

---

## Per-panel detail

| # | Panel / module | File | Stores imported | R/W | Adapter target | Complexity |
|---|---|---|---|---|---|---|
| 1 | AudioRoutingControl | `panels/AudioRoutingControl.svelte` | `capabilities.receiverLabel` | R | extend `panel-adapters` (audio-routing) | trivial |
| 2 | CwPanel | `panels/CwPanel.svelte` | `capabilities.hasCapability` | R | extend `CwProps` in `panel-props` | trivial |
| 3 | DspPanel | `panels/DspPanel.svelte` | `capabilities.hasCapability` | R | extend `DspProps` | trivial |
| 4 | MeterPanel | `panels/MeterPanel.svelte` | `capabilities.hasTx` | R | extend `MeterProps` | trivial |
| 5 | TxPanel | `panels/TxPanel.svelte` | `capabilities.{hasTx,hasCapability}` | R | extend `TxProps` | trivial |
| 6 | RfFrontEnd | `panels/RfFrontEnd.svelte` | `capabilities.{hasCapability,getAtt*,getPre*}` | R | extend `RfFrontEndProps` (att/pre options) | moderate |
| 7 | filter-controls (helper) | `panels/filter-controls.ts` | `capabilities.getControlRange` | R | inject `caps` arg or new `capabilities-adapter` | trivial |
| 8 | meter-utils (helper) | `panels/meter-utils.ts` | `capabilities.{getMeterCalibration,getMeterRedline}` | R | inject `caps` arg or new `capabilities-adapter` | trivial |
| 9 | AudioSpectrumPanel | `panels/audio-scope/AudioSpectrumPanel.svelte` | `radio.current`, `capabilities.getCapabilities` | R | new `deriveAudioSpectrumProps` in `panel-adapters` | moderate |
| 10 | MemoryPanel | `panels/MemoryPanel.svelte` | `radio.current` | R | new `deriveMemoryPanelProps` ({activeFreqHz, activeMode}) | moderate |
| 11 | AmberScope | `panels/lcd/AmberScope.svelte` | `radio`, `capabilities.{hasAudioFft,hasDualReceiver,getCapabilities,hasCapability}` | R | new `deriveAmberScopeProps` | moderate |
| 12 | AmberTelemetryStrip | `panels/lcd/AmberTelemetryStrip.svelte` | `radio` | R | new `deriveAmberTelemetryProps` | trivial |
| 13 | VfoControlPanel | `panels/lcd/VfoControlPanel.svelte` | `radio`, `capabilities.hasCapability` | R | extend existing `vfo-adapter` (or `deriveVfoControlProps`) | moderate |
| 14 | LcdContrastControl | `panels/lcd/LcdContrastControl.svelte` | `lcd-contrast` (5 fns + type) | R+W | new `lcd-chrome-adapter` (contrast facet) | trivial |
| 15 | LcdDisplayModeControl | `panels/lcd/LcdDisplayModeControl.svelte` | `lcd-display-mode` (3 fns + type) | R+W | new `lcd-chrome-adapter` (display-mode facet) | trivial |
| 16 | AmberCockpit | `panels/lcd/AmberCockpit.svelte` | `radio`, `capabilities.{hasAudioFft,hasDualReceiver,getCapabilities,hasCapability}`, `qsy-history.record` | R+W | new `deriveAmberCockpitProps` + `getAmberCockpitHandlers` (depends on qsy-history-adapter) | hard |
| 17 | AmberMemoryStrip | `panels/lcd/AmberMemoryStrip.svelte` | `qsy-history.recent` | R | new `qsy-history-adapter` (`deriveQsyRecent`) | trivial |
| 18 | RxAudioPanel | `panels/RxAudioPanel.svelte` | `connection.isAudioConnected`, `capabilities.hasDualReceiver` | R | extend `RxAudioProps` (audio-adapter) | trivial |

---

## Proposed migration batches

Each batch ≤ 4 panels. Sub-issues open from this plan after #1240
closes.

### Batch 1 — capability flags into existing panel props (4 panels)

- Panels: **CwPanel, DspPanel, MeterPanel, TxPanel**
- Why first: lowest risk, smallest diff. Each panel already calls
  `derive*Props()`; the migration just extends the typed return shape
  to include the `has*` booleans currently read inline. No new
  adapter file. Establishes the pattern.
- Sub-issue title: `refactor(frontend): fold capability flags into Cw/Dsp/Meter/Tx panel props (Tier 2 batch 1/5)`
- Touches: `lib/runtime/props/panel-props.ts` (extend types),
  4 `.svelte` files. ≤200 LOC delta, exactly 4 files (within
  guardrails after type/file split).

### Batch 2 — capability helpers shared adapter (4 files)

- Panels: **RfFrontEnd, AudioRoutingControl, filter-controls,
  meter-utils**
- Why second: the helpers (`filter-controls.ts`, `meter-utils.ts`) are
  the trickiest of Cluster A — they're not Svelte components and they
  feed multiple panels. Doing them together with `RfFrontEnd` (which
  needs option lists, not just booleans) and `AudioRoutingControl`
  (which uses `receiverLabel`) lets one adapter file land all the
  remaining capability surface. New file:
  `lib/runtime/adapters/capabilities-adapter.ts`.
- Sub-issue title: `refactor(frontend): extract capabilities-adapter for RF Front End + helpers (Tier 2 batch 2/5)`

### Batch 3 — radio-state per-panel adapters (4 panels)

- Panels: **AudioSpectrumPanel, MemoryPanel, AmberTelemetryStrip,
  VfoControlPanel**
- Why third: Cluster B without `AmberScope` / `AmberCockpit` (those
  also need qsy-history). All four read `radio.current` and at most
  one capability call — small per-panel `derive*Props()` additions.
- Sub-issue title: `refactor(frontend): per-panel radio-state adapters for AudioSpectrum/Memory/AmberTelemetry/VfoControl (Tier 2 batch 3/5)`

### Batch 4 — LCD chrome + qsy-history (4 panels)

- Panels: **LcdContrastControl, LcdDisplayModeControl, AmberMemoryStrip,
  AmberScope**
- Why fourth: bundles the trivial leftover panels.
  `LcdContrastControl` + `LcdDisplayModeControl` need a new
  `lcd-chrome-adapter.ts`. `AmberMemoryStrip` needs the
  `qsy-history-adapter.ts` (read side). `AmberScope` migrates its
  radio-state read at the same time so Cluster B and the qsy-history
  read side are fully gone after this batch. Two new adapter files.
- Sub-issue title: `refactor(frontend): LCD chrome adapter + qsy-history read adapter + AmberScope (Tier 2 batch 4/5)`

### Batch 5 — AmberCockpit + RxAudioPanel finisher (2 panels)

- Panels: **AmberCockpit, RxAudioPanel**
- Why last: `AmberCockpit` is the only "hard" panel (writes
  qsy-history from a tuning effect; reads radio + multiple
  capabilities). It needs the qsy-history-adapter *write* side, plus
  its own panel adapter. Bundling `RxAudioPanel` (the trivial Cluster E
  finisher) lets the batch close out the migration and unblock ESLint
  tightening (Tier 3).
- Sub-issue title: `refactor(frontend): AmberCockpit + RxAudioPanel — close panel→adapter migration (Tier 2 batch 5/5)`

---

## Open questions

1. **Where does LCD chrome state belong long-term?** Cluster C stores
   (`lcd-contrast.svelte.ts`, `lcd-display-mode.svelte.ts`) are *skin-
   local UI state*, not radio state. Two answers:
   (a) keep them in `lib/stores/` and front them with a thin
   `lcd-chrome-adapter.ts` (plan-of-record above);
   (b) relocate to `skins/amber-lcd/state/` and let panels import
   skin-local state directly with a tightened ESLint rule that bans
   `$lib/stores/*` but allows `$lib/skins/<skin>/state/*`. (b) is
   architecturally cleaner but requires the file move + ESLint config
   change. Decision punted to whoever owns Batch 4.

2. **Should `panel-adapters.ts` keep growing, or split per cluster?**
   It already has 12 panels' worth of derive/handler exports. Adding
   AmberScope / AmberCockpit / AmberTelemetryStrip / AudioSpectrum /
   Memory / VfoControl pushes it past ~25 panels. Suggested split:
   keep `panel-adapters.ts` as a barrel re-export; move actual
   per-panel functions into
   `lib/runtime/adapters/panels/<panel>.ts`. Out of scope for #1240
   itself — flag for the planner of Batch 3.
