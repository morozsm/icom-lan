# Web UI

icom-lan ships with a built-in browser UI for live control, scope/waterfall, meters,
and RX/TX audio.

This page documents the **current implementation** (Svelte frontend + asyncio backend),
public interfaces, and operational workflows.

## Quick Start

```bash
# Default: bind all interfaces on port 8080
icom-lan web

# Explicit host/port
icom-lan web --host 0.0.0.0 --port 9090

# Require API/WebSocket auth token
icom-lan web --auth-token "change-me"
```

Open `http://<server-ip>:8080` (or your custom port).

## What Runs Where

| Layer | Implementation | Notes |
|------|----------------|-------|
| HTTP + WebSocket server | `src/icom_lan/web/server.py` | Pure asyncio, no external web framework |
| WS handlers | `src/icom_lan/web/handlers.py` | Per-channel handlers for control/scope/meters/audio |
| Frontend app | `frontend/` (Svelte + TypeScript) | Built assets are served from `icom_lan.web.static` by default |

The backend manages reconnect and recovery when the radio link drops; scope enable is deferred until `radio_ready` is true.

## Public HTTP Interface

| Method | Path | Purpose |
|-------|------|---------|
| `GET` | `/` | Serve UI entry page (`index.html`) |
| `GET` | `/api/v1/info` | Version, model, connection status, runtime capability summary |
| `GET` | `/api/v1/state` | Current radio state snapshot (camelCase, includes revision + updatedAt) |
| `GET` | `/api/v1/capabilities` | Capabilities, frequency ranges, supported modes/filters, scope/audio config |
| `GET` | `/api/v1/dx/spots` | Buffered DX spots |
| `GET` | `/api/v1/bridge` | Audio bridge status |

### Auth behavior (`--auth-token`)

- `GET /api/*` requires `Authorization: Bearer <token>`.
- WebSocket endpoints accept either:
  - `Authorization: Bearer <token>`, or
  - `?token=<token>` query parameter.
- Static files (`/`, JS, CSS, assets) are still served without token.

!!! note "Audio bridge control path"
    Runtime bridge activation is typically done from CLI flags
    (`icom-lan web --bridge ...` / `--bridge-rx-only`).

## WebSocket Channels

| Endpoint | Direction | Payload type | Purpose |
|---------|-----------|--------------|---------|
| `/api/v1/ws` | bidirectional | JSON text | Commands, responses, notifications, `state_update` stream |
| `/api/v1/scope` | server -> client | Binary | Scope/waterfall frames |
| `/api/v1/meters` | server -> client | Binary | Meter frames (`meters_start` / `meters_stop` control messages) |
| `/api/v1/audio` | bidirectional | JSON + Binary | RX stream + TX uplink |

## Control Channel Workflow (`/api/v1/ws`)

### Command envelope

```json
{"type":"cmd","id":"42","name":"set_freq","params":{"freq":14074000,"receiver":0}}
```

Server response:

```json
{"type":"response","id":"42","ok":true,"result":{"freq":14074000,"receiver":0}}
```

### Connection control messages

- `{"type":"radio_connect","id":"..."}`
- `{"type":"radio_disconnect","id":"..."}`

If backend recovery is already in progress, `radio_connect` returns:

```json
{"type":"response","ok":false,"error":"backend_recovering"}
```

### Common commands

- Tuning/control: `set_freq`, `set_mode`, `set_filter`, `set_band`, `ptt`
- RF/audio levels: `set_power`, `set_rf_gain`, `set_af_level`, `set_squelch`
- DSP/features: `set_nb`, `set_nr`, `set_digisel`, `set_ipplus`, `set_comp`
- Receiver/routing: `select_vfo`, `vfo_swap`, `vfo_equalize`, `set_dual_watch`
- Scope control: `switch_scope_receiver`, `set_scope_during_tx`, `set_scope_center_type`

## Audio Workflow and Constraints

### RX/TX lifecycle

1. Client enables RX:
   - `{"type":"audio_start","direction":"rx"}`
2. Client requests PTT ON on control channel (`ptt: true`).
3. Client enables TX stream:
   - `{"type":"audio_start","direction":"tx"}`
   - then sends binary TX frames to `/api/v1/audio`.
4. Client requests PTT OFF.
5. Backend stops TX stream and restarts RX stream.

### Important constraints

- Browser TX frames are ignored while PTT is OFF (frontend and backend both enforce this).
- IC-7610 LAN behavior is effectively half-duplex for web audio flow: after TX ends,
  RX is restarted explicitly by backend logic.
- If audio send blocks for too long, server closes stale audio WS path and client
  reconnect logic re-establishes the stream.

## Keyboard Shortcuts (Desktop)

| Key | Action |
|-----|--------|
| `F1`-`F11` | Jump to preset amateur bands (160m .. 6m) |
| `M` | Cycle mode through supported modes |
| `ArrowUp` / `ArrowRight` | Tune up by current step |
| `ArrowDown` / `ArrowLeft` | Tune down by current step |
| `Space` | Toggle PTT |
| `Escape` | Close frequency-entry modal |

## Operations Runbook

### Run with DX cluster overlays

```bash
icom-lan web --dx-cluster dxc.nc7j.com:7373 --callsign YOURCALL
```

### Run with custom UI assets

```bash
icom-lan web --static-dir /opt/icom-ui/dist
```

### Quick health checks

```bash
curl http://127.0.0.1:8080/api/v1/info
curl http://127.0.0.1:8080/api/v1/state
```

## Dynamic UI — Radio-Aware Controls

The Web UI adapts to the active radio's capabilities. Capabilities are fetched once
from `GET /api/v1/capabilities` on startup and cached in
`frontend/src/lib/stores/capabilities.svelte.ts`.

### VFO Labels

VFO button labels change based on the radio's VFO scheme:

| Radio | Scheme | Button A label | Button B label |
|-------|--------|----------------|----------------|
| IC-7610 | `main_sub` | **MAIN** | **SUB** |
| IC-7300 | `ab` | **VFO A** | **VFO B** |

The `vfoLabel()` function in the capabilities store drives this:

```typescript
// Returns "MAIN" or "VFO A" depending on active profile
vfoLabel('A')

// Returns "SUB" or "VFO B"
vfoLabel('B')
```

### Capability-Based UI Guards

Controls that depend on hardware features are automatically hidden or disabled when the
active radio profile doesn't support them:

| Control | Capability flag | Visible on IC-7610 | Visible on IC-7300 |
|---------|----------------|--------------------|--------------------|
| DIGI-SEL toggle | `digisel` | ✅ | ❌ hidden |
| IP+ toggle | `ip_plus` | ✅ | ❌ hidden |
| SUB receiver panel | `dual_rx` | ✅ | ❌ hidden |
| TX controls, PTT | `tx` | ✅ | ✅ |
| Audio RX/TX | `audio` | ✅ | ✅ |
| Scope/waterfall | `scope` | ✅ | ✅ |

Use `hasCapability(name)` to check for a capability in Svelte components:

```typescript
import { hasCapability } from '$lib/stores/capabilities.svelte';

// In a Svelte component template:
// {#if hasCapability('digisel')}
//   <DigiSelControl />
// {/if}
```

### State Endpoint and Receiver Count

`GET /api/v1/state` omits the `sub` receiver for single-receiver radios.
Frontend code should guard against the missing `sub` key rather than assuming it is
always present.

```typescript
// Safe receiver access
const sub = state.sub ?? null;
```

## Common Pitfalls for Developers

- **Capability-gated commands:** commands fail with `command_failed` if active profile
  does not expose required capability (for example, `set_rf_gain` on unsupported radios).
- **Receiver indexing:** many commands expect `receiver=0` (MAIN) or `receiver=1` (SUB)
  and validate against runtime profile receiver count.
- **`sub` may be absent:** `GET /api/v1/state` omits `sub` for single-receiver radios —
  always guard with a null check.
- **VFO commands:** use `select_vfo("A")` / `select_vfo("B")` regardless of scheme;
  the backend translates to the correct CI-V codes for the active profile.
- **Authoritative state source:** use `state_update` payloads as source of truth; optimistic
  UI updates can be overwritten by server state.
- **Scope recovery behavior:** scope enable/re-enable is deferred until `radio_ready=true`;
  all-zero scope frames trigger automatic re-enable attempts.

## Related Docs

- [CLI Reference](cli.md#web)
- [Troubleshooting](troubleshooting.md)
- [Web UI Protocol RFC (historical draft)](../internals/rfc-web-ui-v1.md)
- [Reliability semantics](../internals/reliability-semantics.md) — timeouts, cache TTLs, and `radio_ready` / connection state behavior.
