# Rig TOML Schema Specification

This document describes the format of `.toml` rig configuration files used by
`icom-lan` to define radio profiles in a data-driven way.

---

## `[radio]` — Model Identity

| Field            | Type   | Required | Description                                     |
|------------------|--------|----------|-------------------------------------------------|
| `id`             | string | yes      | Unique profile identifier (e.g. `"icom_ic7610"`) |
| `model`          | string | yes      | Human-readable model name (e.g. `"IC-7610"`)    |
| `civ_addr`       | int    | yes      | Default CI-V address (0x00–0xFF)                |
| `receiver_count` | int    | yes      | Number of independent receivers (1 or 2)        |
| `has_lan`        | bool   | yes      | Whether the radio has a LAN (Ethernet) port     |
| `has_wifi`       | bool   | yes      | Whether the radio has built-in WiFi             |

## `[spectrum]` — Scope Parameters

Optional section for radios that support the spectrum scope.

| Field          | Type | Required | Description                                  |
|----------------|------|----------|----------------------------------------------|
| `seq_max`      | int  | yes      | Maximum scope sequence number                |
| `amp_max`      | int  | yes      | Maximum amplitude value in scope data        |
| `data_len_max` | int  | yes      | Maximum number of data points per scope frame |

## `[capabilities]` — Feature Flags

| Field      | Type     | Required | Description                    |
|------------|----------|----------|--------------------------------|
| `features` | string[] | yes      | List of supported capabilities |

Known capability strings:

- `audio` — Audio streaming (RX/TX)
- `scope` — Spectrum scope
- `dual_rx` — Dual receiver operation
- `meters` — Meter readings (S-meter, SWR, ALC, etc.)
- `tx` — Transmit capability
- `cw` — CW keying via CI-V
- `attenuator` — Attenuator control
- `preamp` — Preamplifier control
- `rf_gain` — RF gain control
- `af_level` — AF output level control
- `squelch` — Squelch control
- `nb` — Noise blanker
- `nr` — Noise reduction
- `digisel` — DIGI-SEL (digital IF preselector)
- `ip_plus` — IP+ (intercept point improvement)

## `[modes]` — Operating Modes

| Field  | Type     | Required | Description                                        |
|--------|----------|----------|----------------------------------------------------|
| `list` | string[] | yes      | Supported operating modes (e.g. `"USB"`, `"CW"`)  |

## `[filters]` — IF Filters

| Field  | Type     | Required | Description                                      |
|--------|----------|----------|--------------------------------------------------|
| `list` | string[] | yes      | Available IF filter names (e.g. `"FIL1"`)        |

## `[vfo]` — VFO Configuration

| Field         | Type   | Required    | Description                                       |
|---------------|--------|-------------|---------------------------------------------------|
| `scheme`      | string | yes         | VFO scheme: `"ab"` or `"main_sub"`                |
| `main_select` | int[]  | if main_sub | Wire bytes to select Main VFO (e.g. `[0xD0]`)    |
| `sub_select`  | int[]  | if main_sub | Wire bytes to select Sub VFO (e.g. `[0xD1]`)     |
| `swap`        | int[]  | if main_sub | Wire bytes for VFO swap (e.g. `[0xB0]`)          |

For `scheme = "ab"`, `main_select`/`sub_select`/`swap` are typically `[0x00]`/`[0x01]`/`[0xB0]` (VFO A/B select via cmd 0x07).

For `scheme = "main_sub"`, they use the Main/Sub select bytes specific to dual-receiver radios.

## `[[freq_ranges.ranges]]` — Frequency Ranges

Array of tables, each defining a frequency coverage range.

| Field      | Type   | Required | Description                                  |
|------------|--------|----------|----------------------------------------------|
| `label`    | string | yes      | Range label (e.g. `"HF"`, `"6m"`, `"2m"`)   |
| `start_hz` | int    | yes      | Start frequency in Hz                        |
| `end_hz`   | int    | yes      | End frequency in Hz (must be > `start_hz`)   |
| `bands`    | array  | no       | Amateur band definitions within this range   |

### `[[freq_ranges.ranges.bands]]` — Band Definitions

| Field        | Type   | Required | Description                                 |
|--------------|--------|----------|---------------------------------------------|
| `name`       | string | yes      | Band name (e.g. `"20m"`, `"70cm"`)          |
| `start_hz`   | int    | yes      | Band start frequency in Hz                  |
| `end_hz`     | int    | yes      | Band end frequency in Hz                    |
| `default_hz` | int    | yes      | Default tuning frequency in Hz (within band)|

## `[cmd29]` — Command 29 Routes

Optional section for dual-receiver radios that use Command 29 prefix for
receiver targeting. Single-receiver radios omit this section entirely.

| Field    | Type       | Required | Description                                        |
|----------|------------|----------|----------------------------------------------------|
| `routes` | int[][]    | yes      | List of `[cmd, sub]` or `[cmd]` (sub=None) entries |

Each entry is a 1- or 2-element integer array:
- `[0x11]` — command-only route (sub = None, e.g. ATT)
- `[0x14, 0x01]` — command + sub-command route (e.g. AF Gain)

Example:

```toml
[cmd29]
routes = [
    [0x11],           # ATT (sub=None)
    [0x14, 0x01],     # AF Gain
    [0x16, 0x02],     # PREAMP
]
```

## `[commands]` — CI-V Wire Bytes

Each key maps a command name to its CI-V wire bytes as an integer array.
Values represent the command byte and optional sub-command byte(s) used
to build CI-V frames. For example:

```toml
get_freq = [0x03]           # Single command byte
get_af_level = [0x14, 0x01] # Command + sub-command
```

The command name follows the pattern `get_<param>` / `set_<param>` for
read/write commands, or a verb like `ptt_on`, `scope_on`, `send_cw`.

### `[commands.overrides]` — Model-Specific Overrides

Commands in this sub-table override the defaults for a specific radio model.
Same format as `[commands]`: command names mapped to wire byte arrays.
Empty if the radio uses all default command bytes.

## Wire Byte Format

All wire bytes are specified as arrays of integers in the range `0x00`–`0xFF`.
TOML supports hex integer literals natively: `0x14` is the same as `20`.

Example: `get_af_level = [0x14, 0x01]` means CI-V command byte `0x14`,
sub-command `0x01`.
