# Installation

## Requirements

- **Python 3.11+**
- An Icom radio with LAN/WiFi connectivity (IC-7610, IC-705, IC-7300, IC-9700, etc.)
- Network access to the radio (same LAN/subnet)

## Install from PyPI

```bash
pip install icom-lan
```

## Install from Source

```bash
git clone https://github.com/morozsm/icom-lan.git
cd icom-lan
pip install -e .
```

## Development Install

For running tests and contributing:

```bash
git clone https://github.com/morozsm/icom-lan.git
cd icom-lan
pip install -e ".[dev]"
```

## Optional: Audio Support

For Opus codec audio streaming:

```bash
pip install icom-lan[audio]
```

This installs `opuslib` for Opus codec support. Not required for PCM/uLaw audio.

## Verify Installation

```bash
# Check the CLI is available
icom-lan --help

# Or run as a module
python -m icom_lan --help
```

## Radio Setup

Before connecting, ensure your radio is configured for LAN control:

### IC-7610

1. **Menu → Set → Network** — configure IP address (static recommended)
2. **Menu → Set → Network → Remote Control** — enable "Network Control"
3. **Menu → Set → Network → Network User** — create a username/password
4. Default port: **50001**

### IC-705

1. **Menu → Set → WLAN Set** — connect to your WiFi network
2. **Menu → Set → Network → Remote Control** — enable
3. **Menu → Set → Network → Network User** — create credentials

### IC-7300

1. Requires the **optional LAN module** or use via IC-7610's second CI-V port
2. Same network settings menu structure

!!! tip "Static IP Recommended"
    Assign a static IP to your radio to avoid connection issues after DHCP lease changes.

!!! warning "Firewall"
    Ensure UDP ports **50001-50003** are open between your computer and the radio.
