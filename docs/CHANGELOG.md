# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Multi-vendor rig profile support** — TOML schema extended for non-Icom radios:
  - `rigs/ftx1.toml` — Yaesu FTX-1 (Yaesu CAT, 17 modes, dual RX, meter calibration)
  - `rigs/x6100.toml` — Xiegu X6100 (CI-V 0x70, IC-705 compatible, QRP 8W)
  - `rigs/tx500.toml` — Lab599 TX-500 (Kenwood CAT, minimal command set, QRP 10W)
- **`[protocol]` section** — `type = "civ" | "kenwood_cat" | "yaesu_cat"` (default: `"civ"`)
- **`[controls]` section** — UI control styles: `toggle`, `stepped`, `selector`,
  `toggle_and_level`, `level_is_toggle`
- **`[meters]` section** — Non-linear calibration tables for S-meter and TX meters
  with `redline_raw` threshold
- **`[[rules]]` section** — Declarative constraint rules: `mutex`, `disables`,
  `requires`, `value_limit`
- **Extended VFO schemes** — added `"ab_shared"` (FTX-1) and `"single"` (simple QRP)
- **`[commands]` now optional** — non-CI-V radios may have empty command maps
- **`civ_addr` now optional** — defaults to 0 for Kenwood/Yaesu CAT radios
- `RadioProfile` and `RigConfig` extended with `protocol_type`, `controls`,
  `meter_calibrations`, `rules`
- 42 new tests in `test_rig_multi_vendor.py` (139 total, 0 regressions)

## [0.12.0] — 2026-03-15

### Added

- **Data-driven rig profiles** (Epic #251) — radio configuration moved from hardcoded Python
  to TOML files in `rigs/`:
  - `rigs/ic7610.toml` — IC-7610 reference profile (full feature set, dual receiver)
  - `rigs/ic7300.toml` — IC-7300 profile (single receiver, VFO A/B, no DIGI-SEL/IP+)
  - `rigs/_schema.md` — TOML schema specification
  - `rig_loader.py` — `load_rig()`, `discover_rigs()`, `RigConfig`, `RigLoadError`
  - `command_map.py` — `CommandMap` (immutable CI-V wire byte lookup)
- **IC-7300 support** — tested via USB serial backend; rig profile defines all 200+
  supported commands, VFO A/B scheme, and IC-7300-specific wire byte overrides
- **`cmd_map` parameter on all 223 command functions** — every builder function in
  `commands.py` now accepts `cmd_map: CommandMap | None = None`; when provided, wire bytes
  come from the TOML profile instead of hardcoded IC-7610 defaults
- **`RadioProfile` additions** — `vfo_scheme` (`"ab"` | `"main_sub"`), `has_lan` fields
- **Web UI capability guards** — UI controls for DIGI-SEL, IP+, and dual-receiver
  features are automatically hidden when the active profile doesn't support them
- **Dynamic VFO labels** — Web UI shows "MAIN" / "SUB" for IC-7610 (main_sub scheme)
  and "VFO A" / "VFO B" for IC-7300 (ab scheme)
- **`/api/v1/info` enriched** — `capabilities` object now includes `vfoScheme`, `hasLan`,
  `maxReceivers`, `modes`, `filters` from the active rig profile
- **`/api/v1/capabilities` additions** — `receivers`, `vfoScheme` fields
- **`/api/v1/state` adapts** — omits `sub` receiver state for single-receiver rigs

### Changed

- +3497 lines, 236 new tests across `test_rig_loader.py`, `test_command_map.py`,
  `test_rig_ic7610.py`, `test_rig_ic7300.py`, `test_commands_cmd_map.py`
- Hardcoded IC-7610 wire bytes remain as defaults when `cmd_map=None` — fully backward-compatible

## [Unreleased]

### Added
- **Multi-vendor rig profiles** — TOML schema extended for non-Icom radios:
  - `rigs/ftx1.toml` — Yaesu FTX-1 (17 modes, 6 freq ranges, meter calibration)
  - `rigs/x6100.toml` — Xiegu X6100 (CI-V 0x70, IC-705 compatible, QRP 8W)
  - `rigs/tx500.toml` — Lab599 TX-500 (Kenwood CAT text protocol)
  - New optional TOML sections: `[protocol]`, `[controls]`, `[meters]`, `[[rules]]`
  - 3 protocol types: `civ` (binary), `kenwood_cat` (text), `yaesu_cat` (text)
  - 5 control styles: `toggle`, `stepped`, `selector`, `toggle_and_level`, `level_is_toggle`
  - 4 VFO schemes: `ab`, `main_sub`, `ab_shared`, `single`
  - Meter calibration tables for non-linear S-meter scales (raw→actual lookup)
  - Constraint rules: `mutex`, `disables`, `requires`, `value_limit`
  - `[commands]` and `civ_addr` now optional (for non-CI-V protocols)
  - `_schema.md` updated with full documentation of all new sections
  - 42 new tests in `test_rig_multi_vendor.py`, 0 regressions
- **Serial port auto-discovery** (Epic #222) — `icom-lan discover` now scans both LAN (UDP broadcast) and USB serial ports
  - `enumerate_serial_ports()` — filters USB serial candidates
  - `probe_serial_civ()` — CI-V probing with auto baud detection (19200, 9600, 115200, 4800)
  - `identify_radio()` — model identification from CI-V address
  - `dedupe_radios()` — groups same radio found via LAN and serial
  - CLI flags: `--serial-only`, `--lan-only`, `--timeout`
- **pyserial is now a required dependency** (was optional `[serial]` extra)

### Fixed
- **LAN discovery ignored by IC-7610** — ARE_YOU_THERE packets with `sender_id=0` are silently ignored; now uses random non-zero sender ID
- **Serial CI-V probe missed radio response** — `reader.read(64)` returned only the echo; now reads in a loop until actual response preamble (`FE FE E0`) is found

## [0.11.0] — 2026-03-12

### Added
- **Abstract Radio Protocol** (`radio_protocol.py`) — vendor-neutral interface with `Radio`, `AudioCapable`, `ScopeCapable`, `DualReceiverCapable` protocols
- **Epic #140 complete** — 100% CI-V command coverage (134/134 IC-7610 commands implemented)
- **Epic #215 complete** — Post-audit cleanup: mypy 197→0 errors, dead code removed (-616 lines), `__all__` API surface defined
- `IcomRadio.model`, `.capabilities`, `.radio_state` properties
- `set_state_change_callback()`, `set_reconnect_callback()` public methods
- `control_connected` property for transport health status
- `get_mode()` now returns Protocol-compatible `tuple[str, int | None]`
- Graceful shutdown: SIGTERM handler ensures clean radio disconnect on kill
- `_force_cleanup_civ()` for unconditional CI-V transport teardown
- Retry mechanism for `civ_port=0` (radio session not ready): 3×10s retries
- Connection indicators in Web UI update from `/api/v1/state` poll (200ms)
- `/api/v1/capabilities` endpoint uses `radio.capabilities`

### Fixed
- **Sequence counter overflow** — `_civ_send_seq` / `_audio_send_seq` now wrap at uint16 (was unbounded, crashed after ~1.5h)
- **Broken pipe recovery** — watchdog falls back to full reconnect when soft_reconnect fails
- **CI-V indicator accuracy** — `connected` property checks actual transport health, not just state enum
- UDP error logging rate-limited (first 3, then every 100th)
- `0x16` added to `_COMMANDS_WITH_SUB` (NB/NR/DIGI-SEL sub-command parsing)
- `server.stop()` uses full `disconnect()` instead of `soft_disconnect()` for complete session cleanup

### Changed
- All Web UI/rigctld consumers now use `Radio` Protocol type hints instead of `IcomRadio`
- `isinstance(radio, AudioCapable)` guards instead of `hasattr`
- Test coverage: 85% → 95% (3173 tests, +1434 from v0.10.0)
- **Type safety** — 0 mypy errors, full protocol-based typing for Radio/AudioCapable/ScopeCapable/DualReceiverCapable

## [0.8.0] — 2026-02-28

### Added

- **Web UI v1** — full-featured browser interface at `icom-lan web`:
    - Real-time spectrum and waterfall display (Canvas2D, click-to-tune)
    - Radio controls: VFO A/B, mode, filter, power, ATT, preamp, PTT
    - Band selector buttons (160m–6m with FT8 defaults)
    - Frequency entry, tuning step selector with snap, arrow keys, scroll wheel
    - Frequency marker and filter passband overlay on spectrum/waterfall
    - Eight real-time meter bars (S-meter, Power, SWR, ALC, COMP, Id, Vd, TEMP)
    - RX audio playback and TX audio capture in the browser (WebSocket binary)
    - Responsive layout, light/dark theme toggle, keyboard shortcuts
    - WebSocket pub/sub for scope, meters, audio, and control channels
- **Connect/Disconnect button** in Web UI — toggle radio connection without restarting server
- **Soft reconnect** — disconnect closes only CI-V/audio, keeps control transport alive.
  Reconnect re-opens CI-V instantly (~1s) without discovery or re-authentication.
  Audio auto-restarts after reconnect.
- **Skip discovery on reconnect** — `transport.reconnect()` reuses cached `remote_id`,
  eliminating the 30-60s discovery timeout on IC-7610.
- **Connection state machine** — `RadioConnectionState` enum formalizing connect lifecycle (#61)
- **State cache with TTL** — cached GET fallback values with configurable TTL
  (10s freq/mode, 30s power) via `cache_ttl_s` parameter (#63)
- **API docs from docstrings** — mkdocstrings-generated API reference (#65)
- **Scope assembly timeout** — 5s default prevents memory leak on incomplete frames (#62)

### Changed

- **CI-V commander: fire-and-forget for SET commands** — SET operations no longer wait
  for ACK from the radio, matching wfview behavior. GET commands retain 2s timeout
  with cache fallback on timeout. NAK silently logged at debug level. (#56)
- **`radio.py` refactored into focused modules** — split from 2395 to 1549 lines (#60):
    - `_control_phase.py` (452 lines) — authentication, conninfo, connection setup
    - `_civ_rx.py` (418 lines) — CI-V frame dispatch and RX pump
    - `_audio_recovery.py` (132 lines) — audio stream snapshot/resume
    - `_connection_state.py` — FSM enum for connection lifecycle
    - Public API surface unchanged (mixin pattern)
- **Optimistic port connection** — uses default ports (control+1, control+2) immediately
  instead of blocking on status packet. Status read in background with 2s timeout;
  if radio reports different ports, uses those instead. Eliminates up to 24s connection
  delay when radio returns `civ_port=0` after rapid reconnects.
- **CLI `--port` renamed to `--control-port`** to avoid confusion (#54)

### Fixed

- **CI-V GET timeout during scope streaming** (release blocker, #66) — RX pump now
  drains ALL pending packets from the transport queue each iteration instead of
  processing one at a time. Scope flood (~225 pkt/sec) no longer starves ACK/response
  packets behind hundreds of scope frames.
- **Conninfo local ports** — send reserved ephemeral UDP ports in conninfo packet
  (wfview-style `socket.bind(("", 0))`). Root cause of CI-V instability: radio
  didn't know where to send responses when local ports were 0.
- **Safari iOS audio** — AudioContext resume after background via `visibilitychange`
  listener; increased jitter buffer pre-roll from 50ms to 200ms for VPN use.
- **Flaky `test_hello_on_connect`** — race condition fix, pytest-asyncio dependency (#64)
- **Duplicate WebSocket connections** on page load/reconnect (#50)
- **Scope enable** — single entry point via `server.ensure_scope_enabled()` (#51)
- **PTT button** — toggle mode for click vs hold (#57)
- **Filter sync** after band change (#58)
- **PTT wait_response** restored after fire-and-forget refactor (#59)
- **Watchdog false disconnect** — use packet counter instead of qsize
- **Tuning flood** — throttle tuning commands to prevent CI-V timeout cascade
- **Frequency clamping** — valid range 30 kHz – 60 MHz

### Documentation

- Web UI user guide (`docs/guide/web-ui.md`)
- RFC for Web UI v1 protocol spec and architecture
- Updated architecture docs with mixin pattern and new module structure
- Updated test count: 1202 tests (was 1040)
- Roadmap Phase 8: Virtual Audio Bridge

## [0.7.0] — 2026-02-26

### Added

- Internal PCM<->Opus transcoder foundation for upcoming high-level PCM audio APIs.
- Typed audio exceptions: `AudioCodecBackendError`, `AudioFormatError`, `AudioTranscodeError`.
- High-level async PCM audio APIs: `start_audio_rx_pcm()` / `stop_audio_rx_pcm()`,
  `start_audio_tx_pcm()` / `push_audio_tx_pcm()` / `stop_audio_tx_pcm()`.
- Audio capability introspection: `audio_capabilities()`, `AudioCapabilities`.
- CLI: `icom-lan audio caps`, `audio rx`, `audio tx`, `audio loopback`.
- Runtime audio stats: `get_audio_stats()` with packet loss, jitter, latency metrics.
- Rigctld WSJT-X compatibility: `icom-lan serve --wsjtx-compat`.
- Golden protocol test suite: 45 parametrized fixtures.
- TCP server wire integration tests.

### Changed

- Audio API names explicit with `_opus` suffix.
- Rigctld mode mapping includes `PKTRTTY`.

### Fixed

- First-TX latency spikes in WSJT-X workflows.
- Abandoned rigctld requests no longer execute in background.

### Deprecated

- Ambiguous audio aliases (two-minor-release deprecation window).

## [0.6.0] — 2026-02-25

### Added

- Scope/waterfall API with `ScopeFrame`, `ScopeAssembler`, callbacks.
- Scope rendering: `render_spectrum()`, `render_waterfall()`, `render_scope_image()`.
- CLI `icom-lan scope` with themes, capture, JSON output.
- Mock radio server for integration testing (30 new tests).

## [0.5.1] — 2026-02-25

### Fixed

- `_ensure_audio_transport()` raises `ConnectionError` when audio port is 0.
- Ruff lint warnings resolved.

## [0.5.0] — 2026-02-25

### Added

- Command29 support for dual-receiver radios (IC-7610).
- Attenuator and preamp CLI commands with Command29 framing.

## [0.4.0] — 2026-02-25

### Changed

- Faster non-audio connect path (lazy audio port init).

## [0.3.2] — 2026-02-25

### Added

- Commander layer with priority queue, pacing, dedupe, transactions.
- New APIs: `get_mode_info()`, `get_filter()`, `set_filter()`, `snapshot_state()`.
- Extended integration test coverage.

## [0.3.0] — 2026-02-25

### Added

- Audio streaming (full-duplex, JitterBuffer, codec enum).
- Synchronous API (`icom_lan.sync`).
- Radio model presets (IC-7610, IC-7300, IC-705, IC-9700, IC-R8600, IC-7851).
- Token renewal and auto-reconnect with watchdog.

## [0.2.0] — 2026-02-25

### Added

- CLI tool with full command set.
- VFO control, RF controls, CW keying, power control, network discovery.

## [0.1.0] — 2026-02-24

### Added

- Transport layer, authentication, CI-V commands, meters, PTT, keep-alive.
- Clean-room Icom LAN UDP protocol implementation.

[Unreleased]: https://github.com/morozsm/icom-lan/compare/v0.12.0...HEAD
[0.12.0]: https://github.com/morozsm/icom-lan/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/morozsm/icom-lan/compare/v0.8.0...v0.11.0
[0.8.0]: https://github.com/morozsm/icom-lan/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/morozsm/icom-lan/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/morozsm/icom-lan/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/morozsm/icom-lan/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/morozsm/icom-lan/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/morozsm/icom-lan/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/morozsm/icom-lan/compare/v0.3.1...v0.3.2
[0.3.0]: https://github.com/morozsm/icom-lan/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/morozsm/icom-lan/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/morozsm/icom-lan/releases/tag/v0.1.0
