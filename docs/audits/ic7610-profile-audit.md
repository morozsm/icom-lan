# IC-7610 profile audit — `ic7610.toml` vs wfview `IC-7610.rig`

**Source of truth:** `references/wfview/rigs/IC-7610.rig` (General Version=2.10)  
**Compared to:** `rigs/ic7610.toml` (merged `[commands]` + `[commands.overrides]` as loaded by `rig_loader.load_rig`)  
**Loader reference:** `src/icom_lan/rig_loader.py` — `KNOWN_CAPABILITIES` (no schema mismatch found for current `ic7610.toml` features)

---

## 1. Summary

**Headline counts (automated byte-tuple comparison, merged TOML vs each wfview `Commands\N\String`):**

- **Z — matching:** **115** wfview command rows share an **identical** CI-V byte sequence with at least one merged `commands` entry in `ic7610.toml`.
- **X — missing (no exact tuple):** **19** wfview rows do not; see section 2 (includes internal `00`/`01`, FA/FB, VFO bytes only under `[vfo]`, memory commented out, `27 00` / `29`, `1C 04`, and RX `25`/`26` single-byte vs TOML’s two-byte form).
- **Y — wrong / contradictory vs wfview:** **6** tracked issues — (1) `get_civ_output_ant` bytes vs wfview #110 `1C 04`, (2–3) `cmd29` includes `14 0D` and `1A 06` while wfview sets `Command29=false`, (4) filter width max **9999** vs wfview **10000**, (5) all three `[spectrum]` integers vs wfview, (6) `[antenna]` comment vs wfview `1A 05 00 89` (USB Mod Level).

**Feature-oriented gloss:** If you only count **user-facing CI-V opcodes** that wfview lists but TOML does not expose under `[commands]` (memory channel ops + memory contents + scope wave + main/sub prefix + missing `1C 04`), **X ≈ 8** substantive gaps; VFO subcodes are **not** missing, they live in `[vfo]`.

| Metric | Count | Notes |
|--------|------:|-------|
| **wfview command slots** | **134** | `Commands\size=134` |
| **Exact CI-V byte-sequence match (Z)** | **115** | Same byte tuple in merged TOML `commands` |
| **No exact tuple (X)** | **19** | Section 2 |
| **Wrong / contradictory (Y)** | **6** | Sections 3–4 |

---

## 2. Missing commands (wfview → no matching TOML bytes)

The following wfview entries have **no** merged TOML command whose byte list **equals** the `.rig` `String` (after normalizing `\xNN` escapes). CI-V bytes are shown as space-separated hex.

### 2.1 Not in `[commands]` (or only elsewhere)

| wfview # | Type | CI-V bytes (from `.rig`) | Min | Max | Notes |
|---------:|------|-------------------------|----:|----:|-------|
| 1 | Freq (TRX) | `00` | 0 | 0 | wfview internal / not a CI-V opcode in the usual sense |
| 2 | Mode (TRX) | `01` | 0 | 0 | Same |
| 9 | VFO Swap M/S | `07 B0` | 0 | 0 | Bytes in `[vfo].swap`, not duplicated under `[commands]` |
| 10 | VFO Equal MS | `07 B1` | 0 | 0 | `[vfo].equal` |
| 14 | VFO Main Select | `07 D0` | 0 | 0 | `[vfo].main_select` |
| 15 | VFO Sub Select | `07 D1` | 0 | 0 | `[vfo].sub_select` |
| 17 | Memory Mode | `08` | 1 | 101 | TOML: commented `NOT_IMPLEMENTED` |
| 18 | Memory Write | `09` | 1 | 101 | Commented |
| 19 | Memory to VFO | `0A` | 1 | 101 | Commented |
| 20 | Memory Clear | `0B` | 1 | 101 | Commented |
| 81 | Memory Contents | `1A 00` | 1 | 101 | Commented |
| 103 | AGC Time Constant | `1A 04`* | 0 | 13 | `.rig` stores `String=\\x1a04` (missing `\x` before `04`); **intended** bytes are `1A 04` — matches TOML `get_agc_time_constant` / `set_agc_time_constant` |
| 110 | CI-V Output (ANT) | `1C 04` | 0 | 1 | **No** TOML tuple `1C 04` after overrides; see section 3 |
| 114 | RX Frequency | `25` | 0 | 0 | TOML uses `25 00` / `25 01` (sub-receiver); **extension**, not same bytes as wfview row |
| 115 | RX Mode | `26` | 0 | 0 | TOML uses `26 00` / `26 01` |
| 116 | Scope Wave Data | `27 00` | 0 | 0 | **Absent** from TOML `[commands]` |
| 132 | Main/Sub Prefix | `29` | 0 | 1 | **Absent** from TOML `[commands]` |
| 133 | Command Error FA | `FA` | 0 | 0 | Protocol response token, not a profile command |
| 134 | Command OK FB | `FB` | 0 | 0 | Same |

\*Treat wfview #103 as **`1A 04`**; the literal `.rig` line is malformed (`\\x1a04`).

### 2.2 TOML-only CI-V sequences (not in wfview’s 134 `Commands` list)

These appear in `ic7610.toml` but **no** wfview `Commands\N\String` normalizes to the same byte sequence:

| TOML key(s) | Bytes | Notes |
|-------------|-------|-------|
| `get_manual_notch_width` / `set_manual_notch_width` | `16 57` | Valid for IC-7610 CI-V; wfview `.rig` does not expose this opcode in the enum |
| `get_vox_delay` / `set_vox_delay` | `1A 05 02 92` | Menu-style address; **not** listed in wfview IC-7610 command table |
| `get_selected_freq` / `get_unselected_freq` | `25 00`, `25 01` | Superset of wfview’s single-byte `25` row |
| `get_selected_mode` / `get_unselected_mode` | `26 00`, `26 01` | Superset of wfview’s single-byte `26` row |

---

## 3. Wrong CI-V bytes or conflicting definitions

| Topic | wfview (source) | `ic7610.toml` | Assessment |
|-------|-----------------|---------------|------------|
| **CI-V Output (ANT)** | #110: `1C 04` | Overrides set `get_civ_output_ant` / `set_civ_output_ant` to `1A 05 01 14` (non-`1C 04`) | **Mismatch with wfview slot #110.** May be a different menu item vs. the `1C 04` opcode; the same **key** no longer maps to wfview’s bytes. The base `[commands]` block still documents `1C 04` but **loader overwrites** with overrides. |
| **AGC Time Constant string** | `\\x1a04` (one `\x` group) | `1A 04` | wfview file typo; TOML is **correct** for intended opcode. |
| **RX Frequency / RX Mode** | `25` / `26` only | `25 00`… / `26 00`… | **Encoding choice**, not necessarily wrong vs. radio; differs from wfview’s minimal string. |

---

## 4. Parameter and metadata differences

### 4.1 `Command29` routing (`[cmd29].routes` vs wfview `Command29=true`)

wfview marks these with **`Command29=false`** while TOML **`cmd29`** includes them:

| Bytes | wfview type | TOML |
|-------|-------------|------|
| `14 0D` | Notch Filter | Listed in `cmd29` |
| `1A 06` | Data Mode Filter | Listed in `cmd29` |

wfview marks **`Command29=true`** for **`07`** (VFO Mode Select). TOML does **not** list bare `07` in `cmd29` (only sub-opcodes appear under `[vfo]` / `get_vfo`).

For **`11`** (Attenuator) and **`12`** (Antenna), wfview and TOML agree on use of command 29; TOML uses `[0x11]` / `[0x12]` (one-element arrays), which `rig_loader` normalizes to `(cmd, None)` — **semantically** aligned with wfview’s single-byte `Command29` entries.

### 4.2 Attenuator

| | wfview | TOML |
|---|--------|------|
| Range | `Min=0` `Max=45` (step 3 in `Attenuators` table: 0,3,…,45) | `[attenuator].values = [0, 3, …, 45]` |
| **Match** | ✓ | |

### 4.3 AGC mode count

| | wfview | TOML |
|---|--------|------|
| AGC Status `16 12` | `Max=1` (two states 0–1 in table) | `[agc].modes = [1, 2, 3]` with FAST/MID/SLOW labels |

Possible **model/firmware vs. wfview table** drift; worth verifying against CI-V reference, not auto-“fixing” from `Max=1` alone.

### 4.4 Filter width (opcode `1A 03`)

| | wfview | TOML |
|---|--------|------|
| Range | `Min=50` `Max=10000` | `[filters]` `width_max_hz = 9999` |
| **Difference** | Upper bound **10000** | **9999** |

### 4.5 Filter shape (`16 56`)

| | wfview | TOML |
|---|--------|------|
| | `Max=31` `Bytes=1` | Comment: `0=SHARP, 1=SOFT` |

wfview allows **0–31**; TOML documents **two** states. If the radio uses more encodings, the profile text is **incomplete** vs. wfview.

### 4.6 REF Adjust (`1A 05 00 70`)

wfview: `Max=511`. TOML lists the opcode but does not duplicate `511` in a dedicated range table (only `[commands]`).

### 4.7 Spectrum limits (`[spectrum]` vs `[Rig]`)

| Field | wfview | TOML |
|-------|--------|------|
| Seq max | `SpectrumSeqMax=15` | `seq_max = 11` |
| Amp max | `SpectrumAmpMax=200` | `amp_max = 160` |
| Data len max | `SpectrumLenMax=689` | `data_len_max = 475` |

**All three differ** from wfview’s IC-7610 rig definition.

### 4.8 Frequency ranges and BSR

wfview defines **18** `Bands\N` rows (regional variants for 40m / 80m, **Gen** 10 kHz–60 MHz, **630m** / **2200m**, etc.). TOML `[freq_ranges]` uses a **simplified** HF list plus 6m.

Notable gaps / mismatches:

- **60m:** wfview band uses **5.25–5.45 MHz** (`BSR=0` on that row); TOML uses **5.33–5.41 MHz** and **omits** `bsr_code` on that band while other bands use `0x01`…`0x0A`.
- **630m / 2200m / Gen:** present in wfview `Bands`, **absent** as named bands in TOML `freq_ranges`.
- **80m / 40m:** wfview carries **multiple regional** start/end rows per band; TOML collapses to **one** span each (e.g. 80m **3.5–4.0 MHz**, 40m **7.0–7.3 MHz**), which may not match every `Bands\N\Region` row in wfview.

BSR hex codes for the main HF bands in TOML (`0x01`…`0x0A`) **align** with wfview’s `BSR` values for 160m–6m in the single-row reading order, but **60m BSR=0** in wfview is not reflected in TOML.

### 4.9 Modes

wfview lists **10** modes (LSB, USB, AM, CW, RTTY, FM, CW-R, RTTY-R, PSK, PSK-R) with per-mode filter min/max in Hz. TOML `[modes].list` contains the **same set** (different string order). **No missing mode name** relative to wfview’s `Modes\size=10`.

### 4.10 Documentation bug in `[antenna]` comment

`ic7610.toml` says:

`# CI-V 0x1A 0x05 0x02 0x89: Antenna mode (OFF/Manual/Auto)`

In wfview, **`1A 05 00 89`** is **USB Mod Level** (command #88). **`02 89`** would be a **different** sub-address. The comment **contradicts** wfview’s menu map and the TOML `get_usb_mod_level` entry.

---

## 5. Checklist: all `1A 05` menu addresses in wfview IC-7610.rig

Four-byte sequences **`1A 05 xx yy`** appearing in wfview `Commands\N\String`:

| Sub-address (`xx yy`) | wfview type | In TOML `[commands.overrides]` |
|----------------------|-------------|----------------------------------|
| `00 32` | Quick Dual Watch | ✓ |
| `00 33` | Quick Split | ✓ |
| `00 70` | REF Adjust | ✓ |
| `00 88` | ACC1 Mod Level | ✓ |
| `00 89` | USB Mod Level | ✓ |
| `00 90` | LAN Mod Level | ✓ |
| `00 91` | Data Off Mod Input | ✓ |
| `00 92` | DATA1 Mod Input | ✓ |
| `00 93` | DATA2 Mod Input | ✓ |
| `00 94` | DATA3 Mod Input | ✓ |
| `01 12` | CIV Transceive | ✓ |
| `01 58` | System Date | ✓ |
| `01 59` | System Time | ✓ |
| `01 62` | UTC Offset | ✓ |
| `02 28` | Dash Ratio | ✓ |
| `02 90` | NB Depth | ✓ |
| `02 91` | NB Width | ✓ |

**Extra in TOML (not in wfview command enum):** `1A 05 02 92` — VOX delay (`get_vox_delay` / `set_vox_delay`).

**Not under `1A 05` in wfview #110:** `1C 04` — CI-V Output (ANT); TOML maps `get_civ_output_ant` to `1A 05 01 14` instead.

---

## 6. `KNOWN_CAPABILITIES` (`rig_loader.py`)

All feature strings used in `ic7610.toml` `[capabilities].features` are members of `KNOWN_CAPABILITIES`. wfview exposes **DTCS** / **CTCSS** tables in `.rig`; TOML does **not** enable `dtcs` / `csql` / `voice_tx` capabilities for IC-7610 — that is a **product choice**, not a loader error.

---

## 7. Recommendations

1. **Resolve `get_civ_output_ant`:** Decide whether the profile must follow wfview **`1C 04`** for “CI-V Output (ANT)” or intentionally use **`1A 05 01 14`**. If both exist on the radio, use **two distinct command keys** to avoid loader override ambiguity and document the difference.
2. **Align `cmd29` with wfview** unless you have contrary hardware evidence: remove **`14 0D`** and **`1A 06`** from `[cmd29].routes`, or document why icom-lan requires command 29 for these opcodes.
3. **Spectrum caps:** Either update `[spectrum]` to wfview’s `15` / `200` / `689` or document that UI/protocol uses reduced limits on purpose.
4. **Filter width max:** Set `width_max_hz` to **10000** if you adopt wfview’s `Filter Width` bounds, or cite CI-V manual if **9999** is intentional.
5. **Scope:** Add **`27 00`** (Scope Wave Data) to `[commands]` if spectrum/waveform features need parity with wfview.
6. **Memory:** If M4 parity is done, uncomment or implement memory command keys to match wfview **`08`–`0B`** and **`1A 00`**.
7. **Main/Sub prefix `29`:** Add command mapping if any backend path expects wfview’s “Main/Sub Prefix” opcode.
8. **Freq / BSR:** Extend `freq_ranges` with wfview’s **630m**, **2200m**, and **Gen** rows (and regional splits) if band-aware UI must match wfview; align **60m** `bsr_code` with wfview’s `BSR=0` row if BSR writes depend on it.
9. **Fix `[antenna]` comment** referencing `0x02 0x89` so it does not collide with **USB Mod Level** at `00 89`.
10. **S-meter calibration:** wfview `Meters` tables are richer than TOML’s `[[meters.s_meter.calibration]]`; consider a follow-up audit mapping **Power/SWR/ALC** rig values to human units if the web UI shows those meters.

---

*Generated for diff-only review; `ic7610.toml` was not modified as part of this audit.*
