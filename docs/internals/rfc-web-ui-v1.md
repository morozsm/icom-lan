# RFC: Web UI v1 — Real-Time Scope & Control Interface

**Status:** Draft
**Created:** 2026-02-27
**Author:** KN4KYD

## Overview

Add a built-in web interface to icom-lan that provides real-time spectrum/waterfall display,
radio control, and audio streaming — accessible from any browser on the local network.

**Design principles:**
- Single HTML file, zero frontend dependencies, no build step
- Hybrid WebSocket protocol: JSON for commands, binary for streams
- Protocol-first: the contract must survive Python→Rust backend migration
- Canvas2D rendering (WebGL deferred to v2 if needed)
- Backpressure-aware: server drops frames, never blocks

## Architecture

```
Browser                              icom-lan server
┌──────────────────┐                ┌──────────────────────────┐
│  Single HTML     │   HTTP GET /   │  Static file server      │
│  + vanilla JS    │◄──────────────►│  (index.html)            │
│                  │                │                          │
│  Control panel   │   WS /api/v1/ │  Control handler         │
│  (freq/mode/PTT) │◄─────────────►│  (JSON cmd/response)     │
│                  │   ws           │                          │
│  Canvas2D scope  │   WS /api/v1/ │  Scope handler           │
│  Canvas2D wfall  │◄─────────────►│  (binary scope frames)   │
│                  │   scope        │                          │
│  S/SWR/ALC bars  │   WS /api/v1/ │  Meters handler          │
│                  │◄─────────────►│  (binary meter frames)   │
│                  │   meters       │                          │
│  Web Audio API   │   WS /api/v1/ │  Audio handler           │
│                  │◄─────────────►│  (binary Opus/PCM)       │
│                  │   audio        │                          │
└──────────────────┘                └──────────┬───────────────┘
                                               │
                                               │ UDP :50001-3
                                               ▼
                                    ┌──────────────────┐
                                    │   Icom Radio     │
                                    └──────────────────┘
```

### WebSocket Channels

| Endpoint | Purpose | Data format | Update rate |
|----------|---------|-------------|-------------|
| `/api/v1/ws` | Commands, events, state | JSON text | On-demand |
| `/api/v1/scope` | Spectrum & waterfall | Binary frames | 15-30 fps |
| `/api/v1/meters` | S-meter, SWR, ALC, Power | Binary frames | 10-20 fps |
| `/api/v1/audio` | RX/TX audio | Binary Opus/PCM | Continuous |

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve `index.html` (single-file UI) |
| GET | `/api/v1/info` | Server info: version, radio model, protocol version |
| GET | `/api/v1/capabilities` | Radio capabilities: freq ranges, modes, has_scope, has_audio |

These are cacheable, stateless endpoints. No authentication in v1 (LAN-only).

## Control WebSocket: `/api/v1/ws`

JSON-only channel for commands, responses, events, and state synchronization.

### Connection Lifecycle

```
Client                              Server
  │                                    │
  │──── WS connect ───────────────────►│
  │◄─── hello (JSON) ─────────────────│  auto-sent on connect
  │──── subscribe (JSON) ─────────────►│
  │◄─── state snapshot (JSON) ─────────│  full current state
  │◄─── scope frames (binary) ─────────│  continuous stream
  │◄─── events (JSON) ─────────────────│  freq/mode changes
  │──── commands (JSON) ──────────────►│  set freq/mode/PTT
  │◄─── command responses (JSON) ──────│
  │                                    │
  │──── unsubscribe / close ──────────►│
```

### Frame Multiplexing

WebSocket natively distinguishes text and binary frames:

- **Text frames** → JSON (commands, events, responses)
- **Binary frames** → scope data (and future extensions)

### JSON Messages (Text Frames)

All JSON messages have a `type` field.

#### Server → Client

**hello** (sent automatically on connect):
```json
{
  "type": "hello",
  "proto": 1,
  "server": "icom-lan",
  "version": "0.8.0",
  "radio": "IC-7610",
  "capabilities": ["scope", "audio", "tx"]
}
```

**state** (full state snapshot, sent after subscribe):
```json
{
  "type": "state",
  "data": {
    "freq_a": 14074000,
    "freq_b": 7074000,
    "mode": "USB",
    "filter": "FIL1",
    "ptt": false,
    "power": 100,
    "smeter": 42,
    "swr": 10,
    "scope": {
      "mode": 0,
      "start_freq": 14000000,
      "end_freq": 14350000,
      "receiver": 0
    }
  }
}
```

**event** (state change notification):
```json
{"type": "event", "name": "freq_changed", "data": {"vfo": "A", "freq": 14074500}}
{"type": "event", "name": "smeter", "data": {"value": 67}}
{"type": "event", "name": "ptt", "data": {"state": true}}
{"type": "event", "name": "scope_meta", "data": {"mode": 0, "start_freq": 14000000, "end_freq": 14350000}}
```

**response** (to a command):
```json
{"type": "response", "id": "a1b2", "ok": true, "result": {"freq": 14074000}}
{"type": "response", "id": "a1b3", "ok": false, "error": "invalid_param", "message": "Frequency out of range"}
```

#### Client → Server

**subscribe**:
```json
{"type": "subscribe", "id": "s1", "streams": ["scope", "meters"], "scope_fps": 30, "scope_receiver": 0}
```

**unsubscribe**:
```json
{"type": "unsubscribe", "id": "s2", "streams": ["scope"]}
```

**command** (request-response, `id` is correlation ID):
```json
{"type": "cmd", "id": "a1b2", "name": "set_freq", "params": {"vfo": "A", "freq": 14074000}}
{"type": "cmd", "id": "a1b3", "name": "set_mode", "params": {"mode": "USB"}}
{"type": "cmd", "id": "a1b4", "name": "ptt", "params": {"state": true}}
```

Available commands (v1):
- `set_freq` — params: `{vfo, freq}`
- `set_mode` — params: `{mode}` (USB, LSB, CW, AM, FM, RTTY, etc.)
- `set_filter` — params: `{filter}` (FIL1, FIL2, FIL3)
- `ptt` — params: `{state}` (true/false)
- `set_power` — params: `{level}` (0-255)
- `set_att` — params: `{db}` (0-45, 3dB steps)
- `set_preamp` — params: `{level}` (0, 1, 2)
- `vfo_swap` — no params
- `vfo_equalize` — no params

## Scope WebSocket: `/api/v1/scope`

Dedicated channel for high-frequency spectrum/waterfall data (binary only).

### Binary Scope Frames

Fixed-size header + variable-length pixel data.

```
Offset  Size  Field           Description
──────  ────  ──────────────  ─────────────────────────────────
0       1     msg_type        0x01 = scope_frame
1       1     receiver        0 = Main, 1 = Sub
2       1     mode            0=center, 1=fixed, 2=scroll-C, 3=scroll-F
3       4     start_freq      uint32 LE, Hz
7       4     end_freq        uint32 LE, Hz
11      2     sequence        uint16 LE, wrapping counter
13      1     flags           bit 0: out_of_range
14      2     pixel_count     uint16 LE (typically 475)
16      N     pixels          uint8[], amplitude 0-160
```

Total: 16 + N bytes (~491 bytes for 475 pixels).

At 30fps: ~14.7 KB/s per receiver. Dual receiver (Main+Sub): ~29.4 KB/s.

### Backpressure

The server MUST implement frame dropping:

1. Track outbound buffer size per client
2. When buffer exceeds HIGH_WATERMARK (e.g., 5 frames / ~2.5KB):
   - Drop scope frames (newest replaces queued)
   - NEVER drop command responses or events
3. When buffer drains below LOW_WATERMARK: resume normal delivery
4. Client detects drops via `sequence` gaps — do NOT interpolate, just skip

### Reconnection

- Client handles reconnection with exponential backoff
- On reconnect: re-send `subscribe` message
- Server does NOT persist subscriptions across connections
- State snapshot is always sent after subscribe

## Meters WebSocket: `/api/v1/meters`

Dedicated channel for real-time meter data (S-meter, SWR, ALC, Power, etc.).

Separate from scope and control to keep each channel focused and allow independent
subscription and rate control.

### Binary Meter Frames

```
Offset  Size  Field        Description
──────  ────  ───────────  ─────────────────────────────────
0       1     msg_type     0x20 = meter_frame
1       2     sequence     uint16 LE, wrapping counter
3       1     count        number of meters in this frame
4       N×3   meters[]     array of meter readings:
                             [0] meter_id  (uint8)
                             [1] value_lo  (uint8, low byte)
                             [2] value_hi  (uint8, high byte)
```

### Meter IDs

| ID | Meter | Range | Notes |
|----|-------|-------|-------|
| 0x01 | S-meter (Main) | 0-255 | RX signal strength, main receiver |
| 0x02 | S-meter (Sub) | 0-255 | RX signal strength, sub receiver (IC-7610, IC-9700) |
| 0x03 | Power (Po) | 0-255 | TX output power |
| 0x04 | SWR | 0-255 | TX SWR (only valid during TX) |
| 0x05 | ALC | 0-255 | TX ALC (only valid during TX) |
| 0x06 | COMP | 0-255 | Speech compressor level |
| 0x07 | Id | 0-255 | PA drain current |
| 0x08 | Vd | 0-255 | PA drain voltage |
| 0x09 | TEMP | 0-255 | PA temperature |

### Bandwidth

9 meters × 3 bytes + 4 bytes header = **31 bytes/frame**.
At 20fps: **620 bytes/sec** — negligible.

### Control (JSON text frames on meters WS)

```json
{"type": "meters_start", "meters": ["smeter", "power", "swr", "alc"], "fps": 20}
{"type": "meters_stop"}
```

Server sends meter frames only after `meters_start`. Client can request subset of meters
and desired update rate. Server may send at a lower rate if the radio doesn't provide
data that fast.

---

## Audio WebSocket: `/api/v1/audio`

Separate WebSocket to avoid Head-of-Line blocking with scope data.

### Binary Audio Frames

```
Offset  Size  Field           Description
──────  ────  ──────────────  ─────────────────────────────────
0       1     msg_type        0x10 = audio_rx, 0x11 = audio_tx
1       1     codec           0x01 = Opus, 0x02 = PCM16
2       2     sequence        uint16 LE
4       2     sample_rate     uint16 LE (e.g., 48000 / 100 = 480)
6       1     channels        1 = mono, 2 = stereo
7       1     frame_ms        frame duration in ms (20)
8       N     payload         codec-specific audio data
```

### Audio Control (JSON text frames on audio WS)

```json
{"type": "audio_start", "direction": "rx", "codec": "opus", "sample_rate": 48000}
{"type": "audio_stop", "direction": "rx"}
{"type": "audio_start", "direction": "tx", "codec": "opus", "sample_rate": 48000}
{"type": "audio_stop", "direction": "tx"}
```

### PTT + TX Audio Sequence

```
Client                              Server
  │                                    │
  │── cmd: ptt on (main WS) ─────────►│
  │◄── response: ok ──────────────────│  radio keys up
  │── audio_start tx (audio WS) ─────►│
  │── audio frames (binary) ──────────►│  continuous
  │── audio_stop tx (audio WS) ──────►│
  │── cmd: ptt off (main WS) ────────►│
  │◄── response: ok ──────────────────│  radio unkeys
```

**Rule:** PTT ON must be confirmed before sending TX audio. PTT OFF must be sent AFTER last audio frame.

### Browser Playback (RX)

```javascript
// AudioWorklet with ring buffer for jitter compensation
// Target buffer: 100-200ms (5-10 frames at 20ms each)
// Underrun: silence. Overrun: drop oldest.
```

## Frontend Architecture

### Single HTML File

```
index.html (~500-800 lines)
├── <style>           CSS (dark theme, responsive)
├── <div id="app">    Layout
│   ├── #controls     Frequency, mode, VFO, PTT
│   ├── #scope        Canvas — spectrum graph
│   ├── #waterfall    Canvas — waterfall display
│   ├── #meters       S-meter, SWR, ALC, Power
│   └── #status       Connection status, info
└── <script>          JavaScript
    ├── WebSocket connection + reconnect
    ├── Binary frame parser
    ├── Scope renderer (Canvas2D)
    ├── Waterfall renderer (Canvas2D, scrolling ImageData)
    ├── Color map (LUT Uint32Array[161])
    ├── Audio handler (AudioWorklet)
    ├── Control panel handlers
    └── State management
```

### Waterfall Rendering

```javascript
// Pre-computed color LUT (dark blue → cyan → yellow → red → white)
const COLOR_LUT = new Uint32Array(161);

// Cached ImageData for zero-alloc hot path
const lineImageData = wfCtx.createImageData(475, 1);
const lineBuf32 = new Uint32Array(lineImageData.data.buffer);

function renderWaterfallLine(pixels) {
  // Scroll down by 1 pixel (GPU-accelerated compositing)
  wfCtx.drawImage(wfCanvas, 0, 1);
  
  // Draw new line at top
  for (let i = 0; i < pixels.length; i++) {
    lineBuf32[i] = COLOR_LUT[pixels[i]];
  }
  wfCtx.putImageData(lineImageData, 0, 0);
}
```

### Click-to-Tune

```javascript
wfCanvas.addEventListener('click', (e) => {
  const x = e.offsetX;
  const ratio = x / wfCanvas.width;
  const freq = currentStartFreq + ratio * (currentEndFreq - currentStartFreq);
  sendCommand('set_freq', { vfo: 'A', freq: Math.round(freq) });
});
```

### Frequency Metadata per Waterfall Line

Store per-line metadata for accurate click-to-tune on historical waterfall data:

```javascript
const wfMeta = new Array(WATERFALL_HEIGHT);
// On each new line: wfMeta.pop(); wfMeta.unshift({startFreq, endFreq});
```

Clear waterfall on significant frequency range change.

## Implementation Plan

### Sprint 1: Foundation (3-4 days)
- [ ] WebSocket server (asyncio, no external deps)
- [ ] HTTP static file serving
- [ ] `/api/v1/info` and `/api/v1/capabilities` endpoints
- [ ] Protocol message handling (hello, subscribe, commands)
- [ ] Binary scope frame serialization
- [ ] Backpressure / frame dropping
- [ ] CLI: `icom-lan serve --web [--port 8080]`

### Sprint 2: Scope & Waterfall UI (3-4 days)
- [ ] index.html scaffold (dark theme, responsive layout)
- [ ] WebSocket connection with auto-reconnect
- [ ] Binary frame parser in JS
- [ ] Spectrum graph (Canvas2D)
- [ ] Waterfall display (Canvas2D, scrolling)
- [ ] Color map (classic dark blue → red)
- [ ] Frequency axis labels
- [ ] Click-to-tune on waterfall

### Sprint 3: Radio Control UI (2-3 days)
- [ ] Frequency display + tuning (click/type)
- [ ] Mode selector (USB/LSB/CW/AM/FM)
- [ ] S-meter bar (real-time)
- [ ] PTT button (with safety confirm)
- [ ] Power/SWR/ALC meters
- [ ] VFO A/B switch
- [ ] Attenuator / preamp controls

### Sprint 4: Audio (3-5 days)
- [ ] Audio WebSocket server (separate endpoint)
- [ ] Opus frame delivery (binary)
- [ ] Browser: AudioWorklet with ring buffer
- [ ] RX audio playback
- [ ] TX audio capture (getUserMedia)
- [ ] PTT + TX audio state machine
- [ ] Jitter buffer tuning (100-200ms)

### Sprint 5: Polish (2-3 days)
- [ ] Mobile-responsive layout
- [ ] Dark/light theme toggle
- [ ] Connection status indicator
- [ ] Error handling and user feedback
- [ ] Protocol conformance tests
- [ ] Documentation

## Total Estimate

| Sprint | Scope | Days |
|--------|-------|------|
| 1. Foundation | Server + protocol | 3-4 |
| 2. Scope UI | Waterfall + spectrum | 3-4 |
| 3. Controls | Freq/mode/meters | 2-3 |
| 4. Audio | RX/TX in browser | 3-5 |
| 5. Polish | Mobile, themes, tests | 2-3 |
| **Total** | | **13-19 days** |

## Future (v2)

- WebGL renderer for high-resolution waterfall
- WebRTC audio (for remote access over internet)
- Multi-user support (multiple browsers)
- PWA (installable, offline-capable shell)
- Dual waterfall (Main + Sub for IC-7610)
- Band stack / memory channels
- DX cluster overlay
- Dark/light/custom themes

## Protocol Versioning

- `proto: 1` — initial version (this RFC)
- New fields/commands can be added without version bump (backward compatible)
- Breaking changes require `proto: 2` and new `/api/v2/` endpoints
- Client checks `proto` in hello and shows upgrade notice if unsupported

## References

- [OpenWebRX](https://www.openwebrx.de/) — web SDR with waterfall (reference UX)
- [KiwiSDR](http://kiwisdr.com/) — browser-based SDR receiver
- [WebSDR](http://www.websdr.org/) — pioneer web-based radio
- [wfview](https://wfview.org/) — desktop reference for Icom LAN control
- Council brainstorm session (2026-02-27) — Opus, Sonnet, GPT-5.2, Gemini, GLM
