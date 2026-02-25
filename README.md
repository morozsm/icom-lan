# icom-lan

Python library for controlling Icom transceivers over LAN (UDP). Direct connection — no wfview, hamlib, or RS-BA1 required.

## Features

- **Direct UDP connection** to Icom radios over Ethernet/WiFi
- **Full CI-V command set**: frequency, mode, power, meters, PTT, CW keying, VFO, split
- **Autodiscovery** of radios on the local network
- **CLI tool** for quick terminal control
- **Async API** (asyncio) for integration into larger applications
- **Zero dependencies** — pure Python, stdlib only

## Supported Radios

Tested: **IC-7610**

Should work with any Icom radio that supports LAN control (IC-705, IC-7300, IC-7851, IC-9700, IC-R8600). CI-V addresses are configurable.

## Installation

```bash
pip install icom-lan
```

Or from source:
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
        # Read
        freq = await radio.get_frequency()
        mode = await radio.get_mode()
        s = await radio.get_s_meter()
        print(f"{freq/1e6:.3f} MHz  {mode.name}  S={s}")

        # Write
        await radio.set_frequency(14_074_000)
        await radio.set_mode("USB")
        await radio.set_power(50)

        # VFO
        await radio.select_vfo("MAIN")  # or "SUB" for IC-7610
        await radio.set_split_mode(True)

        # CW
        await radio.send_cw_text("CQ CQ DE KN4KYD K")

asyncio.run(main())
```

### CLI

```bash
# Set credentials via environment
export ICOM_HOST=192.168.1.100
export ICOM_USER=myuser
export ICOM_PASS=mypass

# Status
icom-lan status
# Frequency:    14,074,000 Hz  (14.074000 MHz)
# Mode:      USB
# S-meter:   42
# Power:     50

# Get/set frequency
icom-lan freq
icom-lan freq 14.074m
icom-lan freq 7074k
icom-lan freq 14074000

# Get/set mode
icom-lan mode
icom-lan mode USB

# Meters (JSON)
icom-lan meter --json
# {"s_meter": 42, "power": 50, "swr": 0, "alc": 0}

# CW
icom-lan cw "CQ CQ DE KN4KYD K"

# PTT
icom-lan ptt on
icom-lan ptt off

# Power on/off
icom-lan power-on
icom-lan power-off

# Discover radios on network
icom-lan discover
```

## API Reference

### IcomRadio

| Method | Description |
|--------|-------------|
| `get_frequency()` → `int` | Current frequency in Hz |
| `set_frequency(hz)` | Set frequency |
| `get_mode()` → `Mode` | Current mode (USB, LSB, CW, AM, FM...) |
| `set_mode(mode)` | Set mode (enum or string) |
| `get_power()` → `int` | RF power level (0-255) |
| `set_power(level)` | Set RF power level |
| `get_s_meter()` → `int` | S-meter reading (0-255) |
| `get_swr()` → `int` | SWR meter (0-255, TX only) |
| `get_alc()` → `int` | ALC meter (0-255, TX only) |
| `set_ptt(on)` | Push-to-talk on/off |
| `select_vfo(vfo)` | Select VFO (A/B/MAIN/SUB) |
| `set_split_mode(on)` | Split on/off |
| `set_attenuator(on)` | Attenuator on/off |
| `set_preamp(level)` | Preamp (0=off, 1, 2) |
| `send_cw_text(text)` | Send CW via built-in keyer |
| `power_control(on)` | Remote power on/off |
| `send_civ(cmd, sub, data)` | Send raw CI-V command |

### Configuration

| Parameter | Default | Env Var | Description |
|-----------|---------|---------|-------------|
| `host` | `192.168.1.100` | `ICOM_HOST` | Radio IP address |
| `port` | `50001` | `ICOM_PORT` | Control port |
| `username` | `""` | `ICOM_USER` | Auth username |
| `password` | `""` | `ICOM_PASS` | Auth password |
| `radio_addr` | `0x98` | — | CI-V address (IC-7610) |
| `timeout` | `5.0` | — | Timeout in seconds |

## How It Works

The library implements the Icom proprietary LAN protocol (reverse-engineered by the [wfview](https://wfview.org/) project):

1. **Control port** (50001): UDP handshake, authentication, session management
2. **CI-V port** (50002): CI-V command exchange (frequency, mode, etc.)
3. **Audio port** (50003): Opus audio streaming (not yet implemented)

Connection sequence: Discovery → Login → Token → Conninfo → CI-V Open → Commands

## License

MIT — see [LICENSE](LICENSE).

Protocol knowledge based on wfview (GPLv3) reverse engineering. This is a clean-room implementation, not a derivative work.
