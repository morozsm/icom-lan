# Roadmap

## Completed ✅

### Core Protocol & Architecture
- [x] UDP LAN protocol (control/CI-V/audio ports)
- [x] USB serial backend (IC-7610 validated)
- [x] CI-V command layer with wfview-style fire-and-forget
- [x] Async API (asyncio)
- [x] Commander queue (serialized, paced, retry, dedupe)
- [x] Abstract Radio Protocol (multi-radio architecture)
  - [x] `AudioCapable`, `ScopeCapable`, `DualReceiverCapable` protocols
- [x] Network discovery
- [x] Session management (connect/reconnect/soft-reconnect/disconnect)
- [x] Zero external dependencies (stdlib only)

### Audio (issues #1-#10)
- [x] PCM transcoder layer
- [x] RX high-level API (`start_audio_rx_pcm`)
- [x] TX high-level API (`start_audio_tx_pcm`, `push_audio_tx_pcm`)
- [x] CLI audio subcommands (`rx`, `tx`, `loopback`)
- [x] E2E tests for PCM API and CLI
- [x] Runtime audio stats (`get_audio_stats`)
- [x] Auto-recover audio streams after reconnect (#7)
- [x] Capability negotiation UX + `icom-lan audio caps`
- [x] Task-oriented docs/recipes
- [x] API naming consistency + deprecation plan
- [x] AudioBus pub/sub (v0.12.0, #106)
- [x] Virtual audio bridge (BlackHole/Loopback, v0.12.0)
- [x] Browser audio TX (Opus, v0.9.0)

### Hamlib NET rigctld (issues #16-#22, #27, #32)
- [x] TCP server skeleton (`asyncio.start_server`)
- [x] MVP command set (f/F/m/M/t/T/v/V/s/S/l/q + long-form)
- [x] Read-only safety mode (`--read-only`, RPRT -22)
- [x] Structured logging + guardrails (max clients, idle timeout, OOM guard)
- [x] Golden protocol response suite (45 fixtures)
- [x] TCP wire integration tests
- [x] WSJT-X/rigctl setup docs
- [x] `--wsjtx-compat` DATA mode pre-warm
- [x] DATA mode semantics fix (PKT*, RTTY/PKTRTTY)
- [x] CI-V desync fix + state cache + circuit breaker (#27)

### Web UI (v0.9.0–v0.11.0)
- [x] Spectrum/waterfall display (real-time scope data)
- [x] Full control panel (freq/mode/filter/power/meters)
- [x] Band selector (160m–10m one-click)
- [x] Dual-receiver display (MAIN/SUB state, v0.10.0)
- [x] VFO swap (Main↔Sub, v0.11.0)
- [x] Per-receiver controls (ATT/PRE/NB/NR/DSEL/IP+)
- [x] AF/RF/Squelch sliders
- [x] Meters (S-meter, SWR, ALC, Power, Vd, Id)
- [x] Browser audio RX/TX (Opus codec)
- [x] REST API (`/api/v1/state`, `/api/v1/bridge`)
- [x] DX Cluster integration (#108)
  - [x] Telnet client + spot overlay on waterfall
  - [x] Click-to-tune
  - [x] Deduplication (call+freq)
  - [x] Modal badge

### Dual-Receiver Support (#92, v0.11.0)
- [x] VFO Swap (Main↔Sub) — `0x07 0xB0`
- [x] cmd29 receiver routing for per-receiver commands
- [x] Receiver-aware frontend (15 per-receiver calls)
- [x] SUB scope switching (MAIN/SUB badge, auto-fallback)
- [x] Bidirectional sync (active receiver, Dual Watch)
- [x] Freq/mode on SUB via VFO-switch pattern

### IC-7610 Command Parity (Epic #140, in progress)
#### Completed command families:
- [x] #130: DSP level controls (APF/NR/PBT/NB/filter/AF-mute)
- [x] #131: Operator toggles/status (AGC/VOX/ANF/compressor/break-in)
- [x] #132: VFO/dual-watch/scanning
- [x] #134: Repeater/tone (tone+TSQL)
- [x] #136: Transceiver/RIT/TX status
- [x] #137: Advanced scope controls (center/during-TX/fixed-edge)
- [x] #139: Command parity matrix test+docs gate

#### In progress:
- [ ] #133: Memory and band-stacking
- [ ] #135: System/config (antenna, CI-V options, mod routing, time)
- [ ] #138: Expose parity commands across API/CLI/Web consistently

**Coverage status** (as of 2026-03-07):
- Fully implemented: ~100 / 134 wfview commands
- Partial support: ~10 / 134
- Missing: ~24 / 134
- Known hardware limitations: #153 (TX Freq Monitor)

### Testing & Quality
- [x] 2962+ unit/integration/mock tests
- [x] 95% code coverage
- [x] Golden protocol response suite
- [x] Integration tests with real IC-7610
- [x] Soak tests
- [x] CI parity matrix gate
- [x] Type annotations (`py.typed`)

### Documentation
- [x] MkDocs site (morozsm.github.io/icom-lan)
- [x] Protocol internals deep-dive
- [x] CLI reference
- [x] API reference
- [x] IC-7610 USB serial setup guide
- [x] Security docs
- [x] Session reports in `docs/sessions/` (RAG-indexed)
- [x] Backend architecture docs

## Current: v0.12.0 → v0.13.0

### IC-7610 Command Parity (Epic #140) — Priority P0
- [ ] #133: Memory and band-stacking command family
- [ ] #135: System/config family (antenna, CI-V options, mod routing, date/time/UTC)
- [ ] #138: Expose implemented parity features through API/CLI/Web consistently
- [ ] Update `docs/PROJECT.md` parity status with concrete counts
- [ ] Close #140 epic when all sub-issues merged

### Release checklist (v0.13.0)
- [ ] Verify `ruff check` clean
- [ ] Verify `mkdocs build` clean
- [ ] Move CHANGELOG [Unreleased] → [0.13.0]
- [ ] Version bump: 0.12.0 → 0.13.0
- [ ] GitHub release + PyPI publish
- [ ] Community announcement (Reddit, QRZ)

## Future (Post-Parity)

### Multi-Radio Support
- [ ] IC-705 validation (LAN protocol)
- [ ] IC-7300 validation (LAN protocol)
- [ ] IC-9700 support
- [ ] Radio capability auto-detection
- [ ] Profile-driven radio abstraction (#119)

### Protocol Completeness
- [ ] Mock Radio Server — UDP emulator for CI without hardware
- [ ] Extended response protocol (per-session `extended_mode`)
- [ ] rigctld: `\set_level` (RFPOWER)
- [ ] rigctld: RIT/XIT (`J`/`Z`)
- [ ] rigctld: Tuner control
- [ ] rigctld: `\dump_state` protocol v1

### Web UI & Integrations
- [ ] Web UI: frequency memory presets
- [ ] Web UI: CW keyer interface
- [ ] Web UI: remote PTT/foot-switch emulation
- [ ] Async event/notification stream (S-meter polling, band changes)
- [ ] WSJT-X/JS8Call/fldigi full integration testing
- [ ] Logging integration (ADIF export)

### Hardening & Reliability
- [ ] Integration reliability backlog (#129)
- [ ] Connection state machine refactor
- [ ] Command retry strategies
- [ ] Graceful degradation on partial failures

### Long-term (Research)
- [ ] Universal Radio Bridge (RPi) — USB radios → LAN control
- [ ] Rust core prototype (performance spike)
- [ ] Windows/Linux binary releases
- [ ] Mobile app (React Native?)

---

*Updated: 2026-03-07*
