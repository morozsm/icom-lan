# Code Review: Sprint 3 — Desktop Polish, Mobile, Touch

**Date:** 2026-03-08
**Reviewer:** Claude (automated)
**PRs:** #164 (Desktop), #165 (Mobile), #166 (Touch)
**Status:** ⛔ Blocked — 3 critical issues make PTT shortcut, dual-watch, and pinch-zoom non-functional

---

## Summary

Sprint 3 delivers a visually complete UI with excellent architecture: Svelte 5 rune
patterns are correct throughout, TypeScript is strict, CSS tokens are used consistently,
gesture recognizer design is solid, and the `sendCommand('name', {params})` envelope
format from Sprint 2 C1 is correctly applied in almost every call site. Three new
critical bugs introduce unknown command names that the backend silently rejects.

---

## Sprint 2 Regression Check

| Sprint 2 issue | Status |
|----------------|--------|
| C1 — WS command envelope format | ✅ Fixed — `sendCommand('name', {params})` used everywhere |
| C2 — `set_active_receiver` → `select_vfo` | ✅ Fixed — `select_vfo` with `vfo: 'A'\|'B'` |
| C3 — `set_af_mute` WS call | ✅ Fixed — `toggleMute()` only, no WS command |
| C3 — `set_comp` unknown command | ✅ Fixed — not seen in Sprint 3 components |
| W1 — `SpectrumPanel` scope WS leak | Not re-verified (not in Sprint 3 scope) |
| W3 — `WaterfallCanvas` DPR scaling | ✅ Fixed — `dpr` applied in `ResizeObserver` |
| W10 — dead `onmodechange` prop | ✅ Fixed — removed from `VfoDisplay` and `DesktopLayout` |
| S5 — `CMD_PTT_ON`/`CMD_PTT_OFF` constants | ✅ Fixed — removed from `protocol.ts` |

---

## 🔴 Critical Issues

### C1 — Space-bar PTT sends unknown commands `ptt_on`/`ptt_off`

**File:** `frontend/src/lib/actions/keyboard.ts:94`

**Issue:**

```typescript
case ' ': {
  e.preventDefault();
  const ptt = state?.ptt ?? false;
  sendCommand(ptt ? 'ptt_off' : 'ptt_on', {});  // ← WRONG
  break;
}
```

The backend `ControlHandler._COMMANDS` contains `"ptt"` only:

```python
case "ptt":
    on = bool(params["state"])
    q.put(PttOn() if on else PttOff())
```

`"ptt_on"` and `"ptt_off"` are not in `_COMMANDS`. The server responds with
`{type: "response", ok: false, error: "unknown_command"}`. The space-bar PTT
shortcut is completely non-functional.

**Fix:**

```typescript
case ' ': {
  e.preventDefault();
  const ptt = state?.ptt ?? false;
  sendCommand('ptt', { state: !ptt });
  break;
}
```

Note: This is the same pattern already used correctly by `PttButton.svelte:27` and
`BottomBar.svelte:40`.

---

### C2 — Dual-watch toggle sends `set_dw` — not a valid backend command

**Files:**
- `frontend/src/components/layout/DesktopLayout.svelte:53`
- `frontend/src/components/layout/MobileLayout.svelte:58`

**Issue:** Both layouts send `'set_dw'` which does not appear in `_COMMANDS`:

```typescript
// DesktopLayout.svelte:52-54
function handleDwToggle() {
  sendCommand('set_dw', { on: !(state?.dualWatch ?? false) });  // ← 'set_dw' unknown
}

// MobileLayout.svelte:57-59
function handleDwToggle() {
  sendCommand('set_dw', { on: !(state?.dualWatch ?? false) });  // ← 'set_dw' unknown
}
```

The backend command is `"set_dual_watch"`:

```python
case "set_dual_watch":
    on = bool(params.get("on", False))
    q.put(SetDualWatch(on))
```

Both calls are silently rejected. The dual-watch toggle does nothing.

**Fix:** Replace `'set_dw'` with `'set_dual_watch'` in both files.

---

### C3 — Pinch-to-zoom sends `set_scope_span` — not a valid backend command

**File:** `frontend/src/components/spectrum/WaterfallCanvas.svelte:64`

**Issue:**

```typescript
onPinch(scale: number, _cx: number, _cy: number): void {
  if (options.spanHz <= 0) return;
  const newSpan = Math.max(2_500, Math.min(5_000_000, options.spanHz / scale));
  sendCommand('set_scope_span', { span: Math.round(newSpan) });  // ← unknown command
},
```

`"set_scope_span"` does not exist in `_COMMANDS`. The backend scope control
commands are:
- `"set_scope_center_type"` — changes center/fixed-edge mode
- `"set_scope_fixed_edge"` — sets edge, start_hz, end_hz (for fixed-edge spans)

There is no single-parameter span command. Pinch-to-zoom silently fails.

**Fix options:**

Option A (recommended): Use `"set_scope_fixed_edge"` to map `newSpan` to
`start_hz`/`end_hz` around the current center:

```typescript
onPinch(scale: number, _cx: number, _cy: number): void {
  if (options.spanHz <= 0 || options.centerHz <= 0) return;
  const newSpan = Math.max(2_500, Math.min(5_000_000, options.spanHz / scale));
  const half = Math.round(newSpan / 2);
  sendCommand('set_scope_fixed_edge', {
    edge: 1,
    start_hz: Math.max(0, options.centerHz - half),
    end_hz: options.centerHz + half,
  });
},
```

Option B: Implement `"set_scope_span"` in the backend as a convenience command
that internally computes `start_hz`/`end_hz`.

Note: `set_scope_center_type` and `set_scope_fixed_edge` both require the `"scope"`
capability check — the frontend should guard accordingly.

---

## 🟡 Warnings

### W1 — `MobileLayout` UTC clock: setInterval is never cleaned up

**File:** `frontend/src/components/layout/MobileLayout.svelte:36-45`

**Issue:** The `$effect` creates a nested timer pattern where the inner `setInterval`
leaks permanently:

```typescript
$effect(() => {
  const msToNextMinute = 60_000 - (Date.now() % 60_000);
  const initial = setTimeout(() => {
    utcTime = nowUtc();
    const interval = setInterval(() => {
      utcTime = nowUtc();
    }, 60_000);
    return () => clearInterval(interval); // ← BUG: setTimeout ignores return values
  }, msToNextMinute);
  return () => clearTimeout(initial); // only cancels the initial timeout
});
```

`setTimeout` callbacks are fire-and-forget — their return values are discarded.
The `return () => clearInterval(interval)` is dead code. Once `initial` fires,
`interval` is created and runs indefinitely, even after the component is destroyed.

Compare with `StatusBar.svelte:36-40` which does this correctly:

```typescript
$effect(() => {
  updateClock();
  const id = setInterval(updateClock, 1_000);
  return () => clearInterval(id);
});
```

**Fix:** Follow the `StatusBar` pattern:

```typescript
$effect(() => {
  const id = setInterval(() => { utcTime = nowUtc(); }, 60_000);
  return () => clearInterval(id);
});
```

Or synchronize to minute boundaries by clearing and recreating, but keep the
reference accessible to the `$effect` cleanup.

---

### W2 — `MobileLayout` status bar is hardcoded and disconnected from stores

**File:** `frontend/src/components/layout/MobileLayout.svelte:73-74`

**Issue:**

```svelte
<span class="radio-name">IC-7610</span>
<span class="status-connected" title="Connected">●</span>
```

The radio name is hardcoded `"IC-7610"` and always appears in green (`.status-connected`
has `color: var(--success)`). This makes the mobile status bar useless as a connection
indicator — it will show green even when the radio is disconnected.

Compare with `StatusBar.svelte` which correctly reads from stores:
- `getCapabilities()` for `caps?.model`
- `getConnectionStatus()` for the dot color

**Fix:** Either import `StatusBar.svelte` (same component used by Desktop), or inline
the same store reads:

```typescript
import { getCapabilities } from '../../lib/stores/capabilities.svelte';
import { getConnectionStatus } from '../../lib/stores/connection.svelte';

let caps = $derived(getCapabilities());
let status = $derived(getConnectionStatus());
let isConnected = $derived(status === 'connected');
```

---

### W3 — `WaterfallCanvas` pan-to-tune ignores active receiver

**File:** `frontend/src/components/spectrum/WaterfallCanvas.svelte:74-79`

**Issue:**

```typescript
onPanEnd(): void {
  if (panOffsetHz === 0 || options.centerHz <= 0) return;
  const newCenter = Math.max(0, options.centerHz + panOffsetHz);
  sendCommand('set_freq', { freq: Math.round(newCenter) });  // ← no receiver
  panOffsetHz = 0;
},
```

`set_freq` with no `receiver` defaults to receiver `0` (MAIN) in the backend:

```python
case "set_freq":
    freq = int(params["freq"])
    rx = int(params.get("receiver", 0))  # defaults to MAIN
```

If the user has SUB selected as active, panning the waterfall always tunes MAIN.
This was flagged as Sprint 2 W2 for click-to-tune in `SpectrumPanel`; the same
issue applies to pan-end in `WaterfallCanvas`.

**Fix:** Import the radio state to read the active receiver:

```typescript
import { getRadioState } from '../../lib/stores/radio.svelte';

onPanEnd(): void {
  if (panOffsetHz === 0 || options.centerHz <= 0) return;
  const newCenter = Math.max(0, options.centerHz + panOffsetHz);
  const receiver = getRadioState()?.active === 'SUB' ? 1 : 0;
  sendCommand('set_freq', { freq: Math.round(newCenter), receiver });
  panOffsetHz = 0;
},
```

---

### W4 — `DxClusterPanel` uses `$derived` of a function (Svelte 5 anti-pattern)

**File:** `frontend/src/components/dx/DxClusterPanel.svelte:46-51`

**Issue:**

```typescript
let filteredSpots = $derived((): DxSpot[] => {
  if (!filterCurrentBand) return spots;
  const currentBand = getBand(currentFreq);
  if (!currentBand) return spots;
  return spots.filter((s) => getBand(spotFreqHz(s))?.name === currentBand.name);
});
```

`$derived` computes a value — here, the "value" is a function object. When Svelte
evaluates this `$derived`, it runs the outer arrow function `() => (): DxSpot[] => {...}`,
which returns a new arrow function. No reactive reads happen during this evaluation
(the body of the inner function is not executed), so Svelte tracks zero dependencies.
`filteredSpots` never recomputes when `filterCurrentBand`, `spots`, or `currentFreq` change.

The filter toggle appears to work because Svelte's template compiler tracks reactive
reads made during `{#each filteredSpots() as ...}` — the function body reads reactive
state, so the template re-renders. But the `$derived` wrapper itself is dead weight
and the pattern is fragile (relies on template-level reactivity, breaks if called
outside a template context).

**Fix:** Derive the array directly:

```typescript
let filteredSpots = $derived.by((): DxSpot[] => {
  if (!filterCurrentBand) return spots;
  const currentBand = getBand(currentFreq);
  if (!currentBand) return spots;
  return spots.filter((s) => getBand(spotFreqHz(s))?.name === currentBand.name);
});
```

`$derived.by()` is the correct Svelte 5 syntax for a derived value computed from
a thunk. It tracks reactive reads inside the function and `filteredSpots` becomes
a `DxSpot[]` value, not a function.

---

### W5 — `Toast` auto-dismiss timers are not tracked

**File:** `frontend/src/components/shared/Toast.svelte:20`

**Issue:**

```typescript
function addToast(level: 'info' | 'warning' | 'error', message: string) {
  const id = crypto.randomUUID();
  toasts = [...toasts, { id, level, message }];
  setTimeout(() => dismiss(id), 5_000);  // ← no reference saved
}
```

`setTimeout` IDs are discarded. If Toast is ever destroyed before the 5s timer fires,
the callback attempts to mutate state on a dead component. Toast is currently a
singleton rendered once in `DesktopLayout`, so the risk is low — but in `MobileLayout`
it is not rendered at all (there is no `<Toast />` in MobileLayout), so mobile users
receive no WS notifications.

Two distinct issues:
1. **Toast is missing from MobileLayout** — `notification` WS messages are silently dropped on mobile.
2. **Timer tracking** — Low priority given singleton use, but technically leaks on destroy.

**Fix:**
- Add `<Toast />` to `MobileLayout.svelte` (outside `.mobile-layout`, before end of file, same as Desktop's pattern).
- Track timers for cancel-on-destroy if Toast ever becomes non-singleton.

---

## 🔵 Suggestions

### S1 — `PTT_HOLD_DELAY` defined in gesture-recognizer.ts but never used

**File:** `frontend/src/lib/gestures/gesture-recognizer.ts:27`

```typescript
const PTT_HOLD_DELAY = 200; // ms — min hold before activation
```

This constant is defined at line 27 but not referenced anywhere inside `gesture-recognizer.ts`.
The 200ms delay is separately defined as `HOLD_DELAY_MS = 200` in `PttButton.svelte:13`.
Remove `PTT_HOLD_DELAY` from `gesture-recognizer.ts` (it belongs in `PttButton` only).

---

### S2 — `PttButton` hold-to-cancel checks live `transmitting` state, not captured intent

**File:** `frontend/src/components/audio/PttButton.svelte:64-76`

```typescript
function onPressCancel() {
  pressing = false;
  if (holdTimer !== null) {
    clearTimeout(holdTimer);
    holdTimer = null;
  }
  // Pointer left button area — release TX if active
  if (transmitting) {      // ← reads live server-confirmed state
    vibrate('ptt');
    pending = true;
    pendingValue = false;
    sendCommand('ptt', { state: false });
  }
}
```

`transmitting` is `$derived(getIsTransmitting())` — server-confirmed state that lags
by at least one WS round-trip. If the user holds for >200ms (activating TX), then
immediately slides off the button, `transmitting` may still be `false` while the
`ptt_on` WS response is in-flight. The cancel does nothing, leaving TX stuck on.

The hold timer sets `pendingValue = true` before the server confirms. `onPressCancel`
should use `pendingValue` to detect pending TX intent:

```typescript
function onPressCancel() {
  pressing = false;
  if (holdTimer !== null) {
    clearTimeout(holdTimer);
    holdTimer = null;
  }
  if (transmitting || (pending && pendingValue)) {
    vibrate('ptt');
    pending = true;
    pendingValue = false;
    sendCommand('ptt', { state: false });
  }
}
```

---

### S3 — Keyboard handler does not guard `contenteditable` elements

**File:** `frontend/src/lib/actions/keyboard.ts:37-44`

```typescript
function isInputFocused(): boolean {
  const el = document.activeElement;
  return (
    el instanceof HTMLInputElement ||
    el instanceof HTMLTextAreaElement ||
    el instanceof HTMLSelectElement
  );
}
```

`contenteditable` elements (e.g., any rich-text widget) are not guarded. If the
app ever adds a contenteditable region, arrow keys and space would still steal
focus. Add:

```typescript
return (
  el instanceof HTMLInputElement ||
  el instanceof HTMLTextAreaElement ||
  el instanceof HTMLSelectElement ||
  (el instanceof HTMLElement && el.isContentEditable)
);
```

---

### S4 — `DesktopLayout` misses `<Toast />` bottom-of-file placement guard

**File:** `frontend/src/components/layout/DesktopLayout.svelte:156`

`<Toast />` is rendered after the closing `</div>` of `.desktop-layout`. This is
correct (renders as a sibling in the DOM, not inside the layout container), but it
relies on the parent `AppShell` not restricting overflow. Currently this works, but
document the pattern with a comment to prevent future breakage:

```svelte
<!-- Toast notifications — rendered outside layout container to prevent clipping -->
<Toast />
```

This comment is already present at line 155. ✅ (Just noting it's good practice.)

---

## WS Command Audit (all `sendCommand` calls vs `handlers.py _COMMANDS`)

| File | Line | Command sent | Backend has it? | Params correct? |
|------|------|--------------|-----------------|-----------------|
| `DesktopLayout.svelte` | 40 | `set_freq` | ✅ | ✅ `{freq, receiver: 0\|1}` |
| `DesktopLayout.svelte` | 45 | `set_mode` | ✅ | ✅ `{mode, receiver: 0\|1}` |
| `DesktopLayout.svelte` | 49 | `select_vfo` | ✅ | ✅ `{vfo: 'A'\|'B'}` |
| `DesktopLayout.svelte` | 53 | `set_dw` | ❌ **C2** | N/A — unknown command |
| `MobileLayout.svelte` | 50 | `set_freq` | ✅ | ✅ |
| `MobileLayout.svelte` | 54 | `select_vfo` | ✅ | ✅ |
| `MobileLayout.svelte` | 58 | `set_dw` | ❌ **C2** | N/A — unknown command |
| `DxClusterPanel.svelte` | 67 | `set_freq` | ✅ | ✅ `{freq, receiver: 0\|1}` |
| `keyboard.ts` | 59 | `set_freq` | ✅ | ✅ |
| `keyboard.ts` | 73 | `set_mode` | ✅ | ✅ |
| `keyboard.ts` | 80 | `set_freq` | ✅ | ✅ |
| `keyboard.ts` | 87 | `set_freq` | ✅ | ✅ |
| `keyboard.ts` | 94 | `ptt_on`/`ptt_off` | ❌ **C1** | N/A — unknown commands |
| `WaterfallCanvas.svelte` | 64 | `set_scope_span` | ❌ **C3** | N/A — unknown command |
| `WaterfallCanvas.svelte` | 77 | `set_freq` | ✅ | ⚠️ **W3** missing `receiver` |
| `PttButton.svelte` | 27, 41, 60, 75 | `ptt` | ✅ | ✅ `{state: bool}` |
| `BottomBar.svelte` | 28 | `set_af_level` | ✅ | ✅ `{level, receiver}` |
| `BottomBar.svelte` | 40 | `ptt` | ✅ | ✅ `{state: bool}` |

**Summary:** 3 unknown commands (C1, C2, C3), 1 missing param (W3), all others correct.

---

## Component-by-Component Review

### DesktopLayout.svelte ✅ (except C2)

- CSS Grid: `grid-template-columns: 1fr var(--right-pane-width)` — correct two-column layout. ✅
- Side panel (`right-pane`): scrollable, proper `overflow-y: auto`. ✅
- Band bar: `overflow-x: auto` prevents clipping on narrow widths. ✅
- `setupKeyboard()` returned from `onMount` — correct cleanup. ✅
- `set_dw` command name wrong — **C2**. ❌

### StatusBar.svelte ✅

- UTC clock: `setInterval` correctly cleaned up in `$effect`. ✅
- Connection indicator: reads `getConnectionStatus()` — correct. ✅
- TX/RX badge: reads `state?.ptt` — correct. ✅
- `isPartial` status shown as `--warning` dot — good partial-connection UX. ✅

### Toast.svelte ✅ (with W5 noted)

- `onMount` returns `onMessage(...)` unsubscribe — correct cleanup. ✅
- `notification` type check is correct: `msg.type === 'notification'`. ✅
- Level mapping handles unexpected values safely. ✅
- `pointer-events: none` on container, `pointer-events: all` on individual toasts — correct. ✅
- Auto-dismiss timer tracking — **W5**. ⚠️
- Not included in MobileLayout — **W5**. ⚠️

### DxClusterPanel.svelte ✅ (with W4 noted)

- WS subscription via `onMount(() => return onMessage(...))` — correct cleanup. ✅
- `msg.type === 'dx_spot'` / `'dx_spots'` — matches backend exactly. ✅
- `tuneToSpot`: `set_freq` with `{freq: spotFreqHz(spot), receiver: receiverIdx}` — correct. ✅
- `spot.freq * 1_000` for Hz conversion (DX cluster is kHz) — correct. ✅
- Dedup logic `!(s.dx === spot.dx && s.freq === spot.freq)` — correct. ✅
- `filteredSpots = $derived((): DxSpot[] => {...})` — anti-pattern — **W4**. ⚠️

### keyboard.ts — PTT broken (C1)

- F1–F11 band switching: `set_freq` correct. ✅
- M mode cycling: `set_mode` correct. ✅
- Arrow key tuning: `set_freq` correct. ✅
- Space PTT: `ptt_on`/`ptt_off` — **C1**. ❌
- Input focus guard: correct but misses `contenteditable` — **S3**. ⚠️
- Cleanup: `removeEventListener` in returned function — correct. ✅

### App.svelte ✅

- Error overlay: `role="alert"` with `aria-live="assertive"` — correct. ✅
- Retry timer: tracked and cleared in `onMount` cleanup. ✅
- Error overlay shows over `AppShell` via `z-index: 10000`. ✅
- Retry at 5s: reasonable backoff for initial connection failure. ✅

### MobileLayout.svelte — mostly good (W1, W2, C2)

- `height: 100dvh` — correct, avoids iOS toolbar issue. ✅
- `BottomBar` is a flex child (not fixed position), properly constrained. ✅
- Fullscreen spectrum overlay: `position: fixed; inset: 0; z-index: 100` — correct. ✅
- Overlay close button: `min-width: 44px; min-height: 44px` — meets touch target spec. ✅
- UTC clock timer leak — **W1**. ❌
- Hardcoded radio name + static dot — **W2**. ⚠️
- `set_dw` unknown command — **C2**. ❌

### BottomBar.svelte ✅

- `height: 56px; flex-shrink: 0` — correct fixed-height footer. ✅
- Volume: `sendCommand('set_af_level', { level, receiver: receiverIdx })` — correct. ✅
- PTT: `sendCommand('ptt', { state: next })` — correct. ✅
- `pending` guard prevents double-send. ✅
- `disabled={pending && !transmitting}` — prevents click while pending TX. ✅
- Mute button: calls `toggleMute()` only (local audio mute, no WS command). ✅

### gesture-recognizer.ts ✅

- Pointer capture: `element.setPointerCapture(e.pointerId)` — prevents pointer loss. ✅
- Multi-pointer pinch: `pointers.size === 2` tracking — correct. ✅
- Long press cancel on move > `TAP_MOVE_THRESHOLD`. ✅
- `onPointerCancel`: clears timers and calls `onPanEnd`. ✅
- `destroy()`: removes all 4 listeners, resets `touchAction`. ✅
- `PTT_HOLD_DELAY` unused — **S1**. ⚠️

### use-gesture.ts ✅

- Proxy pattern prevents stale closure capture. ✅
- `update(newCallbacks)` replaces current callbacks live. ✅
- `destroy()` delegates to recognizer. ✅
- Returns `{ update, destroy }` — correct Svelte action contract. ✅

### VfoDisplay.svelte swipe ✅

- Gesture attached to `.vfo-freq` div with `use:gesture`. ✅
- Velocity thresholds: 100/1k/10kHz — reasonable for ham radio use. ✅
- `vibrate('tune')` with `navigator.vibrate` guard in `haptics.ts`. ✅
- `ontune?.(newFreq)` — delegates to parent (which calls `sendCommand`). ✅

### WaterfallCanvas.svelte pinch/pan — C3, W3

- DPR applied in `ResizeObserver` — Sprint 2 W3 fixed. ✅
- `hzPerPixel()` uses `getBoundingClientRect().width * dpr` — correct. ✅
- Pinch: `sendCommand('set_scope_span', ...)` — **C3** unknown command. ❌
- Pan accumulation pattern (defer command to `onPanEnd`) — good design. ✅
- `onPanEnd`: missing `receiver` — **W3**. ⚠️

### PttButton.svelte ✅ (with S2 noted)

- Hold-to-talk: 200ms `setTimeout` before activating TX — correct. ✅
- `setPointerCapture` prevents pointer loss if finger slides. ✅
- `onpointerleave` / `onpointercancel` both wired to `onPressCancel`. ✅
- Short press falls through to `onPtt()` (toggle) via hold timer cancel. ✅
- `touch-action: none` in CSS — prevents browser scroll interference. ✅
- Cancel checks `transmitting` not `pendingValue` — **S2** race risk. ⚠️
- Pulsing animation on TX — nice UX touch. ✅

### haptics.ts ✅

- `navigator.vibrate` guard (`if (!navigator.vibrate) return`) — correct. ✅
- Pattern durations reasonable: tap=10ms, ptt=50ms, tune=[10,30,10], error=[100,50,100]. ✅

---

## Architecture Compliance

| Spec requirement | Status |
|------------------|--------|
| `height: 100dvh` for full-screen layouts | ✅ Both layouts |
| Fixed bottom bar 56px | ✅ BottomBar |
| Touch targets ≥44px | ✅ All interactive controls |
| Svelte 5 `$state`/`$derived`/`$effect` | ✅ Throughout (W4 anti-pattern) |
| TypeScript strict, no `any` | ✅ |
| CSS design tokens only | ✅ No magic values |
| WS command format `sendCommand('name', {params})` | ❌ 3 wrong command names (C1, C2, C3) |
| Event listeners cleaned up on destroy | ✅ keyboard, gestures, WS; ❌ setInterval (W1) |
| Pointer events for touch (not touch events) | ✅ gesture-recognizer.ts |
| `touch-action: none` on gesture elements | ✅ PttButton CSS, gesture-recognizer element style |

---

## Prioritised Fix List

Fix in this order before merge:

1. **C1** — `keyboard.ts:94`: `ptt_on`/`ptt_off` → `ptt` with `{state: !ptt}` (1 line)
2. **C2** — `DesktopLayout.svelte:53`, `MobileLayout.svelte:58`: `set_dw` → `set_dual_watch` (2 lines)
3. **C3** — `WaterfallCanvas.svelte:64`: `set_scope_span` → `set_scope_fixed_edge` (3 lines, needs center+span math)
4. **W1** — `MobileLayout.svelte:36-45`: Fix timer pattern to match `StatusBar`
5. **W5** — `MobileLayout.svelte`: Add `<Toast />` so mobile users see notifications
6. **W4** — `DxClusterPanel.svelte:46`: `$derived(fn)` → `$derived.by(fn)`
7. **W2** — `MobileLayout.svelte:73-74`: Read model+status from stores
8. **W3** — `WaterfallCanvas.svelte:77`: Add `receiver` to pan-end `set_freq`
9. **S2** — `PttButton.svelte`: Add `pending && pendingValue` to cancel guard
10. **S1** — `gesture-recognizer.ts:27`: Remove unused `PTT_HOLD_DELAY` constant
