# Code Review: Sprint 0 — Svelte Scaffold + Backend Revision

**Date:** 2026-03-07
**Reviewer:** Claude (automated)
**PRs:** #157 (frontend scaffold), #158 (revision counter + `/api/v1/info`)
**Status:** ⛔ Blocked — critical issues must be fixed before Sprint 1

---

## Summary

Sprint 0 produced a solid architectural foundation (types, stores, transport, layouts) and
correct backend additions. However, there are **4 critical bugs** that would make the
application completely non-functional on day one of Sprint 1. Three are API schema
mismatches between backend and frontend. One is a fundamental Svelte 5 mistake that
breaks reactivity entirely.

---

## 🔴 Critical Issues

### C1 — Svelte 5 `$state` runes used in plain `.ts` files

**Files:** `frontend/src/lib/stores/radio.ts`, `audio.ts`, `ui.ts`, `connection.ts`,
`capabilities.ts`, `commands.ts`

**Issue:** All six store files use `$state()` runes in plain `.ts` files:

```typescript
// radio.ts — WRONG
let radioState = $state<ServerState | null>(null);
```

Svelte 5 runes are a **compiler-level feature**. The `@sveltejs/vite-plugin-svelte`
only processes `.svelte` files and `.svelte.ts` files (Svelte modules). Plain `.ts`
files are processed by esbuild/tsc, which never runs the Svelte compiler. At runtime,
`$state` is `undefined` → **ReferenceError**, app crashes immediately.

`svelte-check` will also reject these: the ambient `$state` type is declared but the
compiler transform that makes it reactive is never applied.

**Fix:** Rename all 6 store files from `.ts` to `.svelte.ts`:

```
radio.ts        → radio.svelte.ts
audio.ts        → audio.svelte.ts
ui.ts           → ui.svelte.ts
connection.ts   → connection.svelte.ts
capabilities.ts → capabilities.svelte.ts
commands.ts     → commands.svelte.ts
```

Then update all import paths in any file that imports from these stores. Also verify
that `svelte.config.js` extensions include `.svelte.ts` (default `@sveltejs/vite-plugin-svelte`
handles this, but worth checking).

---

### C2 — API schema mismatch: `/api/v1/state` field names

**Files:** `src/icom_lan/radio_state.py`, `frontend/src/lib/types/state.ts`

**Issue:** The backend serialises `RadioState` and `ReceiverState` via Python `asdict()`,
which produces **snake_case** field names. The frontend TypeScript interface declares
**camelCase** names. Every receiver field will be `undefined` in the UI.

| Backend (`asdict()` output) | Frontend type (`ReceiverState`) | Match? |
|-----------------------------|----------------------------------|--------|
| `freq` | `freqHz` | ❌ |
| `data_mode` | `dataMode` | ❌ |
| `s_meter` | `sMeter` | ❌ |
| `af_level` | `afLevel` | ❌ |
| `rf_gain` | `rfGain` | ❌ |
| `filter` | `filter` | ✅ |
| `att` | `att` | ✅ |
| `nb` | `nb` | ✅ |
| `nr` | `nr` | ✅ |
| `squelch` | `squelch` | ✅ |

Additionally, the connection status has a structural and naming mismatch:

| Backend (flat, top-level) | Frontend (`connection` object) | Match? |
|---------------------------|-------------------------------|--------|
| `connected` | `connection.rigConnected` | ❌ (name + nesting) |
| `radio_ready` | `connection.radioReady` | ❌ (name + nesting) |
| `control_connected` | `connection.controlConnected` | ❌ (nesting) |

Top-level global fields also differ:

| Backend | Frontend | Match? |
|---------|----------|--------|
| `dual_watch` | `dualWatch` | ❌ |
| `tuner_status` | `tunerStatus` | ❌ |

Backend returns `active` as the string it holds (likely `"MAIN"` / `"SUB"`). This
probably matches the frontend union type, but verify at runtime.

**Fix (choose one):**

Option A — Fix the backend: add a `to_camel_dict()` serialiser to `RadioState` /
`ReceiverState` that outputs camelCase and wraps connection fields into the
`connection` nested object. Update `_serve_state` to call it.

Option B — Fix the frontend: update `ServerState` / `ReceiverState` to use snake_case
and a flat `connected` / `radio_ready` / `control_connected` structure. Less ergonomic
in TypeScript.

Option A is strongly preferred — camelCase is idiomatic JSON/TypeScript.

Also, `freq` → `freqHz` needs careful thought: the backend field is named `freq` (Hz
implied), the frontend renamed it `freqHz` for explicitness. The serialiser rename must
be explicit here.

---

### C3 — API schema mismatch: `/api/v1/capabilities` field names

**Files:** `src/icom_lan/web/server.py:903`, `frontend/src/lib/types/capabilities.ts`

**Issue:** Backend returns `freq_ranges` (snake_case), frontend type declares `freqRanges`
(camelCase):

```python
# server.py
"freq_ranges": [
    {"start": 30000, "end": 60000000, "label": "HF"},
    ...
],
```

```typescript
// capabilities.ts
export interface Capabilities {
  freqRanges: FreqRange[];   // <-- camelCase
```

`fetchCapabilities()` will deserialise `freqRanges` as `undefined`.

**Fix:** Rename the backend key to `freqRanges` in `_serve_capabilities`.

---

### C4 — WebSocket proxy path mismatch

**Files:** `frontend/vite.config.ts`, `frontend/src/lib/transport/ws-client.ts`,
`src/icom_lan/web/server.py`

**Issue:** The WebSocket client connects to `/ws` by default:

```typescript
// ws-client.ts
export function connect(url: string = '/ws') {
```

The Vite proxy maps `/ws` → `ws://localhost:8080` (path preserved), so the
browser actually connects to `ws://localhost:8080/ws`. The backend serves
WebSocket at `/api/v1/ws`:

```python
# server.py
if path == "/api/v1/ws":
    handler = ControlHandler(...)
```

The path `/ws` does not match any backend WebSocket route → connection
immediately closed with "unknown channel" (close code 1008).

Note: the `/api` HTTP proxy has no `ws: true`, so WebSocket upgrades on
`/api/v1/ws` would also NOT be proxied there. The current proxy setup is
incomplete for all four WS channels.

**Fix:** Add path rewrites or separate WS proxy entries for each channel:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
    },
    '/api/v1/ws': {
      target: 'ws://localhost:8080',
      ws: true,
      changeOrigin: true,
    },
    '/api/v1/scope': {
      target: 'ws://localhost:8080',
      ws: true,
      changeOrigin: true,
    },
    '/api/v1/meters': {
      target: 'ws://localhost:8080',
      ws: true,
      changeOrigin: true,
    },
    '/api/v1/audio': {
      target: 'ws://localhost:8080',
      ws: true,
      changeOrigin: true,
    },
  },
},
```

Remove the now-dead `/ws` proxy entry. Update `ws-client.ts` default to
`'/api/v1/ws'`.

---

## 🟡 Warnings

### W1 — No app initialisation: polling never starts, WS never connects

**Files:** `frontend/src/App.svelte`, `frontend/src/main.ts`

**Issue:** `App.svelte` only renders `<AppShell />`. It never:
- Calls `fetchCapabilities()` and `setCapabilities()`
- Starts HTTP polling via `startPolling()`
- Calls `connect()` from `ws-client.ts`

All stores are permanently empty. The transport layer is dead code until
this wiring is added.

**Expected pattern** (to be added in Sprint 1):

```svelte
<!-- App.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchCapabilities, fetchState, startPolling } from './lib/transport/http-client';
  import { connect, addMessageHandler } from './lib/transport/ws-client';
  import { setCapabilities } from './lib/stores/capabilities.svelte';
  import { setRadioState } from './lib/stores/radio.svelte';
  import { setConnected, setWsConnected } from './lib/stores/connection.svelte';
  import AppShell from './components/layout/AppShell.svelte';

  onMount(async () => {
    const caps = await fetchCapabilities();
    setCapabilities(caps);
    const stop = startPolling(async () => {
      const state = await fetchState();
      setRadioState(state);
      setConnected(true);
    });
    connect('/api/v1/ws');
    return stop;
  });
</script>

<AppShell />
```

This review notes the gap — Sprint 1 should address it as the first task.

---

### W2 — `ws-client.ts` never updates connection store

**File:** `frontend/src/lib/transport/ws-client.ts:16-39`

**Issue:** `onopen` and `onclose` callbacks don't call `setWsConnected(true/false)`.
The `wsConnected` state in `connection.ts` is permanently `false`, even when the
WebSocket is open. Any UI that checks WS status will always show "disconnected".

```typescript
// ws-client.ts
ws.onopen = () => {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  // Missing: setWsConnected(true)
};

ws.onclose = () => {
  ws = null;
  reconnectTimer = setTimeout(() => connect(url), RECONNECT_DELAY_MS);
  // Missing: setWsConnected(false)
};
```

**Fix:** Import and call `setWsConnected` in both callbacks. Be careful about circular
imports (connection store → ws-client → connection store). Use a callback parameter or
an event emitter pattern if needed.

---

### W3 — Dual layout state: `AppShell` and `ui.ts` are independent

**Files:** `frontend/src/components/layout/AppShell.svelte`,
`frontend/src/lib/stores/ui.ts`

**Issue:** `AppShell.svelte` maintains its own `width` / `isMobile` reactive state.
The `ui.ts` store also has a `layout` field initialised from `window.innerWidth`.
These are completely separate — updating `setLayout()` in the store does not affect
what `AppShell` renders, and resizing the window does not update the store's
`layout` field.

When Sprint 1 components call `getUiState().layout` to decide behaviour, they'll see
a stale value.

**Fix:** `AppShell` should call `setLayout()` inside its resize handler, so there is
exactly one source of truth. Or remove the `layout` field from `ui.ts` and read from
`AppShell` via a Svelte context / prop.

---

### W4 — `index.html` uses Vite default title and favicon

**File:** `frontend/index.html`

**Issue:**
- Title is `"frontend"` (the package.json name)
- Favicon is `/vite.svg` (Vite branding)
- No `viewport-fit=cover` for iPhone safe areas (notch / Dynamic Island)

```html
<!-- current -->
<title>frontend</title>
<link rel="icon" type="image/svg+xml" href="/vite.svg" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
```

```html
<!-- should be -->
<title>IC-7610</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
```

The `viewport-fit=cover` is important for mobile — without it, the bottom bar could
be hidden behind the iPhone home indicator.

---

### W5 — `tokens.css` is missing `--space-5`

**File:** `frontend/src/styles/tokens.css`

**Issue:** The spacing scale jumps from `--space-4: 16px` to `--space-6: 24px`,
skipping `--space-5`. If any component uses `var(--space-5)`, it silently resolves
to the inherited value (or empty), not 20px.

```css
/* tokens.css */
--space-4: 16px;
/* --space-5 is missing */
--space-6: 24px;
```

**Fix:** Add `--space-5: 20px;` between them.

---

### W6 — Backend: modes and filters hardcoded in two places

**File:** `src/icom_lan/web/server.py:853-854, 907-908`

**Issue:** `["USB", "LSB", "CW", "AM", "FM", "RTTY", "CWR"]` and
`["FIL1", "FIL2", "FIL3"]` are duplicated verbatim in both `_serve_info` and
`_serve_capabilities`. If one is updated, the other won't be.

**Fix:** Extract to module-level constants at the top of `server.py`:

```python
_MODES = ["USB", "LSB", "CW", "AM", "FM", "RTTY", "CWR"]
_FILTERS = ["FIL1", "FIL2", "FIL3"]
```

---

## 🔵 Suggestions

### S1 — Duplicate `WsCommand` / `WsMessage` types

**Files:** `frontend/src/lib/types/protocol.ts`,
`frontend/src/lib/transport/protocol.ts`

**Issue:** `WsCommand` and `WsMessage` interfaces are defined in both files.
`ws-client.ts` imports from `transport/protocol.ts`. The `types/protocol.ts`
file has the richer version (with `AckMessage`, `ErrorMessage`, `NotificationMessage`
subtypes). These will diverge.

**Fix:** Delete `transport/protocol.ts`, move its unique additions (`CMD_*` constants,
`makeCommandId()`) into `types/protocol.ts`, and update `ws-client.ts` to import
from `types/protocol.ts`.

---

### S2 — `makeCommandId()` collision risk

**File:** `frontend/src/lib/transport/protocol.ts:24-26`

**Issue:**

```typescript
export function makeCommandId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
```

Two commands created in the same millisecond with the same random 7-char suffix
would collide. Browser `Math.random()` is not cryptographically strong.

**Fix:** Use `crypto.randomUUID()` which is available in all modern browsers:

```typescript
export function makeCommandId(): string {
  return crypto.randomUUID();
}
```

---

### S3 — `sendCommand` throws instead of queuing when disconnected

**File:** `frontend/src/lib/transport/ws-client.ts:48-53`

**Issue:**

```typescript
export function sendCommand(cmd: WsCommand) {
  if (ws?.readyState !== WebSocket.OPEN) {
    throw new Error('WebSocket not connected');
  }
  ws.send(JSON.stringify(cmd));
}
```

During the 2-second reconnect window, any user interaction (PTT, frequency change)
throws an unhandled error. The `PendingCommand` / `commands.ts` store was presumably
designed to handle this — commands should queue and drain on reconnect.

Consider returning a Promise and rejecting it after a timeout instead of throwing
synchronously. Or let callers check `isConnected()` and disable interactive controls
when disconnected.

---

### S4 — Desktop right-pane width is a magic number

**File:** `frontend/src/components/layout/DesktopLayout.svelte:38`

**Issue:**

```css
grid-template-columns: 1fr 320px;
```

`320px` is not a CSS token. If this value needs to change for different screen
sizes, it's scattered.

**Fix:** Add `--right-pane-width: 320px` to `tokens.css` and use it here.

---

### S5 — `AppShell` initial `window.innerWidth` is called synchronously on import

**File:** `frontend/src/components/layout/AppShell.svelte:7`

**Issue:**

```typescript
let width = $state(window.innerWidth);
```

This is fine for a fully client-side SPA — but if any test runner (e.g., Vitest
with JSDOM) imports this component without a full browser environment, it'll crash
with `window is not defined`. A defensive guard improves testability:

```typescript
let width = $state(typeof window !== 'undefined' ? window.innerWidth : 1024);
```

---

### S6 — `clearFinishedCommands` silently drops `failed` commands

**File:** `frontend/src/lib/stores/commands.ts:24-26`

**Issue:**

```typescript
export function clearFinishedCommands() {
  commands = commands.filter((c) => c.status === 'pending');
}
```

This removes both `acked` and `failed` commands. If the caller wants to log or
retry failed commands before clearing, they can't. The function name says "clear
finished" which is accurate — but document this explicitly or add a separate
`clearFailed()` function.

---

## Backend Review

### ✅ Revision counter (`radio_poller.py`)

- `_revision: int = 0` initialised correctly.
- `bump_revision()` called by `_on_radio_state_change` in `server.py`. Correct call site.
- `asyncio` is single-threaded → no race conditions, no need for locks. ✅
- `revision` property is read-only (no setter). ✅

### ✅ `/api/v1/info` endpoint

- Backward-compatible: legacy `server`, `version`, `proto`, `radio` fields preserved. ✅
- New structured `capabilities` and `connection` objects added. ✅
- Handles `radio is None` gracefully. ✅
- `wsClients: len(self._client_tasks)` is technically a count of all client tasks (including HTTP), not just WS clients. Minor inaccuracy — acceptable for now.

### ✅ `updatedAt` timezone

```python
d["updatedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
```

Uses `datetime.timezone.utc` (not the deprecated `datetime.utcnow()`). Correct.
Produces `+00:00` suffix. Frontend can parse it via `new Date(updatedAt)`. ✅

### ✅ Tests (`test_web_server_coverage.py`)

- 8 tests for the revision counter: start at 0, increments, monotonicity, state change trigger. ✅
- `_serve_state` output checked for `revision` (int) and `updatedAt` (parseable ISO 8601 with tzinfo). ✅
- `/api/v1/info` structured output tested. ✅
- Backward-compatible fields tested. ✅
- Edge case: `revision == 0` when no poller attached. ✅

Minor gap: no test for the case where `_serve_state` is called multiple times in the
same event loop tick to confirm `updatedAt` timestamps differ (nanosecond resolution
should make this fine in practice).

---

## Architecture Compliance

| Spec requirement | Implemented? |
|-----------------|--------------|
| `revision` counter in `/api/v1/state` | ✅ |
| `updatedAt` in `/api/v1/state` | ✅ |
| Svelte 5 + TypeScript scaffold | ✅ structure, ❌ runes |
| `$state` / `$derived` / `$effect` in stores | ❌ (wrong file extension) |
| HTTP polling 200ms with stale detection | ✅ transport code, ❌ not wired |
| WebSocket auto-reconnect (2s) | ✅ |
| CSS design system tokens | ✅ (minor: missing `--space-5`) |
| Desktop/mobile layouts | ✅ scaffold |
| `freqRanges` in capabilities response | ❌ (`freq_ranges`) |
| camelCase state fields | ❌ (snake_case from `asdict()`) |
| Connection nested object | ❌ (flat top-level) |

---

## Prioritised Fix List for Sprint 1 Start

Before writing any Sprint 1 features, fix in this order:

1. **C1** — Rename all stores to `.svelte.ts` and update imports
2. **C2** — Add camelCase serialiser to `RadioState.to_dict()` (or new method)
3. **C3** — Rename `freq_ranges` → `freqRanges` in `_serve_capabilities`
4. **C4** — Fix Vite proxy WS routes, update `ws-client.ts` default URL
5. **W1** — Wire up polling + WS connect in `App.svelte`
6. **W2** — Call `setWsConnected()` in `ws-client.ts` `onopen`/`onclose`
7. **W4** — Fix `index.html` title, favicon, viewport meta
8. **S1** — Consolidate duplicate `protocol.ts` files

Items W3, W5, W6, S2–S6 can be addressed opportunistically during Sprint 1.
