# IC-7610 USB Serial Backend Setup (macOS)

This guide shows how to control the IC-7610 via **USB serial CI-V + USB audio devices** instead of the default LAN backend.

## Why Use the Serial Backend?

- **No network required** — direct USB connection
- **Lower latency** — no UDP/network overhead
- **Simpler setup** — no IP config, username, or password
- **Field operation** — works without WiFi/Ethernet

## Hardware Requirements

- IC-7610 transceiver
- USB A-to-B cable (typically included with the radio)
- macOS computer (tested on Ventura+ arm64/Intel)

## Radio Configuration

!!! danger "Critical Setup Step"
    On the IC-7610, navigate to **Menu → Set → Connectors → CI-V → CI-V USB Port** and set it to **`Link to [CI-V]`**, **NOT** `[REMOTE]`.
    
    - `Link to [CI-V]` — serial CI-V commands work (required for icom-lan serial backend)
    - `[REMOTE]` — RS-BA1 mode, serial CI-V is blocked
    
    This finding was confirmed with live hardware validation in issue #146.

### Recommended Radio Settings

| Setting | Value | Why |
|---------|-------|-----|
| **CI-V USB Port** | `Link to [CI-V]` | ✅ Required — enables serial CI-V |
| **CI-V USB Baud Rate** | `115200` | Recommended for scope/waterfall |
| **CI-V Address** | `0x98` (default) | Library auto-detects, but confirm if changed |
| **USB Audio TX** | Enabled | Allows browser/WSJT-X TX via USB audio |
| **USB Audio RX** | Enabled | Exports RX audio to computer |

!!! note "Baud Rate"
    - `115200` baud is recommended for scope/waterfall capability
    - Lower baud rates (19200, 9600) work for basic control (freq, mode, PTT) but scope/waterfall is disabled by a guardrail due to high packet rate
    - CI-V baud rate IS significant on IC-7610 — it must match between radio and library

## macOS Setup

### 1. Install icom-lan

```bash
pip install icom-lan

# For serial CI-V control:
pip install icom-lan

# For USB audio RX/TX and audio-device listing:
pip install 'icom-lan[serial,bridge]'

# serial: pyserial + pyserial-asyncio
# bridge: sounddevice + numpy + opuslib
```

### 2. Connect the Radio

1. Power on the IC-7610
2. Connect USB A-to-B cable from Mac to IC-7610 **USB (B)** port (rear panel, square connector)
3. Wait ~5 seconds for macOS to enumerate the device

### 3. Find the Serial Device

```bash
# List serial devices
ls -l /dev/cu.usbserial-*

# Example output:
# /dev/cu.usbserial-111120
```

The IC-7610 typically appears as `/dev/cu.usbserial-XXXXXX` where `XXXXXX` is the radio's serial number.

You can also use `icom-lan discover --serial-only` to find USB-connected radios automatically:

```bash
icom-lan discover --serial-only
```

```
IC-7610:
  • Serial: /dev/cu.usbserial-111120 (19200 baud)
```

### 4. Find USB Audio Devices

```bash
# List available audio devices
icom-lan --list-audio-devices
```

This command requires the optional bridge dependencies:

```bash
pip install 'icom-lan[bridge]'
```

Example output:

```
4 audio device(s):
  [0] IC-7610 USB Audio  (in=2, out=2)
  [1] Built-in Microphone  (in=2, out=0)
  [2] Built-in Output  (in=0, out=2)
  [3] BlackHole 2ch  (in=2, out=2)
```

The IC-7610 USB audio device is typically named `IC-7610 USB Audio` or similar.

!!! tip "JSON Output"
    ```bash
    icom-lan --list-audio-devices --json
    ```
    Returns structured JSON for scripting.

### 5. Test the Connection

```bash
# Set environment variables
export ICOM_SERIAL_DEVICE=/dev/cu.usbserial-111120
export ICOM_SERIAL_BAUDRATE=115200

# Test basic control
icom-lan --backend serial status
icom-lan --backend serial freq
icom-lan --backend serial mode
```

Expected output:

```
Frequency:    14,074,000 Hz  (14.074000 MHz)
Mode:         USB
S-meter:      42
Power:        50
```

### 6. Test Audio (Optional)

```bash
# Capture 10 seconds of RX audio to WAV
icom-lan --backend serial \
    --rx-device "IC-7610 USB Audio" \
    audio rx --out test_rx.wav --seconds 10

# Audio devices are auto-detected if not specified
```

## Usage Examples

### CLI

```bash
# Status check
icom-lan --backend serial status

# Set frequency
icom-lan --backend serial freq 7.074m

# Set mode
icom-lan --backend serial mode USB

# PTT on/off
icom-lan --backend serial ptt on
icom-lan --backend serial ptt off

# CW keying
icom-lan --backend serial cw "CQ CQ DE KN4KYD K"

# Attenuator (uses Command29 for IC-7610)
icom-lan --backend serial att 18
icom-lan --backend serial att 0

# Preamp
icom-lan --backend serial preamp 1
icom-lan --backend serial preamp 0
```

### Python API

```python
import asyncio
from icom_lan.backends.factory import create_radio
from icom_lan.backends.config import SerialBackendConfig

async def main():
    config = SerialBackendConfig(
        device="/dev/cu.usbserial-111120",
        baudrate=115200,
        radio_addr=0x98,
        rx_device="IC-7610 USB Audio",  # or None for auto-detect
        tx_device="IC-7610 USB Audio",  # or None for auto-detect
    )
    
    radio = create_radio(config)
    
    async with radio:
        # Control
        freq = await radio.get_frequency()
        print(f"Frequency: {freq/1e6:.3f} MHz")
        
        await radio.set_frequency(14_074_000)
        await radio.set_mode("USB")
        
        # Meters
        s = await radio.get_s_meter()
        print(f"S-meter: {s}")
        
        # Audio (if audio_capable)
        from icom_lan.radio_protocol import AudioCapable
        if isinstance(radio, AudioCapable):
            def on_audio(packet):
                print(f"RX audio: {len(packet.data)} bytes")
            
            await radio.start_audio_rx_opus(on_audio)
            await asyncio.sleep(10)
            await radio.stop_audio_rx_opus()

asyncio.run(main())
```

### Web UI with Serial Backend

```bash
# Start web UI on serial backend
icom-lan --backend serial \
    --rx-device "IC-7610 USB Audio" \
    --tx-device "IC-7610 USB Audio" \
    web

# Then open http://localhost:8080
```

The web UI will show:
- Frequency/mode control
- Meters (S-meter, power, SWR during TX)
- RX audio streaming to browser
- TX audio from browser microphone (if USB audio TX is enabled)

### rigctld with Serial Backend

```bash
# Start rigctld server on serial backend
icom-lan --backend serial serve

# Then configure WSJT-X:
# Radio: Hamlib NET rigctl
# Network Server: localhost:4532
```

## Capability Differences: LAN vs Serial

| Feature | LAN Backend | Serial Backend |
|---------|-------------|----------------|
| **Control (freq/mode/PTT)** | ✅ Full | ✅ Full |
| **Meters (S/SWR/ALC)** | ✅ Full | ✅ Full |
| **Audio RX** | ✅ Opus/PCM over UDP | ✅ USB audio device |
| **Audio TX** | ✅ Opus/PCM over UDP | ✅ USB audio device |
| **Scope/Waterfall** | ✅ Full (~225 pkt/s) | ⚠️ Requires ≥115200 baud* |
| **Dual Receiver** | ✅ Command29 | ✅ Command29 |
| **Remote Access** | ✅ Over LAN/VPN | ❌ USB only |
| **Discovery** | ✅ UDP broadcast | ✅ CI-V auto-probe |

\* **Scope guardrail**: Serial backend enforces a minimum 115200 baud for scope/waterfall operations due to high CI-V packet rate. Lower baud rates risk command timeout/starvation. Override is possible via `allow_low_baud_scope=True` or `ICOM_SERIAL_SCOPE_ALLOW_LOW_BAUD=1` (use with caution).

## Troubleshooting

### "No such file or directory: /dev/cu.usbserial-..."

**Cause**: USB cable not connected, or radio not powered on.

**Fix**:
1. Check USB cable connection (rear panel **USB (B)** port on IC-7610)
2. Power-cycle the radio
3. Wait 5-10 seconds after power-on
4. Run `ls -l /dev/cu.usbserial-*` again

### "Permission denied: /dev/cu.usbserial-..."

**Cause**: User lacks permissions to access serial device.

**Fix** (macOS typically doesn't need this, but if it happens):
```bash
# Add your user to the dialout group (Linux)
sudo usermod -a -G dialout $USER

# Logout and login again
```

On macOS, if you see permissions issues, try:
```bash
# Check ownership
ls -l /dev/cu.usbserial-*

# Typically owned by root:wheel with mode 0666 (world read/write)
# If not, contact system admin or check USB security settings
```

### "Audio device 'IC-7610 USB Audio' not found"

**Cause**: USB audio not exported by radio, or wrong device name.

**Fix**:
1. Verify USB audio is enabled in radio settings:
   - Menu → Set → Connectors → USB Audio → **Enabled**
2. List available devices:
   ```bash
   icom-lan --list-audio-devices
   ```
3. Use exact device name from the list (case-sensitive)
4. If still not visible, disconnect/reconnect USB cable

### "Scope over serial requires baudrate >= 115200"

**Symptom**: `CommandError` when calling `enable_scope()` or `capture_scope_frame()` with baud rate < 115200.

**Cause**: Scope/waterfall CI-V traffic is high-rate (~225 packets/sec on LAN). Lower serial baud rates cannot sustain this rate without starving command responses.

**Fix**:
1. **Recommended**: Set CI-V USB Baud Rate to **115200** in radio settings
2. **Override** (use with caution):
   ```python
   config = SerialBackendConfig(..., allow_low_baud_scope=True)
   ```
   or
   ```bash
   export ICOM_SERIAL_SCOPE_ALLOW_LOW_BAUD=1
   ```
   Library will log a warning about timeout risk.

### "CI-V response timed out" on serial

**Causes**:
1. **Wrong baud rate** — radio and library must match
2. **Wrong CI-V USB Port setting** — must be `Link to [CI-V]`, not `[REMOTE]`
3. **Serial port busy** — another app (wfview, hamlib, etc.) is using the serial device

**Fix**:
1. Check radio baud rate: Menu → Set → Connectors → CI-V → CI-V USB Baud Rate
2. Check CI-V USB Port setting (see "Critical Setup Step" above)
3. Close other apps using the serial port:
   ```bash
   # Check what's using the port (macOS)
   lsof | grep cu.usbserial
   ```

### Audio TX not working

**Cause**: Radio USB Audio TX not enabled.

**Fix**:
1. Menu → Set → Connectors → USB Audio → **USB Audio TX** → **Enabled**
2. Check PTT is active before transmitting audio
3. Verify `--tx-device` matches the USB audio device name

## Environment Variables

For convenience, set these in your shell profile:

```bash
# ~/.bashrc or ~/.zshrc
export ICOM_SERIAL_DEVICE=/dev/cu.usbserial-111120
export ICOM_SERIAL_BAUDRATE=115200
export ICOM_USB_RX_DEVICE="IC-7610 USB Audio"
export ICOM_USB_TX_DEVICE="IC-7610 USB Audio"

# Then simply:
icom-lan --backend serial status
```

## Migration from LAN to Serial

If you're currently using the LAN backend and want to switch to serial:

1. **No code changes needed** — use `create_radio(config)` factory with typed config:
   ```python
   # Before (LAN)
   from icom_lan.backends.config import LanBackendConfig
   config = LanBackendConfig(host="192.168.1.100", ...)
   
   # After (Serial)
   from icom_lan.backends.config import SerialBackendConfig
   config = SerialBackendConfig(device="/dev/cu.usbserial-111120", ...)
   
   # Same factory call
   radio = create_radio(config)
   ```

2. **CLI**: add `--backend serial` flag:
   ```bash
   # Before (LAN, default)
   icom-lan status
   
   # After (Serial)
   icom-lan --backend serial status
   ```

3. **Capability check**: scope/waterfall requires ≥115200 baud (see table above)

4. **Audio device selection**: LAN uses Opus/PCM over UDP, serial uses USB audio devices (explicit device names or auto-detect)

## Next Steps

- **Web UI + Serial**: See [Web UI Guide](web-ui.md)
- **rigctld + Serial**: See [CLI Reference](cli.md)
- **Python API**: See [API Reference](../api/radio.md)
- **Troubleshooting**: See [Troubleshooting Guide](troubleshooting.md)

---

**Hardware validated**: 2026-03-06, IC-7610 over USB on macOS (Darwin arm64), Python 3.11.14, pytest 9.0.2 (issue #146)
