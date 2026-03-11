# P1 Radio Protocol Slim — Plan (Issue 207)

**Goal:** Slim down the base `Radio` protocol so that only methods/properties that **every** transceiver must have remain on `Radio`. Optional features move into capability protocols (new or existing). No code changes in this step — audit and plan only.

---

## 1. Current Radio protocol — full list

From `src/icom_lan/radio_protocol.py`, the **Radio** protocol currently defines:

| # | Member | Type |
|---|--------|------|
| 1 | `connect` | async method |
| 2 | `disconnect` | async method |
| 3 | `connected` | property |
| 4 | `radio_ready` | property |
| 5 | `get_frequency` | async method |
| 6 | `set_frequency` | async method |
| 7 | `get_mode` | async method |
| 8 | `set_mode` | async method |
| 9 | `get_data_mode` | async method |
| 10 | `set_data_mode` | async method |
| 11 | `set_ptt` | async method |
| 12 | `get_s_meter` | async method |
| 13 | `get_swr` | async method |
| 14 | `get_power` | async method |
| 15 | `set_powerstat` | async method |
| 16 | `set_power` | async method |
| 17 | `set_af_level` | async method |
| 18 | `set_rf_gain` | async method |
| 19 | `set_squelch` | async method |
| 20 | `radio_state` | property |
| 21 | `model` | property |
| 22 | `capabilities` | property |
| 23 | `set_state_change_callback` | method |
| 24 | `set_reconnect_callback` | method |

---

## 2. Classification: core vs optional capability

### Core (every transceiver must have)

- **Lifecycle:** `connect`, `disconnect`, `connected`, `radio_ready`
- **Frequency:** `get_frequency`, `set_frequency`
- **Mode:** `get_mode`, `set_mode`, `get_data_mode`, `set_data_mode`
- **TX:** `set_ptt`
- **State/identity:** `radio_state`, `model`, `capabilities`

Rationale: A minimal “controllable transceiver” can connect, tune frequency, set mode, key PTT, and expose live state and capability tags. No meters, levels, or power control are required for the core contract.

### Optional capability

- **Meters (read-only):** `get_s_meter`, `get_swr`, `get_power` → **MetersCapable** (new)
- **Power control:** `set_powerstat`, `set_power` → **PowerControlCapable** (new)
- **Receiver levels:** `set_af_level`, `set_rf_gain`, `set_squelch` → **LevelsCapable** (new)
- **Server integration callbacks:** `set_state_change_callback`, `set_reconnect_callback` → **StateNotifyCapable** (new)

**DSP / advanced controls:** Already in **AdvancedControlCapable** (`set_filter`, `set_nb`, `set_nr`, `set_digisel`, `set_ip_plus`, `set_attenuator_level`, `set_preamp`). No new **DspCapable** protocol is proposed; AdvancedControlCapable already covers DSP-like (NB, NR, digisel, IP+) and hardware (attenuator, preamp). If desired later, AdvancedControlCapable could be split into e.g. **DspCapable** (nb, nr, digisel, ip_plus) and **HardwareLevelCapable** (filter, attenuator, preamp) — out of scope for this plan.

---

## 3. Target protocol layout

### Radio (slim core) — keeps only

- `connect`, `disconnect`, `connected`, `radio_ready`
- `get_frequency`, `set_frequency`
- `get_mode`, `set_mode`, `get_data_mode`, `set_data_mode`
- `set_ptt`
- `radio_state`, `model`, `capabilities`

### LevelsCapable (new)

- `set_af_level(level, receiver=0)`
- `set_rf_gain(level, receiver=0)`
- `set_squelch(level, receiver=0)`

### MetersCapable (new)

- `get_s_meter(receiver=0)`
- `get_swr()`
- `get_power()`

### PowerControlCapable (new)

- `set_powerstat(on: bool)`
- `set_power(level: int)`

### StateNotifyCapable (new)

- `set_state_change_callback(callback | None)`
- `set_reconnect_callback(callback | None)`

### Existing capability protocols (unchanged in this step)

- **AudioCapable**, **CivCommandCapable**, **ModeInfoCapable**, **ScopeCapable**, **DualReceiverCapable**, **StateCacheCapable**, **RecoverableConnection**, **AdvancedControlCapable** — no method moves from Radio into these; only new protocols and moves from Radio are defined above.

---

## 4. Consumers to update (implementation phase)

After the protocol split is implemented, the following must be updated to use capability checks and the new protocols:

1. **CLI** (`src/icom_lan/cli.py`)
   - `get_audio_capabilities()` usage remains; add `isinstance(radio, LevelsCapable)` (or equivalent) where setting AF/RF/squelch; `isinstance(radio, MetersCapable)` for `_cmd_meter` (get_s_meter, get_power, get_swr); `isinstance(radio, PowerControlCapable)` for `_cmd_power` set path; `isinstance(radio, AudioCapable)` and `isinstance(radio, ScopeCapable)` already used — ensure no direct use of moved methods on `Radio` without a check.

2. **Web — RadioPoller** (`src/icom_lan/web/radio_poller.py`)
   - Command handlers that call `set_power`, `set_rf_gain`, `set_af_level`, `set_squelch`: guard with `isinstance(radio, LevelsCapable)` / `isinstance(radio, PowerControlCapable)` as appropriate. No change to get_audio_capabilities (that comes from types/get_audio_capabilities); ensure poller only calls meter/level/power methods when the radio implements the corresponding capability.

3. **Web — server** (`src/icom_lan/web/server.py`)
   - `set_state_change_callback` / `set_reconnect_callback`: call only if `isinstance(radio, StateNotifyCapable)` (or keep calling on Radio if we keep these on Radio; the plan recommends moving to StateNotifyCapable so core stays minimal).

4. **Web — handlers** (`src/icom_lan/web/handlers.py`)
   - Commands such as `set_power`, `set_powerstat`, `set_rf_gain`, `set_af_level`, `set_squelch`: ensure dispatch uses capability checks (LevelsCapable, PowerControlCapable) before calling; handlers already have capability checks — align with new protocol names.

5. **Rigctld** (`src/icom_lan/rigctld/handler.py`)
   - `_cmd_get_level` uses `get_s_meter`, `get_power`, `get_swr`: use `isinstance(radio, MetersCapable)` and call only when True; otherwise return an appropriate error or cached value. Any future set_power / set_powerstat implementation should check `PowerControlCapable`.

6. **Backends / IcomRadio** (`src/icom_lan/radio.py`, `src/icom_lan/backends/`)
   - Implement the new capability protocols (LevelsCapable, MetersCapable, PowerControlCapable, StateNotifyCapable) on backends that support these features; remove those methods from the “core” surface where they are no longer part of `Radio`.

7. **Sync wrapper** (`src/icom_lan/sync.py`)
   - Sync wrappers for `get_power`, `set_power`, `get_s_meter`, `get_swr` (and any level setters if exposed) should delegate to the async implementation only when the radio implements the corresponding capability protocol; type hints may use union of Radio + capability protocols as needed.

8. **Public API** (`src/icom_lan/__init__.py`, `docs/api/`)
   - Export new protocols: `LevelsCapable`, `MetersCapable`, `PowerControlCapable`, `StateNotifyCapable`. Update `docs/api/public-api-surface.md` and any docs that describe the Radio protocol.

---

## 5. Summary

- **Radio** keeps: lifecycle, frequency, mode, data mode, PTT, `radio_state`, `model`, `capabilities`.
- **LevelsCapable (new):** `set_af_level`, `set_rf_gain`, `set_squelch`.
- **MetersCapable (new):** `get_s_meter`, `get_swr`, `get_power`.
- **PowerControlCapable (new):** `set_powerstat`, `set_power`.
- **StateNotifyCapable (new):** `set_state_change_callback`, `set_reconnect_callback`.
- **AdvancedControlCapable:** unchanged; no separate DspCapable in this plan.
- **Consumers:** CLI, web (radio_poller, server, handlers), rigctld handler, backends, sync wrapper, and public API exports must be updated to use the new capability protocols and `isinstance` checks where they call the moved methods.

This document is the reference for the next step: implementing the protocol split in code.

---

## 6. Implementation status (step 3 done)

- **Step 3 (consumers and public API)** is complete: CLI, web (radio_poller, server, handlers), rigctld handler, sync wrapper, and `__init__.py` exports now use the new capability protocols and `isinstance` checks. Docs updated (`docs/api/public-api-surface.md`, this plan).
