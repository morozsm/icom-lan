# icom-lan — Project Documentation

## Goal

Create a Python library for direct control of Icom transceivers with a shared radio core:
- LAN backend (UDP, native Icom protocol)
- serial backend (USB CI-V + exported USB audio devices, in progress)

No intermediary software (wfview, RS-BA1, hamlib) is required for supported paths.

### Objectives
- Connect to Icom over network (authentication, keep-alive)
- Send/receive CI-V commands (frequency, mode, power, meters)
- Receive/transmit audio stream (Opus)
- Simple Pythonic API (sync + async)
- Keep one `Radio` contract for API/CLI/Web/rigctld consumers
- Support IC-7610 first, then expand to other models/families via backend/profile architecture

### Non-goals (for now)
- GUI
- Full wfview replacement
- Non-IC-7610 serial expansion before IC-7610 USB MVP is stable
- Cross-platform USB/audio polish beyond macOS-first rollout

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                           icom-lan                           │
│                                                              │
│  Consumers: API / CLI / Web / rigctld                       │
│                 │                                            │
│                 ▼                                            │
│      radio_protocol.Radio (+ capability protocols)           │
│                 │                                            │
│                 ▼                                            │
│            backends.factory.create_radio()                   │
│                 │                                            │
│                 ▼                                            │
│     Icom7610CoreRadio (shared commander/state/civ routing)   │
│          ┌───────────────────────────────┴─────────────────┐ │
│          ▼                                                 ▼ │
│  Icom7610LanRadio                                Icom7610SerialRadio
│  - control/auth/keepalive (UDP)                  - serial session
│  - CI-V over UDP                                 - CI-V over USB serial
│  - LAN audio (Opus/PCM)                          - USB audio devices
└──────────┬───────────────────────────────────────────────┬───┘
           │                                               │
           ▼                                               ▼
   IC-7610 over LAN                                IC-7610 over USB
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

### Phase 7 — Platform Foundation (M2) ✅ COMPLETE
**Goal:** Backend-neutral architecture for stable platform evolution.

- [x] Extract shared IC-7610 executable core (`Icom7610CoreRadio`) with LAN compatibility wrapper
- [x] Introduce profile-driven model/capability abstraction (`RadioProfile`)
- [x] Establish backend factory/config wiring (`create_radio`, backend config objects)
- [x] Add serial CI-V link foundation + deterministic serial test matrix
- [x] Expand reliability matrix and stabilize connect/recovery behavior

### Phase 8 — IC-7610 USB Backend MVP (M3) ✅ COMPLETE
**Goal:** Complete IC-7610 serial backend (control + audio + scope) and wire all consumers.

- [x] `#144` Serial radio wrapper/session
- [x] `#145` USB audio driver
- [x] `#146` Scope/waterfall on serial with guardrails (live hardware validated, 2026-03-06)
- [x] `#147` CLI backend selection and serial/audio flags
- [x] `#148` Web backend-neutral integration
- [x] `#149` rigctld backend-neutral integration
- [x] `#151` Docs/migration/capability matrix (2026-03-06)

### Phase 9 — IC-7610 wfview Command Parity (M4) ⏳ IN PROGRESS
**Goal:** Close the remaining IC-7610 command parity gap against wfview using a maintained command matrix and regression gate.

- [x] `#139` parity matrix + regression gate (`docs/parity/ic7610_command_matrix.json`)
- [x] `#130` DSP / level command family
- [x] `#131` operator toggles / status family
- [ ] `#132` VFO / dual-watch / scanning family
- [ ] `#133` memory + band-stacking family
- [ ] `#134` repeater / tone family
- [ ] `#135` system / configuration family
- [ ] `#136` transceiver / RIT / TX status family
- [x] `#137` advanced scope controls
- [ ] `#138` cross-surface exposure (API / CLI / Web / rigctld)

### Current Status
**Package version in `pyproject.toml`: `0.11.0`.**
**Reliability integration backlog (items 1-13) completed on 2026-03-05.**
**Latest full regression (local, 2026-03-06):** green; exact counts are tracked in issue comments because the total moves as the parity/integration suite grows.
- **M2 Platform Foundation (step #141):** extracted shared IC-7610 executable core (`Icom7610CoreRadio`) with LAN compatibility wrapper (`IcomRadio`) and no behavior changes.
- **M2 profile abstraction (issue #119):** runtime `RadioProfile` matrix added for multi-model behavior; `model`/`capabilities` and receiver/cmd29 routing are now profile-driven with explicit unsupported-operation guards.
- **M3 serial scope guardrails (issue #146, 2026-03-06):** serial backend keeps the shared error contract in disconnected state (`ConnectionError` before low-baud guardrail evaluation), includes deterministic low-baud guardrail with explicit override (`allow_low_baud_scope` / `ICOM_SERIAL_SCOPE_ALLOW_LOW_BAUD`), and now has dedicated serial integration scope profile/gating (`ICOM_SERIAL_DEVICE`, `ICOM_SERIAL_BAUDRATE`, `ICOM_SERIAL_RADIO_ADDR`) alongside serial-specific CI-V pacing (`ICOM_SERIAL_CIV_MIN_INTERVAL_MS`) while LAN scope behavior remains unchanged.
- **M3 CLI integration (issue #147, 2026-03-06):** unified CLI backend selection now routes through `create_radio(...)`, includes serial/audio flags, supports JSON audio-device listing, and preserves backward-compatible LAN defaults.
- **M3 web integration (issue #148, 2026-03-06):** web startup/runtime now stays on the shared factory/config path for both LAN and serial radios, removes backend-specific state pokes from `web/`, gates scope/audio behavior via runtime capability protocols, and adds serial-focused smoke/contract coverage so LAN-only assumptions are caught in CI.
- **M3 rigctld integration (issue #149, 2026-03-06):** rigctld startup now reuses the shared factory/config path for `--backend lan` and `--backend serial`, shares backend-provided state cache when available, prefers backend-native mode introspection via `radio_protocol.ModeInfoCapable` while falling back to the core `Radio.get_mode()/set_mode(str, ...)` contract, and adds serial TCP smoke coverage for read/write rigctld commands while keeping audit logging and circuit-breaker behavior unchanged.
- **M3 documentation (issue #151, 2026-03-06):** comprehensive IC-7610 USB serial backend setup guide (macOS-first), backend capability matrix (LAN vs Serial), migration/backward-compatibility section, troubleshooting for serial CI-V and USB audio, and critical hardware finding (`CI-V USB Port` must be `Link to [CI-V]`, not `[REMOTE]`) documented across guide/radios.md, guide/troubleshooting.md, radio-protocol.md, and new guide/ic7610-usb-setup.md.
- **M3 status:** complete (epic #152 closed-out).
- **M4 advanced scope parity (issue #137, 2026-03-06):** `advanced_scope` is now fully implemented in maintained library/runtime surfaces, including receiver select, single/dual, mode/span/edge/hold/ref/speed, during-TX, center type, VBW/RBW, fixed-edge bounds, and receive-side projection into `RadioState.scope_controls`.
- **IC-7610 parity matrix (issue #139, 2026-03-07): 131 implemented, 0 partial, 0 missing, 3 not_applicable — 100% COMPLETE**; source of truth is `docs/parity/ic7610_command_matrix.json`, and the explicit parity smoke profile is `pytest -m "integration and ic7610_parity" tests/integration`.
- **M4 parity family counts (from matrix):**
  - `baseline_core` (pre-M4 baseline, no owner issue): 38 implemented, 0 partial, 0 missing
  - `#132 vfo_dualwatch_scan`: 10 implemented, 0 partial, 0 missing
  - `#136 transceiver_status`: 11 implemented, 0 partial, 0 missing
  - `#137 advanced_scope`: 13 implemented, 0 partial, 0 missing
  - `#130 dsp_levels`: 21 implemented, 0 partial, 0 missing
  - `#131 operator_toggles`: 15 implemented, 0 partial, 0 missing
  - `#133 memory_bandstack`: 6 implemented, 0 partial, 0 missing
  - `#134 tone_repeater`: 4 implemented, 0 partial, 0 missing
  - `#135 system_config`: 16 implemented, 0 partial, 0 missing

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
  - USB audio driver unit tests (selection/lifecycle/error paths),
  - web/rigctld smoke tests on serial mock backend to guard against LAN-only assumptions.
- Added production `SerialCivLink` driver for IC-7610 USB CI-V with robust FE FE ... FD framing
  recovery, collision/abort handling, timeout/overflow guardrails, writer backpressure handling,
  and optional dependency guard (`pip install icom-lan[serial]`).
- Added production `UsbAudioDriver` for IC-7610 serial backend with deterministic device probe/
  selection (auto-detect + explicit RX/TX overrides), RX/TX lifecycle guardrails, actionable
  optional dependency errors (`sounddevice`/`numpy`), and serial-audio contract coverage for web
  audio channel + bridge flows.

## Test Equipment

- **Icom IC-7610** at `192.168.55.40`
- LAN ports: 50001 (control), 50002 (CI-V), 50003 (audio)
- USB path: CI-V serial device + exported RX/TX audio devices
- Local development host on the same LAN (IP redacted)

## License Notes

- wfview: **GPLv3** — used only as reference for understanding the protocol
- Our code: **MIT** — clean independent implementation, not copy-paste
- We don't copy wfview code, only study the packet format and protocol logic
- This is legal: protocol reverse engineering for interoperability is protected by law (EU Directive 2009/24/EC, US DMCA interoperability exception)
