# Quick Start

Get your first connection in under 5 minutes.

## 1. Set Credentials

Use environment variables to avoid putting credentials in code:

```bash
export ICOM_HOST=192.168.1.100   # Your radio's IP
export ICOM_USER=myuser           # Network username
export ICOM_PASS=mypass           # Network password
```

## 2. Try the CLI

```bash
# Check radio status
icom-lan status
```

Expected output:

```
Frequency:    14,074,000 Hz  (14.074000 MHz)
Mode:         USB
S-meter:      42
Power:        50
```

```bash
# Change frequency
icom-lan freq 14.074m

# Change mode
icom-lan mode USB

# Read meters as JSON
icom-lan meter --json
```

## 3. Python API

Use **`create_radio`** with a backend config to get a **`Radio`** instance (works for both LAN and USB serial backends):

```python
import asyncio
from icom_lan import create_radio, LanBackendConfig

async def main():
    config = LanBackendConfig(
        host="192.168.1.100",
        username="myuser",
        password="mypass",
    )
    async with create_radio(config) as radio:
        # Read current state
        freq = await radio.get_frequency()
        mode, _ = await radio.get_mode()
        s_meter = await radio.get_s_meter()
        print(f"{freq/1e6:.3f} MHz  {mode}  S={s_meter}")

        # Tune to 20m FT8
        await radio.set_frequency(14_074_000)
        await radio.set_mode("USB")

asyncio.run(main())
```

For LAN-only scripts you can still use **`IcomRadio(host, username=..., password=...)`** — see [API Reference](../api/radio.md).

## 4. Discover Radios

Don't know your radio's IP? Use autodiscovery:

```bash
icom-lan discover
```

```
Scanning for Icom radios (3 seconds)...
  Found: 192.168.1.100:50001  id=0xDEADBEEF

1 radio(s) found.
```

## What's Next?

- **[CLI Reference](cli.md)** — full list of CLI commands
- **[CI-V Commands](commands.md)** — frequency, mode, meters, PTT, CW, VFO
- **[Public API Surface](../api/public-api-surface.md)** — supported vs advanced exports
- **[API Reference](../api/radio.md)** — complete Radio API and legacy IcomRadio reference
- **[Connection Lifecycle](connection.md)** — understand the handshake and keep-alive
