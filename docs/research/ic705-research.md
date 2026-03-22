# IC-705 Backend Research

## Research Status

**Date:** 2026-03-22
**Phase:** Research (M5.1)
**Hardware:** Pending acquisition (blocker for integration testing only)

## IC-705 Overview

The **IC-705** is Icom's portable HF/VHF/UHF QRP transceiver:
- Power: 5/10W (HF/6m), 5W (2m/70cm)
- Battery powered (BP-272)
- Built-in GPS, Bluetooth, WiFi, D-STAR
- Single receiver (vs IC-7610's dual)
- Target market: Portable/field operation

## Key Differences: IC-705 vs IC-7610

### Hardware Capabilities

| Feature | IC-705 | IC-7610 | Impact |
|---------|--------|---------|--------|
| **Receivers** | 1 | 2 | No dual watch, single VFO Main |
| **CI-V Address** | 0xA4 (164) | 0x98 (152) | Profile config |
| **Command 29** | ❌ No | ✅ Yes | No extended commands (0x1D 0x29) |
| **LAN** | ✅ WiFi | ✅ Ethernet | Same protocol, different physical layer |
| **Spectrum** | Seq=11, Amp=160, Len=475 | Seq=15, Amp=200, Len=689 | Smaller scope buffer |
| **Memory** | 99 memories, 100 groups | 101 memories, 1 group | Different memory structure |
| **Power** | 5-10W QRP | 100W | Different power range |

### CI-V Protocol Differences

#### Command 0x1D (Extended Commands)
- **IC-7610:** Supports sub 0x29 (many extended features)
- **IC-705:** Does NOT support sub 0x29 (`HasCommand29=false` in wfview)
- **Impact:** Need to verify which commands use 0x1D 0x29 path and find alternatives

#### Receiver Routing
- **IC-7610:** Commands need receiver selection (Main/Sub)
- **IC-705:** Single receiver only — simpler routing
- **Impact:** Profile `receiver_count = 1`, no dual-watch capability

#### VFO Scheme
- **IC-7610:** Uses Main/Sub receiver paradigm
- **IC-705:** Traditional VFO A/B (single receiver)
- **Impact:** Different VFO selection codes and semantics

### LAN Protocol Compatibility

Based on wfview and IC-705.rig file:

✅ **Same UDP packet structure** (packettypes.h applies to all models)
✅ **Same ports:** 50001 (control), 50002 (CI-V), 50003 (audio)
✅ **Same auth flow:** Login → Token → Conninfo → Keep-alive
✅ **Same CI-V wrapping:** UDP CI-V data packets work identically

**Conclusion:** LAN backend transport/auth layer should be **100% compatible**.

### Audio Codec Support

#### Opus Codec
- **IC-7610:** ✅ Opus over LAN (confirmed in production)
- **IC-705:** ❓ **Needs verification** — likely Opus (same generation radio)
- **Action:** Check wfview audio codec negotiation for IC-705

#### Sample Rates
- IC-7610: 8/16/24 kHz Opus
- IC-705: TBD (likely same, but verify)

### Scope/Waterfall (0x27)

- **IC-7610:** Dual receiver → separate scope streams
- **IC-705:** Single receiver → single scope stream
- **Impact:** Simpler scope routing, smaller buffer (475 vs 689 max)

Command 0x27 format verification:
- [ ] Check if IC-705 uses same 0x27 packet structure
- [ ] Verify scope data format (likely identical)
- [ ] Confirm spectrum length limits (wfview: 475 max)

## Implementation Checklist

### Phase 1: Profile Definition
- [x] Create `rigs/ic705.toml` based on ic7300/ic7610 templates ✅ 2026-03-22
- [x] Set `receiver_count = 1` ✅
- [x] Remove `dual_rx`, `dual_watch`, `main_sub_tracking` capabilities ✅
- [x] Set correct CI-V address (0xA4) ✅
- [x] Set spectrum limits (seq=11, amp=160, len=475) ✅
- [x] Define frequency ranges (HF/VHF/UHF — 705 is multi-band) ✅
- [x] Define VFO scheme ("vfo_ab") with correct codes ✅
- [ ] Verify mode list with hardware (draft includes DV for D-STAR)
- [x] Command 29 not needed (single receiver) ✅

### Phase 2: LAN Backend
- [ ] Verify existing `Icom7610LanRadio` works with IC-705 (should be profile-driven)
- [ ] Test connection/auth with IC-705 hardware (when available)
- [ ] Verify CI-V command compatibility
- [ ] Test audio streaming (Opus codec)
- [ ] Verify scope/waterfall data

### Phase 3: Serial Backend
- [ ] Check IC-705 USB CI-V device name (macOS)
- [ ] Verify USB audio device names
- [ ] Test serial CI-V commands
- [ ] Verify baud rate support

### Phase 4: Integration Testing
- [ ] Hardware setup (IC-705 + LAN/USB connectivity)
- [ ] Core integration suite (connect, CI-V, audio, scope)
- [ ] CLI auto-detection test
- [ ] Web UI adaptation test
- [ ] Zero regression in IC-7610 tests

## Research Questions

### Q1: Opus Codec on IC-705 LAN?
- **Status:** Needs verification
- **Method:** Check wfview `icomudpaudio.cpp` for IC-705 codec negotiation
- **Expected:** Yes (same generation, same firmware architecture)

### Q2: Command 29 Alternatives for IC-705
- **Status:** ✅ RESOLVED
- **Finding:** Command 29 (0x1D 0x29) is a **receiver routing prefix** for IC-7610's dual receivers
- **Evidence:** All basic CI-V commands are IDENTICAL between IC-705 and IC-7610:
  - AF Gain: 0x14 0x01
  - RF Gain: 0x14 0x02
  - Squelch: 0x14 0x03
  - Attenuator: 0x11
  - Preamp: 0x16 0x02
  - S Meter: 0x15 0x01
- **Impact:** IC-705 supports same commands, just doesn't need receiver routing prefix
- **Implementation:** Set `receiver_count = 1` in profile, existing command layer will work

### Q3: VFO Codes for IC-705
- **Status:** ✅ RESOLVED
- **IC-705 VFO Commands (CI-V 0x07):**
  - VFO A Select: 0x07 0x00
  - VFO B Select: 0x07 0x01
  - VFO Equal AB: 0x07 0xA0 (copy A to B)
  - VFO Swap A/B: 0x07 0xB0
- **IC-7610 Receiver Commands (CI-V 0x07):**
  - Main Select: 0x07 0xD0
  - Sub Select: 0x07 0xD1
  - Swap M/S: 0x07 0xB0
  - Equal MS: 0x07 0xB1
  - Dual Watch On/Off: 0x07 0xC0/0xC1
- **Impact:** Need profile `vfo_scheme = "vfo_ab"` for IC-705 vs `"main_sub"` for IC-7610

### Q4: Frequency Ranges
- **Status:** ✅ DOCUMENTED
- **IC-705 Coverage (multi-band portable):**
  - HF: 0.03-29.7 MHz (RX), 1.8-29.7 MHz (TX, amateur bands)
  - 6m: 50-54 MHz (RX/TX)
  - 2m: 144-146 MHz (RX/TX)
  - 70cm: 430-450 MHz (RX), 430-440 MHz (TX, region dependent)
- **IC-7610 Coverage (HF-only):**
  - 0.03-60 MHz (RX), 1.8-54 MHz (TX, amateur bands)
- **Impact:** IC-705 has VHF/UHF bands, IC-7610 does not. Need comprehensive freq_ranges in TOML.

## Next Steps

1. ✅ Initial wfview reference extraction (this document)
2. ✅ Create `rigs/ic705.toml` profile (draft created)
3. ✅ Deep-dive Command 29 audit (resolved: not needed for single receiver)
4. ✅ Extract VFO codes from wfview (documented: 0x07 0x00/0x01/0xA0/0xB0)
5. ⏭️ Verify audio codec in wfview source (likely Opus, needs hardware confirm)
6. ✅ Document frequency ranges with band plan (HF+6m+2m+70cm defined)
7. ⏭️ Hardware verification phase (requires IC-705 acquisition)
8. ⏭️ LAN backend compatibility testing
9. ⏭️ Serial backend implementation
10. ⏭️ Integration test suite expansion

## References

- wfview `references/wfview/rigs/IC-705.rig`
- wfview `include/rigidentities.h` (model ID: 0xA4)
- IC-7610 TOML: `rigs/ic7610.toml`
- Current profiles system: `src/icom_lan/profiles.py`

---

**Research lead:** Founding Engineer
**Target milestone:** M5.1 (IC-705 Backend Implementation)
**Issue:** MSMA-14
