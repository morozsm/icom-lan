# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.16.1] — 2026-04-14

### Fixed
- **LAN discovery crash** — `OSError: [Errno 65] No route to host` when network
  is unavailable no longer produces a raw traceback; CLI prints a clear message
  and suggests using `--host` explicitly
- **CI strict mypy** — resolved `no-any-return` in `radio_poller.py` for
  `mypy --strict` boundary check
- **Dynamic CI badges** — tests, version, and mypy badges in README now
  auto-update from CI via gist-backed shields.io endpoints

## [0.16.0] — 2026-04-14

### Added
- **DSP Pipeline** (Epic #682) — pluggable audio processing framework:
  - `DSPNode` Protocol, `DSPPipeline` engine, `PassthroughNode`, `GainNode`
  - `NRScipyNode` — spectral subtraction noise reduction (scipy FFT)
  - `TapRegistry` — multi-consumer PCM analysis bus
  - Inter-node resampling utility; `[dsp]` optional dependency group
- **CW Auto Tuner** (#675, #677, #678) — FFT peak detection engine (`CwAutoTuner`),
  backend `cw_auto_tune` command, restored AUTO TUNE button in Web UI
- **AudioAnalyzer** (#679) — realtime SNR estimation from PCM stream
- **UDP Discovery Responder** — companion apps can broadcast `ICOM_LAN_DISCOVER` on
  UDP 8470 and receive server URL, version, and radio status via unicast;
  `--no-discovery` CLI flag to opt out
- **Unified frontend architecture** (Epics #647–#653, #662–#665) — `FrontendRuntime`
  singleton, skin registry, runtime adapters, self-wired panels (AGC, Mode, Antenna,
  RfFrontEnd, RIT/XIT, Scan, CW, DSP, TX, Filter, BandSelector), eslint import
  boundary guardrails, LCD and mobile layout migration to unified runtime path
- **SUB receiver polling** (#562, #563) — TOML commands, receiver routing, AF/RF/squelch
  level polling in slow loop
- **TX meters** (#559) — ALC, Power, COMP, SWR polling during transmit
- **Scope backpressure** (#533) — adaptive poller gap, scope backlog shedding hook,
  `queue_pressure` metric on `IcomTransport`
- **Initial state fetch** (#532) — `_fetch_initial_state()` on connect and reconnect,
  readiness-gated state snapshot in WebServer
- **Cross-sidebar drag** (#566–#568) — move panels between left/right sidebars,
  localStorage persistence, dynamic panel rendering
- **Yaesu FTX-1 enhancements** (#551) — IF bulk query, clarifier clear, APF, CW spot,
  break-in delay, power switch (PS), data mode methods
- **IC-7300 improvements** (#545, #546, #564) — segmented BCD filter width encoding,
  scope marker TOML entry, cleanup of NOT_IMPLEMENTED comments
- **Meter calibration** (#556) — power/SWR/ALC tables in `ic7610.toml`, scope REF
  range constraints, `meter_redlines` in RadioProfile, generic calibration accessors
- **SystemController** (#665) — centralized HTTP system actions
- **Skin abstraction** (#326) — `ProfessionalSkin` (Phase 1)
- **Frontend test coverage** (#555) — component-level tests for LCD, Mobile, Spectrum,
  BandPlan, DspPanel, CwPanel, SpectrumToolbar, DxOverlay, EiBi, state-adapter,
  ws-client, radio store, audio subsystem
- **FTX-1 polling tests** (#551) — integration test suite for Yaesu CAT poller

### Changed
- **Single version source** — `__version__` now reads from `pyproject.toml` via
  `importlib.metadata` instead of being hardcoded in `__init__.py`
- **Frontend panel architecture** — extracted DspPanel + CwPanel logic to dedicated
  panel-logic modules (#594); extracted SpectrumToolbar, BandPlanOverlay,
  MobileRadioLayout, SpectrumPanel inline logic to separate files (#590–#593)
- **LCD layout** (#636) — adapts to reduced viewport height

### Fixed
- **CW auto tune** (#671) — reverted incorrect `cw_sync_tune`, removed broken
  AUTO TUNE button before reimplementing correctly
- **Shutdown reliability** (#634) — `os._exit()` for orphaned threads, manual loop
  with executor timeout, PortAudio stream close before task cancel, shutdown step
  timeouts
- **Audio stability** — drop frames while `AudioContext` suspended, resume once in
  `start()` instead of per-frame
- **Yaesu serial** — report `disconnected` status correctly, show serial port in
  startup banner, graceful poller disconnect handling
- **Connection readiness** (#602) — expose readiness fields from backend state
- **Frontend null guards** (#603–#605) — null receiver state, null numeric fields
  coerced to defaults, encoder revision for initial state snapshot
- **Disconnect cleanup** (#600) — clear stale state, reset delta and radio store
- **Code review fixes** (#670, #576) — 5 findings from session audit, layering and
  model guards, reconnect timing
- **Drag-reorder** — unregister instances from registry on component destroy
- **All mypy errors resolved** — `ControlPhaseHost` protocol gap, `YaesuCatRadio`
  missing `get_data_mode`/`set_data_mode`, scipy stubs, `no-any-return` fixes
- **All ruff errors resolved** — unused imports in test_cli.py

### Documentation
- Refreshed Web UI guide for v2 runtime and skin workflows (#681)

## [0.15.1] — 2026-04-10

### Changed
- **Web UI v2 is now the default layout.** New visitors and fresh installs see the
  redesigned RadioLayout v2 interface. Users who previously selected v1 keep their
  choice (persisted in localStorage). Switch manually with `?ui=v1` or `?ui=v2`.

## [0.15.0] — 2026-04-10

### Added
- **Zero-config CLI startup** (Epic #526) — `icom-lan web` auto-discovers radio via LAN broadcast,
  `--preset hamradio|digimode|serial|headless` for common scenarios, smart startup banner with
  loopback device hints (#527, #528, #529, #530).
- **Drag-and-drop panel reorder** — drag handles on right sidebar panels (#557).
- **Complete CI-V command coverage** (Epic #535) — scope settings popover (#538), missing polling
  entries (#539), VOX/CW/DSP panels (#540), TX band edge support (#541), memory channel
  manager + scan modes (#542, #543), TX meters + scope toolbar controls (#536, #537).
- **Center dead zone for RF/SQL dual slider** — prevents accidental threshold jumps.
- **Poller deadlock regression tests** (#554) — state consistency + deadlock detection tests.
- **Yaesu CAT backend and CLI factory routing** — `--backend yaesu-cat`, capability-based polling,
  rigctl routing strategy, Web ControlHandler support, meters/advanced-control conformance,
  and follow-up code review fixes for issues #427-#445.
- **Universal radio profile system** — declarative `OperatingProfile` / `apply_profile()` /
  `PRESETS`, packet/data profile helpers for IC-705, and additional sync control methods.
- **TLS/HTTPS for Web UI** — HTTPS listener support with automatic self-signed certificates (#205).
- **Audio FFT UI work** — full-color `AudioSpectrumPanel`, standard-layout integration, audio-scope
  WebSocket channel, variable FFT bandwidth handling, and audio spectrum rendering fixes.
- **Expanded Web/rigctld command coverage** — raw CI-V passthrough, levels/functions support,
  data mode inputs/levels, VOX, tone/TSQL, CW text/stop, band/split, system/config,
  selected/unselected freq+mode, memory API support, and scope toolbar controls.
- **Capability/tag cleanup** — extracted `capabilities.py`, added `system_settings` tag,
  `supports_command()` on the Radio protocol, and removed remaining protocol abstraction gaps.
- **Issue #448 UI/antenna work** — v2 antenna panel, capability/state tracking, corrected IC-7610
  TX ANT vs RX ANT semantics, and startup readiness checks split between connect-time validation
  and server-side guards.

### Changed
- **Connection readiness contract** — `radio.connect()` now owns bounded wait-for-ready and fails
  if the radio never becomes usable; Web UI and rigctld startup now perform instant guards only.
- **Protocol/capability routing** — replaced several `isinstance(AdvancedControlCapable)` checks with
  capability tags and centralized capability constants.
- **Spectrum/waterfall interaction architecture** — clean separation of gesture, drag, and tune layers.
- **Frontend/test hygiene** — resolved Svelte/type issues, fixed frontend redesign regressions,
  refreshed API docs and badges, and updated test fixtures for stricter protocol mocks.

### Fixed
- **Meter calibration** (#536) — corrected S-meter, RF power, SWR, ALC calibration tables per
  IC-7610 CI-V Reference p.4; dimmed irrelevant meter rows.
- **Scope REF BCD encode/decode** (#553) — fixed to match IC-7610 CI-V Reference p.15.
- **CENTER Type polling** (#552) — fixed root cause: poller was overwriting scope CENTER Type
  to Filter on every poll cycle; restored CTR mode indicator at center position.
- **Tuning indicator** (#552) — proportional positioning + scope REF display.
- **Deadlock: EnableScope** — EnableScope await blocked all commands during initial fetch.
- **Click-to-tune** — only on waterfall, not spectrum area; via pointerup instead of click event.
- **Reliable shutdown** — 3-tier signal handling, reuse_address for TIME_WAIT, force exit on
  second Ctrl-C, proper audio relay shutdown order.
- **AF scope** — bandwidth tracks actual filter width, crash fix when center_freq is 0.
- **Power-off state** not detected on server restart.
- **Startup fail-fast** — added pre-flight port check (#422), fail-fast on `civ_port=0` (#424),
  and eliminated half-working Web/rigctld startups when the radio transport is not actually ready.
- **IC-705 Wi-Fi binding** — hardened routed local bind handling and validated LAN support.
- **Audio/runtime stability** — fixed broadcaster restart behavior, audio handler lifecycle,
  control transport queue overflow after long runs, and Python 3.13 flaky tests (#398).
- **Scope/UI correctness** — fixed scope dispatch capability checks, scope polling/state updates,
  step-control width, BCD span payloads, speed arrow direction, PTT TX wiring, and optimistic
  state sync for antenna/scope controls.
- **Type-check/lint cleanup** — resolved all 188 ruff lint errors and 499 mypy type errors:
  file-level noqa for re-export modules, mixin TYPE_CHECKING base pattern, per-module mypy
  overrides for duck-typing consumers, and ControlPhaseHost protocol expansion.

### Documentation
- Added/updated Radio Profiles guide, web/rigctld API references, and test badges/documentation sync.

## [0.14.2] — 2026-03-27

### Changed
- **Git cleanup** — removed 83 tracked files (-33k lines): backups, internal dev docs
  (plans/sprints/reviews/audits), scripts, mockups, references, credentials in run-dev.sh
- **Documentation refresh** — index.md, radios.md, README.md updated for multi-vendor reality;
  FTX-1 moved from "planned" to "tested"; mkdocs nav expanded with 12 missing pages;
  5 broken links fixed; mkdocs build --strict passes clean
- **CI fixed** — removed parity matrix tests (depended on deleted files); marked 2 flaky
  reconnect tests as xfail (#398); CI green on Python 3.11/3.12/3.13

## [0.14.1] — 2026-03-27

### Fixed
- FTX-1 LCD layout, band indicator, DSP/TX panel redesign, CAT fixes (feature/ftx1-filter-width)
- Removed FTX-1 monitor tests (ML command not supported via CAT)
- Fixed tuner routing through command queue for Yaesu radios

## [0.14.0] — 2026-03-27

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
- **Yaesu CAT backend** (Epic #107) — full implementation for Yaesu FTX-1/FT-710/FT-991A:
  - YaesuCatTransport (async line protocol, `;` terminated, echo handling)
  - CAT template formatter + response parser (compile-once)
  - Polling scheduler for smooth meters (fast meters, slower state)
  - Full Web UI integration (command dispatch, levels, audio)
- **Audio FFT Scope** (Epic #383) — IF waterfall from USB/LAN audio stream:
  - AudioFftScope class (real-time FFT processor, consumes PCM, produces ScopeFrame)
  - Backend-agnostic (works with any AudioCapable radio)
  - Reuses existing scope protocol (SpectrumPanel + WaterfallCanvas)
- **Amber LCD display** (#389, #386) — retro KX3-style UI for radios without hardware spectrum:
  - 7-segment font, segmented bargraph, status indicators
  - Embedded Audio FFT strip (trapezoid filter visualization)
  - Grouped indicators (ATT/PRE/ATU/Contour/PROC/VOX)
  - Adaptive lerp (smooth animated filter width transitions)
- **Profile-driven command dispatch** (Epic #390-#396) — auto-wire all TOML commands to Web UI:
  - Frontend capability guards for multi-radio (hide unsupported controls)
  - Optimistic UI updates for NB/NR levels
  - Auto-reconnect on persistent serial errors
- **Serial discovery** (Epic #222) — `icom-lan discover` scans LAN + USB serial:
  - Multi-protocol probing (CI-V auto baud, Yaesu CAT, Kenwood CAT)
  - Deduplication (same radio found via LAN and serial)
- 42 new tests in `test_rig_multi_vendor.py` + 636 new tests total (3934 passed, 0 regressions)

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

[Unreleased]: https://github.com/morozsm/icom-lan/compare/v0.16.1...HEAD
[0.16.1]: https://github.com/morozsm/icom-lan/compare/v0.16.0...v0.16.1
[0.16.0]: https://github.com/morozsm/icom-lan/compare/v0.15.1...v0.16.0
[0.15.1]: https://github.com/morozsm/icom-lan/compare/v0.15.0...v0.15.1
[0.15.0]: https://github.com/morozsm/icom-lan/compare/v0.14.2...v0.15.0
[0.14.2]: https://github.com/morozsm/icom-lan/compare/v0.14.1...v0.14.2
[0.14.1]: https://github.com/morozsm/icom-lan/compare/v0.14.0...v0.14.1
[0.14.0]: https://github.com/morozsm/icom-lan/compare/v0.12.0...v0.14.0
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
