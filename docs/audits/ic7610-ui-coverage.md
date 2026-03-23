# IC-7610 profile vs Web UI coverage audit

**Scope:** `rigs/ic7610.toml` capability tags and CI-V command map vs `frontend/src/` (Svelte), `src/icom_lan/web/server.py` (HTTP), `src/icom_lan/web/handlers.py` (WebSocket control channel), `src/icom_lan/web/radio_poller.py` (command queue + polling).

**Audit date:** 2026-03-22

## Architecture (how to read the matrix)

| Layer | Behavior |
|--------|-----------|
| **REST** | There are **no** per-parameter REST routes for rig control. Clients use **`GET /api/v1/state`** (snapshot), **`GET /api/v1/capabilities`**, **`GET /api/v1/info`**, plus **`POST /api/v1/radio/power`**, **`POST /api/v1/radio/connect`**, **`POST /api/v1/radio/disconnect`**, **`/api/v1/bridge`**. |
| **WebSocket** | Control plane: **`/api/v1/ws`** — JSON `cmd` messages; see `ControlHandler._COMMANDS` in `handlers.py`. |
| **Backend** | Queued writes: `RadioPoller._execute`. Read path: CI-V RX → `RadioState` + poller `_STATE_QUERIES` / `_FAST_CMDS`. Library methods in `radio.py` / `commands.py` may exist **without** any web exposure. |
| **UI** | **Default shell is still v1:** `App.svelte` uses `initUiVersion()` which defaults to **`v1`** (`AppShell` → `DesktopLayout` / `MobileLayout`) unless `?ui=v2` or localStorage selects v2. **`RadioLayout.svelte` (components-v2)** is the newer deck. This report notes **v2** vs **v1-only** where they differ. |

**Legend**

| Symbol | Meaning |
|--------|---------|
| TOML | Declared in `ic7610.toml` |
| Backend | Implemented in icom-lan runtime (poller queue, `IcomRadio` / CI-V RX path, or `AdvancedControlCapable` in WS handler) |
| REST | Any relevant **GET** surface (`/state`, `/capabilities`, `/info`) or **POST** where applicable |
| WS | Accepted on `/api/v1/ws` as a `cmd` name |
| UI | Visible control, slider, or intentional keyboard binding that sends the command |

---

## 1. Summary

| Metric | Count |
|--------|------:|
| **Capability tags** in `[capabilities].features` | **42** |
| With **any** production UI (v1 **or** v2, including keyboard-only where noted) | **~30** |
| With **components-v2** panel/control (excluding demo-only `ControlButtonDemo.svelte`) | **~26** |
| **No dedicated UI** (polled state only, or backend only) | **~12** |

| Metric | Approx. |
|--------|------:|
| **Distinct command keys** under `[commands]` + `[commands.overrides]` | **~130** |
| With **WebSocket** `cmd` support | **~45** unique command names (aliases such as `set_att` / `set_attenuator` count once toward UX) |
| With **RadioPoller** `Command` dataclass + `_execute` | **Subset of WS** (queue drives the same writes) |
| **TOML / library only** (no WS, no poller command) | Large majority of **get_** helpers, scope getters, menu 0x1A 0x05 items, etc. |

**“End-to-end” (TOML → backend → WS → UI)** in the strict sense exists for the **core deck**: frequency/mode/filter/VFO, many RX DSP levels, RIT/XIT, split, AGC, TX audio chain basics, tuner, PTT (v1 + keyboard), spectrum waterfall tuning, band BSR recall. Large gaps: **squelch**, **APF / twin-peak / manual notch width**, **FM tone / TSQL**, **scan**, **drive gain / SSB TX BW / break-in / keyer** as UI, many **scope query** commands, and most **menu** overrides unless specifically wired.

---

## 2. Coverage matrix — capability tags

Each row is one string from `[capabilities].features` in `ic7610.toml`.

| Capability | TOML | Backend | REST | WS | UI | Notes |
|------------|:----:|:-------:|:----:|:--:|:-:|:------|
| `audio` | ✅ | ✅ | ✅ | — | ✅ | v2: `RxAudioPanel` + `/api/v1/audio` WS; LAN streaming |
| `dual_rx` | ✅ | ✅ | ✅ | — | ✅ | v2: dual `VfoPanel`; v1: `VfoDisplay` / `ReceiverSwitch` |
| `dual_watch` | ✅ | ✅ | ✅ | ✅ | ⚠️ | WS `set_dual_watch`; **v1** `ReceiverSwitch`; **no v2 toggle** wired to `makeVfoHandlers.onDualWatchToggle` |
| `af_level` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `RxAudioPanel` (`set_af_level`) |
| `rf_gain` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `RfFrontEnd.svelte` |
| `squelch` | ✅ | ✅ | ✅ | ✅ | ❌ | Polled; `set_squelch` in `ControlHandler`; **no slider in v1/v2** (only a keyboard focus hint to a missing control) |
| `attenuator` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `RfFrontEnd` + `AttenuatorControl`; v1: `FeatureToggles` |
| `preamp` | ✅ | ✅ | ✅ | ✅ | ✅ | Same as attenuator |
| `digisel` | ✅ | ✅ | ✅ | ✅ | ⚠️ | **v1** `FeatureToggles`; v2: badge only (`toVfoProps`), **no toggle** |
| `ip_plus` | ✅ | ✅ | ✅ | ✅ | ⚠️ | v2: keyboard `toggle_ip_plus` only (`command-bus.ts`); v1: **no** `FeatureToggles` button |
| `antenna` | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | `set_antenna_1` / `set_antenna_2`; **v1** `AntennaPanel` / `FeatureToggles` if `capabilities.antennas` > 1 (profile may omit → default 1) |
| `rx_antenna` | ✅ | ✅ | ✅ | ✅ | ⚠️ | **v1** `AntennaPanel` RX row; not in v2 sidebars |
| `nb` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `DspPanel.svelte` |
| `nr` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `DspPanel.svelte` |
| `notch` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `DspPanel` auto/manual + `set_notch_filter` (**raw 0–255**, UI labelled Hz — mismatch risk) |
| `apf` | ✅ | ✅ | ✅ | — | ❌ | Polled on IC-7610 (`0x16 0x32`); **no** `set_audio_peak_filter` / APF level in WS `_COMMANDS` |
| `twin_peak` | ✅ | ✅ | ✅ | — | ❌ | Polled; **no** WS command in `handlers.py` |
| `pbt` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `FilterPanel.svelte` |
| `filter_width` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `FilterPanel` + `SpectrumPanel` drag → `set_filter_width` |
| `filter_shape` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `FilterPanel` |
| `tx` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `TxPanel.svelte`; PTT **v1** `PttButton` / `BottomBar`; v2 **no** PTT chip in `RadioLayout` |
| `split` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `VfoOps.svelte`; v1: `SplitRitPanel` |
| `vox` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `TxPanel` |
| `compressor` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `TxPanel` (`set_compressor`, `set_compressor_level`) |
| `monitor` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `TxPanel` |
| `drive_gain` | ✅ | ✅ | ✅ | — | ❌ | In `RadioState`; **no** WS `set_drive_gain` in `ControlHandler` |
| `ssb_tx_bw` | ✅ | ✅ | ✅ | — | ❌ | Polled for IC-7610; **no** WS/UI |
| `cw` | ✅ | ✅ | ✅ | ✅ | ⚠️ | v2: CW pitch slider → `set_cw_pitch`; **no** key speed, break-in, dash ratio, `send_cw` UI |
| `break_in` | ✅ | ✅ | ✅ | — | ❌ | No WS/UI |
| `rit` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `RitXitPanel.svelte`; v1: `SplitRitPanel` |
| `xit` | ✅ | ✅ | ✅ | ✅ | ✅ | Same (uses `set_rit_tx_status` / shared offset) |
| `tuner` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `TxPanel` ATU; v1: `TunerPanel.svelte` |
| `meters` | ✅ | ✅ | ✅ | — | ✅ | v2: `LinearSMeter`, `DockMeterPanel`; v1: `SMeter`, `PowerMeter` |
| `scope` | ✅ | ✅ | ✅ | — | ✅ | `/api/v1/scope` binary WS + `SpectrumPanel`; partial scope **setters** via WS (`switch_scope_receiver`, `set_scope_during_tx`, `set_scope_center_type`, `set_scope_fixed_edge`) — **no** UI for most |
| `repeater_tone` | ✅ | ✅ | ✅ | — | ❌ | No WS/UI |
| `tsql` | ✅ | ✅ | ✅ | — | ❌ | No WS/UI |
| `data_mode` | ✅ | ✅ | ✅ | ✅ | ✅ | v2: `ModePanel.svelte` |
| `power_control` | ✅ | ✅ | ✅ | ✅ | ✅ | `POST /api/v1/radio/power` + `StatusBar.svelte`; WS `set_powerstat` |
| `dial_lock` | ✅ | ✅ | ✅ | ✅ | ⚠️ | WS `set_dial_lock`; **keyboard** `toggle_dial_lock` in v2; **no** visible toggle in v2 layout |
| `scan` | ✅ | ✅ | ✅ | — | ❌ | `scan_start` / `scan_stop` exist in library; **not** in `ControlHandler._COMMANDS` |
| `bsr` | ✅ | ✅ | ✅ | ✅ | ✅ | `set_band` in WS; v2: `BandSelector.svelte` (BSR recall in poller) |
| `main_sub_tracking` | ✅ | ✅ | ✅ | — | ❌ | In `RadioState` / `toVfoOpsProps`; **not** shown or toggled in `VfoOps.svelte` |

**REST column:** ✅ = capability metadata or live fields exposed via **`GET /api/v1/capabilities`**, **`GET /api/v1/info`**, or **`GET /api/v1/state`** (when the radio updates `RadioState`). ⚠️ = partial (e.g. antenna count may not serialize from profile). **—** = N/A for REST *invocation* (streaming uses dedicated WS paths).

---

## 3. Coverage matrix — CI-V commands (`[commands]` + overrides)

Commands are grouped to keep the table usable. **Backend** ✅ means: implemented for use by icom-lan (library `radio.py` / `commands.py`, poller, CI-V RX parsing, or scope/audio paths), not necessarily exposed as a WS `cmd`.

### 3.1 Frequency, mode, VFO, split, band

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `get_freq` / `set_freq` | ✅ | ✅ | ✅ | ✅ `set_freq` | ✅ | v2 `FrequencyDisplayInteractive`; spectrum drag |
| `get_mode` / `set_mode` | ✅ | ✅ | ✅ | ✅ `set_mode` | ✅ | `ModePanel` / v1 `ModeSelector` |
| `get_band_edge_freq` | ✅ | ✅ | ⚠️ | ❌ | — | Library; band edges in `/capabilities` |
| `get_vfo` / `set_vfo` | ✅ | ✅ | ✅ | ✅ `set_vfo` | ✅ | VFO swap via `0x07` in poller |
| `get_split` / `set_split` | ✅ | ✅ | ✅ | ✅ `set_split` | ✅ | `VfoOps` / `SplitRitPanel` |
| `get_dual_watch` | ✅ | ✅ | ✅ | ✅ `get_dual_watch` | — | Read-only WS handler |
| `set_dual_watch_on` / `set_dual_watch_off` | ✅ | ✅ | ✅ | ✅ `set_dual_watch` | ⚠️ | v1 UI; v2 handler exists but not mounted |
| `get_main_sub_band` | ✅ | ✅ | ✅ | ❌ | — | Polled |
| `get_main_sub_tracking` / `set_main_sub_tracking` | ✅ | ✅ | ✅ | ❌ | ❌ | **No** WS command |
| `get_selected_freq` / `get_unselected_freq` / `get_selected_mode` / `get_unselected_mode` | ✅ | ❌ | ❌ | ❌ | ❌ | Marked NOT_IMPLEMENTED in TOML |
| `get_tuning_step` / `set_tuning_step` | ✅ | ✅ | ⚠️ | ❌ | ⚠️ | v2 local `tuning.svelte` store; not wired to CI-V step |
| `set_band` (BSR) | ✅ | ✅ | ✅ | ✅ `set_band` | ✅ | `BandSelector` |

### 3.2 RF front end, audio levels

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `get_attenuator` / `set_attenuator` | ✅ | ✅ | ✅ | ✅ | ✅ | `set_attenuator` / alias `set_att` |
| `get_preamp` / `set_preamp` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_digisel` / `set_digisel` | ✅ | ✅ | ✅ | ✅ | ⚠️ | v1 toggle |
| `get_digisel_shift` / `set_digisel_shift` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_ip_plus` / `set_ip_plus` | ✅ | ✅ | ✅ | ✅ | ⚠️ | Keyboard (v2) |
| `get_af_level` / `set_af_level` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_rf_gain` / `set_rf_gain` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_squelch` / `set_squelch` | ✅ | ✅ | ✅ | ✅ | ❌ | |
| `get_af_mute` / `set_af_mute` | ✅ | ✅ | ✅ | ❌ | ⚠️ | v2 “mute” path zeros AF via `set_af_level`, not `set_af_mute` |

### 3.3 Antenna

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `get_antenna` / `set_antenna` | ✅ | ✅ | ✅ | ✅ `set_antenna_1` / `set_antenna_2` | ⚠️ | v1; `FeatureToggles` sends `{ on: true }` only |
| `get_rx_antenna` / `set_rx_antenna` | ✅ | ✅ | ✅ | ✅ `set_rx_antenna_ant1` / `ant2` | ⚠️ | v1 `AntennaPanel` |
| `get_civ_output_ant` / `set_civ_output_ant` | ✅ | ❌ | ❌ | ❌ | ❌ | NOT_IMPLEMENTED |

### 3.4 DSP: NB, NR, notch, APF, twin peak

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `get_nb` / `set_nb`, `get_nb_level` / `set_nb_level` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_nr` / `set_nr`, levels | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_auto_notch` / `set_auto_notch`, `get_manual_notch` / `set_manual_notch` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_notch_filter` / `set_notch_filter` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_manual_notch_width` / `set_manual_notch_width` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_audio_peak_filter` / `set_audio_peak_filter`, `get_apf_type_level` / `set_apf_type_level` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_twin_peak_filter` / `set_twin_peak_filter` | ✅ | ✅ | ✅ | ❌ | ❌ | |

### 3.5 Filter / AGC

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `get_pbt_*` / `set_pbt_*` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_filter_width` / `set_filter_width` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_filter_shape` / `set_filter_shape` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_agc` / `set_agc`, `get_agc_time_constant` / `set_agc_time_constant` | ✅ | ✅ | ✅ | ✅ | ✅ | v2 `AgcPanel` |

### 3.6 TX chain

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `ptt_on` / `ptt_off` | ✅ | ✅ | ✅ | ✅ `ptt` / `ptt_on` / `ptt_off` | ⚠️ | v1 PTT; v2 `makeSystemHandlers` **not** wired in `RadioLayout` |
| `get_rf_power` / `set_rf_power` | ✅ | ✅ | ✅ | ✅ | ⚠️ | **v1** `FeatureToggles` range; **no** v2 slider |
| `get_mic_gain` / `set_mic_gain` | ✅ | ✅ | ✅ | ✅ | ✅ | v2 `TxPanel` |
| `get_drive_gain` / `set_drive_gain` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_compressor` / `set_compressor`, levels | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_monitor` / `set_monitor`, gains | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_vox` / `set_vox`, `get_vox_gain` / `set_vox_gain` | ✅ | ✅ | ✅ | ✅ `set_vox` | ⚠️ | **No** vox gain UI |
| `get_anti_vox_gain` / `set_anti_vox_gain` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_ssb_tx_bandwidth` / `set_ssb_tx_bandwidth` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_xfc_status` / `set_xfc_status`, `get_tx_freq_monitor` / `set_tx_freq_monitor` | ✅ | ✅ | ✅ | ❌ | ❌ | Polled `0x1C 0x03` |

### 3.7 CW / keyer

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `send_cw` / `stop_cw` | ✅ | ✅ | ✅ | ❌ | ❌ | CLI / library |
| `get_cw_pitch` / `set_cw_pitch` | ✅ | ✅ | ✅ | ✅ | ✅ | v2 `DspPanel` |
| `get_key_speed` / `set_key_speed` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_break_in` / `set_break_in`, delay | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_dash_ratio` / `set_dash_ratio` (override) | ✅ | ✅ | ✅ | ❌ | ❌ | |

### 3.8 RIT / XIT

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `get_rit_frequency` / `set_rit_frequency`, `get_rit_status` / `set_rit_status`, `get_rit_tx_status` / `set_rit_tx_status` | ✅ | ✅ | ✅ | ✅ | ✅ | |

**Bug (keyboard):** `toggle_rit` / `toggle_xit` in `command-bus.ts` send `set_rit` / `set_xit`, which are **not** in `ControlHandler._COMMANDS` (server expects `set_rit_status` / `set_rit_tx_status`). Those shortcuts will fail until renamed.

### 3.9 Tuner, meters

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `get_tuner_status` / `set_tuner_status` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `get_s_meter` … `get_id_meter` | ✅ | ✅ | ✅ | ❌ | ✅ | Polled; shown in meters / S-meter widgets |

### 3.10 FM tone / data mode

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `get_repeater_tone` / `set_repeater_tone`, `get_repeater_tsql` / `set_repeater_tsql` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_tone_freq` / `set_tone_freq`, `get_tsql_freq` / `set_tsql_freq` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_data_mode` / `set_data_mode` | ✅ | ✅ | ✅ | ✅ | ✅ | |

### 3.11 Scope

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `scope_on` / `scope_off` / `scope_data_output` | ✅ | ✅ | ✅ | ❌ | ✅ | Server enables scope when `/api/v1/scope` connects |
| `get_scope_wave` / `set_scope_wave` | ✅ | ✅ | ✅ | ❌ | — | Data path binary WS |
| `get_scope_*` (main_sub, span, mode, …) | ✅ | ⚠️ | ❌ | ❌ | ❌ | Mostly **not** exposed to web |
| `get_main_sub_prefix` / `set_main_sub_prefix` | ✅ | ✅ | ❌ | ❌ | ❌ | Internal framing |
| `switch_scope_receiver`, `set_scope_during_tx`, `set_scope_center_type`, `set_scope_fixed_edge` | ✅ | ✅ | ✅ | ✅ | ⚠️ | `SpectrumPanel` / `WaterfallCanvas` use **some** |

### 3.12 Scan, power, system, BSR, misc

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `scan_start` / `scan_stop` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `power_on` / `power_off` | ✅ | ✅ | ✅ | ✅ `set_powerstat` | ✅ | Also `POST /api/v1/radio/power` |
| `get_transceiver_id`, `get_speech` | ✅ | ✅ | ⚠️ | ❌ | ❌ | |
| `get_dial_lock` / `set_dial_lock` | ✅ | ✅ | ✅ | ✅ | ⚠️ | Keyboard |
| `get_ref_adjust` / `set_ref_adjust` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_bsr` / `set_bsr` | ✅ | ✅ | ✅ | ⚠️ | ✅ | Recall via `set_band`; full BSR read/write not exposed as WS |

### 3.13 `[commands.overrides]` (menu / advanced)

| Command key(s) | TOML | Backend | REST | WS cmd | UI | Notes |
|----------------|:----:|:-------:|:----:|:------:|:--:|:------|
| `set_acc1_mod_level` / `set_usb_mod_level` / `set_lan_mod_level` | ✅ | ✅ | ✅ | ✅ | ❌ | |
| `get_data*_mod_input` / `set_data*_mod_input` | ✅ | ✅ | ✅ | ❌ | ❌ | DATA mod source matrix from TOML unused in UI |
| `get_civ_transceive` / `set_civ_transceive` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_system_date` / `set_system_date`, `get_system_time` / `set_system_time` | ✅ | ✅ | ✅ | ✅ | ❌ | WS read/get + queue set |
| `get_utc_offset` / `set_utc_offset` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_quick_split` / `set_quick_split`, `get_quick_dual_watch` / `set_quick_dual_watch` | ✅ | ✅ | ✅ | ❌ | ❌ | |
| `get_nb_depth` / `set_nb_depth`, `get_nb_width` / `set_nb_width` | ✅ | ✅ | ✅ | ❌ | ❌ | TOML `[nb]` describes depth/width; UI uses `set_nb_level` only |
| `get_vox_delay` / `set_vox_delay` | ✅ | ❌ | ❌ | ❌ | ❌ | NOT_IMPLEMENTED in TOML |

---

## 4. Fully implemented (typical user path)

These are **strong** end-to-end paths for IC-7610 today:

- Frequency / mode / FIL / IF width / shape / PBT / AGC (v2 left column + spectrum).
- Split, VFO swap / equalize, band BSR recall (`set_band`).
- RX DSP: NB/NR, auto/manual notch + position, dual-path metering.
- RIT / XIT offsets and enables.
- TX: mic gain, PTT (v1 or space-toggle in v1 path), compressor + level, monitor + level, VOX on/off, ATU.
- Audio: AF level, optional browser RX streaming; spectrum waterfall + passband resize.
- Power / connection: `StatusBar` HTTP + `set_powerstat` / connect/disconnect.

---

## 5. Backend only (no or incomplete UI)

- **APF**, **twin peak**, **manual notch width**, **NB depth/width** (menu overrides), **drive gain**, **SSB TX bandwidth**, **break-in** and **keyer** parameters, **anti-vox** / **vox delay**, **FM tone / TSQL**, **scan**, **main/sub tracking**, **DIGI-SEL shift**, **XFC / TX monitor** toggles, most **scope query** CI-V, **DATA mod input** matrix, **UTC offset** / **CI-V transceive** / **quick** menu helpers.
- **Library-only** getters marked NOT_IMPLEMENTED in TOML (`get_selected_*`, `get_civ_output_ant`, `get_vox_delay`).

---

## 6. TOML only (or intentionally not wired)

- Commented **memory** commands in TOML.
- Any command with **NOT_IMPLEMENTED** note in `ic7610.toml` without matching `commands.py` / radio implementation.

---

## 7. Recommendations (highest user value)

1. **Squelch** — add `ValueControl` to `RfFrontEnd.svelte` (capability-gated); data already in `RadioState` and WS `set_squelch`.
2. **RF power (v2)** — expose `set_rf_power` in `TxPanel` or VFO dock when `hasTx()`.
3. **PTT (v2)** — wire `PttButton` / push-to-talk or mount `makeSystemHandlers` in `RadioLayout`.
4. **Dual Watch (v2)** — surface `onDualWatchToggle` next to `VfoOps`.
5. **DIGI-SEL + IP+** — small toggle row in v2 (mirror v1 `FeatureToggles` DSP group).
6. **Antenna / RX ANT** — port `AntennaPanel` patterns into v2 or a compact strip; ensure `capabilities` JSON includes **`antennas`** when profile has `tx_count > 1`.
7. **Drive gain + SSB TX BW** — add WS commands in `ControlHandler` + poller `Command` types, then sliders in `TxPanel`.
8. **Fix keyboard** — `set_rit` / `set_xit` → `set_rit_status` / `set_rit_tx_status`.
9. **Notch UI** — align displayed units with CI-V (raw vs Hz) or map in the client.
10. **Scope controls** — minimal UI for receiver selection and “scope during TX” if operators need it without a CLI.

---

## 8. File reference index (quick navigation)

| Area | Primary files |
|------|----------------|
| Profile | `rigs/ic7610.toml` |
| WS allow-list | `src/icom_lan/web/handlers.py` — `ControlHandler._COMMANDS`, `_enqueue_command` |
| Poller queue | `src/icom_lan/web/radio_poller.py` — `Command` dataclasses, `_execute`, `_STATE_QUERIES`, `_FAST_CMDS` |
| HTTP | `src/icom_lan/web/server.py` — `/api/v1/*` routes |
| v2 layout | `frontend/src/components-v2/layout/RadioLayout.svelte`, `LeftSidebar.svelte`, `RightSidebar.svelte` |
| v2 commands | `frontend/src/components-v2/wiring/command-bus.ts` |
| v1 shell | `frontend/src/components/layout/DesktopLayout.svelte`, `FeatureToggles.svelte`, `AntennaPanel.svelte`, `PttButton.svelte` |
| Spectrum | `frontend/src/components/spectrum/SpectrumPanel.svelte`, `WaterfallCanvas.svelte` |

---

*Generated from repository analysis; counts are approximate where command aliases and dual code paths (v1/v2) overlap.*
