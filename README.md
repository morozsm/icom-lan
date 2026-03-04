# icom-lan

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1772%20passed-brightgreen.svg)](#testing)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](#testing)

**Python library for controlling Icom transceivers over LAN (UDP).**

Direct connection to your radio — no wfview, hamlib, or RS-BA1 required.

## Features

- 📡 **Direct UDP connection** — no intermediate software needed
- 🎛️ **Full CI-V command set** — frequency, mode, filter, power, meters, PTT, CW keying, VFO, split, ATT, PREAMP
- 🔍 **Network discovery** — find radios on your LAN automatically
- 💻 **CLI tool** — `icom-lan status`, `icom-lan freq 14.074m`
- ⚡ **Async API** — built on asyncio for seamless integration
- 🚀 **Fast non-audio connect path** — CLI/status calls don't block on audio-port negotiation
- 🧠 **Commander queue** — wfview-style serialized command execution with pacing, retries, and dedupe
- 📊 **Scope/waterfall** — real-time spectrum data with callback API
- 🌐 **Built-in Web UI** — spectrum, waterfall, controls, meters, and audio in your browser (`icom-lan web`):
  - 🎛️ **Dual-receiver display** — MAIN and SUB receiver state (IC-7610)
  - 📻 **Band selector** — one-click band buttons (160m–10m)
  - 🔊 **Browser audio TX** — transmit from your microphone via Opus codec
  - 🎚️ **Full control panel** — AF/RF/Squelch sliders, NB/NR/DIGI-SEL/IP+ toggles, ATT/Preamp, VFO A/B
  - 📊 **Meters** — S-meter, SWR (color-coded), ALC, Power, Vd, Id
  - 🔄 **Live state sync** — HTTP polling at 200ms, no page refresh needed
- 🔊 **Virtual audio bridge** — route radio audio to BlackHole/Loopback for WSJT-X, fldigi, JS8Call (`icom-lan web --bridge "BlackHole 2ch"`)
- 🔌 **Hamlib NET rigctld server** — drop-in replacement for `rigctld`, works with WSJT-X, JS8Call, fldigi
- 🎛️ **Dual-receiver support** — MAIN/SUB via Command29 (IC-7610)
- 🎤 **Browser audio TX** — transmit from browser microphone
- 📡 **UDP relay proxy** — remote access via VPN/Tailscale
- 🔒 **Zero dependencies** — pure Python, stdlib only
- 📝 **Type-annotated** — full `py.typed` support

## Supported Radios

| Radio | Status | CI-V Address |
|-------|--------|-------------|
| **IC-7610** | ✅ Tested | `0x98` |
| IC-705 | Should work | `0xA4` |
| IC-7300 | Should work | `0x94` |
| IC-9700 | Should work | `0xA2` |
| IC-7851 | Should work | `0x8E` |
| IC-R8600 | Should work | `0x96` |

Any Icom radio with LAN/WiFi control should work — the CI-V address is configurable.

## Installation

```bash
pip install icom-lan
```

From source:

```bash
git clone https://github.com/morozsm/icom-lan.git
cd icom-lan
pip install -e .
```

## Quick Start

### Python API

```python
import asyncio
from icom_lan import IcomRadio

async def main():
    async with IcomRadio("192.168.1.100", username="user", password="pass") as radio:
        # Read current state
        freq = await radio.get_frequency()
        mode = await radio.get_mode()
        s = await radio.get_s_meter()
        print(f"{freq/1e6:.3f} MHz  {mode.name}  S={s}")

        # Tune to 20m FT8
        await radio.set_frequency(14_074_000)
        await radio.set_mode("USB")

        # VFO & Split
        await radio.select_vfo("MAIN")
        await radio.set_split_mode(True)

        # CW
        await radio.send_cw_text("CQ CQ DE KN4KYD K")

        # Scope / Waterfall
        def on_frame(frame):
            print(f"{frame.start_freq_hz/1e6:.3f}–{frame.end_freq_hz/1e6:.3f} MHz, {len(frame.pixels)} px")
        radio.on_scope_data(on_frame)
        await radio.enable_scope()

asyncio.run(main())
```

### CLI

```bash
# Set credentials via environment
export ICOM_HOST=192.168.1.100
export ICOM_USER=myuser
export ICOM_PASS=mypass

# Radio status
icom-lan status

# Frequency (multiple input formats)
icom-lan freq             # Get
icom-lan freq 14.074m     # Set (MHz)
icom-lan freq 7074k       # Set (kHz)
icom-lan freq 14074000    # Set (Hz)

# Mode
icom-lan mode USB

# Meters (JSON output)
icom-lan meter --json

# CW keying
icom-lan cw "CQ CQ DE KN4KYD K"

# PTT
icom-lan ptt on
icom-lan ptt off

# Attenuator & Preamp (Command29-aware for IC-7610)
icom-lan att              # Get attenuation level
icom-lan att 18           # Set 18 dB
icom-lan preamp           # Get preamp level
icom-lan preamp 1         # Set PREAMP 1

# Scope / Waterfall snapshot (requires: pip install icom-lan[scope])
icom-lan scope                      # Combined spectrum + waterfall → scope.png
icom-lan scope --spectrum-only      # Spectrum only (1 frame)
icom-lan scope --theme grayscale    # Grayscale theme
icom-lan scope --json               # Raw data as JSON (no Pillow needed)

# Example output
![Scope + waterfall example](docs/assets/scope-example.png)

# Remote power on/off
icom-lan power-on
icom-lan power-off

# UDP relay proxy (for VPN/Tailscale remote access)
icom-lan proxy --remote-host 192.168.55.40 --listen-port 50001

# Discover radios on network
icom-lan discover

# Built-in Web UI (spectrum, waterfall, controls, audio)
icom-lan web                            # Start on 0.0.0.0:8080
icom-lan web --port 9090                # Custom port
# Then open http://your-ip:8080 in a browser

# Hamlib NET rigctld-compatible server (use with WSJT-X, JS8Call, fldigi)
icom-lan serve                          # Listen on 0.0.0.0:4532
icom-lan serve --port 4532 --read-only  # Read-only mode (no TX control)
icom-lan serve --max-clients 5          # Limit concurrent clients
icom-lan serve --wsjtx-compat           # Pre-warm DATA mode for WSJT-X CAT/PTT flow

# Then in WSJT-X: Rig → Hamlib NET rigctl, Address: localhost, Port: 4532

# All-in-one: Web UI + audio bridge + rigctld
icom-lan web --bridge "BlackHole 2ch"
# Now WSJT-X gets: CAT via rigctld (:4532) + audio via BlackHole

# List available audio devices
icom-lan audio bridge --list-devices

# Audio bridge only (no web UI)
icom-lan audio bridge --device "BlackHole 2ch"
icom-lan audio bridge --device "BlackHole 2ch" --rx-only
```

## API Reference

### IcomRadio Methods

| Method | Description |
|--------|-------------|
| `get_frequency()` → `int` | Current frequency in Hz |
| `set_frequency(hz)` | Set frequency |
| `get_mode()` → `Mode` | Current mode |
| `get_mode_info()` → `(Mode, filter)` | Current mode + filter number (if reported) |
| `set_mode(mode, filter_width=None)` | Set mode (optionally with filter 1-3) |
| `get_filter()` / `set_filter(n)` | Read/set filter number |
| `get_power()` → `int` | RF power level (0–255) |
| `set_power(level)` | Set RF power |
| `get_s_meter()` → `int` | S-meter (0–255) |
| `get_swr()` → `int` | SWR meter (0–255, TX only) |
| `get_alc()` → `int` | ALC meter (0–255, TX only) |
| `set_ptt(on)` | Push-to-talk on/off |
| `select_vfo(vfo)` | Select VFO (A/B/MAIN/SUB) |
| `set_split_mode(on)` | Split on/off |
| `get_attenuator_level(receiver)` → `int` | Read attenuator in dB (Command29) |
| `set_attenuator_level(db, receiver)` | Set attenuator dB (0–45, 3 dB steps) |
| `get_preamp(receiver)` → `int` | Read preamp level (Command29) |
| `set_preamp(level, receiver)` | Set preamp (0=off, 1=PRE1, 2=PRE2) |
| `on_scope_data(callback)` | Register callback for scope/waterfall frames |
| `enable_scope(output=True)` | Enable scope display + data output |
| `disable_scope()` | Disable scope data output |
| `send_cw_text(text)` / `stop_cw_text()` | Send/stop CW via built-in keyer |
| `power_control(on)` | Remote power on/off |
| `snapshot_state()` / `restore_state(state)` | Best-effort state save/restore |
| `send_civ(cmd, sub, data)` | Send raw CI-V command |
| `get_nb(receiver)` / `set_nb(on, receiver)` | Noise Blanker on/off (Command29) |
| `get_nr(receiver)` / `set_nr(on, receiver)` | Noise Reduction on/off (Command29) |
| `get_digisel(receiver)` / `set_digisel(on, receiver)` | DIGI-SEL on/off (Command29) |
| `get_ip_plus(receiver)` / `set_ip_plus(on, receiver)` | IP+ on/off (Command29) |
| `get_data_mode()` / `set_data_mode(on)` | DATA mode on/off |
| `get_af_level(receiver)` / `set_af_level(level, receiver)` | AF gain level (0-255, Command29) |
| `get_rf_gain(receiver)` / `set_rf_gain(level, receiver)` | RF gain level (0-255, Command29) |
| `set_squelch(level, receiver)` | Squelch level (0-255, Command29) |
| `start_audio_rx()` / `stop_audio_rx()` | Start/stop RX audio stream |
| `start_audio_tx()` / `stop_audio_tx()` | Start/stop TX audio stream |
| `push_audio_tx_opus(data)` | Push Opus audio frames for TX |
| `audio_bus` | AudioBus pub/sub for multi-consumer audio distribution |
| `vfo_exchange()` | Exchange VFO A↔B frequencies |
| `vfo_equalize()` | Copy active VFO to inactive |

### HTTP Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/state` | Dual-receiver state JSON (MAIN+SUB) |
| `GET /api/v1/bridge` | Audio bridge status |
| `POST /api/v1/bridge` | Start audio bridge |
| `DELETE /api/v1/bridge` | Stop audio bridge |

### Configuration

| Parameter | Default | Env Var | Description |
|-----------|---------|---------|-------------|
| `host` | — | `ICOM_HOST` | Radio IP address |
| `port` | `50001` | `ICOM_PORT` | Control port |
| `username` | `""` | `ICOM_USER` | Auth username |
| `password` | `""` | `ICOM_PASS` | Auth password |
| `radio_addr` | `0x98` | — | CI-V address |
| `timeout` | `5.0` | — | Timeout (seconds) |

## How It Works

The library implements the Icom proprietary LAN protocol:

1. **Control port** (50001) — UDP handshake, authentication, session management
2. **CI-V port** (50002) — CI-V command exchange
3. **Audio port** (50003) — RX/TX audio streaming (including full-duplex orchestration)

```
Discovery → Login → Token → Conninfo → CI-V Open → Commands
```

See the [protocol documentation](https://morozsm.github.io/icom-lan/internals/protocol/) for a deep dive.

## Multi-Radio Architecture

icom-lan uses an abstract **Radio Protocol** that enables support for multiple radio backends with a single Web UI and API.

```
┌──────────────────────────────────────────────┐
│          Web UI  /  rigctld  /  CLI           │
├──────────────────────────────────────────────┤
│          Radio Protocol (core)                │
│  ┌──────────────┬─────────────┬────────────┐ │
│  │ AudioCapable │ ScopeCapable│ DualRxCap. │ │
│  └──────────────┴─────────────┴────────────┘ │
├────────┬──────────┬──────────┬───────────────┤
│IcomLAN │IcomSerial│ YaesuCAT │  Future...    │
└────────┴──────────┴──────────┴───────────────┘
```

- **`Radio`** — core protocol: freq, mode, PTT, meters, power, levels
- **`AudioCapable`** — audio streaming (LAN or USB audio device)
- **`ScopeCapable`** — spectrum/panadapter data
- **`DualReceiverCapable`** — dual independent receivers (IC-7610 Main/Sub)

📖 **Full protocol docs:** [Radio Protocol](docs/radio-protocol.md)

## Testing

```bash
# Unit tests (no radio required) — 1772 tests, 95% coverage
pytest tests/test_*.py

# Mock integration tests (full UDP protocol, no radio required)
pytest tests/test_mock_integration.py

# Integration tests (real radio required)
export ICOM_HOST=192.168.55.40
export ICOM_USER=your_username
export ICOM_PASS=your_password
pytest -m integration tests/integration

# Guarded power-cycle test (will actually power off/on radio)
export ICOM_ALLOW_POWER_CONTROL=1
pytest -m integration tests/integration/test_radio_integration.py::TestPowerHardware::test_power_cycle_roundtrip -q -s

# Soak test (seconds)
export ICOM_SOAK_SECONDS=120
pytest -m integration tests/integration/test_radio_integration.py::TestSoak::test_soak_retries_and_logging -q -s
```

## Documentation

📖 **Full documentation:** [morozsm.github.io/icom-lan](https://morozsm.github.io/icom-lan)

- [Getting Started](https://morozsm.github.io/icom-lan/guide/quickstart/)
- [CLI Reference](https://morozsm.github.io/icom-lan/guide/cli/)
- [API Reference](https://morozsm.github.io/icom-lan/api/radio/)
- [Protocol Internals](https://morozsm.github.io/icom-lan/internals/protocol/)
- [Security](https://morozsm.github.io/icom-lan/SECURITY/)

## Security

- Zero external dependencies — minimal attack surface
- Credentials passed via env vars or parameters, never stored
- The Icom protocol uses UDP without encryption — see [SECURITY.md](docs/SECURITY.md)

## License

MIT — see [LICENSE](LICENSE).

Protocol knowledge based on [wfview](https://wfview.org/) (GPLv3) reverse engineering. This is an independent clean-room implementation, not a derivative work.

## Acknowledgments

- The [wfview](https://wfview.org/) project for their extensive reverse engineering of the Icom LAN protocol
- The amateur radio community for testing and feedback

## Trademark Notice

Icom™ and the Icom logo are registered trademarks of [Icom Incorporated](https://www.icomjapan.com/). This project is not affiliated with, endorsed by, or sponsored by Icom. Product names are used solely for identification and compatibility purposes (nominative fair use).

---

73 de KN4KYD 🏗️
