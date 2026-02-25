# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[0.3.0]: https://github.com/morozsm/icom-lan/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/morozsm/icom-lan/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/morozsm/icom-lan/releases/tag/v0.1.0
