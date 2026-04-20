# CLI Reference

The `icom-lan` CLI provides quick access to radio control from the terminal.

## Global Options

All commands accept these options:

| Option | Env Var | Default | Description |
|--------|---------|---------|-------------|
| `--host` | `ICOM_HOST` | auto-discover | Radio IP address (LAN backend). If omitted, discovers radio via UDP broadcast. |
| `--control-port` | `ICOM_PORT` | `50001` | Radio UDP control port (`--port` is a deprecated alias) |
| `--user` | `ICOM_USER` | `""` | Username (LAN backend) |
| `--pass` | `ICOM_PASS` | `""` | Password (LAN backend) |
| `--timeout` | — | `5.0` | Timeout in seconds |
| `--json` | — | `false` | Emit JSON when supported by the selected command |
| `--backend` | — | auto | Backend type: `lan`, `serial`, or `yaesu-cat`. Auto-inferred from `--serial-port` if set. |
| `--serial-port` | `ICOM_SERIAL_DEVICE` | auto-discover | Serial device path. If omitted with `--backend serial`, discovers via USB scan. |
| `--serial-baud` | `ICOM_SERIAL_BAUDRATE` | env or backend default | Serial baud (`115200` for `serial`, `38400` for `yaesu-cat` when env is unset) |
| `--serial-ptt-mode` | `ICOM_SERIAL_PTT_MODE` | `civ` | Serial PTT mode (`civ` currently supported) |
| `--rx-device` | `ICOM_USB_RX_DEVICE` | auto | USB audio RX device name (serial/CAT profiles with audio support) |
| `--tx-device` | `ICOM_USB_TX_DEVICE` | auto | USB audio TX device name (serial/CAT profiles with audio support) |
| `--list-audio-devices` | — | — | List USB audio devices and exit |
| `--version` | — | — | Print version and exit |

!!! tip "Zero-config startup"
    If you have a single radio on the network, just run `icom-lan web` — it auto-discovers the radio via LAN broadcast. No `--host` needed.

    For permanent setups, set environment variables in your shell profile:

    ```bash
    # ~/.bashrc or ~/.zshrc
    export ICOM_HOST=192.168.55.40
    export ICOM_USER=myuser
    export ICOM_PASS=mypass
    ```

## Auto-discovery

When `--host` is omitted (LAN backend), icom-lan sends a UDP broadcast to find radios:

- **1 radio found** → uses it automatically, prints the IP
- **Multiple radios** → lists them, asks you to specify `--host`
- **No radios** → error with troubleshooting hints

Similarly, when `--backend serial` is set without `--serial-port`, serial ports are scanned automatically.

The `--backend` flag is auto-inferred:

- `--serial-port` provided → infers `--backend serial`
- `ICOM_SERIAL_DEVICE` set → infers `--backend serial`
- Otherwise → `lan` (default)

## Presets

Use `--preset` with `web` or `serve` commands for common scenarios:

| Preset | What it enables |
|--------|----------------|
| `hamradio` | Audio bridge + rigctld |
| `digimode` | Audio bridge + rigctld + WSJT-X compatibility |
| `serial` | Serial backend (auto-detect port) |
| `headless` | rigctld only (no web UI) |

```bash
icom-lan web --preset digimode          # Full digital mode setup
icom-lan web --preset hamradio          # General ham radio setup
```

User-provided flags override preset values: `--preset digimode --bridge "MyDevice"` uses your device name.

## Backend Selection

icom-lan supports three backends: **LAN** (default), **serial** (USB CI-V), and
**yaesu-cat** (text CAT over serial).

### LAN backend (default)

```bash
# Auto-discover radio on LAN
icom-lan status

# Explicit IP
icom-lan --host 192.168.55.40 status
icom-lan --backend lan status
```

### Serial backend

```bash
# Auto-discover serial port
icom-lan --backend serial status

# Explicit port (--backend serial is inferred)
icom-lan --serial-port /dev/tty.usbmodem-IC7610 status
```

Set via environment variable to avoid repeating:

```bash
export ICOM_SERIAL_DEVICE=/dev/tty.usbmodem-IC7610
icom-lan status    # auto-infers --backend serial
```

### Yaesu CAT backend

```bash
# Connects via Yaesu CAT serial protocol (for example FTX-1 / FT-710 profiles)
icom-lan --backend yaesu-cat --serial-port /dev/tty.usbserial-FTX1 status
icom-lan --backend yaesu-cat --serial-port /dev/tty.usbserial-FTX1 freq
```

### Serial baud defaults by backend

If `--serial-baud` and `ICOM_SERIAL_BAUDRATE` are both unset:

- `--backend serial` defaults to `115200`
- `--backend yaesu-cat` defaults to `38400`

### Audio device selection (serial backend)

The serial backend uses USB audio devices exported by the radio. By default, devices are auto-detected.

```bash
# List all available audio devices
icom-lan --list-audio-devices
icom-lan --list-audio-devices --json

# Specify explicit devices
icom-lan --backend serial --serial-port /dev/tty.usbmodem-IC7610 \
    --rx-device "IC-7610 USB Audio" \
    --tx-device "IC-7610 USB Audio" \
    audio rx --out rx.wav --seconds 10
```

### `discover` command — LAN + serial

The `discover` command scans both LAN (UDP broadcast) and USB serial ports concurrently:

```bash
icom-lan discover                      # LAN + serial (default)
icom-lan discover --lan-only           # UDP broadcast only
icom-lan discover --serial-only        # USB serial ports only
icom-lan discover --timeout 5          # Longer LAN listen window
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

### `antenna`

Get or set antenna selection.

```bash
# Get current antenna state
icom-lan antenna

# Set antenna
icom-lan antenna --ant1 on
icom-lan antenna --ant2 on
icom-lan antenna --rx-ant1 on
icom-lan antenna --rx-ant2 off
```

| Flag | Default | Description |
|------|---------|-------------|
| `--ant1` | — | Set ANT1 (`on`/`off`) |
| `--ant2` | — | Set ANT2 (`on`/`off`) |
| `--rx-ant1` | — | Set RX antenna on ANT1 (`on`/`off`) |
| `--rx-ant2` | — | Set RX antenna on ANT2 (`on`/`off`) |

### `date`

Get or set the radio's internal date.

```bash
icom-lan date
```

### `time`

Get or set the radio's internal time.

```bash
icom-lan time
```

### `dualwatch`

Get or set dual watch mode.

```bash
icom-lan dualwatch
```

### `tuner`

Control the antenna tuner.

```bash
icom-lan tuner
```

### `levels`

Get or set radio levels (AF, RF, squelch, etc.).

```bash
icom-lan levels
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

Discover Icom radios on LAN and USB serial ports. Results are grouped by radio identity — the same physical radio connected via both LAN and USB appears as one entry with two connection methods.

```bash
icom-lan discover                   # LAN + serial
icom-lan discover --lan-only        # UDP broadcast only
icom-lan discover --serial-only     # USB serial ports only
icom-lan discover --timeout 5       # Longer LAN listen window (default: 3s)
```

```
Scanning for Icom radios (3s LAN + serial)...

Found 1 radio with 2 connection methods:

IC-7610:
  • LAN: 192.168.55.40
  • Serial: /dev/cu.usbserial-11320 (19200 baud)
```

Multiple radios:

```
Found 2 radios with 3 connection methods:

IC-7610:
  • LAN: 192.168.55.40
  • Serial: /dev/cu.usbserial-11320 (19200 baud)

IC-705:
  • Serial: /dev/cu.usbserial-54321 (115200 baud)
```

| Flag | Default | Description |
|------|---------|-------------|
| `--lan-only` | off | Only scan via UDP broadcast |
| `--serial-only` | off | Only scan USB serial ports |
| `--timeout SECONDS` | `3.0` | LAN broadcast listen timeout |

### `serve`

Start a rigctld-compatible TCP server so that logging and contesting software (WSJT-X, JS8Call, Ham Radio Deluxe, etc.) can control the radio without a full Hamlib installation.

```bash
# Basic rigctld server on default port 4532
icom-lan serve

# Custom port, read-only, max 5 clients
icom-lan serve --port 4533 --read-only --max-clients 5

# Write every command to an audit log
icom-lan serve --audit-log /var/log/icom-audit.jsonl

# Rate-limit to 10 commands/sec per client, verbose debug logs
icom-lan serve --rate-limit 10 --log-level DEBUG

# WSJT-X preset (enables DATA mode automatically on first connect)
icom-lan serve --wsjtx-compat
```

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Server listen address |
| `--port` | `4532` | Server TCP port |
| `--read-only` | off | Reject all set commands; allow only reads |
| `--max-clients` | `10` | Maximum concurrent TCP clients |
| `--cache-ttl` | `0.2` | How long (seconds) to cache radio state before re-querying |
| `--wsjtx-compat` | off | Pre-warm for WSJT-X: auto-enable DATA mode on first client connect |
| `--log-level` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `--audit-log PATH` | — | Append one JSON line per command to `PATH` (disabled by default) |
| `--rate-limit N` | — | Max commands per second per client; excess commands are dropped (unlimited by default) |

!!! note "rigctld compatibility"
    The server speaks a subset of the Hamlib rigctld protocol over plain TCP. Tested with WSJT-X, JS8Call, and `rigctl` CLI.

### `proxy`

Transparent UDP relay that forwards all radio traffic between a remote client and the physical radio. Useful for accessing a shack radio over a VPN without exposing the radio's IP directly.

```bash
# Forward radio at 192.168.55.40 to all VPN clients
icom-lan proxy --radio 192.168.55.40

# Listen only on VPN interface, custom base port
icom-lan proxy --radio 192.168.55.40 --listen 10.8.0.1 --port 50010
```

| Option | Default | Description |
|--------|---------|-------------|
| `--radio` | *(required)* | Radio IP address to forward to |
| `--listen` | `0.0.0.0` | Local address to listen on |
| `--port` | `50001` | Base UDP port (proxy binds `port`, `port+1`, `port+2` for control/audio/data) |

### `web`

Start the all-in-one server: Web UI + optional audio bridge + rigctld.

```bash
# Web UI only (auto-discovers radio)
icom-lan web

# Use a preset for common scenarios
icom-lan web --preset digimode          # Bridge + rigctld + WSJT-X compat
icom-lan web --preset hamradio          # Bridge + rigctld

# Web UI + audio bridge + rigctld (recommended for WSJT-X)
icom-lan web --bridge "BlackHole 2ch"

# Web UI + WSJT-X compatibility on embedded rigctld
icom-lan web --bridge --wsjtx-compat

# Web UI + bridge (RX only, no TX from virtual device)
icom-lan web --bridge "BlackHole 2ch" --bridge-rx-only

# Disable rigctld (enabled by default on :4532)
icom-lan web --no-rigctld

# Custom ports
icom-lan web --port 9090 --rigctld-port 4533

# Require token for /api and WebSocket channels
icom-lan web --auth-token "change-me"
```

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Web server bind address |
| `--port` | `8080` | Web server port |
| `--static-dir PATH` | — | Serve static files from a custom directory (default: built-in assets) |
| `--bridge DEVICE` | — | Start audio bridge with named virtual device |
| `--bridge-tx-device DEVICE` | — | Separate TX-only device for bidirectional bridge (e.g. `BlackHole 16ch`) |
| `--bridge-rx-only` | — | Bridge receives only (no TX from virtual device) |
| `--no-rigctld` | — | Disable built-in rigctld server |
| `--rigctld-port` | `4532` | Rigctld listen port |
| `--dx-cluster HOST:PORT` | — | Connect to DX cluster server for real-time spot overlays (opt-in) |
| `--callsign CALL` | — | Your callsign for DX cluster login (required with `--dx-cluster`) |
| `--auth-token TOKEN` | — | Require `Authorization: Bearer <TOKEN>` for `/api/*` and WS channels |

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

## PID File (optional)

For daemon-like commands (`web`, `serve`), you can opt in to writing a PID file by setting the **`ICOM_PID_FILE`** environment variable to the desired path. The file is created only when starting `web` or `serve` and is removed automatically on clean exit or SIGTERM.

```bash
# Enable PID file for web/serve (e.g. in systemd or a wrapper script)
export ICOM_PID_FILE=/var/run/icom-lan.pid
icom-lan web

# Graceful shutdown
kill $(cat /var/run/icom-lan.pid)

# Check if icom-lan is running
test -f /var/run/icom-lan.pid && ps -p $(cat /var/run/icom-lan.pid)
```

If `ICOM_PID_FILE` is unset or empty, no PID file is written. This avoids conflicts when running multiple instances or in tests.

## Daemon Logging and Rotation (`web` / `serve`)

`web` and `serve` are long-running commands, so the CLI enables file logging by default
to preserve diagnostics across reconnects/restarts.

- Default file path: `logs/icom-lan.log`
- Handler type: Python `RotatingFileHandler`
- Rotation defaults: `50_000_000` bytes per file, `5` backups

You can tune this behavior with environment variables:

| Variable | Default | Meaning |
|---|---:|---|
| `ICOM_LOG_FILE` | `logs/icom-lan.log` (for `web`/`serve`) | Log file path. Set to `off`, `none`, or `-` to disable file logging entirely. |
| `ICOM_LOG_MAX_BYTES` | `50000000` | Rotate when file reaches this size (bytes). |
| `ICOM_LOG_BACKUP_COUNT` | `5` | Number of rotated files to keep. Set `0` to disable rotation. |
| `ICOM_DEBUG` | unset | Enables debug-level logging and also enables file logging if `ICOM_LOG_FILE` is not disabled. |

```bash
# Custom log location (systemd/container-friendly)
export ICOM_LOG_FILE=/var/log/icom-lan/daemon.log
icom-lan web

# Smaller files with more backups
export ICOM_LOG_MAX_BYTES=10000000
export ICOM_LOG_BACKUP_COUNT=10
icom-lan serve

# Explicitly disable file logs (stdout/stderr only)
export ICOM_LOG_FILE=off
icom-lan web
```

## Flag Reference

Compact per-flag reference for all notable options, including which subcommand accepts them, the default value, and a minimal working example.

### Global flags

These flags apply to **every** command and must come before the subcommand name.

| Flag | Command | Default | Description |
|------|---------|---------|-------------|
| `--version` | *(global)* | — | Print version and exit |
| `--control-port PORT` | *(global)* | `50001` (`$ICOM_PORT`) | Radio UDP control port; `--port` is a deprecated alias |
| `--model MODEL` | *(global)* | — | Radio model (e.g. `IC-7300`); resolves from `rigs/*.toml` |
| `--radio-addr ADDR` | *(global)* | — | CI-V address override (hex or decimal) |

```bash
# Print installed version
icom-lan --version

# Connect to a radio on a non-default port
icom-lan --control-port 50002 status

# Specify radio model explicitly
icom-lan --model IC-7300 --backend serial --serial-port /dev/cu.usbserial-XXX status
```

### `serve` flags

| Flag | Command | Default | Description |
|------|---------|---------|-------------|
| `--audit-log PATH` | `serve` | *(disabled)* | Append one JSON line per command to `PATH` |
| `--cache-ttl N` | `serve` | `0.2` | Seconds to cache radio state before re-querying |
| `--log-level LEVEL` | `serve` | `INFO` | Log verbosity: `DEBUG` `INFO` `WARNING` `ERROR` `CRITICAL` |
| `--max-clients N` | `serve` | `10` | Maximum concurrent TCP clients |
| `--rate-limit N` | `serve` | *(unlimited)* | Max commands per second per client; excess are dropped |
| `--read-only` | `serve` | off | Reject all set (write) commands; allow reads only |
| `--wsjtx-compat` | `serve` | off | Auto-enable DATA mode on first client connect (WSJT-X pre-warm) |
| `--preset NAME` | `serve` | *(none)* | Apply a named preset: `hamradio`, `digimode`, `serial`, `headless` |

```bash
# Log every command to a JSONL audit trail
icom-lan serve --audit-log /var/log/icom-audit.jsonl

# Tighten cache for faster state sync
icom-lan serve --cache-ttl 0.05

# Verbose debug logging
icom-lan serve --log-level DEBUG

# Limit to 3 simultaneous clients
icom-lan serve --max-clients 3

# Drop commands faster than 10/sec per client
icom-lan serve --rate-limit 10

# Prevent accidental frequency/mode changes
icom-lan serve --read-only

# Enable WSJT-X compatibility preset
icom-lan serve --wsjtx-compat
```

### `proxy` flags

| Flag | Command | Default | Description |
|------|---------|---------|-------------|
| `--radio IP` | `proxy` | *(required)* | Radio IP address to forward all UDP traffic to |
| `--listen ADDR` | `proxy` | `0.0.0.0` | Local interface address to bind on |

```bash
# Forward traffic to radio at 192.168.1.100 (listen on all interfaces)
icom-lan proxy --radio 192.168.1.100

# Bind only on the VPN interface
icom-lan proxy --radio 192.168.1.100 --listen 10.8.0.1
```

### `web` flags

| Flag | Command | Default | Description |
|------|---------|---------|-------------|
| `--host ADDR` | `web` | `0.0.0.0` | Bind Web UI server to a specific interface |
| `--bridge-tx-device DEVICE` | `web` | *(none)* | Separate TX-only audio device for bidirectional bridge |
| `--static-dir PATH` | `web` | *(built-in)* | Serve static web assets from a custom directory instead of the built-in UI |
| `--dx-cluster HOST:PORT` | `web` | *(none)* | Connect to a DX cluster server for real-time spot overlays |
| `--callsign CALL` | `web` | *(none)* | Your callsign for DX cluster login (required with `--dx-cluster`) |
| `--auth-token TOKEN` | `web` | *(none)* | Require Bearer auth for API/WS endpoints |
| `--tls` | `web` | off | Enable HTTPS with auto-generated self-signed certificate |
| `--tls-cert PATH` | `web` | *(none)* | Path to TLS certificate PEM file |
| `--tls-key PATH` | `web` | *(none)* | Path to TLS private key PEM file |
| `--bridge-label LABEL` | `web` | *(none)* | Descriptive label for audio bridge log messages |
| `--no-rigctld` | `web` | off | Disable built-in rigctld server |
| `--rigctld-port PORT` | `web` | `4532` | Rigctld listen port |
| `--wsjtx-compat` | `web` | off | Enable WSJT-X compatibility pre-warm on embedded rigctld |
| `--preset NAME` | `web` | *(none)* | Apply a named preset: `hamradio`, `digimode`, `serial`, `headless` |

```bash
# Bidirectional bridge: RX from BlackHole 2ch, TX through BlackHole 16ch
icom-lan web --bridge "BlackHole 2ch" --bridge-tx-device "BlackHole 16ch"

# Serve a custom-built web UI from a local directory
icom-lan web --static-dir /opt/icom-ui/dist

# Connect to a DX cluster and show spot overlays on the waterfall
icom-lan web --dx-cluster dxc.nc7j.com:7373 --callsign KN4KYD

# Protect API + WS endpoints with a bearer token
icom-lan web --auth-token "change-me"
```

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
