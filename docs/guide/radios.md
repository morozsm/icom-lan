# Supported Radios

## Tested

### IC-7610

- **CI-V Address:** `0x98`
- **LAN Ports:** 50001 (control), 50002 (CI-V), 50003 (audio)
- **USB:** Serial CI-V + USB audio devices ([setup guide](ic7610-usb-setup.md))
- **Features verified:** frequency, mode, power, S-meter, SWR, ALC, PTT, CW keying, VFO select, split, attenuator, preamp, power on/off, discovery (LAN only), scope/waterfall
- **Dual receiver:** use `select_vfo("MAIN")` / `select_vfo("SUB")`

#### Backend Comparison

| Feature | LAN Backend | Serial Backend |
|---------|-------------|----------------|
| **Control (freq/mode/PTT)** | ✅ Full | ✅ Full |
| **Meters (S/SWR/ALC)** | ✅ Full | ✅ Full |
| **Audio RX** | ✅ Opus/PCM over UDP | ✅ USB audio device |
| **Audio TX** | ✅ Opus/PCM over UDP | ✅ USB audio device |
| **Scope/Waterfall** | ✅ Full (~225 pkt/s) | ⚠️ Requires ≥115200 baud |
| **Dual Receiver** | ✅ Command29 | ✅ Command29 |
| **Remote Access** | ✅ Over LAN/VPN | ❌ USB only |
| **Discovery** | ✅ UDP broadcast | ❌ N/A |
| **Setup** | IP, username, password | USB cable + device path |

!!! tip "USB Serial Setup"
    See the **[IC-7610 USB Serial Backend Setup Guide](ic7610-usb-setup.md)** for step-by-step instructions on using the serial backend (macOS-first).
    For IC-7610 USB operation, set **Menu → Set → Connectors → CI-V → CI-V USB Port**
    to the CI-V option (`Link to [CI-V]`), not `[REMOTE]`.

## Should Work (Untested)

These radios use the same Icom LAN protocol and should work out of the box. Community testing and reports welcome!

### IC-705

- **CI-V Address:** `0xA4`
- **Connectivity:** WiFi (built-in)
- **Notes:** WiFi may have higher latency than Ethernet — consider increasing timeout.

```python
radio = IcomRadio("192.168.1.101", radio_addr=0xA4, timeout=10.0)
```

### IC-7300

- **CI-V Address:** `0x94`
- **Connectivity:** Ethernet (optional LAN module)
- **Notes:** Requires optional LAN interface module.

### IC-9700

- **CI-V Address:** `0xA2`
- **Connectivity:** Ethernet (built-in)
- **Notes:** VHF/UHF/SHF — supports satellite mode and three bands.

### IC-7851

- **CI-V Address:** `0x8E`
- **Connectivity:** Ethernet (built-in)

### IC-R8600

- **CI-V Address:** `0x96`
- **Connectivity:** Ethernet (built-in)
- **Notes:** Receiver only — PTT/TX commands will be rejected.

## Using Presets

Instead of remembering CI-V addresses, use the built-in presets:

```python
from icom_lan import IcomRadio, get_civ_addr

# Look up by model name
radio = IcomRadio("192.168.1.100", radio_addr=get_civ_addr("IC-705"))
```

## Custom CI-V Address

If you've changed your radio's CI-V address in the menu, specify it explicitly:

```python
radio = IcomRadio("192.168.1.100", radio_addr=0x42)
```

## Adding Support for New Radios

The library is CI-V address agnostic — any radio that speaks the Icom LAN protocol should work by specifying the correct `radio_addr`. If you test with a new model:

1. Try connecting with the model's default CI-V address
2. Verify basic operations (frequency, mode, meters)
3. [Open an issue](https://github.com/morozsm/icom-lan/issues) or PR with your findings

### Finding Your Radio's CI-V Address

- Check your radio's **Menu → Set → CI-V** settings
- Look it up in the Icom CI-V reference manual
- The default is usually printed in the radio's specification sheet
