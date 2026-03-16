# Web Server

Built-in web UI and REST API.

## REST API — Endpoint Reference

### `GET /api/v1/info`

Version, model, connection status, and runtime capability summary.

```json
{
  "version": "0.12.0",
  "radio": "IC-7300",
  "model": "IC-7300",
  "capabilities": {
    "hasSpectrum": true,
    "hasAudio": true,
    "hasTx": true,
    "hasDualRx": false,
    "hasAttenuator": true,
    "hasPreamp": true,
    "hasTuner": false,
    "hasCw": true,
    "maxReceivers": 1,
    "tags": ["attenuator", "audio", "cw", "meters", "nb", "nr", "preamp", "rf_gain", "scope", "tx"],
    "modes": ["USB", "LSB", "CW", "CW-R", "AM", "FM", "RTTY", "RTTY-R"],
    "filters": ["FIL1", "FIL2", "FIL3"],
    "vfoScheme": "ab",
    "hasLan": false
  },
  "connection": {
    "rigConnected": true,
    "radioReady": true,
    "controlConnected": true
  }
}
```

#### New fields (Epic #251)

| Field | Type | Description |
|-------|------|-------------|
| `capabilities.vfoScheme` | `"ab"` \| `"main_sub"` | VFO labeling scheme. `"ab"` → VFO A/B; `"main_sub"` → MAIN/SUB |
| `capabilities.hasLan` | `bool` | Whether the radio has a LAN (Ethernet) port |
| `capabilities.maxReceivers` | `int` | Number of independent receivers (1 or 2) |
| `capabilities.modes` | `string[]` | Supported operating modes from rig profile |
| `capabilities.filters` | `string[]` | Supported IF filter names from rig profile |

---

### `GET /api/v1/state`

Current radio state snapshot. All keys are camelCase.

**Behavior change (Epic #251):** For single-receiver radios (`receiver_count < 2`),
the `sub` key is omitted from the response entirely. Dual-receiver radios (IC-7610)
still return both `main` and `sub`.

```json
{
  "main": { "freqHz": 14074000, "mode": "USB", "filter": 1, ... },
  "revision": 42,
  "updatedAt": "2026-03-15T10:00:00Z",
  "connection": { "rigConnected": true, "radioReady": true, "controlConnected": true }
}
```

Single-receiver response (IC-7300):

```json
{
  "main": { "freqHz": 7074000, "mode": "USB", "filter": 1, ... },
  "revision": 7,
  "updatedAt": "2026-03-15T10:00:00Z",
  "connection": { ... }
}
```

---

### `GET /api/v1/capabilities`

Full capabilities object including rig profile data.

```json
{
  "scope": true,
  "audio": true,
  "tx": true,
  "capabilities": ["attenuator", "audio", "cw", "meters", "nb", "nr", ...],
  "receivers": 1,
  "vfoScheme": "ab",
  "freqRanges": [
    {
      "label": "HF",
      "start": 30000,
      "end": 60000000,
      "bands": [
        { "name": "20m", "start": 14000000, "end": 14350000, "default": 14200000, "bsrCode": 5 },
        { "name": "60m", "start": 5250000, "end": 5450000, "default": 5357000 }
      ]
    }
  ],
  "modes": ["USB", "LSB", "CW", ...],
  "filters": ["FIL1", "FIL2", "FIL3"]
}
```

#### New fields (Epic #251)

| Field | Type | Description |
|-------|------|-------------|
| `receivers` | `int` | Receiver count from rig profile (1 or 2) |
| `vfoScheme` | `"ab"` \| `"main_sub"` | VFO labeling scheme |
| `freqRanges[].bands[].bsrCode` | `int` (optional) | Band Stack Register code used by Web UI `set_band` workflow |

---

### `set_band` command (WebSocket `/api/v1/ws`)

Control payload:

```json
{"type":"cmd","id":"42","name":"set_band","params":{"band":5}}
```

`band` is the numeric BSR code (typically from `freqRanges[].bands[].bsrCode`).
Backend behavior:

1. Attempts BSR recall (`0x1A 0x01 <band> 0x01`) and applies recalled freq/mode.
2. On recall failure, falls back to profile `default_hz` for matching `bsr_code`.
3. If no matching `bsr_code` exists, command acknowledges but no retune is applied.

## Modules

- `server.py` — asyncio HTTP/WebSocket server
- `handlers.py` — WebSocket command handlers
- `radio_poller.py` — State polling for /api/v1/state endpoint
- `websocket.py` — WebSocket connection management
- `protocol.py` — Web protocol types and messages
- `dx_cluster.py` — DX cluster integration

## REST API

See [Web UI Guide](../guide/web-ui.md) for endpoint documentation.

## See Also

- [Audio](audio.md)
- [Scope](scope.md)
