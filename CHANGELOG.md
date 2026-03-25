# Changelog

All notable changes to [icom-lan](https://github.com/morozsm/icom-lan) are documented here.

## [0.13.0] — 2026-03-25

### 🚀 M6 Productization Complete

#### M6.1: Audio Codec Support
- **`_audio_codecs.py`**: pure-Python µlaw (mu-law) to PCM16 decoder — 256-entry lookup table, zero external dependencies
- Standard ulaw-to-PCM16 conversion with graceful fallback on decode errors
- Integrates with `AudioBroadcaster._relay_loop()` for transparent web audio transcoding
- Radios returning `AudioCodec.ULAW_1CH` or `ULAW_2CH` now stream correctly to web clients
- 11 comprehensive unit tests covering full 256-byte lookup table, multi-sample handling, stereo conversion, edge cases

#### M6.P2.1: Delta Encoding for WebSocket State Updates
- **`web/_delta_encoder.py`**: DeltaEncoder class for differential state snapshots
- Computes and transmits only changed fields between updates (10-50× payload reduction: ~2KB → 50-100 bytes)
- Periodic full-state refresh every 100 updates prevents client/server drift
- 22 unit tests covering all encoding/decoding paths and edge cases
- Integrated into `WebSocketServer._broadcast_state_update()` for production web clients

#### M6.P2.2: Audio Buffer Pooling
- **`_audio_buffer_pool.py`**: AudioBufferPool class with thread-safe LIFO reuse strategy
- Pre-allocates buffers (default 5 @ 1280 bytes) for common audio frame sizes (16kHz/48kHz mono/stereo @ 20ms)
- Temporary buffer allocation on exhaustion prevents unbounded growth
- 99.5% allocation reduction in high-frequency audio paths (50+ packets/sec)
- 15 comprehensive unit tests: pool mechanics, reuse, threading, concurrent access, performance metrics
- Performance: >50k acquire/release ops/sec, >30k ops/sec under 5 concurrent threads
- Integrated into `AudioBroadcaster.__init__()` with infrastructure for codec optimization

#### M6.P2.3: Web Audio Streaming Performance Profiling & Validation
- Comprehensive benchmark suite (10 tests) covering codecs, relay loop, and full pipeline
- **Performance Results** (all exceed SLOs with 18-588× headroom):
  - µlaw decode: 8.67µs p50 latency, 18.84M samples/sec throughput (SLO headroom: 2174×)
  - Frame encode: 0.17µs p50 latency, 8.4M frames/sec throughput (SLO headroom: 588×)
  - Full pipeline: 25.5µs p50, 373.5µs p99 latency (SLO headroom: 78×)
  - Relay loop: 1.01ms with async dispatch, 1995 frames/sec (SLO headroom: 19×)
  - Buffer pool: 99.5% allocation reduction verified
- `docs/AUDIO_STREAMING_PROFILE.md`: detailed analysis with SLO definitions, architecture insights, and monitoring recommendations
- **Conclusion**: Pipeline is production-ready; no bottlenecks identified

#### M6.3: Performance Regression Testing
- 7 SLO-based regression tests in `test_performance_regressions.py`
- CI-V frame parsing latency: <1ms per frame ✅
- BCD encoding performance: <50ms for 3000 ops ✅
- Frame building performance: >1000 frames/ms ✅
- End-to-end CI-V pipeline: <20ms ✅
- **Performance Baseline**: 514 core unit tests in 1.88s (3.6ms median), 3446 total in ~79s (23ms median)
- `docs/PERFORMANCE.md`: comprehensive SLO definitions and optimization roadmap

#### Test Coverage
- **Total test count**: 3446 tests (514 core unit, 3384 total with performance/profiling tests)
- **New in M6**: 65 tests (11 audio codec, 22 delta encoder, 15 buffer pool, 10 streaming profile, 7 performance regression)
- **Coverage**: 95% line coverage with mypy strict mode for web modules

### USB Audio Topology Resolver (Multi-Radio Support)
- **`usb_audio_resolve.py`**: resolves correct USB Audio device for serial CI-V when multiple identical devices connected
- macOS IORegistry topology matching via `ioreg` (TTY suffix → locationID → hub prefix → audio device mapping)
- **`Icom7610SerialRadio`**: automatic serial port → audio device pairing for multi-radio setups

### Frontend Improvements
- **ATT/PRE mutually exclusive**: enabling ATT clears PRE and vice versa with optimistic state updates
- **Stable button widths**: RX controls use `min-width` + `nowrap` to prevent layout shifts
- **AGC button**: AGC on/off control added to RX controls panel

### Architecture Enhancements
- **Optimistic state updates**: all toggled controls write to `RadioState` immediately on click (before CI-V ACK)
- **Data-driven poller**: `RadioPoller` reads polling queries from TOML `CommandMap` instead of hardcoded lists
- **Plain CI-V fallback**: single-receiver radios (IC-7300) use plain CI-V without Command29 receiver selector byte

---

## [0.13.0-pre] — 2026-03-13

### Added
- Memory and band-stacking register commands (Issue #133)
  - `set_memory_mode(channel)` - Select memory channel (1-101)
  - `memory_write()` - Write VFO to selected memory channel
  - `memory_to_vfo(channel)` - Load memory channel to VFO
  - `memory_clear(channel)` - Clear memory channel
  - `set_memory_contents(mem)` - Write full memory channel data
  - `set_band_stack(bsr)` - Write band stacking register
  - New dataclasses: `MemoryChannel`, `BandStackRegister`

### Known Limitations
- **Memory GET commands not supported by IC-7610**
  - `get_memory_mode()` raises `NotImplementedError`
  - `get_memory_contents(channel)` raises `NotImplementedError`
  - `get_band_stack(band, register)` raises `NotImplementedError`
  - **Reason:** IC-7610 CI-V protocol does not support reading current memory
    channel or memory contents. Command 0x08 is SELECT-only per the official
    CI-V Reference Manual (page 4). Commands 0x1A 0x00 and 0x1A 0x01 GET
    variants are not documented.
  - **Workaround:** Use SET commands to write known values, then track state
    in application code.

## [0.12.0] — 2026-03-03

### 🔊 AudioBus Pub/Sub & Virtual Audio Bridge ([#106](https://github.com/morozsm/icom-lan/issues/106))

- **AudioBus** (`audio_bus.py`): new pub/sub audio distribution system — multiple consumers share a single radio RX stream
  - `radio.audio_bus.subscribe(name="...")` → `AudioSubscription` (async iterator + context manager)
  - First subscriber triggers `start_audio_rx_opus()`, last unsubscribe schedules `stop_audio_rx_opus()`
  - Sliding window queue: on overflow, oldest packet dropped (preserves real-time continuity)
  - Default queue size: 64 packets
- **Audio Bridge** (`audio_bridge.py`): bidirectional PCM bridge between radio and virtual audio devices (BlackHole, Loopback)
  - CLI: `icom-lan audio bridge --device "BlackHole 2ch"` + `--list-devices` + `--rx-only`
  - Auto-detects BlackHole/Loopback/VB-Audio virtual devices
  - Opus decode → PCM → virtual device output; virtual device input → Opus encode → radio TX
  - Noise gate on TX path, stats logging every 10s
  - Optional dep: `pip install icom-lan[bridge]` (sounddevice + numpy + opuslib)
- **Web server integration**: `icom-lan web --bridge "BlackHole 2ch"` runs bridge alongside web UI sharing the same radio connection
  - REST API: `GET/POST/DELETE /api/v1/bridge`
  - `--bridge-rx-only` for receive-only mode
- **Rigctld default**: `icom-lan web` now starts rigctld on `:4532` by default; `--no-rigctld` to disable
- **AudioBroadcaster refactored**: now uses AudioBus subscription instead of direct `start_audio_rx_opus` calls
- **AudioCapable Protocol**: added `audio_bus` property

### 🔧 Fixes

- **TX audio chunking**: IC-7610 silently drops audio UDP packets with payload > 1364 bytes; `push_tx()` now chunks large payloads matching wfview behavior (1920-byte PCM frame → 1364 + 556)
- **Bridge PCM codec passthrough**: when radio uses PCM codec (0x04), bridge sends raw PCM directly instead of transcoding PCM→Opus→send; fixes zero-power TX
- **Bridge codec auto-detection**: reads `radio.audio_codec` at startup — PCM data written directly to sounddevice, Opus decoded only when codec is `OPUS_1CH`/`OPUS_2CH`
- **Separate TX device**: `--bridge-tx-device` CLI flag avoids feedback loop when using single BlackHole device for bidirectional audio
- **AudioSubscription CancelledError**: `asyncio.CancelledError` in `__anext__` caught gracefully; timeout returns `None` (silence) instead of re-raising
- **RX loop auto-restart**: on transient error, waits 1s then recreates task
- **PID file**: `/tmp/icom-lan.pid` written on startup, removed on exit; `kill $(cat /tmp/icom-lan.pid)` for graceful shutdown
- CI: `test_soft_reconnect_handles_connect_failure` mock changed from `OSError` to `IcomTimeout` (was timing out in CI due to 10 retry attempts)

### 🧪 Tests

- 19 new AudioBus tests, 14 AudioBridge tests, all handler tests updated
- **1772 passed, 0 failures, 95% coverage**

## [0.11.0] — 2026-03-03

### 🎯 Full Dual-Receiver Support ([#92](https://github.com/morozsm/icom-lan/issues/92))

- **VFO Swap (Main↔Sub)**: clicking VFO B sends CI-V `0x07 0xB0` — swaps frequencies, modes, audio, and scope between MAIN and SUB receivers. This is the only way to switch LAN audio on IC-7610 (mono audio is always from MAIN receiver)
- **cmd29 receiver routing** ([#93](https://github.com/morozsm/icom-lan/issues/93)): `receiver` parameter added to 9 command builders and 10 radio methods for per-receiver SET commands (ATT, PRE, NB, NR, levels, features)
- **Receiver-aware frontend** ([#94](https://github.com/morozsm/icom-lan/issues/94)): all 15 per-receiver `sendCommand()` calls include receiver, per-receiver mode/filter labels
- **SUB scope switching** ([#95](https://github.com/morozsm/icom-lan/issues/95)): `SwitchScopeReceiver` command, MAIN/SUB badge on waterfall, zero-frame fallback auto-reverts to MAIN
- **Bidirectional sync** ([#96](https://github.com/morozsm/icom-lan/issues/96)): polls active receiver (`0x07 0xD2`) and Dual Watch (`0x07 0xC2`) from radio, DW badge in UI
- **Freq/mode on SUB via VFO-switch pattern**: IC-7610 `0x05`/`0x06` do not support cmd29 — temporarily switches active VFO, sends command, switches back

### 🔧 Fixes

- **LAN audio routing** ([#97](https://github.com/morozsm/icom-lan/issues/97)): discovered IC-7610 rejects stereo codecs through LAN; VFO Swap is the correct solution
- **MagicMock `_radio_state` gotcha**: `getattr(mock, attr, None)` returns MagicMock, not None — added `isinstance(str)` guard in `_current_active()` helper

### 🧪 Tests

- 7 new tests for VFO swap, scope switching, bidirectional sync
- **1302 passed, 0 failures**

## [0.10.0] — 2026-03-02

### 🌐 Web UI

- **MAIN/SUB receiver controls**: click VFO A/B panels to switch active receiver; controls, sliders, mode/filter, and frequency update independently per receiver. Scope/waterfall remains on MAIN band (SUB scope planned in [#92](https://github.com/morozsm/icom-lan/issues/92))
- **Per-receiver badges**: ATT, PRE, NB, NR, DSEL, IP+ show independent state for each VFO
- **Force-update on VFO switch**: all controls refresh immediately when switching receivers
- **Client-side tune debounce** (40ms): coalesces rapid frequency changes, prevents CI-V command flooding
- **Scope cosmetics**: brighter S-meter labels, dB/freq axis text, more visible grid lines
- **VFO section layout**: increased height with shrink-0 to prevent scope overlap

### 🔧 Fixes

- **CI-V idle keepalive** (critical): `start_idle_loop()` was missing on CI-V transport — radio killed sessions after ~40s of inactivity
- **Scope recovery after reconnect**: re-enables scope after soft reconnect via `_on_reconnect` callback
- **Scope health monitor**: detects all-zero frames and re-enables scope; skips re-enable when radio is disconnected (prevents reconnect storms)
- **Filter flicker**: removed `1A 03` from CI-V RX parser — IC-7610 returns filter width code, not selector
- **Poller crash guard**: catch-all exception handler prevents silent asyncio task death
- **SelectVfo fire-and-forget**: VFO switch no longer blocks poller waiting for ACK
- **no_radio guard**: properly rejects commands when radio is not connected

### 🧪 Tests

- Fixed 4 broken tests: set_freq response format, set_mode enqueue pattern, no_radio guard logic, flaky retransmit timing
- **1268 passed, 0 failures**

## [0.9.0] — 2026-03-02

Major release: complete Web UI rewrite, dual-receiver support, CI-V reliability overhaul, and architecture refactor. **100+ commits** since v0.7.0.

### ⚠️ Breaking Changes

- CLI flag `--port` renamed to `--control-port` to avoid confusion with web/serve ports (#54)
- CI-V commander switched to fire-and-forget (wfview-style) — `wait_response` no longer default for SET commands (#56)

### 🌐 Web UI

Complete rewrite from scratch — now a full remote control panel in your browser.

- **v2.0 UI**: Dark theme, responsive layout, spectrum + waterfall canvas (#68)
- **Dual-receiver display**: MAIN and SUB state for IC-7610 via Command29 (#91)
- **Band selector**: One-click buttons for 160m–6m with band-center frequencies
- **Audio RX/TX**: Listen to your radio in the browser; transmit from microphone via Opus codec (#41, #70)
- **Full control panel**: AF/RF/Squelch sliders, NB/NR/DIGI-SEL/IP+ toggles, ATT/Preamp, VFO A/B select & swap
- **Meters**: S-meter, SWR (color-coded), ALC, Power (watts), Vd, Id
- **PTT toggle**: Click-to-toggle (not momentary) for safety (#57)
- **Frequency tuning**: Click waterfall to tune, arrow keys, scroll wheel, tuning step selector
- **Filter passband overlay** on spectrum display
- **HTTP state endpoint**: `GET /api/v1/state` — dual-receiver JSON polled at 200ms (#91)
- **Connect/Disconnect button** in UI
- **Keyboard shortcuts** and theme toggle (#42)

### 📡 Dual-Receiver Support (IC-7610)

- **RadioState model**: `ReceiverState` for MAIN + SUB with all parameters (#91)
- **Command29 queries**: Per-receiver ATT, preamp, NB, NR, DIGI-SEL, IP+, AF, RF, squelch, filter
- **0x25/0x26 commands**: Dual-receiver frequency and mode readback
- **Interleaved polling**: Meters at 40Hz, state queries at 20Hz — full cycle in 1.35s (4× faster than wfview)
- 33 new tests for RadioState and Command29 parsing

### 🔧 CI-V Reliability

- **Root cause fix**: CI-V transport now binds to the correct local port from conninfo (#66)
- **BCD meter decoding**: IC-7610 meters are BCD-encoded, was parsed as binary
- **Fire-and-forget commander**: Matches wfview architecture — no ACK waits for SET commands (#56, #74)
- **3-phase watchdog recovery**: Soft reconnect → full reconnect → never gives up
- **Idle keepalive** on control/audio transports
- **CI-V data watchdog** with configurable timeout
- **Queue drain fix**: RX pump processes all pending packets per iteration (prevents scope flood starvation) (#66)
- **Conninfo retry**: Up to 3 retries when radio reports civ_port=0 (#67)
- **Scope assembly timeout**: Prevents incomplete frame memory leaks (#62)

### 🎛️ New API Methods

- `get_nb()` / `set_nb()` — Noise Blanker (Command29)
- `get_nr()` / `set_nr()` — Noise Reduction (Command29)
- `get_digisel()` / `set_digisel()` — DIGI-SEL (Command29)
- `get_ip_plus()` / `set_ip_plus()` — IP+ (Command29)
- `get_af_level()` / `set_af_level()` — AF gain (Command29)
- `get_rf_gain()` / `set_rf_gain()` — RF gain (Command29)
- `set_squelch()` — Squelch level (Command29)
- `get_data_mode()` / `set_data_mode()` — DATA mode
- `vfo_exchange()` / `vfo_equalize()` — VFO operations
- Audio TX: `start_audio_tx()`, `push_audio_tx_opus()`
- `GET /api/v1/state` — HTTP endpoint for dual-receiver state

### 🏗️ Architecture

- **Radio module split**: `radio.py` → `_control_phase.py`, `_civ_rx.py`, `_audio_recovery.py` (#60)
- **Connection state machine**: Formal FSM with enum states (#61)
- **RadioPoller**: Single CI-V serializer with interleaved meter/state polling (#72)
- **AudioBroadcaster**: Single shared RX stream for all WebSocket clients (#70)
- **Meter calibration on backend**: wfview IC-7610 calibration tables in `meter_cal.py`
- **State cache with TTL**: GET fallbacks expire after configurable timeout (#63)
- **UDP relay proxy**: Remote access via VPN/Tailscale (#73)

### 🐛 Bug Fixes

- IC-7610 0x16 response format: sub-command in data[0], value in data[1]
- IP+ (0x16/0x65) and DIGI-SEL (0x16/0x4E) are separate functions — was conflated
- 0x25/0x26 byte order: receiver byte is first, not last
- Slider jitter from poll noise — added ±3 dead zone
- Watchdog false reconnect loop — reset timestamp on soft_reconnect
- Audio buffer capped at 150ms to keep sync with waterfall
- Safari iOS audio resume after background tab
- Scope pub/sub broadcast — all clients get live frames
- Duplicate WebSocket connections on page load/reconnect (#50)
- PTT restored to wait_response (needs ACK for safety) (#59)
- Filter selector sync after band change (#58)
- Flaky tests: hello_on_connect race and missing pytest-asyncio (#64)

### 📊 Stats

- **1,265 tests** passing (78 skipped, 0 failed)
- **82 public API methods**
- **0 external dependencies** (pure Python, stdlib only)

---

## [0.7.0] — 2026-02-24

Initial PyPI release.

- LAN UDP connection to Icom transceivers (IC-7610 tested)
- Full CI-V command set: frequency, mode, filter, power, meters, PTT, CW keying
- Network discovery (`icom-lan discover`)
- CLI tool with env-var configuration
- Async Python API (`IcomRadio` context manager)
- Scope/waterfall data with callback API
- Hamlib NET rigctld-compatible TCP server (`icom-lan serve`)
- Web UI v1 with spectrum display
- Zero external dependencies
- 1,040 tests passing
