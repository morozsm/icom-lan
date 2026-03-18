# Adding a New Radio (Rig Profiles)

## Overview

icom-lan uses **TOML rig files** to define radio capabilities, CI-V commands, and hardware
parameters. Adding a new radio means adding a new `.toml` file — no Python changes required
for most radios.

Rig files live in `rigs/`. The two reference files are:

- `rigs/ic7610.toml` — IC-7610 (dual receiver, LAN, full feature set)
- `rigs/ic7300.toml` — IC-7300 (single receiver, USB serial, no DIGI-SEL/IP+)

## Quick Start

```bash
# 1. Copy the reference rig file
cp rigs/ic7610.toml rigs/ic9700.toml

# 2. Edit the [radio] section with correct values
# 3. Update [capabilities] to match what your radio actually supports
# 4. Update [commands] — most Icom HF radios share the same wire bytes
# 5. Add [commands.overrides] for model-specific differences
# 6. Run the loader tests
uv run pytest tests/test_rig_loader.py -v
```

## TOML Schema Reference

See [`rigs/_schema.md`](../../rigs/_schema.md) for complete field documentation.
Below is a practical walkthrough.

## Section-by-Section Walkthrough

### `[radio]` — Model Identity

```toml
[radio]
id = "icom_ic9700"        # unique snake_case ID
model = "IC-9700"         # human-readable, used in UI and logs
civ_addr = 0xA2           # default CI-V address
receiver_count = 2        # 1 or 2 independent receivers
has_lan = true            # Ethernet port built-in?
has_wifi = false          # WiFi built-in?
default_baud = 115200     # optional: default serial baud rate
```

`id` must be globally unique. Convention: `icom_<model_lower>` (e.g. `icom_ic7300`).
`default_baud` is used by `--model` CLI auto-config for serial connections.

### `[spectrum]` — Scope Parameters

Include only if the radio has a built-in spectrum scope:

```toml
[spectrum]
seq_max = 11
amp_max = 160
data_len_max = 475
```

These values are the same for IC-7610 and IC-7300 — copy them verbatim unless your
radio's scope frame format differs (check the CI-V reference manual).

### `[capabilities]` — Feature Flags

```toml
[capabilities]
features = [
    "audio",      # RX/TX audio streaming
    "scope",      # spectrum scope
    "dual_rx",    # dual independent receivers (omit for single-receiver radios)
    "meters",     # S-meter, SWR, ALC, etc.
    "tx",         # transmit capability
    "cw",         # CW keying via CI-V
    "attenuator", # ATT control
    "preamp",     # preamplifier
    "rf_gain",    # RF gain
    "af_level",   # AF output level
    "squelch",    # squelch
    "nb",         # noise blanker
    "nr",         # noise reduction
    "digisel",    # DIGI-SEL (IC-7610 only, omit for IC-7300)
    "ip_plus",    # IP+ (IC-7610 only, omit for IC-7300)
]
```

The capability list controls Web UI guards — features not listed will be hidden or
disabled in the UI automatically.

### `[attenuator]`, `[preamp]`, `[agc]` — RX Control Steps

These optional sections define the available values for front-panel RX controls.
The Web UI reads these to render cycle buttons with correct labels and step sizes.

```toml
[attenuator]
values = [0, 20]  # IC-7300: OFF or 20 dB
# values = [0, 6, 12, 18]  # IC-7610: 6 dB steps

[preamp]
values = [0, 1, 2]  # 0=OFF, 1=PRE1, 2=PRE2

[agc]
modes = [1, 2, 3]  # 1=FAST, 2=MID, 3=SLOW
labels = { "1" = "FAST", "2" = "MID", "3" = "SLOW" }
```

**ATT and PRE are mutually exclusive** — the radio hardware enforces this, and the
UI applies optimistic updates (enabling ATT clears PRE, and vice versa).

If these sections are omitted, the Web UI hides the corresponding buttons.

### `[modes]` and `[filters]`

```toml
[modes]
list = ["USB", "LSB", "CW", "CW-R", "AM", "FM", "RTTY", "RTTY-R"]

[filters]
list = ["FIL1", "FIL2", "FIL3"]
```

These populate the mode/filter selectors in the Web UI.

### `[vfo]` — VFO Scheme

Two schemes are supported:

**`main_sub`** — for dual-receiver radios (IC-7610, IC-9700):

```toml
[vfo]
scheme = "main_sub"
main_select = [0xD0]
sub_select = [0xD1]
swap = [0xB0]
```

**`ab`** — for single-receiver radios (IC-7300, IC-705):

```toml
[vfo]
scheme = "ab"
main_select = [0x00]   # VFO A
sub_select = [0x01]    # VFO B
swap = [0xB0]
```

The `scheme` value drives VFO label rendering in the Web UI: `main_sub` → "MAIN"/"SUB",
`ab` → "VFO A"/"VFO B".

### `[[freq_ranges.ranges]]` — Frequency Coverage

Each range entry defines a contiguous frequency span with optional amateur band definitions:

```toml
[[freq_ranges.ranges]]
label = "HF"
start_hz = 30_000
end_hz = 60_000_000

[[freq_ranges.ranges.bands]]
name = "20m"
start_hz = 14_000_000
end_hz = 14_350_000
default_hz = 14_200_000
bsr_code = 0x05
```

For VHF/UHF radios, add additional ranges:

```toml
[[freq_ranges.ranges]]
label = "2m"
start_hz = 144_000_000
end_hz = 148_000_000

[[freq_ranges.ranges.bands]]
name = "2m"
start_hz = 144_000_000
end_hz = 148_000_000
default_hz = 146_520_000
```

`bsr_code` is optional but strongly recommended for bands that support Icom
Band Stack Register recall (`CI-V 0x1A 0x01`):

- **Present** `bsr_code`: Web UI can use `set_band` and restore last freq/mode
  stored in radio memory for that band.
- **Missing** `bsr_code`: UI should use `default_hz` fallback (`set_freq`).

Notes:

- Keep `bsr_code` values unique within one rig profile to avoid ambiguous mapping.
- In built-in IC-7300/IC-7610 profiles, 60m intentionally has no `bsr_code`, so
  it uses default-frequency fallback.

### `[commands]` — CI-V Wire Bytes

Each key maps a command name to its CI-V wire bytes as an integer array:

```toml
[commands]
get_freq = [0x03]           # single command byte
get_af_level = [0x14, 0x01] # command + sub-command
set_af_level = [0x14, 0x01]
```

Most Icom HF radios share the same command bytes as the IC-7610 — copy the IC-7610
`[commands]` section and remove any commands your radio doesn't support.

### `[commands.overrides]` — Model-Specific Wire Bytes

Commands that differ from the IC-7610 defaults go here:

```toml
[commands.overrides]
# IC-7300 uses a different register for S-meter squelch status
get_s_meter_sql_status = [0x16, 0x43]

# IC-7300-specific menu items
acc1_mod_level = [0x1A, 0x05, 0x00, 0x64]
usb_mod_level  = [0x1A, 0x05, 0x00, 0x65]
```

Overrides are merged on top of `[commands]` at load time.

### `[cmd29]` — Command 29 Routes (Dual-Receiver Only)

Command 29 is a prefix used to route commands to a specific receiver on dual-receiver
radios. **Omit this section entirely for single-receiver radios.**

```toml
[cmd29]
routes = [
    [0x11],           # ATT (sub=None)
    [0x14, 0x01],     # AF Gain
    [0x16, 0x02],     # PREAMP
    [0x16, 0x40],     # NR
    [0x16, 0x4E],     # DIGI-SEL
    [0x16, 0x65],     # IP+
]
```

Check the IC-7610 rig file for the full list. For other dual-receiver radios, consult
your radio's CI-V reference manual for which commands support receiver targeting.

## Finding Wire Bytes

1. **Icom CI-V reference manual** — the authoritative source for your model
2. **`docs/parity/ic7610_command_matrix.json`** — IC-7610 command matrix with verified wire bytes
3. **`rigs/ic7610.toml`** — annotated reference (IC-7610 = the baseline)
4. **wfview `.rig` files** — different format but same underlying CI-V addresses

## Testing Your Rig File

```bash
# Basic load + validation
uv run python -c "
from pathlib import Path
from icom_lan.rig_loader import load_rig
cfg = load_rig(Path('rigs/ic9700.toml'))
print(cfg.model, cfg.civ_addr, cfg.receiver_count)
print('capabilities:', cfg.capabilities)
"

# Full test suite (must pass before opening a PR)
uv run pytest tests/ -x -q

# Loader-specific tests
uv run pytest tests/test_rig_loader.py -v
```

`load_rig()` validates all required sections and field types — errors include the
filename and field path to make diagnosis easy.

## Common Mistakes

| Mistake | Error message |
|---------|--------------|
| Missing `[capabilities].features` | `[capabilities].features must not be empty` |
| Unknown capability string | `unknown capability 'xyz'. Known: [...]` |
| `[vfo].scheme` not in `{"ab", "main_sub"}` | `[vfo].scheme must be one of ...` |
| `[cmd29]` in a single-receiver rig | Works but wastes cycles — omit it |
| Duplicate command keys | TOML parser error (last value wins in some parsers) |
| CI-V address out of range | `[radio].civ_addr = X out of range 0x00–0xFF` |

## Using a Rig File at Runtime

```python
from pathlib import Path
from icom_lan.rig_loader import load_rig

cfg = load_rig(Path("rigs/ic9700.toml"))
profile = cfg.to_profile()          # RadioProfile for command routing
cmd_map = cfg.to_command_map()      # CommandMap for CI-V wire bytes

print(profile.receiver_count)       # 2
print(profile.vfo_scheme)           # "main_sub"
print(cmd_map.get("get_af_level"))  # (0x14, 0x01)
```

Or load all rigs at once:

```python
from pathlib import Path
from icom_lan.rig_loader import discover_rigs

rigs = discover_rigs(Path("rigs/"))
for model, cfg in rigs.items():
    print(model, cfg.civ_addr)
# IC-7300 0x94
# IC-7610 0x98
```

## See Also

- [`rigs/_schema.md`](../../rigs/_schema.md) — complete TOML schema specification
- [`docs/api/rig-loader.md`](../api/rig-loader.md) — `load_rig()` / `discover_rigs()` API
- [`docs/guide/radios.md`](radios.md) — supported radios and backend comparison
- [`docs/api/commands.md`](../api/commands.md) — using `CommandMap` with command functions
