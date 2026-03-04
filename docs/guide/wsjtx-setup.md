# WSJT-X / JTDX / JS8Call Setup Guide

This guide covers configuring WSJT-X (and compatible apps like JTDX, JS8Call)
to work with `icom-lan serve` as a Hamlib NET rigctld replacement.

## Quick Start

### 1. Start the server

**Recommended: all-in-one** (Web UI + audio bridge + rigctld):

```bash
# Install bridge dependencies
pip install icom-lan[bridge]

# Install BlackHole virtual audio device (macOS)
brew install blackhole-2ch

# Start all-in-one server
icom-lan --host <RADIO_IP> --user <USER> --pass <PASS> web --bridge "BlackHole 2ch"
```

This starts:
- **Web UI** on `:8080`
- **Audio bridge** routing radio RX/TX ↔ BlackHole virtual device
- **Rigctld** on `:4532` (enabled by default)

**Alternative: rigctld only** (no Web UI or audio bridge):

```bash
icom-lan --host <RADIO_IP> --user <USER> --pass <PASS> serve --wsjtx-compat
```

### 2. Configure WSJT-X

In **Settings → Radio**:

| Setting | Value |
|---------|-------|
| **Rig** | `Hamlib NET rigctl` |
| **Network Server** | `127.0.0.1:4532` |
| **PTT Method** | `CAT` |
| **Mode** | `Data/Pkt` |
| **Split Operation** | `Fake It` |

Press **Test CAT** — the button should turn green.
Press **Test PTT** — the radio should key up briefly.

### 3. Configure WSJT-X Audio (with BlackHole bridge)

If using `--bridge "BlackHole 2ch"`, configure WSJT-X audio:

In **Settings → Audio**:

| Setting | Value |
|---------|-------|
| **Input** | `BlackHole 2ch` |
| **Output** | `BlackHole 2ch` |

The audio bridge routes:
- **Radio RX → BlackHole → WSJT-X Input** (decode FT8/FT4)
- **WSJT-X Output → BlackHole → Radio TX** (transmit FT8/FT4)

## The `--wsjtx-compat` Flag

### What it does

When a CAT client connects for the first time:

- If the radio is in USB, LSB, or RTTY **with DATA mode OFF**,
  the server automatically enables DATA mode.
- This eliminates a known first-TX latency when WSJT-X switches
  from plain SSB to packet mode (PKTUSB).

### When to use it

- **Use** `--wsjtx-compat` if you run WSJT-X, JTDX, or JS8Call
  and want instant TX on the first transmission.
- **Don't use** if you need the radio to stay in the exact mode
  you set manually (e.g., SSB voice operation alongside CAT control).

### What it changes on the radio

Only the DATA mode flag (CI-V `0x1A 0x06`). It does **not** change
frequency, power, filter, or any other setting.

## Known Behavior

### USB → PKTUSB first-TX delay

When WSJT-X connects to a radio in plain USB (DATA off), it sends
`M PKTUSB -1` to switch to packet mode. This involves two radio changes:

1. Verify/set USB mode
2. Enable DATA mode

Some CAT client stacks (including WSJT-X and wfview's rigctld) introduce
a ~15–20 second delay before the first PTT after this transition.
**This is not an icom-lan bug** — the same behavior occurs with wfview's
built-in rigctld emulation.

**Workarounds:**

- Use `--wsjtx-compat` (recommended) — pre-warms DATA on connect.
- Manually set the radio to USB-D1 before starting WSJT-X.
- Once DATA mode is active, subsequent TX cycles work without delay.

### After closing WSJT-X

The server gracefully handles client disconnect:

- Abandoned commands are cancelled (no background CI-V spam).
- The poller stops when the last client disconnects.
- Reconnecting a new WSJT-X session works immediately.

## Troubleshooting

### Test CAT fails (button stays red)

1. Verify the server is running: `rigctl -m 2 -r localhost:4532 f`
2. Check the server log for connection/auth errors.
3. Ensure no other application is using port 4532.

### Test PTT fails or has long delay

1. Confirm PTT Method is set to **CAT** (not VOX or hardware).
2. If starting from plain USB, use `--wsjtx-compat` or pre-set DATA mode.
3. Check server logs for CI-V timeout patterns.

### Radio becomes unresponsive after disconnect

1. The circuit breaker may have tripped. Wait ~6 seconds for auto-recovery.
2. Restart the server if needed: Ctrl-C and re-launch.
3. Check if another application (wfview, flrig) is also controlling the radio.

### Mode shows USB instead of PKTUSB

- Ensure WSJT-X Mode is set to **Data/Pkt** (not None or USB).
- With `--wsjtx-compat`, DATA mode should already be active on connect.

## Compatible Applications

Tested with:

- **WSJT-X** 2.7+ (FT8, FT4, JT65, etc.)
- **JTDX** (FT8/FT4 variant)
- **JS8Call** (JS8 mode)
- **fldigi** (various digital modes)
- **Log4OM 2** (logging + CAT)
- **MacLoggerDX** (macOS logging)

Any application that supports `Hamlib NET rigctl` should work.
