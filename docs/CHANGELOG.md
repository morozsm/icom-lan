# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Internal PCM<->Opus transcoder foundation (`icom_lan._audio_transcoder`) for
  upcoming high-level PCM audio APIs.
- Typed audio exceptions for actionable codec/format failures:
  `AudioCodecBackendError`, `AudioFormatError`, `AudioTranscodeError`.
- High-level async PCM audio APIs on `IcomRadio`:
  - RX: `start_audio_rx_pcm()` / `stop_audio_rx_pcm()`
  - TX: `start_audio_tx_pcm()` / `push_audio_tx_pcm()` / `stop_audio_tx_pcm()`
  RX callbacks receive decoded PCM frame bytes (or `None` gap placeholders).
- Audio capability introspection API:
  - `IcomRadio.audio_capabilities()` (async and sync wrappers)
  - `get_audio_capabilities()` and `AudioCapabilities` export
- CLI command: `icom-lan audio caps` with optional `--json` output.
- CLI audio subcommands:
  - `icom-lan audio rx --out rx.wav --seconds 10`
  - `icom-lan audio tx --in tx.wav`
  - `icom-lan audio loopback --seconds 10`
  with shared `--sample-rate`, `--channels`, `--json`, and `--stats` flags.

### Changed

- Audio low-level API names are now explicit with `_opus` suffix:
  `start_audio_rx_opus()`, `stop_audio_rx_opus()`, `start_audio_tx_opus()`,
  `push_audio_tx_opus()`, `stop_audio_tx_opus()`, plus full-duplex
  `start_audio_opus()` / `stop_audio_opus()`.
- Added parameter validation for high-level PCM TX startup and clearer runtime
  errors when PCM TX is pushed before startup.
- Added parameter validation for high-level PCM RX startup
  (`sample_rate`, `channels`, `frame_ms`, `jitter_depth`, callback).
- Audio defaults now come from deterministic capability rules:
  codec preference order, highest sample rate, and channels implied by codec.

### Deprecated

- Ambiguous audio aliases are deprecated (still functional during a two-minor-release window):
  `start_audio_rx()`, `stop_audio_rx()`, `start_audio_tx()`, `push_audio_tx()`,
  `stop_audio_tx()`, `start_audio()`, `stop_audio()`.
- Synchronous wrapper aliases are likewise deprecated in favor of
  `icom_lan.sync.IcomRadio.*_opus()` names.

## [0.6.0] — 2026-02-25

### Added

- **Scope/waterfall API** — real-time spectrum data from the radio:
    - `ScopeFrame` dataclass with receiver, mode, frequency range, pixel amplitudes
    - `ScopeAssembler` — reassembles multi-sequence CI-V `0x27 0x00` bursts into complete frames
    - `IcomRadio.on_scope_data(callback)` — register callback for assembled scope frames
    - `IcomRadio.enable_scope()` / `disable_scope()` — control scope display and data output
    - Scope command builders: `scope_on`, `scope_off`, `scope_data_output`, `scope_main_sub`,
      `scope_single_dual`, `scope_set_mode`, `scope_set_span`, `scope_set_edge`, `scope_set_hold`,
      `scope_set_ref`, `scope_set_speed`, `scope_set_vbw`, `scope_set_rbw`
    - IC-7610: up to 689 pixels, 15 sequences/frame, dual receiver support
- **Scope rendering** (`pip install icom-lan[scope]`):
    - `render_spectrum()` — spectrum plot (amplitude vs frequency) with grid and labels
    - `render_waterfall()` — heatmap waterfall display, newest frame at top
    - `render_scope_image()` — combined spectrum + waterfall PNG
    - Color themes: `classic` (WSJT-X style) and `grayscale`, extensible via THEMES dict
    - `capture_scope_frame()` / `capture_scope_frames()` — convenience capture methods
- **CLI `icom-lan scope`**:
    - `--output`, `--frames`, `--theme`, `--spectrum-only`, `--width`, `--json`, `--capture-timeout`
- **Mock radio server** (`tests/mock_server.py`) — full UDP emulator for integration testing:
    - Two-port protocol (control + CI-V), complete handshake lifecycle
    - CI-V command responses: frequency, mode, power, meters, ATT, PREAMP, DIGI-SEL
    - `MockIcomRadio` with configurable state and error injection (`auth_fail`, `response_delay`)
    - 30 new integration tests (`tests/test_mock_integration.py`)

### Changed

- `ScopeFrame.pixels` uses `bytes` (not `list[int]`) for memory efficiency
- `enable_scope()` / `disable_scope()` now verify ACK and raise `CommandError` on NAK
- Scope callback persists through disconnect (user manages lifecycle)

## [0.5.1] — 2026-02-25

### Fixed

- `_ensure_audio_transport()` now raises `ConnectionError("Audio port not available")`
  when audio port is unresolved (0) instead of silently guessing a default port
  and hanging on network timeout.
- Fix `ruff` lint warnings: remove unused imports, add new symbols to `__all__`.

## [0.5.0] — 2026-02-25

### Added

- **Command29 support** for dual-receiver radios (IC-7610):
    - `build_cmd29_frame()` — builds CI-V frames with `0x29 <receiver>` prefix.
    - `RECEIVER_MAIN` (0x00) / `RECEIVER_SUB` (0x01) constants.
    - `parse_civ_frame()` now transparently unwraps Command29 responses.
- **Attenuator CLI** (`icom-lan att [VALUE]`):
    - Get current attenuation level (`icom-lan att`)
    - Set level in dB: `icom-lan att 18` (0–45 in 3 dB steps)
    - Toggle: `icom-lan att on`, `icom-lan att off`
    - JSON output: `icom-lan att --json`
- **Preamp CLI** (`icom-lan preamp [VALUE]`):
    - Get current preamp level (`icom-lan preamp`)
    - Set level: `icom-lan preamp 0` (off), `1` (PRE1), `2` (PRE2)
    - JSON output: `icom-lan preamp --json`
- `get_attenuator()` command builder (was missing — only set existed).

### Changed

- **ATT/PREAMP/DIGI-SEL commands now use Command29 framing** by default:
    - `get_preamp()`, `set_preamp()`, `get_attenuator()`, `set_attenuator_level()`,
      `set_attenuator()`, `get_digisel()`, `set_digisel()` all accept `receiver=` parameter.
    - Fixes "Radio rejected preamp level 1" on IC-7610 (the radio requires
      Command29 receiver context for these commands).
- Radio API methods (`IcomRadio.get_preamp()`, `.set_preamp()`, `.get_attenuator_level()`,
  `.set_attenuator_level()`, `.set_attenuator()`) now accept `receiver=` parameter.

## [0.4.0] — 2026-02-25

### Changed

- **Faster non-audio connect path**:
    - CI-V port resolution no longer waits for audio-port negotiation.
    - Audio port initialization is lazy (resolved on first audio use).
    - CLI/API non-audio operations (e.g., `status`) are significantly faster.

### Added

- Additional integration stress coverage for concurrent commander operations.

## [0.3.2] — 2026-02-25

### Added

- **Commander layer** (`icom_lan.commander`):
    - priority CI-V queue (`IMMEDIATE/NORMAL/BACKGROUND`)
    - command pacing (`ICOM_CIV_MIN_INTERVAL_MS`)
    - dedupe keys for background polling
    - transaction helper (`snapshot -> body -> restore`)
- **New radio APIs**:
    - `get_mode_info()`, `get_filter()`, `set_filter()`
    - `get_attenuator()`, `get_preamp()`
    - `snapshot_state()`, `restore_state()`, `run_state_transaction()`
- **Integration coverage expansion**:
    - CW stop interrupt test
    - VFO exchange/equalize integration scenarios
    - full-duplex audio orchestration test
    - TX audio payload test
    - guarded power off/on cycle test (`ICOM_ALLOW_POWER_CONTROL=1`)
    - reconnect + audio recovery test
    - soak test with JSON timeout/recovery logging (`ICOM_SOAK_SECONDS`)

### Improved

- CI-V reliability on real hardware via serialized command execution and pacing.
- Audio stream bring-up reliability (including audio OpenClose behavior).
- Integration guardrails to restore safe baseline state after risky tests.

## [0.3.0] — 2026-02-25

### Added

- **Audio streaming** (Phase 3):
    - `AudioCodec` enum: uLaw, PCM 8/16-bit, Opus 1ch/2ch
    - `JitterBuffer`: reorder out-of-order packets, gap detection, overflow protection
    - Full-duplex audio: simultaneous RX + TX
    - `start_audio()` / `stop_audio()` convenience API
    - Configurable `audio_codec` and `audio_sample_rate` on `IcomRadio`
- **Synchronous API** (`icom_lan.sync`):
    - Blocking `IcomRadio` wrapper with context manager
    - Full API parity with async version
- **Radio model presets** (`icom_lan.radios`):
    - IC-7610 (0x98), IC-7300 (0x94), IC-705 (0xA4), IC-9700 (0xA2), IC-R8600 (0x96), IC-7851 (0x8E)
    - `get_civ_addr()` helper function
- **Token renewal**: background task every 60s (matches wfview protocol)
- **Auto-reconnect**: watchdog + exponential backoff reconnect (opt-in)
    - `auto_reconnect`, `reconnect_delay`, `reconnect_max_delay`, `watchdog_timeout` params

### Improved

- **Test suite**: 180 → 401 tests, coverage 63% → 88%
- **Code quality**: all ruff errors fixed, ack/nak checks added
- ACK/NAK verification for attenuator and preamp commands

### Security

- Removed private IP addresses from all source and git history
- Internal development docs excluded from public repository

## [0.2.0] — 2026-02-25

### Added

- **CLI tool** (`icom-lan`) with commands: `status`, `freq`, `mode`, `power`, `meter`, `ptt`, `cw`, `power-on`, `power-off`, `discover`
- **VFO control**: `select_vfo()`, `vfo_equalize()`, `vfo_exchange()`, `set_split_mode()`
- **RF controls**: `set_attenuator()`, `set_preamp()`
- **CW keying**: `send_cw_text()`, `stop_cw_text()` — with auto-chunking
- **Power control**: `power_control()` for remote power on/off
- **Network discovery**: broadcast-based autodiscovery of Icom radios
- `__main__.py` for `python -m icom_lan` execution
- JSON output option (`--json`) for CLI commands
- Frequency parsing with k/m suffix (`14.074m`, `7074k`)

### Changed

- Bumped version to 0.2.0

## [0.1.0] — 2026-02-24

### Added

- **Transport layer**: async UDP connection with discovery handshake
- **Dual-port architecture**: control port (50001) + CI-V port (50002)
- **Full authentication**: login → token ack → conninfo exchange → status
- **CI-V commands**: `get/set_frequency()`, `get/set_mode()`, `get/set_power()`
- **Meters**: `get_s_meter()`, `get_swr()`, `get_alc()`
- **PTT**: `set_ptt(on/off)`
- **Keep-alive**: automatic ping loop (500ms) and retransmit handling
- **Sequence tracking**: gap detection and retransmit requests
- **Context manager**: `async with IcomRadio(...) as radio:`
- **Custom exceptions**: `ConnectionError`, `AuthenticationError`, `CommandError`, `TimeoutError`
- **Type annotations**: full `py.typed` marker
- **151 unit tests** with mocked transport (no hardware required)
- Integration tests for IC-7610

### Technical

- Clean-room implementation of the Icom LAN UDP protocol
- Protocol knowledge from wfview reverse engineering (GPLv3 reference only)
- BCD frequency encoding/decoding
- Icom credential substitution-table obfuscation
- Waterfall/echo filtering in CI-V response handling
- GUID echo in conninfo exchange (required for CI-V port discovery)

[Unreleased]: https://github.com/morozsm/icom-lan/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/morozsm/icom-lan/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/morozsm/icom-lan/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/morozsm/icom-lan/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/morozsm/icom-lan/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/morozsm/icom-lan/compare/v0.3.1...v0.3.2
[0.3.0]: https://github.com/morozsm/icom-lan/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/morozsm/icom-lan/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/morozsm/icom-lan/releases/tag/v0.1.0
