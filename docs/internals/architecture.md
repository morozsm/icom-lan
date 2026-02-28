# Architecture

## Overview

```
┌──────────────────────────────────────────────────────────┐
│                        icom-lan                          │
│                                                          │
│  ┌─────────┐   ┌──────────┐   ┌────────────────────┐    │
│  │   CLI   │   │  Web UI  │   │  Rigctld Server    │    │
│  │(cli.py) │   │(web/)    │   │  (rigctld.py)      │    │
│  └────┬────┘   └────┬─────┘   └────────┬───────────┘    │
│       └──────────────┼──────────────────┘                │
│                      │                                   │
│            ┌─────────┴──────────┐                        │
│            │     IcomRadio      │  ← Public API           │
│            │    (radio.py)      │     Unchanged surface   │
│            ├────────────────────┤                        │
│            │  Mixins:           │                        │
│            │  ┌───────────────┐ │                        │
│            │  │ControlPhase  │ │  _control_phase.py     │
│            │  │ (auth/connect)│ │  Auth → Token → Ports  │
│            │  ├───────────────┤ │                        │
│            │  │  CivRx       │ │  _civ_rx.py            │
│            │  │ (RX pump)    │ │  Drain-all + dispatch   │
│            │  ├───────────────┤ │                        │
│            │  │AudioRecovery │ │  _audio_recovery.py    │
│            │  │ (snapshot)   │ │  Snapshot/resume        │
│            │  └───────────────┘ │                        │
│            ├────────────────────┤                        │
│            │  ConnectionState   │  _connection_state.py  │
│            │  (FSM enum)        │                        │
│            ├────────────────────┤                        │
│            │  IcomCommander     │  commander.py          │
│            │  (priority queue)  │  IMMEDIATE/NORMAL/BG   │
│            ├────────────────────┤                        │
│            │  State Cache       │  Configurable TTL      │
│            │  (GET fallbacks)   │  10s freq, 30s power   │
│            └────────┬──────────┘                        │
│                     │                                   │
│         ┌───────────┼───────────────┐                   │
│         │           │               │                   │
│    ┌────┴─────┐ ┌───┴────┐  ┌──────┴──────┐            │
│    │ Control  │ │  CI-V  │  │   Audio     │            │
│    │Transport │ │Transport│  │ Transport   │            │
│    │ (:50001) │ │(:50002)│  │  (:50003)   │            │
│    └────┬─────┘ └───┬────┘  └──────┬──────┘            │
└─────────┼───────────┼──────────────┼────────────────────┘
          │   UDP     │   UDP        │   UDP
          ▼           ▼              ▼
  ┌─────────────────────────────────────────┐
  │            Icom Radio (IC-7610)          │
  │   Control    CI-V      Audio             │
  │   :50001    :50002    :50003             │
  └─────────────────────────────────────────┘
```

## Module Responsibilities

### `radio.py` — High-Level Public API (1549 lines)

The central orchestrator. `IcomRadio` inherits from three mixins and manages:

- **Three transport instances**: control (50001), CI-V (50002), audio (50003, lazy)
- **Commander integration**: enqueues CI-V operations with priorities and pacing
- **State cache**: GET command results cached with TTL, returned on timeout
- **Public API methods**: `get_frequency()`, `set_mode()`, etc. — all unchanged

### `_control_phase.py` — Connection Setup (452 lines)

`ControlPhaseMixin` handles the full handshake sequence:

- Discovery → Login → Token ACK → GUID extraction → Conninfo → Status
- **Optimistic ports**: uses default ports (control+1, control+2) immediately
- **Background status check**: reads status packet with 2s timeout; uses radio-reported
  ports if they differ from defaults
- **Local port reservation**: `socket.bind(("", 0))` for CI-V and audio (wfview-style)
- Token renewal (60s background task)

### `_civ_rx.py` — CI-V Receive Pump (418 lines)

`CivRxMixin` handles all incoming CI-V traffic:

- **Drain-all pattern**: processes ALL queued packets per iteration (not one-at-a-time)
- **Frame dispatch**: parses CI-V frames, routes to waiters or callbacks
- **Scope assembly**: reassembles multi-sequence 0x27 bursts into `ScopeFrame`
- **Stale waiter cleanup**: drops abandoned waiters to prevent resource leaks

### `_audio_recovery.py` — Audio Resilience (132 lines)

`AudioRecoveryMixin` handles audio stream lifecycle:

- Snapshot active audio state before disconnect
- Resume audio streams after reconnect
- Lazy audio transport initialization

### `_connection_state.py` — Connection FSM

`RadioConnectionState` enum: `DISCONNECTED` → `CONNECTING` → `AUTHENTICATING` →
`CONNECTED` → `DISCONNECTING`. Used for guard clauses and state assertions.

### `commander.py` — CI-V Command Queue

Serialized command execution layer:

- **Priority queue**: `IMMEDIATE` / `NORMAL` / `BACKGROUND`
- **Fire-and-forget**: SET commands don't wait for ACK (wfview-style)
- **GET timeout**: 2s with cache fallback
- **Pacing**: configurable inter-command delay (`ICOM_CIV_MIN_INTERVAL_MS`)
- **Dedupe**: background polling keys prevent duplicate requests

### `transport.py` — UDP Transport

Low-level asyncio UDP handler. Each `IcomTransport` instance manages:

- UDP socket via `asyncio.DatagramProtocol`
- Discovery handshake (Are You There → I Am Here → Are You Ready)
- Keep-alive pings (500ms interval)
- Sequence tracking with gap detection and retransmit requests
- Packet queue (`asyncio.Queue[bytes]`) for consumers

### `web/` — Built-in Web UI

WebSocket-based browser interface:

- `server.py` — aiohttp web server, WebSocket handler management
- `handlers.py` — scope, meters, audio, and control WebSocket handlers
- `static/index.html` — single-page app with Canvas2D rendering
- Audio: PCM16 binary frames over WebSocket, Web Audio API playback

### `commands.py` — CI-V Encoding/Decoding

Pure functions for building and parsing CI-V frames. No state, no I/O.

### `auth.py` — Authentication

Icom credential encoding, login/conninfo packet construction.

## Data Flow

### CI-V Command (GET)

```
radio.get_frequency()
  → commander.enqueue(priority=NORMAL)
  → build CI-V frame: FE FE 98 E0 03 FD
  → _civ_transport.send_tracked()
  → UDP → radio:50002
  → response arrives in _packet_queue
  → _civ_rx_loop drains queue → parse → match waiter → return
  → (on timeout: return cached value if available)
```

### CI-V Command (SET, fire-and-forget)

```
radio.set_frequency(14_074_000)
  → commander.enqueue(priority=NORMAL)
  → build CI-V frame: FE FE 98 E0 05 ... FD
  → _civ_transport.send_tracked()
  → UDP → radio:50002
  → (no wait for ACK — fire and forget)
```

### Scope Streaming

```
radio:50002 sends ~225 scope packets/sec
  → _civ_rx_loop drains ALL from queue each iteration
  → scope frames (cmd 0x27) → ScopeAssembler → callback
  → non-scope frames → routed to command waiters
  → (drain-all prevents scope flood from starving GET responses)
```

## Key Design Decisions

### Drain-All RX Pattern (#66)

The CI-V port receives mixed traffic: scope data (~225 pkt/sec), command responses,
unsolicited status updates. Processing one packet per iteration caused GET commands
to time out because responses waited behind hundreds of scope packets. The drain-all
pattern processes every queued packet each iteration, matching wfview's synchronous
`dataReceived()` approach.

### Optimistic Port Connection

Icom radios use fixed port offsets (control+1 for CI-V, control+2 for audio).
Instead of blocking on the status packet (which returns `civ_port=0` after rapid
reconnects), we connect immediately to default ports and verify asynchronously.

### Fire-and-Forget SET Commands (#56)

SET commands (frequency, mode, power, PTT) don't need ACK confirmation for
normal operation. Waiting for ACK under scope flood caused cascading timeouts.
GET commands still wait (with cache fallback), matching wfview's behavior.

### Mixin Pattern (#60)

`radio.py` was split using Python mixins to keep the public API surface unchanged
while separating concerns. `IcomRadio` inherits from `ControlPhaseMixin`,
`CivRxMixin`, and `AudioRecoveryMixin`. Cross-mixin access uses
`self._xxx  # type: ignore[attr-defined]` — accepted trade-off for zero API breakage.

## Dependencies

```
icom-lan (runtime)
└── Python 3.11+ stdlib only
    ├── asyncio, struct, socket, logging, dataclasses

icom-lan[dev]
├── pytest, pytest-asyncio

icom-lan[scope]
└── Pillow (for scope image rendering)
```
