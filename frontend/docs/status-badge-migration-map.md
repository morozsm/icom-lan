# StatusBadge Migration Map

GitHub issue: **#336**

## Purpose
Map all current `StatusBadge` usages to the correct destination after the approved architectural split:

- **Display path** -> `StatusIndicator`
- **Interactive path** -> `status-toggle` semantic role
- **Transitional / needs review** -> cases that should not be migrated blindly

## Architectural decision
`StatusBadge` is legacy / transitional because it currently conflates two different concerns:

1. **Display indicator** — read-only visual status
2. **Interactive control** — clickable user action / toggle

These must be separated.

Important:
- `StatusIndicator` is a dedicated display primitive
- `status-toggle` is a **semantic role**, not a permanently fixed visual family
- a theme may render `status-toggle` using different approved button families (Fill / Dot / Hardware Plain / etc.)

---

## Basket A — Display path -> `StatusIndicator`

These usages are read-only and should migrate to `StatusIndicator`.

| File | Current usage | Why | Recommended target |
|---|---|---|---|
| `src/components-v2/panels/TxPanel.svelte` | `TX ACTIVE` / `TX IDLE` | Pure status display, no click handler | `StatusIndicator` |
| `src/components-v2/vfo/VfoPanel.svelte` | compact `badgeItems` in control strip | Compact read-only display badges in VFO chrome | `StatusIndicator size="xs"` |

### Notes
- `VfoPanel` compact badges are the clearest `StatusIndicator` target in the codebase.
- `TX ACTIVE / TX IDLE` is also a pure indicator and should migrate early because it is semantically unambiguous.

---

## Basket B — Interactive path -> `status-toggle`

These usages are clickable and should migrate to the **status-toggle semantic role**.
They should not remain modeled as display badges.

| File | Current usage | Why | Recommended target |
|---|---|---|---|
| `src/components-v2/panels/TxPanel.svelte` | `ATU` | User-toggleable feature | status-toggle |
| `src/components-v2/panels/TxPanel.svelte` | `VOX` | User-toggleable feature | status-toggle |
| `src/components-v2/panels/TxPanel.svelte` | `COMP` | User-toggleable feature | status-toggle |
| `src/components-v2/panels/TxPanel.svelte` | `MON` | User-toggleable feature | status-toggle |
| `src/components-v2/panels/DspPanel.svelte` | `NB` (`ON` / `OFF`) | Clickable feature toggle | status-toggle |
| `src/components-v2/panels/RitXitPanel.svelte` | `RIT` | Clickable toggle | status-toggle |
| `src/components-v2/panels/RitXitPanel.svelte` | `XIT` | Clickable toggle | status-toggle |

### Notes
- These should migrate away from `StatusBadge` first on the interactive side.
- Current visual candidate may be Fill, but the architecture must preserve theme flexibility.
- Migration should target a semantic status-toggle model, not permanently hardcode `FillButton` as the only future outcome.

---

## Basket C — Action path -> `action-button`

These usages are not indicators and not sustained toggles. They are momentary command-style controls.

| File | Current usage | Why | Recommended target |
|---|---|---|---|
| `src/components-v2/panels/RitXitPanel.svelte` | `CLEAR` | Command-style action, no sustained active state | `action-button` semantic role |
| `src/components-v2/panels/DspPanel.svelte` | `Auto Tune` | Command-style action; current wiring is not implemented and no sustained state exists in ServerState | `action-button` semantic role |

### Notes
- `CLEAR` is visually badge-like today, but semantically it behaves like a command button.
- It should migrate toward the `action-button` role rather than being forced into either `StatusIndicator` or `status-toggle`.
- Similar controls are expected elsewhere (for example future tune/reset/clear style actions).

---

## Migration priority

### Priority 1 — easiest, least ambiguous
1. `TxPanel`: `TX ACTIVE / TX IDLE` -> `StatusIndicator`
2. `VfoPanel`: compact display badges -> `StatusIndicator`

### Priority 2 — interactive split
3. `TxPanel`: `ATU`, `VOX`, `COMP`, `MON` -> status-toggle
4. `DspPanel`: `NB`, `Auto Tune` -> status-toggle
5. `RitXitPanel`: `RIT`, `XIT` -> status-toggle

### Priority 3 — explicit review case
6. `RitXitPanel`: `CLEAR` -> decide as action control

---

## Recommended implementation strategy

### Step 1
Promote `StatusIndicator` as the display primitive and use it for the unambiguous display path.

### Step 2
Treat interactive usages as migration toward the **status-toggle role** while keeping visual-family flexibility.
Do not lock the architecture to `status-toggle === FillButton`.

### Step 3
Treat `CLEAR` and similar command-style controls as the **action-button role**.
Do not force them into either indicator or sustained-toggle semantics.

---

## Summary
`StatusBadge` should stop being a two-faced component.

The codebase should move toward:
- **display status** -> `StatusIndicator`
- **interactive status** -> `status-toggle`
- **momentary command actions** -> `action-button`
