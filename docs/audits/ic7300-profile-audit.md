# IC-7300 rig profile audit (wfview vs `rigs/ic7300.toml`)

**Reference:** `references/wfview/rigs/IC-7300.rig` (wfview v2.10, `Commands\size=183`).  
**Target:** `rigs/ic7300.toml` (`[commands]` + merged `[commands.overrides]`).  
**Loader context:** `KNOWN_CAPABILITIES` in `src/icom_lan/rig_loader.py` (valid feature tags only; IC-7300 correctly omits e.g. `ip_plus`, `dual_rx`).

**Method:** Each wfview `Commands\N\String` was parsed as a CI-V subcommand byte sequence (after leading `FE` / address / `FD` framing, as in wfview). A wfview entry **matches** the TOML profile if **any** command key expands to the **identical** byte tuple. This does not imply the key names align with wfview `Type=` labels.

---

## 1. Summary

**Headline (exact byte match vs wfview command strings):** **82 missing**, **0 wrong opcodes** on overlapping definitions, **101 matching**.

| Metric | Count | Notes |
|--------|------:|------|
| **wfview command entries** | **183** | Includes placeholders and response codes |
| **Exact byte-sequence match in TOML** | **101** | At least one TOML key shares the same opcode bytes |
| **No matching TOML key (missing sequence)** | **82** | Includes 2 wfview placeholders with no Get/Set |
| **Missing with Get or Set enabled** | **80** | Operational gaps vs wfview’s command table |
| **Wrong CI-V bytes (same feature, different opcode in both)** | **0** | No case found where TOML and wfview both list the same `Type` but disagree on bytes; overlap is compared by bytes, not labels |
| **TOML-only sequences (not in any wfview `Commands\N\String`)** | **12** | 6 logical pairs (get/set) → **6 opcodes** |

**wfview quirk:** `Repeater TSQL` and `S Meter Sql Status` both use `16 43` (duplicate `String` in `.rig`).

---

## 2. Missing commands (in `.rig`, no identical bytes in TOML)

### 2.1 Placeholders (no Get/Set in wfview)

| wfview `Type` | CI-V bytes (hex) |
|---------------|------------------|
| Freq (TRX) | `00` |
| Mode (TRX) | `01` |

### 2.2 VFO / memory / responses

| wfview `Type` | CI-V bytes (hex) | wfview Min | wfview Max |
|---------------|------------------|------------|------------|
| VFO A Select | `07 00` | 0 | 0 |
| VFO B Select | `07 01` | 0 | 0 |
| VFO Equal AB | `07 A0` | 0 | 0 |
| VFO Swap A/B | `07 B0` | 0 | 0 |
| Memory Mode | `08` | 1 | 101 |
| Memory Clear | `0B` | 1 | 101 |
| Memory Contents | `1A 00` | 1 | 101 |
| S Meter Sql Status | `15 04` | 0 | 1 |
| IP Plus Status | `16 65` | 0 | 1 |
| Scope Wave Data | `27 00` | 0 | 0 |
| Command Error FA | `FA` | 0 | 0 |
| Command OK FB | `FB` | 0 | 0 |

**Note on VFO:** TOML encodes `07` plus sub-bytes under `[vfo]` (`main_select`, `sub_select`, `swap`, `equal`) and `get_vfo` / `set_vfo` = `[0x07]`. That may be sufficient for a composite API, but there are **no** dedicated TOML keys whose value equals `07 00`, `07 01`, `07 A0`, or `07 B0`.

**Note on split:** wfview `Split/Duplex` uses `0F` with Get+Set. TOML has `set_split = [0x0F]` only — **no** `get_split` key (same opcode, missing getter in profile).

### 2.3 `0x1A 0x05` menu — RX/TX tone & scope edge registers (all missing as TOML command tuples)

wfview defines **81** distinct `1A 05 …` four-byte subcommand sequences. TOML implements **13** that also appear in wfview, plus **`1A 05 00 70`** (ref adjust), which wfview **does not** list for IC-7300.

**Missing from TOML (68 addresses)** — bytes are `1A 05` + third + fourth octet:

| Sub-address (`00 xx`) | wfview labels |
|----------------------|----------------|
| `00 01` … `00 10` | SSB/AM/FM/CW RX HPFLPF, Bass, Treble; CW RX HPFLPF |
| `00 12`, `00 13` | SSB TX Bass / Treble |
| `00 17` … `00 20` | AM/FM TX Bass / Treble |

| Sub-address (`01 xx`) | wfview labels |
|----------------------|----------------|
| `01 12` … `01 50` | Scope Edge1–3 for 1.6M … 74M bands (3 edges × many bands) |

| Sub-address (`02 xx`) | wfview labels |
|----------------------|----------------|
| `02 04` … `02 16` | Scope Edge4 for same band set |

**Present in both wfview and TOML (`1A 05`)**

| Bytes (hex) | wfview `Type` | TOML keys (representative) |
|-------------|---------------|----------------------------|
| `1A 05 00 30` | Quick Split | `get_quick_split` / `set_quick_split` |
| `1A 05 00 61` | CI-V Output (ANT) | `get_civ_output_ant` / `set_civ_output_ant` |
| `1A 05 00 64` | ACC1 Mod Level | `get_acc1_mod_level` / `set_acc1_mod_level` |
| `1A 05 00 65` | USB Mod Level | `get_usb_mod_level` / `set_usb_mod_level` |
| `1A 05 00 66` | Data Off Mod Input | `get_data_off_mod_input` / `set_data_off_mod_input` |
| `1A 05 00 67` | DATA1 Mod Input | `get_data1_mod_input` / `set_data1_mod_input` |
| `1A 05 00 71` | CIV Transceive | `get_civ_transceive` / `set_civ_transceive` |
| `1A 05 00 94` | System Date | `get_system_date` / `set_system_date` |
| `1A 05 00 95` | System Time | `get_system_time` / `set_system_time` |
| `1A 05 00 96` | UTC Offset | `get_utc_offset` / `set_utc_offset` |
| `1A 05 01 89` | NB Depth | `get_nb_depth` / `set_nb_depth` |
| `1A 05 01 90` | NB Width | `get_nb_width` / `set_nb_width` |
| `1A 05 01 91` | VOX Delay | `get_vox_delay` / `set_vox_delay` |

**In TOML only (not in wfview IC-7300.rig)**

| Bytes (hex) | TOML keys |
|-------------|-----------|
| `1A 05 00 70` | `get_ref_adjust` / `set_ref_adjust` |

---

## 3. Table of differences (parameters, bands, metadata)

| Area | wfview `.rig` | `rigs/ic7300.toml` | Severity |
|------|----------------|-------------------|----------|
| **NB depth range** | Command `NB Depth`: Min=**1**, Max=**10** (`1A 05 01 89`) | `[nb]` `depth_min=0`, `depth_max=9` | **High** — range off-by-one vs wfview |
| **IF filter width** | Filter Width: Min=50, Max=**10000** (`1A 03`) | `[filters]` `width_max_hz=9999` | **Medium** — upper limit 1 Hz short |
| **AGC (`16 12`)** | AGC Status: Min=**0**, Max=**2** (3 steps) | `[agc]` modes `[1, 2, 3]` | **Medium** — encoding may match radio manual; **does not** match wfview numeric range |
| **Break-in (`16 47`)** | Min=0, Max=**1** | `[break_in]` values `[0, 1, 2]` (OFF/SEMI/FULL) | **Medium** — wfview only documents two states |
| **RIT (`21 00`)** | Min=**-999**, Max=**999** | `[rit]` `range_hz=9999`; `[controls.rit]` raw ±9999 | **Medium** — scaling/units need alignment with CI-V BCD rules |
| **Speech (`13`)** | GetCommand=**false**, SetCommand=**true** | `get_speech = [0x13]` (no `set_speech`) | **Low** — direction flag mismatch vs wfview |
| **IP Plus** | Command `IP Plus Status` `16 65` present | Capability comment says not on IC-7300; feature `ip_plus` **absent** | **Policy** — intentional deviation from wfview unless revalidated against CI-V PDF/hardware |
| **Antenna (`12`)** | `Antennas\size=0`; no `12` in wfview command list | `get_antenna` / `set_antenna` = `[0x12]` | **Reference** — TOML follows CI-V guide, not wfview command enum |
| **DATA mode (`1A 06`)** | Not present in wfview IC-7300 command table | `get_data_mode` / `set_data_mode` = `[0x1A, 0x06]` | **Reference** — same as above |
| **Manual notch position** | No `14 0D` in wfview IC-7300.rig | `get_notch_filter` / `set_notch_filter` = `[0x14, 0x0D]` | **Reference** |
| **APF** | No `16 32` in wfview IC-7300.rig | `get_audio_peak_filter` / `set_audio_peak_filter` = `[0x16, 0x32]` | **Reference** |
| **APF level** | No `14 05` in wfview IC-7300.rig | `get_apf_type_level` / `set_apf_type_level` = `[0x14, 0x05]` | **Reference** |
| **S-meter SQL** | Two commands: `15 01` and `15 04` | Only `get_s_meter_sql_status` = `[0x15, 0x01]` | **Medium** — second opcode missing from profile |
| **4m band** | `Bands`: 70.0–70.5 MHz, BSR=0, Num=9 | No dedicated band row; HF block ends 60 MHz | **Low** — regional; wfview still lists band |
| **60m** | 5.25–5.45 MHz (ITU-style window in wfview) | 5.33–5.41 MHz (channelized) | **Low** — different regulatory representation |
| **40m** | Multiple regional rows (e.g. 7.0–7.2 vs 7.0–7.3 MHz) | Single 7.0–7.3 MHz | **Low** — TOML matches one wfview row, not all |
| **80m** | Multiple rows (up to 3.8 / 3.9 / 4.0 MHz) | Single 3.5–4.0 MHz | **Low** |
| **60m BSR** | wfview `BSR=0` for 60m band entry | TOML **no** `bsr_code` on 60m | **Medium** for BSR parity with wfview stacking model |
| **Gen / BSR 11** | “Gen” 30 kHz–74.8 MHz, `BSR=11` | HF range 30 kHz–60 MHz without `bsr_code=0x0B` style row | **Low** — modelled differently |

---

## 4. Frequency ranges & BSR codes

- **CI-V address:** wfview `CIVAddress=148` (0x94) = TOML `civ_addr = 0x94` — **match**.
- **Band stacking:** wfview `Band Stacking Reg` = `1A 01`; TOML `get_bsr` / `set_bsr` — **match**.
- **Per-band BSR:** For named HF bands where TOML sets `bsr_code`, values align with wfview’s `BSR` field for the **corresponding** band name (e.g. 160m→1, 80m→2, 40m→3, …, 6m→10). **Exceptions:** 60m uses BSR 0 in wfview but TOML omits `bsr_code`; wfview **4m** / **Gen** semantics are not mirrored as separate TOML band rows.
- **Overall coverage:** wfview lists a **Gen** span up to **74.8 MHz**; TOML splits HF (≤60 MHz) and 6m (50–54 MHz) and does not add wfview’s 70 MHz **4m** slice.

---

## 5. `0x27` scope commands

All wfview `27 xx` commands except **`27 00` (Scope Wave Data)** appear in TOML (including `27 10` for on/off). TOML uses `get_*` names for most scope subcommands; wfview marks them get+set — naming only.

---

## 6. Modes, attenuator, tuning steps (wfview side tables)

| Table | wfview | TOML | Match? |
|-------|--------|------|--------|
| **Modes** | 8 modes (LSB, USB, AM, CW, RTTY, FM, CW-R, RTTY-R) with per-mode filter Min/Max | `modes.list` same set (order differs) | **OK** |
| **Attenuator** | Command `11`: Min 0, Max 20; table 0 dB / −20 dB | `[attenuator]` `[0, 20]` | **OK** |
| **Preamp** | `16 02`: 0–2 | `[preamp]` `[0, 1, 2]` | **OK** |
| **Tuning steps** | 10 entries (1 Hz … 25 kHz), `Tuning Step` command `10`, Max=8 | TOML has `get_tuning_step` / `set_tuning_step` = `[0x10]` only | **Partial** — step list not duplicated in TOML (may be OK if encoded elsewhere) |

---

## 7. Recommendations

1. **Decide reference precedence:** For items present in the IC-7300 CI-V PDF but absent from wfview’s command list (`12`, `1A 06`, `14 0D`, `16 32`, `14 05`), keep them but document “CI-V PDF / hardware, not wfview”.
2. **Align numeric metadata with wfview where intended:** Fix **`[nb]` depth** to **1–10** (or document why 0–9), and **`width_max_hz`** to **10000** if wfview is authoritative.
3. **Resolve AGC and break-in enums** against the official CI-V table; if the radio uses 1–3 and three break-in states, document explicit mapping vs wfview’s 0–2 / 0–1 fields.
4. **Add missing wfview opcodes if the API should be wfview-complete:** `15 04`, `get_split`, memory commands (`08`, `0B`, `1A 00`), `27 00`, and optionally `16 65` (if `ip_plus` is re-enabled).
5. **`1A 05` scope edge & EQ menus:** Add structured entries (or a single pattern + table) for the **68** missing sub-addresses if the web UI or poller should match wfview periodic commands (wfview polls **Scope Edge** generically; individual edge registers are still in the `.rig` file).
6. **Bands / BSR:** If stacking must match wfview exactly, add **4m** (or extend range), reconcile **60m** `bsr_code`, and consider regional **40m** / **80m** variants or document a single ITU choice.
7. **Speech command:** Rename or split into set-only to match wfview flags, or confirm read support from CI-V PDF.
8. **`KNOWN_CAPABILITIES`:** No change required for IC-7300; optional future `ip_plus` if `16 65` is exposed.

---

*Generated for diff review only; `rigs/ic7300.toml` was not modified as part of this audit.*
