# Code Review: Sprint 2 — Core Rendering, VFO, Controls

**Date:** 2026-03-08
**Reviewer:** Claude (automated)
**PRs:** #161 (Spectrum + Waterfall), #162 (VFO + Meters + ReceiverSwitch), #163 (Controls + Audio)
**Status:** ⛔ Blocked — 3 critical issues make every interactive control non-functional

---

## Summary

Sprint 2 delivered well-structured, visually coherent components. The Canvas rendering
engines are solid, the Svelte 5 rune patterns are correct throughout, and TypeScript
props interfaces are properly defined. However, there is one system-wide critical bug
that makes **every single WS command silently dropped by the server**, plus two additional
critical bugs: an unknown command and a phantom field. The math in the spectrum/waterfall
renderers is correct; a few off-by-one issues exist in the S-meter label logic.

---

## Sprint 1 Regression Check

| Sprint 1 issue | Status |
|----------------|--------|
| C1 — `setHttpConnected(false)` on polling failure | Not verified (not in Sprint 2 scope) |
| C2 — Command timeout enforcement | Not verified |
| C3 — `http-client.test.ts` fixture | Not verified |
| W1 — `NotificationMessage.text` vs `message` | ✅ Fixed — `NotificationMessage` now uses `message` |
| W2 — double `setState('disconnected')` in `disconnect()` | ✅ Fixed — manual call removed |
| W3 — guard `CONNECTING` in `connect()` | ✅ Fixed — both `OPEN` and `CONNECTING` guarded |
| W5 — `scope_data` in JSON union | ✅ Fixed — removed from `WsIncoming` |

---

## 🔴 Critical Issues

### C1 — ALL WS commands are silently dropped: wrong message envelope format

**Files:** Every component that calls `sendCommand()` — `SpectrumPanel.svelte`,
`BandSelector.svelte`, `ModeSelector.svelte`, `FilterSelector.svelte`,
`FeatureToggles.svelte`, `AudioControls.svelte`, `PttButton.svelte`,
`DesktopLayout.svelte`

**Issue:** The backend `ControlHandler._handle_text()` dispatches on `msg.get("type")`.
A `"cmd"` type routes to `_handle_command()`, which then reads `msg.get("name")` for
the command name and `msg.get("params")` for parameters. The expected wire format is:

```json
{ "type": "cmd", "name": "set_freq", "id": "...", "params": { "freq": 14074000, "receiver": 0 } }
```

Every component calls `sendCommand()` with a flat object where `type` is the command name:

```typescript
// BandSelector.svelte:32 — WRONG
sendCommand({ type: 'set_freq', id: makeCommandId(), freq: band.defaultHz, receiver: receiverIdx });

// PttButton.svelte:22 — WRONG
sendCommand({ type: 'ptt', id: makeCommandId(), state: next });
```

The backend receives `{type: 'set_freq', ...}` and falls through to the `else` branch
in `_handle_text()` which logs `"control: unknown message type: 'set_freq'"` and discards
it. No response is sent. No error is visible to the user. Every single user interaction
(tune, mode change, filter, PTT, volume) is silently discarded.

**Fix:** Either:

Option A (recommended) — Wrap in `sendCommand()` itself so callers don't need to know:

```typescript
// ws-client.ts
export function sendCommand(name: string, params: Record<string, unknown>, id?: string): boolean {
  return _ctrl.send({
    type: 'cmd',
    name,
    id: id ?? crypto.randomUUID(),
    params,
  });
}
```

Then callers become: `sendCommand('set_freq', { freq: 14074000, receiver: 0 })`.

Option B — Fix all call sites to use the envelope:

```typescript
sendCommand({ type: 'cmd', name: 'set_freq', id: makeCommandId(), params: { freq: band.defaultHz, receiver: receiverIdx } });
```

Option A is strongly preferred — it's a single change and prevents regression.

Note: `CMD_PTT_ON = 'ptt_on'` and `CMD_PTT_OFF = 'ptt_off'` in `protocol.ts` are also
wrong — the backend command is `"ptt"` with a `state: bool` parameter, not two separate
commands. These constants are unused but should be removed to avoid confusion.

---

### C2 — `set_active_receiver` is not a valid backend command

**File:** `frontend/src/components/layout/DesktopLayout.svelte:50-54`

**Issue:**

```typescript
function handleReceiverSwitch(receiver: 'MAIN' | 'SUB') {
  sendCommand({
    type: 'set_active_receiver',
    id: makeCommandId(),
    receiver,
  });
}
```

`"set_active_receiver"` does not exist in `ControlHandler._COMMANDS`. Even after
fixing C1 (envelope format), the server would respond with `unknown_command: 'set_active_receiver'`.

Looking at the backend, selecting the active VFO is done via `"select_vfo"` with a
`vfo: "A" | "B"` parameter:

```python
# handlers.py:654-657
case "select_vfo":
    vfo = str(params.get("vfo", "A"))
    q.put(SelectVfo(vfo))
    return {"vfo": vfo}
```

**Fix:** Replace with the correct command:

```typescript
function handleReceiverSwitch(receiver: 'MAIN' | 'SUB') {
  const vfo = receiver === 'MAIN' ? 'A' : 'B';
  // After fixing C1: sendCommand('select_vfo', { vfo })
  sendCommand({ type: 'cmd', name: 'select_vfo', id: makeCommandId(), params: { vfo } });
}
```

---

### C3 — `set_af_mute` and `set_comp` are not valid backend commands

**File:** `frontend/src/components/audio/AudioControls.svelte:23`,
`frontend/src/components/controls/FeatureToggles.svelte:25`

**Issue:** Two commands sent by Sprint 2 components do not exist in `_COMMANDS`:

```typescript
// AudioControls.svelte:23
sendCommand({ type: 'set_af_mute', id: makeCommandId(), on: !muted, receiver: receiverIdx });

// FeatureToggles.svelte:25
sendCommand({ type: 'set_comp', id: makeCommandId(), on: !comp });
```

Neither `"set_af_mute"` nor `"set_comp"` appear in `ControlHandler._COMMANDS` or
`_enqueue_command`. Both would be silently dropped even after fixing C1.

`set_af_mute` is a client-side audio mute (browser mutes the audio stream) — the
backend has no such command. The `toggleMute()` call in `onMute()` is correct for
local audio, but sending a WS command for it is wrong.

`set_comp` (compressor) has no backend implementation in the current command set.

**Fix for `set_af_mute`:** Remove the `sendCommand` call. `toggleMute()` handles
client-side mute. If radio-level AF mute is needed, it requires a backend implementation first.

**Fix for `set_comp`:** Either implement `set_comp` in the backend (requires `SetCompressor`
command dataclass and handler case), or remove the button until the backend supports it.

---

## 🟡 Warnings

### W1 — `SpectrumPanel` leaks the scope WebSocket channel on unmount

**File:** `frontend/src/components/spectrum/SpectrumPanel.svelte:79-108`

**Issue:** `onMount` opens a scope WebSocket via `scopeCh.connect('/api/v1/scope')`.
The cleanup function only calls `unsubBinary()` and `unsubMsg()` — it does not call
`scopeCh.disconnect()`. After the component unmounts (e.g., switching to mobile layout
or navigating away), the scope WebSocket stays open indefinitely. `getChannel('scope')`
returns the same `WsChannel` singleton, so subsequent mounts call `connect()` while
already connected — which is correctly guarded — but the channel is never freed.

If `SpectrumPanel` is ever unmounted while the app is running (fullscreen toggle would
not trigger this, but layout switching would), scope data continues to arrive and is
simply discarded, wasting bandwidth.

**Fix:** Call `scopeCh.disconnect()` in the cleanup:

```typescript
return () => {
  unsubBinary();
  unsubMsg();
  scopeCh.disconnect();   // add this
};
```

---

### W2 — `SpectrumPanel` click-to-tune does not specify receiver

**File:** `frontend/src/components/spectrum/SpectrumPanel.svelte:67-71`

**Issue:**

```typescript
function handleTune(hz: number): void {
  const freq = Math.round(hz);
  if (freq <= 0) return;
  sendCommand({ type: 'set_freq', id: makeCommandId(), freq });
}
```

No `receiver` parameter is included. The backend defaults to receiver 0 (MAIN). If the
user is operating with SUB as the active receiver, clicking the waterfall to tune always
tunes MAIN instead. The VFO display shows frequency updates on MAIN while the user
expected SUB to change.

**Fix:** Read the active receiver from the store:

```typescript
import { getRadioState } from '../../lib/stores/radio.svelte';

function handleTune(hz: number): void {
  const freq = Math.round(hz);
  if (freq <= 0) return;
  const receiverIdx = getRadioState()?.active === 'SUB' ? 1 : 0;
  sendCommand({ type: 'cmd', name: 'set_freq', id: makeCommandId(), params: { freq, receiver: receiverIdx } });
}
```

---

### W3 — `WaterfallCanvas` does not apply `devicePixelRatio` scaling

**File:** `frontend/src/components/spectrum/WaterfallCanvas.svelte:44-52`

**Issue:**

```typescript
const ro = new ResizeObserver((entries) => {
  const rect = entries[0]?.contentRect;
  if (!rect) return;
  const w = Math.max(1, Math.floor(rect.width));
  const h = Math.max(1, Math.floor(rect.height));
  canvas.width = w;
  canvas.height = h;
  renderer?.resize(w, h);
});
```

`SpectrumCanvas` correctly multiplies dimensions by `window.devicePixelRatio` and calls
`ctx.setTransform(dpr,0,0,dpr,0,0)`. `WaterfallCanvas` does not — it sets physical canvas
pixels equal to CSS pixels. On a 2× Retina display, the waterfall renders at half the
physical resolution of the spectrum directly above it. The mismatch is visible as the
waterfall looking blurry compared to the sharp spectrum line.

The waterfall renderer uses direct `putImageData()` so DPR handling is slightly more complex
(the image data must match the physical pixel dimensions), but the fix is the same as for
`SpectrumCanvas`:

```typescript
const dpr = window.devicePixelRatio || 1;
canvas.width = Math.round(w * dpr);
canvas.height = Math.round(h * dpr);
renderer?.resize(canvas.width, canvas.height);
```

Note: `pixelToFreq()` must then receive `e.clientX - rect.left` scaled by `dpr` as well,
otherwise click-to-tune calculates the wrong pixel position.

---

### W4 — `SMeter` S9+40 boundary uses a magic number instead of `S_UNIT`

**File:** `frontend/src/components/meters/SMeter.svelte:24-26`

**Issue:**

```typescript
if (above <= S_UNIT) return 'S9+10';      // ≤17 → correct
if (above <= 2 * S_UNIT) return 'S9+20';  // ≤34 → correct
if (above <= 59) return 'S9+40';          // ≤59 → wrong magic number
return 'S9+60';
```

`S_UNIT = 17`. The S9+40 boundary should be `above <= 3 * S_UNIT` (≤51) and S9+60 at
`above <= 4 * S_UNIT` (≤68). The magic `59` makes the S9+40 band 25 raw units wide
instead of 17, and S9+60 starts at raw=212 instead of raw=204. Values from 205-212 are
incorrectly labelled S9+40 when they should be S9+60.

Additionally, the scale comment says `S9+40=212` and `S9+60=237`, but `237 = 153 + 84 = 153 + 4*21`,
not `153 + 4*17 = 221`. The comment at line 10-11 was apparently derived from a different
scale and then the code was written to partially match it. The entire above-S9 region needs
to be anchored consistently to `S_UNIT`.

**Fix:**

```typescript
if (above <= S_UNIT) return 'S9+10';
if (above <= 2 * S_UNIT) return 'S9+20';
if (above <= 3 * S_UNIT) return 'S9+40';
return 'S9+60';
```

---

### W5 — `FeatureToggles` reads `rx?.agc` which may be stale for AGC display

**File:** `frontend/src/components/controls/FeatureToggles.svelte:13`

**Issue:**

```typescript
let agc = $derived(rx?.agc ?? null);
```

`agc` is read from the active receiver state (`ReceiverState.agc?: number`). This is
display-only — there is no toggle button for AGC. However, ATT and PRE are also display-only
(no toggle buttons in the component) but they show current values. If ATT or PRE need
to be changed, the user has no way to do so from this component. The architecture document
shows ATT and PRE as interactive toggles (`[NB] [NR] [ATT] [PRE]`), but the component
renders them as read-only `value-badge` spans.

This is a scope gap, not a bug, but worth noting: clicking ATT/PRE badges does nothing.
The document implies they should cycle through attenuation levels (0/6/12/18 dB for ATT,
1/2 for PRE on IC-7610).

---

### W6 — `VfoDisplay` always shows "MAIN"/"sub" badge regardless of VFO label

**File:** `frontend/src/components/vfo/VfoDisplay.svelte:101-105`

**Issue:**

```svelte
{#if active}
  <span class="active-badge">MAIN</span>
{:else}
  <span class="sub-badge">sub</span>
{/if}
```

The badge always says "MAIN" or "sub" regardless of the `label` prop ("VFO A" / "VFO B").
In a split scenario where SUB is active, the SUB display shows "MAIN" and the MAIN display
shows "sub". This is semantically confusing — "MAIN"/"sub" refers to which is active, but
the label prop already conveys which VFO this display represents.

The architecture document suggests the active indicator should use "MAIN" / "sub" terminology
consistently, but it would be clearer if the badge said "ACTIVE" (or used an indicator dot)
rather than duplicating the receiver role name.

This is a minor UX issue but could confuse operators who are used to "VFO A active" semantics.

---

### W7 — `BandSelector` missing `2m` and `70cm` bands

**File:** `frontend/src/components/controls/BandSelector.svelte:13-25`

**Issue:** The `BANDS` array includes HF bands and 6m but omits the two VHF/UHF bands
the IC-7610 supports. The architecture document's band list explicitly includes
`2m=144MHz` and `70cm=430MHz`. The capabilities check in `docs/plans/2026-03-07-ui-architecture.md`
section 2.1 shows the backend returns `freq_ranges` including HF 30kHz-60MHz and 6m 50-54MHz.
The IC-7610 also covers 144MHz and 430MHz.

Without these bands, users on VHF/UHF have no quick band switch — they must type the
frequency manually via FreqEntry.

**Fix:** Add the missing bands (check `getCapabilities().freqRanges` to determine what the
connected radio actually supports before showing them):

```typescript
{ name: '2m',   defaultHz: 144_200_000, minHz: 144_000_000, maxHz: 148_000_000 },
{ name: '70cm', defaultHz: 430_000_000, minHz: 430_000_000, maxHz: 440_000_000 },
```

---

### W8 — `SpectrumCanvas` creates gradient object on every render frame

**File:** `frontend/src/lib/renderers/spectrum-renderer.ts:101-104`

**Issue:**

```typescript
const grad = ctx.createLinearGradient(0, 0, 0, height);
grad.addColorStop(0, fillColor);
grad.addColorStop(1, 'rgba(30,58,138,0.02)');
ctx.fillStyle = grad;
```

`ctx.createLinearGradient()` allocates a new `CanvasGradient` object on every call to
`renderSpectrum()`. This runs at RAF frequency (up to 60 fps), creating ~60 objects/second
that immediately become garbage. On mobile the GC pressure is measurable.

The gradient only changes when `fillColor` or `height` changes — both of which are rare.

**Fix:** Cache the gradient inside the renderer and recreate only when dimensions or
`fillColor` change. Since `renderSpectrum` is a stateless function, the caller
(`SpectrumCanvas.svelte`) should either cache it or the function should accept an
optional pre-built gradient parameter. The simplest fix is a module-level WeakMap
keyed on the context:

```typescript
// Or just accept this as a minor perf issue for now and document it.
// More impactful: skip rendering when data hasn't changed (no $effect deduplication currently).
```

---

### W9 — `WaterfallCanvas` `pixelToFreq()` uses CSS pixel coordinates, not physical pixels

**File:** `frontend/src/components/spectrum/WaterfallCanvas.svelte:36-38`,
`frontend/src/lib/renderers/waterfall-renderer.ts:146-150`

**Issue:** `handleClick` passes `e.clientX - rect.left` (CSS pixels) to `pixelToFreq()`,
which divides by `this.width` (canvas physical pixels set equal to CSS pixels, as per W3).
This is only accidentally correct because DPR is not applied. If W3 is fixed (DPR scaling
applied), CSS pixel coordinates must be multiplied by DPR before passing to `pixelToFreq()`,
or `pixelToFreq()` must accept CSS coordinates and internally scale.

This is a dependency: fix W3 first, then verify the click math.

---

### W10 — `VfoDisplay` `onmodechange` prop is declared but never dispatched

**File:** `frontend/src/components/vfo/VfoDisplay.svelte:13, 23`

**Issue:**

```typescript
interface Props {
  // ...
  onmodechange?: (mode: string) => void;  // declared
}

let { ..., ontune }: Props = $props();    // onmodechange is destructured but never used
```

`onmodechange` is destructured (implicitly, as it's not in the destructure list — it's
silently ignored). The component has no mode selector UI. `DesktopLayout` passes an
`onmodechange` handler:

```typescript
onmodechange={(m) => handleModeChange('MAIN', m)}
```

This handler is never called because no event is ever dispatched. Mode changes only
happen via `ModeSelector`, not per-VFO. The prop is dead code that creates a false
impression of per-VFO mode selection capability.

**Fix:** Remove `onmodechange` from the `Props` interface and from `DesktopLayout`'s
prop passing, or implement a click-on-mode-label interaction that opens a modal.

---

## 🔵 Suggestions

### S1 — `FreqEntry` quick-freq list is hardcoded FT8 frequencies only

**File:** `frontend/src/components/vfo/FreqEntry.svelte:56-62`

The quick-access frequencies (3.573, 7.074, 14.074, 21.074, 28.074 MHz) are all FT8
frequencies. Operators on CW, SSB, or RTTY get no quick access. These should be
configurable or derived from the current mode, or at minimum include common CW/SSB
calling frequencies alongside the FT8 defaults.

---

### S2 — `SpectrumCanvas` `$effect` re-renders on `options` reference change even if values are identical

**File:** `frontend/src/components/spectrum/SpectrumCanvas.svelte:34-36`

```typescript
$effect(() => {
  if (data !== null || options) scheduleRender();
});
```

`options` is a `$derived` object reconstructed on every `centerHz`/`spanHz` change in
`SpectrumPanel`. Svelte 5 does object identity comparison, not deep equality. If the
derived options object is reconstructed with the same values (e.g., same centerHz after
a server state re-poll that didn't change the scope), this effect fires unnecessarily.
At 200ms polling intervals with 60fps RAF, this is minor but worth noting. Consider
memoizing the options object with explicit equality checks.

---

### S3 — `DxOverlay` key collision when two spots have same callsign+frequency

**File:** `frontend/src/components/spectrum/DxOverlay.svelte:36`

```svelte
{#each positioned as { spot, pct } (spot.dx + spot.freq)}
```

The key `spot.dx + spot.freq` concatenates a string and number, which could collide:
`"JA1"` + `"4076000"` = `"JA14076000"` could equal `"JA14"` + `"076000"` = `"JA14076000"`.
Use a more robust key:

```svelte
{#each positioned as { spot, pct } (`${spot.dx}@${spot.freq}@${spot.spotter}`)}
```

---

### S4 — `PowerMeter` receives raw watts but backend state field is `powerLevel` (raw 0-255)

**File:** `frontend/src/components/layout/DesktopLayout.svelte:123`,
`frontend/src/components/meters/PowerMeter.svelte`

**Issue:**

```typescript
// DesktopLayout.svelte
<PowerMeter power={state?.powerLevel ?? 0} swr={0} />
```

`PowerMeter` renders `{power}W` and computes fill as `power / maxPower`. If `powerLevel`
from the backend is a raw 0-255 value (as with S-meter), then the display would show
"255W" at full power and `maxPower=100` would produce fill >100%.

Check the backend `radio_state.py` to confirm whether `powerLevel` is already in watts
or is a raw 0-255 value like `s_meter`. If it's raw, a conversion function is needed,
similar to the S-meter's `sMeterLabel()`.

---

### S5 — `CMD_PTT_ON` / `CMD_PTT_OFF` constants are wrong and unused

**File:** `frontend/src/lib/types/protocol.ts:62-63`

```typescript
export const CMD_PTT_ON = 'ptt_on';
export const CMD_PTT_OFF = 'ptt_off';
```

The backend PTT command is `"ptt"` with `params: { state: bool }`, not `"ptt_on"` /
`"ptt_off"`. These constants are not used anywhere. Remove them before someone uses
them and sends an `unknown_command` error silently.

---

### S6 — No `2m`/`70cm` band awareness in `activeBand` derived value

**File:** `frontend/src/components/controls/BandSelector.svelte:29`

Even after adding 2m/70cm to `BANDS` (W7), if the radio is tuned to 144 MHz and
capabilities don't include those bands in the BANDS array, `activeBand` would be `null`
and no button would be highlighted. This is fine for out-of-band frequencies but should
be considered when adding the VHF/UHF bands.

---

### S7 — `ReceiverSwitch` `dualWatch` prop displayed but not clickable

**File:** `frontend/src/components/controls/ReceiverSwitch.svelte:33-35`

The Dual Watch badge is display-only. Turning DW on/off requires a `set_dual_watch`
command, but there is no button for it in this component. The architecture document shows
DW as a toggle. Either add a toggle here or document that DW is controlled elsewhere.

---

### S8 — `WaterfallRenderer.destroy()` does not null-out the canvas context reference

**File:** `frontend/src/lib/renderers/waterfall-renderer.ts:159-163`

```typescript
destroy(): void {
  this.destroyed = true;
  this.rowBuf = null;
  this.rowData = null;
  // this.ctx still references the canvas context
}
```

After `destroy()`, `this.ctx` holds a reference to the `CanvasRenderingContext2D` which
transitively keeps the canvas element alive. Setting `this.ctx = null` (with a type cast)
after setting `this.destroyed = true` allows the canvas to be GC'd sooner.

---

## Canvas / Rendering Math Verification

### Spectrum renderer — math is correct

- Grid lines: 6 horizontal (H_LINES=5 → 0 to 5 inclusive, 6 lines), 11 vertical.
  This is intentional — the extra line at the boundary closes the grid box. ✅
- Frequency labels: `startHz = centerHz - spanHz/2`, labels at `startHz + (i/V_LINES)*spanHz` for i=0..10. ✅
- Amplitude mapping: `amp = data[idx] / 160`, `y = height * (1 - amp)`, 0→bottom, 160→top. ✅
- Auto-scale: not implemented, `refLevel` is in options but unused. The architecture
  document mentions it as `refLevel: number` (reserved). This is acceptable for Sprint 2. ⚪

### Waterfall renderer — math is correct

- `pushRow()` scrolls with `drawImage(canvas, 0, 0, w, h-1, 0, 1, w, h-1)` — copies
  rows 0..h-2 to rows 1..h-1, effectively shifting down. ✅
- New row placed at y=0 via `putImageData(rowBuf, 0, 0)`. ✅
- `pixelToFreq(x) = centerHz - spanHz/2 + (x/width)*spanHz` — linear mapping,
  correct for center-mode scope. ✅
- Color LUT built once, referenced per-frame, no allocations in hot path. ✅

### Scope frame parser — offsets are correct

Backend `encode_scope_frame` layout (16 bytes):
```
0:      MSG_TYPE_SCOPE (0x01)
1:      receiver
2:      mode
3-6:    start_freq_hz (uint32 LE)
7-10:   end_freq_hz   (uint32 LE)
11-12:  seq_u16       (uint16 LE)
13:     flags
14-15:  pixel_count   (uint16 LE)
16+:    pixels
```

`parseScopeFrame` reads: byte 0 (magic), byte 1 (receiver), bytes 3-6 (startFreq uint32 LE),
bytes 7-10 (endFreq uint32 LE), bytes 14-15 (pixelCount uint16 LE). All offsets match. ✅

The mode byte at offset 2 is not read by the parser. This is acceptable — the component
uses mode from the radio state store, not from the scope frame. ✅

### DX overlay positioning — math is correct

```typescript
pct: ((s.freq - startFreq) / (endFreq - startFreq)) * 100
```

Linear mapping within visible spectrum range, clamped by filter condition `s.freq >= startFreq && s.freq <= endFreq`. ✅
CSS `left: {pct}%` with `transform: translateX(-50%)` centers the badge on the frequency. ✅

### VFO digit step math — correct

```typescript
const step = Math.pow(10, position);
const newFreq = freq + delta * step;
```

Position 0=1Hz, 1=10Hz, ..., 5=100kHz, 6=1MHz, etc. `Math.pow(10, position)` gives
the correct step size. ✅

### FreqEntry conversion — correct

```typescript
onconfirm?.(Math.round(mhz * 1_000_000));
```

`parseFloat(inputStr)` treats input as MHz, multiply by 1e6 for Hz, round to nearest Hz. ✅
Guard: `mhz > 0 && mhz < 1` — wait, `isValid = parsedHz > 0 && parsedHz < 1_000_000_000` = <1GHz. ✅

---

## WS Command Format Audit (against `handlers.py`)

| Component | Sends | Backend expects | Match? |
|-----------|-------|-----------------|--------|
| All components | `{type: 'set_freq', freq, receiver}` | `{type:'cmd', name:'set_freq', params:{freq, receiver}}` | ❌ C1 |
| PttButton | `{type: 'ptt', state: bool}` | `{type:'cmd', name:'ptt', params:{state: bool}}` | ❌ C1 |
| AudioControls | `{type: 'set_af_mute', ...}` | command does not exist | ❌ C3 |
| FeatureToggles | `{type: 'set_comp', ...}` | command does not exist | ❌ C3 |
| DesktopLayout | `{type: 'set_active_receiver', ...}` | command does not exist | ❌ C2 |
| DesktopLayout | `{type: 'set_freq', receiver: 'MAIN'}` | `params.receiver` expects `int` (0 or 1), not string | ❌ type mismatch |

**Note on receiver type:** `DesktopLayout.handleTune` passes `receiver: 'MAIN'` (string)
directly in the command object. After C1 is fixed, the backend does `int(params.get("receiver", 0))`
which would throw `ValueError: invalid literal for int() with base 10: 'MAIN'`.
`BandSelector`, `ModeSelector`, `FilterSelector`, `FeatureToggles`, `AudioControls` all
correctly compute `receiverIdx` as `0 | 1`. `DesktopLayout.handleTune` passes the string
`'MAIN'` or `'SUB'` — this needs to be converted: `const rx = receiver === 'MAIN' ? 0 : 1`.

---

## Architecture Compliance

| Spec requirement | Implemented? |
|-----------------|--------------|
| Svelte 5 `$state`/`$derived`/`$effect` in `.svelte.ts` | ✅ correct throughout |
| TypeScript props interfaces | ✅ all components |
| CSS design tokens used | ✅ no magic colors/spacing |
| Server state read-only in components | ✅ all stores via getters |
| WS command format matches backend | ❌ C1 — wrong envelope |
| ResizeObserver updates canvas physical dimensions | ✅ SpectrumCanvas, ❌ WaterfallCanvas (W3) |
| DPR scaling applied to canvas | ✅ SpectrumCanvas, ❌ WaterfallCanvas (W3) |
| RAF loop cleaned up on destroy | ✅ SpectrumCanvas |
| Waterfall channel disconnected on destroy | ❌ W1 |
| PTT is server-confirmed (no optimistic) | ✅ PttButton correctly waits |
| ReceiverSwitch checks capabilities | ✅ `hasDualReceiver` prop from parent |
| Band frequencies correct | ✅ HF+6m correct, ⚠️ 2m+70cm missing (W7) |

---

## Prioritised Fix List for Sprint 3 Start

Fix in this order before merging Sprint 3:

1. **C1** — Fix WS command envelope in `sendCommand()` (single fix, unblocks everything)
2. **C2** — Replace `set_active_receiver` with `select_vfo` + string→vfo mapping
3. **C3** — Remove `set_af_mute` WS call; remove or backend-implement `set_comp`
4. **C1 sub** — Fix `DesktopLayout.handleTune` receiver type: `'MAIN'/'SUB'` → `0/1`
5. **W3** — Apply DPR scaling to `WaterfallCanvas` (then verify W9 click math)
6. **W1** — Add `scopeCh.disconnect()` in `SpectrumPanel` cleanup
7. **W2** — Add receiver to `SpectrumPanel.handleTune`
8. **W4** — Fix S9+40 boundary: `above <= 59` → `above <= 3 * S_UNIT`
9. **W10** — Remove dead `onmodechange` prop from `VfoDisplay` and `DesktopLayout`
10. **S5** — Remove `CMD_PTT_ON`/`CMD_PTT_OFF` constants
11. **W7** — Add 2m/70cm bands (gated on capabilities check)

Items W5, W6, W8, S1-S4, S6-S8 can be addressed opportunistically during Sprint 3.
