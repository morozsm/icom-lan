# Code Review: Sprint 1 — Transport + State Stores

**Date:** 2026-03-07
**Reviewer:** Claude (automated)
**PRs:** #159 (Transport layer), #160 (Svelte 5 state stores)
**Status:** ⛔ Blocked — 3 critical issues must be fixed before Sprint 2

---

## Summary

Sprint 1 delivered solid foundations: exponential backoff with heartbeat detection,
revision-gated state updates, and correct Svelte 5 `.svelte.ts` module patterns. The
Sprint 0 critical fixes (C1–C4) are all verified fixed. However, three new bugs were
introduced: the HTTP connection health indicator is permanently stuck at "connected"
after first successful poll, pending commands never time out, and the test fixtures
break `svelte-check`. There is also an internal type inconsistency in `protocol.ts`
that would produce a field-not-found bug when notifications arrive.

### Sprint 0 Regression Check

| Sprint 0 issue | Status |
|----------------|--------|
| C1 — stores in `.svelte.ts` | ✅ Fixed — all 6 stores use `.svelte.ts` |
| C2 — camelCase state fields | ✅ Frontend types already camelCase; backend fix assumed in place |
| C3 — `freqRanges` in capabilities | ✅ `Capabilities.freqRanges` correct |
| C4 — Vite WS proxy + ws-client URL | ✅ Fixed — 4 WS routes, default `/api/v1/ws` |
| W1 — App.svelte wiring | ✅ Fixed — capabilities fetch, polling, WS connect all wired |
| W2 — `setWsConnected()` in ws-client | ✅ Fixed — singleton `_ctrl.onStateChange` calls it |
| S2 — `crypto.randomUUID()` | ✅ Fixed — both `commands.svelte.ts` and `protocol.ts` use it |

---

## 🔴 Critical Issues

### C1 — `httpConnected` permanently stuck at `true` after first successful poll

**Files:** `frontend/src/App.svelte`, `frontend/src/lib/transport/http-client.ts`,
`frontend/src/lib/stores/connection.svelte.ts`

**Issue:** `App.svelte` calls `setHttpConnected(true)` only on successful state updates:

```typescript
// App.svelte
stopPolling = startPolling((state) => {
  setRadioState(state);
  setHttpConnected(true);   // ← only on success
});
```

`startPolling` silently swallows all fetch errors:

```typescript
// http-client.ts
} catch {
  // network errors are transient — don't crash the app
}
```

`setHttpConnected(false)` is called **nowhere** in the codebase. Once the first
poll succeeds, `httpConnected` is permanently `true`. If the backend goes down,
`getConnectionStatus()` returns `'partial'` (WS drops → `wsConnected = false`)
instead of `'disconnected'`. Users see misleading connection status.

**Fix:** Track consecutive failures in `startPolling`. After N failed polls (e.g. 3),
call `setHttpConnected(false)`:

```typescript
let consecutiveErrors = 0;
const ERROR_THRESHOLD = 3;

try {
  const state = await fetchState();
  consecutiveErrors = 0;
  setHttpConnected(true);   // ← move here from App.svelte
  if (state.revision > lastRevision) { ... }
} catch {
  consecutiveErrors++;
  if (consecutiveErrors >= ERROR_THRESHOLD) {
    setHttpConnected(false);
  }
}
```

Remove `setHttpConnected(true)` from `App.svelte` callback — `startPolling` should
own this responsibility entirely.

---

### C2 — Pending commands never time out

**File:** `frontend/src/lib/stores/commands.svelte.ts`

**Issue:** `PendingCommand.timeoutMs = 5000` is stored but never enforced.
There is no `setTimeout` anywhere in the codebase that calls `failCommand()`.
Commands accumulate permanently in the queue with status `'pending'`. The
`hasPending()` derived value will return `true` forever after the first command
that isn't explicitly acked or failed. Any UI indicator tied to it (spinner,
disabled controls) will never clear.

```typescript
// commands.svelte.ts — addCommand() creates command but never schedules timeout
export function addCommand(type: string, payload: unknown): PendingCommand {
  const cmd: PendingCommand = {
    id: crypto.randomUUID(),
    // ...
    timeoutMs: 5000,   // ← stored but ignored
  };
  commands.push(cmd);
  return cmd;   // ← no setTimeout(failCommand, 5000)
}
```

**Fix:** Schedule timeout enforcement in `addCommand`:

```typescript
export function addCommand(type: string, payload: unknown): PendingCommand {
  const cmd: PendingCommand = { /* ... */ };
  commands.push(cmd);
  setTimeout(() => {
    const current = commands.find((c) => c.id === cmd.id);
    if (current?.status === 'pending') {
      current.status = 'failed';
    }
  }, cmd.timeoutMs);
  return cmd;
}
```

---

### C3 — `http-client.test.ts` fixture fails TypeScript type checking

**File:** `frontend/src/lib/transport/__tests__/http-client.test.ts:6-45`

**Issue:** `makeState()` in the HTTP client tests returns a `ServerState` object
that is missing all the extended fields that are declared as **required** in
`state.ts`:

```typescript
// state.ts — all required (no ?)
powerLevel: number;
scanning: boolean;
tuningStep: number;
overflow: boolean;
// ... 25 more required fields
scopeControls: ScopeControls;
```

```typescript
// http-client.test.ts — makeState() omits all of the above
function makeState(revision: number): ServerState {
  return {
    revision,
    // ...main, sub, connection only
    // NO powerLevel, scanning, scopeControls, etc.
  };
}
```

`svelte-check` and `tsc` will report type errors on this file. CI will fail.

Note: `radio.test.ts` has a correct `makeState()` that includes all fields. The
http-client test file should use the same complete fixture.

**Fix:** Either copy the complete fixture from `radio.test.ts` into a shared
`tests/fixtures.ts`, or make all extended `ServerState` fields optional with `?`.
Making them optional is the correct long-term design (not all radio models have
all fields), but requires updating the type and all places that assume required fields.

---

## 🟡 Warnings

### W1 — `NotificationMessage.text` contradicts `WsIncoming` `message` field

**File:** `frontend/src/lib/types/protocol.ts`

**Issue:** The same server notification is typed in two incompatible ways within
the same file:

```typescript
// WsIncoming union — uses "message"
| { type: 'notification'; level: string; message: string }

// NotificationMessage interface — uses "text"
export interface NotificationMessage extends WsMessage {
  type: 'notification';
  level: 'info' | 'warning' | 'error';
  text: string;   // ← different field name!
}
```

When the backend sends a notification, it uses exactly one field name. Whichever
interface a component uses, the other field will be `undefined`. Sprint 2 Toast
component will be broken by this.

**Fix:** Decide on one field name (check the actual backend WS handler — likely
`message`), align both types, and delete the duplicate.

---

### W2 — `disconnect()` fires state handlers twice

**File:** `frontend/src/lib/transport/ws-client.ts:82-90`

**Issue:** In `disconnect()`, `ws.close()` is called while `intentionalClose = true`.
This triggers the `onclose` callback synchronously (in real browsers: next event loop
tick, but still fires), which calls `setState('disconnected')`. Then `disconnect()`
continues and calls `setState('disconnected')` again:

```typescript
disconnect() {
  this.intentionalClose = true;
  this._clearTimers();
  this.ws?.close();              // → triggers onclose → setState('disconnected') [1]
  this.ws = null;
  this.setState('disconnected'); // → setState('disconnected') [2] — duplicate!
  this.attempt = 0;
}
```

For the singleton `_ctrl`, this means `setWsConnected(false)` is called twice on
every intentional disconnect. Any component or effect depending on `wsConnected`
fires twice unnecessarily.

**Fix:** In `disconnect()`, remove the manual `this.setState('disconnected')` call
and rely solely on the `onclose` handler. Set `this.ws = null` before calling `close()`
so `onclose` sees the null already set:

```typescript
disconnect() {
  this.intentionalClose = true;
  this._clearTimers();
  const ws = this.ws;
  this.ws = null;
  ws?.close();       // onclose fires, sees intentionalClose=true, no reconnect
  this.attempt = 0;
}
```

---

### W3 — `connect()` guard ignores `CONNECTING` state — risk of double WebSocket

**File:** `frontend/src/lib/transport/ws-client.ts:43-45`

**Issue:**

```typescript
connect(url: string) {
  if (this.ws?.readyState === WebSocket.OPEN) return;  // ← only OPEN is guarded
  this.url = url;
  this.intentionalClose = false;
  this._open();
}
```

If `connect()` is called while `this.ws.readyState === WebSocket.CONNECTING`
(during the reconnect window before the socket opens), a second `WebSocket` is
created. Both try to connect to the same URL. One will succeed and the other will
close, triggering a spurious reconnect loop.

This is realistically triggered if: app code calls `connect()` in a Svelte `onMount`
that fires twice due to StrictMode or HMR, or if a component mounts that also calls
`connect()`.

**Fix:**

```typescript
connect(url: string) {
  const rs = this.ws?.readyState;
  if (rs === WebSocket.OPEN || rs === WebSocket.CONNECTING) return;
  // ...
}
```

---

### W4 — Server restart would permanently freeze UI (revision counter reset)

**File:** `frontend/src/lib/stores/radio.svelte.ts:15-20`

**Issue:** `setRadioState` rejects any state where `state.revision <= lastRevision`:

```typescript
export function setRadioState(state: ServerState): void {
  if (state.revision > lastRevision) {
    lastRevision = state.revision;
    radioState = state;
  }
}
```

If the Python backend restarts and its revision counter resets to 0 (or any value
below the frontend's `lastRevision`), all subsequent state updates are silently
discarded. The UI permanently shows stale state from before the restart. No error
is logged, no reconnect is triggered.

This is a real operational scenario: power cycle the radio, restart the backend.

**Fix:** Detect revision resets. A revision that drops from a high value to 0 is
a server restart, not a stale packet:

```typescript
export function setRadioState(state: ServerState): void {
  const isReset = lastRevision > 10 && state.revision < lastRevision / 2;
  if (state.revision > lastRevision || isReset) {
    lastRevision = state.revision;
    radioState = state;
  }
}
```

Or expose a `resetRadioState()` function and call it from the WS disconnect handler.

---

### W5 — `scope_data` in JSON message union is structurally impossible

**File:** `frontend/src/lib/types/protocol.ts:14-16`

**Issue:**

```typescript
export type WsIncoming =
  | { type: 'scope_data'; data: ArrayBuffer }  // ← this cannot arrive as JSON
  | { type: 'dx_spot'; spot: DxSpot }
  // ...
```

Scope data is sent as **binary WebSocket frames** (ArrayBuffer), routed to
`binaryHandlers`. Binary frames cannot be JSON-parsed. Including `scope_data`
in the JSON discriminated union is wrong — it can never be received via
`JSON.parse()`, so any code that tries to narrow `WsMessage` to `scope_data`
via `msg.type === 'scope_data'` will never match.

**Fix:** Remove `scope_data` from `WsIncoming`. The binary scope channel is
handled via `WsChannel.onBinary()`, not `onMessage()`.

---

### W6 — No tests for `audio.svelte.ts` or `capabilities.svelte.ts`

**Files:** `frontend/src/lib/stores/__tests__/` (directory)

**Issue:** 4 of 6 store test files exist. `audio.svelte.ts` and
`capabilities.svelte.ts` have zero test coverage:

```
commands.test.ts    ✅ 9 tests
connection.test.ts  ✅ 8 tests
radio.test.ts       ✅ 11 tests
ui.test.ts          ✅ 7 tests
audio.test.ts       ❌ MISSING
capabilities.test.ts ❌ MISSING
```

`capabilities.svelte.ts` has non-trivial logic: `hasDualReceiver()` reads from
the nested `capabilities.capabilities[]` array (confusing field naming);
`getSupportedFilters()` returns `[]` until `setCapabilities()` is called.
None of this is tested.

`audio.svelte.ts` `setVolume()` has clamping logic (`Math.max(0, Math.min(100, ...)`)
that should be tested with boundary values.

**Fix:** Add `audio.test.ts` and `capabilities.test.ts` covering at least the
non-trivial cases.

---

### W7 — `App.svelte` startup failure is silent — blank screen with no error

**File:** `frontend/src/App.svelte:11-16`

**Issue:**

```svelte
void (async () => {
  const caps = await fetchCapabilities();   // ← if this throws, everything stops
  setCapabilities(caps);
  stopPolling = startPolling((state) => { ... });
  connect('/api/v1/ws');
})();
```

If the backend is unreachable at startup, `fetchCapabilities()` throws. The `void`
operator discards the rejected Promise. `stopPolling` is never assigned, polling
never starts, WS never connects. The user sees a blank `<AppShell>` with no error
message, no retry logic, and no way to know the backend is down.

**Fix:** Wrap in try/catch with retry logic or at minimum set an error state:

```svelte
try {
  const caps = await fetchCapabilities();
  setCapabilities(caps);
} catch (err) {
  console.error('Failed to fetch capabilities:', err);
  // set an error state to show "Backend unreachable" in UI
  // then retry after N seconds
  return;
}
```

---

## 🔵 Suggestions

### S1 — `WsIncoming` discriminated union is dead code

**File:** `frontend/src/lib/types/protocol.ts:13-22`

`WsIncoming` is defined but never used. `ws-client.ts` casts parsed messages to
the loose `WsMessage` type:

```typescript
const msg = JSON.parse(event.data as string) as WsMessage;
this.messageHandlers.forEach((h) => h(msg));
```

Message handlers receive `WsMessage`, not `WsIncoming`. The well-typed discriminated
union provides no actual type safety anywhere in the codebase. Either use it
(change `MessageHandler` to `(msg: WsIncoming) => void`) or remove it to avoid
maintenance drift.

---

### S2 — `deriveFeatureFlags()` in `capabilities.ts` is unused

**File:** `frontend/src/lib/types/capabilities.ts:30-40`

`deriveFeatureFlags()` is exported but not imported anywhere. `capabilities.svelte.ts`
re-implements the same logic inline with slightly different naming (`hasTx()` checks
`capabilities.tx` boolean while `deriveFeatureFlags` checks the `'tx'` string in
`capabilities[]`). Delete the dead function or use it in `capabilities.svelte.ts`.

---

### S3 — `fetchInfo()` is unused

**File:** `frontend/src/lib/transport/http-client.ts:17-21`

`fetchInfo()` is exported but never called in `App.svelte` or anywhere else.
If the `InfoResponse` data (version, uptime) is not displayed in Sprint 1, the
function is dead code for now. Fine to keep if Sprint 2 uses it; add a comment
explaining intent.

---

### S4 — No jitter in exponential backoff

**File:** `frontend/src/lib/transport/ws-client.ts:15-18`

```typescript
function calcBackoff(attempt: number): number {
  return Math.min(BACKOFF_BASE_MS * 2 ** attempt, BACKOFF_MAX_MS);
}
```

Multiple browser tabs (or multiple clients) experiencing a simultaneous disconnect
(e.g., backend restart) will all reconnect at exactly 1s, 2s, 4s, ... causing
thundering herd. Add ±20% jitter:

```typescript
function calcBackoff(attempt: number): number {
  const base = Math.min(BACKOFF_BASE_MS * 2 ** attempt, BACKOFF_MAX_MS);
  return base * (0.8 + Math.random() * 0.4);
}
```

---

### S5 — Unbounded send queue — stale command storm on reconnect

**File:** `frontend/src/lib/transport/ws-client.ts:95-100`

Commands queued while disconnected are all sent on reconnect with no deduplication
or size limit. If the user changes frequency 50 times during a 30-second outage,
all 50 `set_freq` commands drain immediately on reconnect. The server processes
them all, wasting bandwidth and time.

Consider limiting queue size (drop oldest if over N=10) or deduplicating by command
type (last write wins for idempotent commands like `set_freq`).

---

## Architecture Compliance

| Spec requirement | Implemented? |
|-----------------|--------------|
| Svelte 5 `$state` / `$derived` in `.svelte.ts` | ✅ |
| Exponential backoff for WS reconnect | ✅ (no jitter — S4) |
| HTTP polling 200ms with revision gate | ✅ |
| Inflight guard (no pile-up) | ✅ |
| WS heartbeat / dead connection detection | ✅ (10s passive) |
| Send queue when disconnected + drain on connect | ✅ (unbounded — S5) |
| App initialisation sequence | ✅ (no error handling — W7) |
| `httpConnected` reflects HTTP health | ❌ never set to false (C1) |
| Command timeout enforcement | ❌ `timeoutMs` stored but ignored (C2) |
| Type checking passes | ❌ test fixture type error (C3) |
| Notification field name consistent | ❌ `text` vs `message` (W1) |
| All 6 stores tested | ❌ audio + capabilities missing (W6) |

---

## Prioritised Fix List for Sprint 2 Start

Fix in this order before merging Sprint 2:

1. **C1** — Add `setHttpConnected(false)` on polling failure threshold
2. **C2** — Enforce `timeoutMs` in `addCommand` with `setTimeout` → `failCommand`
3. **C3** — Fix `http-client.test.ts` `makeState()` to include all `ServerState` fields
4. **W1** — Align notification field: pick `message` or `text`, delete the other
5. **W2** — Fix double `setState('disconnected')` in `disconnect()`
6. **W3** — Guard `CONNECTING` state in `connect()`
7. **W6** — Add `audio.test.ts` and `capabilities.test.ts`
8. **W7** — Add error handling + retry in `App.svelte` startup sequence

Items W4, W5, S1–S5 can be addressed opportunistically during Sprint 2.
