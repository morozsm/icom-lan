# CLI Reference

The `icom-lan` CLI provides quick access to radio control from the terminal.

## Global Options

All commands accept these options:

| Option | Env Var | Default | Description |
|--------|---------|---------|-------------|
| `--host` | `ICOM_HOST` | `192.168.1.100` | Radio IP address |
| `--port` | `ICOM_PORT` | `50001` | Control port |
| `--user` | `ICOM_USER` | `""` | Username |
| `--pass` | `ICOM_PASS` | `""` | Password |
| `--timeout` | — | `5.0` | Timeout in seconds |

!!! tip "Use Environment Variables"
    Set `ICOM_HOST`, `ICOM_USER`, and `ICOM_PASS` in your shell profile to avoid typing them every time.

    ```bash
    # ~/.bashrc or ~/.zshrc
    export ICOM_HOST=192.168.1.100
    export ICOM_USER=myuser
    export ICOM_PASS=mypass
    ```

## Commands

### `status`

Show radio status (frequency, mode, S-meter, power).

```bash
icom-lan status
icom-lan status --json
```

```
Frequency:    14,074,000 Hz  (14.074000 MHz)
Mode:         USB
S-meter:      42
Power:        50
```

JSON output:

```json
{
  "frequency_hz": 14074000,
  "frequency_mhz": 14.074,
  "mode": "USB",
  "s_meter": 42,
  "power": 50
}
```

### `freq`

Get or set the operating frequency.

```bash
# Get current frequency
icom-lan freq

# Set frequency (multiple formats)
icom-lan freq 14074000      # Hz
icom-lan freq 14074k        # kHz
icom-lan freq 14.074m       # MHz
```

### `mode`

Get or set the operating mode.

```bash
# Get current mode
icom-lan mode

# Set mode
icom-lan mode USB
icom-lan mode CW
icom-lan mode LSB
```

Available modes: `LSB`, `USB`, `AM`, `CW`, `RTTY`, `FM`, `WFM`, `CW_R`, `RTTY_R`, `DV`

### `power`

Get or set the RF power level (0–255).

```bash
# Get current power
icom-lan power

# Set power level
icom-lan power 128
```

!!! note "Power Scale"
    The 0–255 value is the radio's internal representation. The mapping to actual watts depends on your radio model and mode.

### `meter`

Read all available meters.

```bash
icom-lan meter
icom-lan meter --json
```

```
S-METER  42
POWER    50
SWR      n/a
ALC      n/a
```

!!! info
    SWR and ALC are only available during TX. They show `n/a` when receiving.

### `audio caps`

Show icom-lan audio capability metadata and deterministic defaults.

```bash
icom-lan audio caps
icom-lan audio caps --json
icom-lan audio caps --stats
icom-lan audio caps --json --stats
```

Text output includes:

- supported codecs
- supported sample rates
- supported channels
- default codec/rate/channels
- deterministic selection rules used for defaults
- with `--stats`: a 1-second RX probe and runtime audio quality stats snapshot

JSON output example:

```json
{
  "supported_codecs": [
    {"name": "ULAW_1CH", "value": 1},
    {"name": "PCM_1CH_8BIT", "value": 2}
  ],
  "supported_sample_rates_hz": [8000, 16000, 24000, 48000],
  "supported_channels": [1, 2],
  "default_codec": {"name": "PCM_1CH_16BIT", "value": 4},
  "default_sample_rate_hz": 48000,
  "default_channels": 1,
  "runtime_stats": {
    "active": false,
    "state": "idle",
    "packet_loss_percent": 0.0,
    "jitter_ms": 0.0
  }
}
```

### `audio rx`

Capture RX audio to a 16-bit PCM WAV file.

```bash
icom-lan audio rx --out rx.wav --seconds 10
icom-lan audio rx --out rx.wav --seconds 10 --sample-rate 48000 --channels 1
icom-lan audio rx --out rx.wav --json
```

### `audio tx`

Transmit a WAV file (`16-bit PCM`, matching sample rate/channels).

```bash
icom-lan audio tx --in tx.wav
icom-lan audio tx --in tx.wav --sample-rate 48000 --channels 1
icom-lan audio tx --in tx.wav --json
```

### `audio loopback`

Run a quick RX-to-TX PCM loopback window.

```bash
icom-lan audio loopback --seconds 10
icom-lan audio loopback --seconds 10 --sample-rate 48000 --channels 1
icom-lan audio loopback --json
```

### Shared audio flags (`rx`/`tx`/`loopback`)

- `--sample-rate` — PCM sample rate in Hz (must be supported by `icom-lan`)
- `--channels` — PCM channel count (must be supported by `icom-lan`)
- `--json` — machine-readable JSON output
- `--stats` — print transfer counters/metrics (human-readable mode)

### `att`

Get or set the attenuator level.

```bash
# Get current attenuation
icom-lan att
icom-lan att --json

# Set level in dB (0–45, 3 dB steps)
icom-lan att 18
icom-lan att 0

# Toggle shortcuts
icom-lan att on     # Sets 18 dB
icom-lan att off    # Sets 0 dB
```

```
Attenuator: 18 dB
```

JSON output:

```json
{
  "attenuator_db": 18,
  "attenuator_on": true
}
```

!!! note "IC-7610 Levels"
    The IC-7610 supports 0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45 dB.
    Values not on 3 dB boundaries will be rejected.

### `preamp`

Get or set the preamplifier level.

```bash
# Get current preamp level
icom-lan preamp
icom-lan preamp --json

# Set level
icom-lan preamp 0     # Off
icom-lan preamp 1     # PREAMP 1
icom-lan preamp 2     # PREAMP 2
icom-lan preamp off   # Same as 0
```

```
Preamp: PRE1
```

JSON output:

```json
{
  "preamp_level": 1,
  "preamp_name": "PRE1"
}
```

### `ptt`

Toggle Push-To-Talk.

```bash
icom-lan ptt on
icom-lan ptt off
```

!!! danger "Caution"
    Activating PTT will key your transmitter. Ensure your antenna is connected and you are authorized to transmit on the current frequency.

### `cw`

Send CW text via the radio's built-in keyer.

```bash
icom-lan cw "CQ CQ DE KN4KYD K"
```

The text is sent in chunks of up to 30 characters. Supports A–Z, 0–9, and standard prosigns.

### `power-on` / `power-off`

Remote power control.

```bash
icom-lan power-on
icom-lan power-off
```

!!! warning
    `power-on` only works if the radio supports wake-on-LAN and the network connection is maintained in standby mode.

### `discover`

Discover Icom radios on the local network via UDP broadcast.

```bash
icom-lan discover
```

```
Scanning for Icom radios (3 seconds)...
  Found: 192.168.1.100:50001  id=0xDEADBEEF

1 radio(s) found.
```

### `web`

Start the all-in-one server: Web UI + optional audio bridge + rigctld.

```bash
# Web UI only
icom-lan web

# Web UI + audio bridge + rigctld (recommended for WSJT-X)
icom-lan web --bridge "BlackHole 2ch"

# Web UI + bridge (RX only, no TX from virtual device)
icom-lan web --bridge "BlackHole 2ch" --bridge-rx-only

# Disable rigctld (enabled by default on :4532)
icom-lan web --no-rigctld

# Custom ports
icom-lan web --port 9090 --rigctld-port 4533
```

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | `8080` | Web server port |
| `--bridge DEVICE` | — | Start audio bridge with named virtual device |
| `--bridge-rx-only` | — | Bridge receives only (no TX from virtual device) |
| `--no-rigctld` | — | Disable built-in rigctld server |
| `--rigctld-port` | `4532` | Rigctld listen port |

### `audio bridge`

Route radio audio to/from a virtual audio device (BlackHole, Loopback, VB-Audio).

```bash
# List available audio devices
icom-lan audio bridge --list-devices

# Start bridge
icom-lan audio bridge --device "BlackHole 2ch"

# RX only (no TX from virtual device)
icom-lan audio bridge --device "BlackHole 2ch" --rx-only
```

!!! tip "macOS Setup"
    Install BlackHole for virtual audio routing:
    ```bash
    brew install blackhole-2ch
    ```
    After install, reboot to load the audio driver. Then `BlackHole 2ch` appears as an audio device.

!!! note "Dependencies"
    Audio bridge requires optional dependencies:
    ```bash
    pip install icom-lan[bridge]
    ```
    On macOS with Homebrew, you may also need:
    ```bash
    export DYLD_LIBRARY_PATH=/opt/homebrew/lib
    ```

## Scope / Waterfall

Capture spectrum and waterfall data from the radio's scope display and render as PNG.

Requires optional dependency: `pip install icom-lan[scope]`

```bash
# Combined spectrum + waterfall (50 frames, ~3 seconds)
icom-lan scope

# Spectrum only (1 frame, fast)
icom-lan scope --spectrum-only

# Custom output and frame count
icom-lan scope --output waterfall.png --frames 100

# Grayscale theme
icom-lan scope --theme grayscale

# Wider image
icom-lan scope --width 1200

# Raw JSON data (no Pillow needed)
icom-lan scope --json
icom-lan scope --spectrum-only --json

# Custom capture timeout
icom-lan scope --capture-timeout 20
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output`, `-o` | `scope.png` | Output file path |
| `--frames`, `-n` | `50` | Number of frames for waterfall |
| `--theme` | `classic` | Color theme (`classic` or `grayscale`) |
| `--spectrum-only` | — | Capture 1 frame, render spectrum only |
| `--width` | `800` | Image width in pixels |
| `--json` | — | Output raw frame data as JSON |
| `--capture-timeout` | `10`/`15` | Capture timeout in seconds |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (connection, auth, command failure) |

## Examples

```bash
# Monitor frequency in a loop
watch -n 1 icom-lan freq --json

# Quick band change
icom-lan freq 7.074m && icom-lan mode USB

# Check RF chain setup
icom-lan att && icom-lan preamp

# Script-friendly JSON output
FREQ=$(icom-lan freq --json | jq -r '.frequency_hz')
echo "Currently on $FREQ Hz"
```
