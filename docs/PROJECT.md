# icom-lan — Project Documentation

## Goal

Create a Python library for direct control of Icom transceivers over LAN (UDP), without intermediary software (wfview, RS-BA1, hamlib).

### Objectives
- Connect to Icom over network (authentication, keep-alive)
- Send/receive CI-V commands (frequency, mode, power, meters)
- Receive/transmit audio stream (Opus)
- Simple Pythonic API (sync + async)
- Support for IC-7610, IC-705, IC-7300, IC-9700

### Non-goals (for now)
- GUI
- Full wfview replacement
- USB/serial support (hamlib handles that)

## Architecture

```
┌─────────────────────────────────────────────┐
│                 icom-lan                     │
│                                             │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Transport │  │   CIV    │  │  Audio   │ │
│  │  (UDP)    │  │ Commands │  │ (Opus)   │ │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘ │
│        │             │             │        │
│  ┌─────┴─────────────┴─────────────┴─────┐  │
│  │         IcomRadio (public API)        │  │
│  └──────────────────┬────────────────────┘  │
│                     │                       │
│  ┌──────────────────┴────────────────────┐  │
│  │    rigctld TCP Server (:4532)         │  │
│  │    (Hamlib NET rigctl compatible)     │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                     │ UDP
                     ▼
            ┌─────────────────┐
            │   Icom Radio    │
            │  192.168.x.x    │
            │  :50001 control │
            │  :50002 ci-v    │
            │  :50003 audio   │
            └─────────────────┘
```

## Icom LAN Protocol (based on wfview research)

### Overview
Icom uses a proprietary UDP protocol for LAN connectivity. Not officially documented. Fully reverse-engineered by the wfview team.

### Ports
| Port | Purpose |
|------|---------|
| 50001 | Control — authentication, connection management |
| 50002 | CI-V Serial — CI-V command passthrough |
| 50003 | Audio — bidirectional audio stream (Opus) |

### Connection Phases
1. **Discovery** — optional, searching for radios on the network
2. **Login** — sending credentials (username/password)
3. **Auth** — receiving token/confirmation
4. **Keep-alive** — periodic ping (~500ms), otherwise the radio drops the connection
5. **CI-V** — sending/receiving CI-V commands via UDP wrapper
6. **Audio** — audio streaming (Opus codec, 8/16/24 kHz)
7. **Disconnect** — graceful shutdown

### Packet Structure
Each UDP packet has a fixed-format header (see `packettypes.h` in wfview):
- Packet length (2 bytes, LE)
- Packet type (2 bytes)
- Sequence number (2 bytes)
- Sender ID (4 bytes)
- Receiver ID (4 bytes)
- Payload (variable length)

### Key wfview Source Files (reference)
| File | Lines | Description |
|------|-------|-------------|
| `include/packettypes.h` | 684 | Packet structures, type constants |
| `src/radio/icomudpbase.cpp` | 585 | Base UDP: connection, keep-alive, retransmit |
| `src/radio/icomudphandler.cpp` | 690 | Main handler: login, auth, routing |
| `src/radio/icomudpcivdata.cpp` | 248 | CI-V data over UDP |
| `src/radio/icomudpaudio.cpp` | 303 | Audio streaming |
| `src/radio/icomcommander.cpp` | 3533 | CI-V commands (frequency, mode, meters, etc.) |
| `src/rigcommander.cpp` | 256 | High-level radio interface |
| **Total** | **~6300** | |

## Development Phases

### Phase 1 — Transport (MVP) ✅ COMPLETE
**Goal:** Establish UDP connection with the radio, complete authentication, maintain keep-alive.

- [x] Parse packet format from `packettypes.h`
- [x] Implement UDP transport (asyncio)
- [x] Discovery handshake (Are You There → I Am Here → Are You Ready)
- [x] Login + auth handshake
- [x] Token acknowledgement
- [x] Conninfo exchange (obtain CI-V/audio ports)
- [x] Dual-port architecture (control port 50001 + CI-V port 50002)
- [x] Keep-alive loop (ping + retransmit)
- [x] Graceful disconnect
- [x] Test: connect to IC-7610 at 192.168.55.40

**Result:** `radio.connect()` / `radio.disconnect()` work. ✅

### Phase 2 — CI-V Commands ✅ COMPLETE
**Goal:** Send and receive CI-V commands over the network connection.

- [x] Wrap CI-V in UDP packets (per `icomudpcivdata.cpp`)
- [x] Open CI-V data stream (OpenClose packet)
- [x] Filter waterfall/echo packets
- [x] Basic commands: get/set frequency, mode, power
- [x] Read meters: S-meter, SWR, ALC, power
- [x] PTT on/off
- [x] Test: read and set frequency on IC-7610

**Result:** `radio.get_frequency()`, `radio.get_mode()`, `radio.get_s_meter()` work. ✅

### Phase 3 — Audio Streaming ✅ COMPLETE
**Goal:** Receive and transmit audio.

- [x] Opus decode/encode (RX/TX)
- [x] PCM transcoder layer (high-level API)
- [x] Callback API for audio
- [x] Buffering (JitterBuffer) and flow control
- [x] Full-duplex audio
- [x] Audio auto-recovery after reconnect
- [x] Runtime audio stats API
- [x] Audio capability negotiation
- [x] CLI: `icom-lan audio rx/tx/loopback`

**Result:** Full audio stack — Opus and PCM API, CLI, stats, auto-recovery. ✅

### Phase 4 — Polish & Publish ✅ COMPLETE
**Goal:** Production-ready library for PyPI.

- [x] Sync + async API
- [x] Autodiscovery of radios on the network
- [x] Multi-model support (IC-7610, IC-705, IC-7300, IC-9700)
- [x] CLI utility (`icom-lan status`, `icom-lan freq 14074000`)
- [x] Documentation + MkDocs site
- [x] PyPI publication (v0.8.0)

### Phase 5 — Hamlib NET rigctld ✅ COMPLETE
**Goal:** Drop-in rigctld replacement for WSJT-X, JS8Call, fldigi.

- [x] TCP server skeleton (asyncio)
- [x] MVP command set (f/F/m/M/t/T/v/V/s/S/l/q)
- [x] Read-only safety mode
- [x] Structured logging + guardrails
- [x] Golden protocol response suite (45 fixtures)
- [x] WSJT-X compatibility (--wsjtx-compat)
- [x] DATA mode semantics fix
- [x] CI-V desync fix + circuit breaker

### Phase 6 — Scope/Waterfall ✅ COMPLETE (v0.6.0)

### Current Status
**v0.8.0 released on PyPI. Reliability integration backlog (items 1-13) completed on 2026-03-05.**
**Latest full regression:** `1797 passed, 95 skipped`.
- **M2 Platform Foundation (step #141):** extracted shared IC-7610 executable core (`Icom7610CoreRadio`) with LAN compatibility wrapper (`IcomRadio`) and no behavior changes.
- **M2 profile abstraction (issue #119):** runtime `RadioProfile` matrix added for multi-model behavior; `model`/`capabilities` and receiver/cmd29 routing are now profile-driven with explicit unsupported-operation guards.

### Reliability Test Expansion (2026-03-05)
- Added extended integration coverage scaffolding for:
  - transport sequence wrap-around and ACK mixed stress,
  - session longevity/contention/readiness transitions,
  - control API roundtrips (DATA/RF/AF/squelch/NB/NR/IP+/state),
  - PCM audio path and scope lifecycle,
  - negative auth/connect paths and legacy script migration to pytest.
- Added regression matrix gate for shared-core LAN + serial-ready architecture:
  - backend-agnostic contract tests (LAN fixture + deterministic serial mock fixture),
  - deterministic serial framing/stability unit tests (partial frames/timeouts/overflow),
  - USB audio stub unit tests (selection/lifecycle/error paths),
  - web/rigctld smoke tests on serial mock backend to guard against LAN-only assumptions.

## Test Equipment

- **Icom IC-7610** at `192.168.55.40`
- Ports: 50001 (control), 50002 (serial), 50003 (audio)
- Mac mini M4 Pro on the same LAN (`192.168.55.152`)

## License Notes

- wfview: **GPLv3** — used only as reference for understanding the protocol
- Our code: **MIT** — clean independent implementation, not copy-paste
- We don't copy wfview code, only study the packet format and protocol logic
- This is legal: protocol reverse engineering for interoperability is protected by law (EU Directive 2009/24/EC, US DMCA interoperability exception)
