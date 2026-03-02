# Changelog

## [0.8.0] — 2026-03-02

### ✨ Features
- **Dual-receiver state model**: `RadioState` with MAIN/SUB `ReceiverState`, served via `GET /api/v1/state` (#91)
- **HTTP state polling**: Frontend polls state at 200ms, replaces 12 individual WS event handlers (#91)
- **cmd29 dual-receiver CI-V**: Per-receiver queries for ATT/preamp/NB/NR/DSEL/IP+/AF/RF/SQL/filter
- **NB/NR/DIGI-SEL/IP+ toggle buttons**: Full CI-V control with badge indicators
- **Squelch marker** on S-meter overlay
- **SWR meter**: Calibrated values with color coding (green/yellow/red)
- **ALC meter**: Percentage display with OVER indicator
- **VFO A/B select, swap**: Click to switch active receiver
- **Preamp buttons** (OFF/1/2) with CI-V control
- **AF/RF/Squelch sliders**: Bidirectional sync with radio
- **PTT toggle button**: Click-to-toggle (not momentary) for safety
- **Power level slider**: Synced with PWR meter, shows watts during RX
- **Click PWR bar** to set output power
- **Band buttons**: 60m–10m with band-center frequencies, 3-column grid
- **Audio broadcaster**: Single shared RX stream for all clients (#70)
- **UDP relay proxy**: Remote access via VPN/Tailscale (#73)
- **Interleaved meter/state polling**: Even cycles=meters (40Hz), odd=state (20Hz)
- **Web UI v2.0**: Complete rewrite with spectrum/waterfall, band selector, audio RX/TX

### 🐛 Bug Fixes
- **CI-V transport stability**: Local port binding fix — radio now knows where to send responses
- **BCD meter decoding**: IC-7610 sends meters as BCD, was parsed as binary
- **0x25/0x26 byte order**: Receiver byte is first (data[0]), not last
- **IC-7610 0x16 response format**: Sub-command in data[0], value in data[1]
- **IP+ ≠ DIGI-SEL**: Separated 0x16/0x65 (IP+) from 0x16/0x4E (DIGI-SEL)
- **Slider jitter**: Dead zone ±3 prevents noise from poll updates
- **RX pump restart** on soft_reconnect
- **Watchdog false reconnect loop**: Reset timestamp on soft_reconnect
- **Audio buffer cap** at 150ms — drop frames to keep sync
- **freq_changed/mode_changed always notify**: Removed stale cache guard

### ♻️ Refactoring
- **RadioPoller**: Single CI-V serializer with command queue (#72)
- **Fire-and-forget CI-V**: Matches wfview architecture (#74)
- **Meter calibration on backend**: wfview IC-7610 tables in `meter_cal.py`
- **Radio module split**: `_control_phase.py`, `_civ_rx.py`, `_audio_recovery.py`
- **Connection FSM enum**: Clean state transitions

### ✅ Tests
- 1265 tests passing, 78 skipped
- New: `test_radio_state.py` (12), `test_cmd29_parsing.py` (21)

## [0.7.0] — 2026-02-24

- Initial PyPI release
- LAN connection, CI-V control, rigctld-compatible TCP server
- Web UI with spectrum display and audio streaming
