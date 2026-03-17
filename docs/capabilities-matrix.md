# Capabilities Matrix — Verified from CI-V Reference

Sources:
- IC-7300MK2 CI-V Reference Guide (PDF)
- IC-7610 wfview rig file (`.rig` format, verified against wfview 2.20)
- Actual hardware testing (IC-7610 firmware 1.42, IC-7300)

## Receiver Architecture

| Feature | IC-7610 | IC-7300 | TOML key |
|---------|---------|---------|----------|
| Receivers | 2 (MAIN+SUB) | 1 | `[radio] receiver_count` |
| VFO scheme | Main/Sub | A/B | `[vfo] scheme` |
| Dual watch | ✅ (hardware) | ❌ | `dual_watch` in features |
| LAN | ✅ | ❌ | `[radio] has_lan` |
| Command29 | ✅ (dual-receiver targeting) | ❌ | `[cmd29]` section |

## Antenna System

| Feature | IC-7610 | IC-7300 | Notes |
|---------|---------|---------|-------|
| TX antennas | 2 (ANT1, ANT2) | 1 | CI-V 0x12: Max=1 on 7610 (0=ANT1, 1=ANT2) |
| RX-only antenna | ✅ (0x16 0x53, 0/1) | ❌ | Separate RX antenna input |
| Antenna per-band | ✅ | N/A | Per-band antenna memory |

**Correction:** IC-7610 has **2 TX + 1 RX antenna**, not "3 antennas".

TOML:
```toml
[antenna]
tx_count = 2        # ANT1, ANT2
has_rx_ant = true   # Separate RX antenna jack
```
vs IC-7300:
```toml
[antenna]
tx_count = 1
has_rx_ant = false
```

## RF Front End

| Feature | IC-7610 | IC-7300 | CI-V | TOML |
|---------|---------|---------|------|------|
| Attenuator | 0/6/12/18 dB | 0/20 dB | 0x11 | `[attenuator] values` |
| Preamp | OFF/P1/P2 | OFF/P1/P2 | 0x16 0x02 (0/1/2) | `[preamp] values` |
| RF Gain | 0-255 | 0-255 | 0x14 0x02 | `rf_gain` in features |
| DIGI-SEL | ✅ | ❌ | 0x16 0x4E | `digisel` in features |
| IP+ | ✅ | ❌ | 0x16 0x65 | `ip_plus` in features |

**IC-7610 ATT:** wfview shows Max=45, but actual hardware values are 0/6/12/18 dB (discrete steps). The CI-V sends the dB value directly.
**IC-7300 ATT:** Only 0x00=OFF, 0x20=ON (20 dB). Binary toggle.

## DSP / Noise

| Feature | IC-7610 | IC-7300 | CI-V | Notes |
|---------|---------|---------|------|-------|
| NR on/off | 0x16 0x40 (0/1) | 0x16 0x40 (0/1) | Same | Simple ON/OFF on both |
| NR level | 0x14 0x06 (0-255) | 0x14 0x06 (0-255) | Same | Continuous 0-255 |
| NB on/off | 0x16 0x22 (0/1) | 0x16 0x22 (0/1) | Same | |
| NB level | 0x14 0x12 (0-255) | 0x14 0x12 (0-255) | Same | |
| NB depth | ❓ | 0-9 (0x1A 0x05 menu) | IC-7300 menu | |
| NB width | ❓ | 0-255 (0x1A 0x05 menu) | IC-7300 menu | |
| Auto notch | 0x16 0x41 (0/1) | 0x16 0x41 (0/1) | Same | |
| Manual notch | 0x16 0x48 (0/1) | 0x16 0x48 (0/1) | Same | |
| Notch freq | 0x14 0x0D (0-255) | 0x14 0x0D (0-255) | Same | |
| APF | 0x16 0x32 (0/1) | 0x16 0x32 (0/1) | Same | Audio Peak Filter |
| Twin Peak | 0x16 0x4F (0/1) | 0x16 0x4F (0/1) | Same | |

**NR modes:** Both IC-7610 and IC-7300 have NR as simple ON/OFF via CI-V (0x16 0x40).
The "NR1/NR2/NR3" seen in front panels is a **menu setting**, not a direct CI-V toggle.
NR level (0x14 0x06) controls the strength. For UI: show NR as ON/OFF + level slider.

## Filter

| Feature | IC-7610 | IC-7300 | CI-V | Notes |
|---------|---------|---------|------|-------|
| PBT Inner | 0x14 0x07 (0-255) | 0x14 0x07 (0-255) | Same | Center=128, ±range |
| PBT Outer | 0x14 0x08 (0-255) | 0x14 0x08 (0-255) | Same | Center=128, ±range |
| IF Shift | N/A (use PBT) | N/A (use PBT) | — | PBT acts as IF shift |
| Filter shape | 0x16 0x56 | 0x16 0x56 | Same | SOFT/SHARP |
| Filter select | 0x06 (mode+filter) | 0x06 (mode+filter) | Same | FIL1/FIL2/FIL3 |

**Note:** IC-7610 and IC-7300 both use Twin PBT (Inner+Outer), not IF Shift.
PBT range: 0-255 BCD (00 00 ~ 02 55). Center = 128 (01 28). This maps to roughly ±1200 Hz.

## RIT / XIT

| Feature | IC-7610 | IC-7300 | CI-V | Notes |
|---------|---------|---------|------|-------|
| RIT frequency | 0x21 0x00 | 0x21 0x00 | Same | ±9.999 kHz (wfview: ±999) |
| RIT on/off | 0x21 0x01 | 0x21 0x01 | Same | |
| ∂TX (XIT) | 0x21 0x02 | 0x21 0x02 | Same | Called "∂TX" in CI-V |

**Both radios have RIT AND ∂TX (XIT)**. The IC-7300 CI-V Reference confirms 0x21 0x02 (∂TX on/off).
RIT frequency range: ±9.999 kHz per wfview (Min=-999, Max=999 in 10 Hz steps).

TOML: both get `rit` and `xit` in features.

## TX Controls

| Feature | IC-7610 | IC-7300 | CI-V | Notes |
|---------|---------|---------|------|-------|
| PTT | 0x1C 0x00 (0/1) | 0x1C 0x00 (0/1) | Same | |
| Tuner/ATU | 0x1C 0x01 (0/1/2) | 0x1C 0x01 (0/1/2) | Same | 0=off, 1=on, 2=tuning |
| Mic gain | 0x14 0x0B (0-255) | 0x14 0x0B (0-255) | Same | |
| RF power | 0x14 0x0A (0-255) | 0x14 0x0A (0-255) | Same | |
| VOX on/off | 0x16 0x46 (0/1) | 0x16 0x46 (0/1) | Same | |
| VOX gain | 0x14 0x16 (0-255) | 0x14 0x16 (0-255) | Same | |
| Anti-VOX | 0x14 0x17 (0-255) | 0x14 0x17 (0-255) | Same | |
| Compressor | 0x16 0x44 (0/1) | 0x16 0x44 (0/1) | Same | |
| Comp level | 0x14 0x0E (0-255) | 0x14 0x0E (0-255) | Same | |
| Monitor | 0x16 0x45 (0/1) | 0x16 0x45 (0/1) | Same | |
| Monitor gain | 0x14 0x15 (0-255) | 0x14 0x15 (0-255) | Same | |
| Break-in | 0x16 0x47 (0/1/2) | 0x16 0x47 (0/1/2) | Same | 0=off, 1=semi, 2=full |
| Drive gain | 0x14 0x14 (0-255) | ❌ | 7610 only | |
| Split | 0x0F (0/1) | 0x0F (0/1) | Same | |
| Data mode | 0x1A 0x06 | 0x1A 0x06 | Same | |
| CW send | 0x17 | 0x17 | Same | |
| CW pitch | 0x14 0x09 (0-255) | 0x14 0x09 (0-255) | Same | Maps to 300-900 Hz |
| Key speed | 0x14 0x0C (0-255) | 0x14 0x0C (0-255) | Same | |

## Power / System

| Feature | IC-7610 | IC-7300 | CI-V | Notes |
|---------|---------|---------|------|-------|
| Power on/off | 0x18 (0x01/0x00) | 0x18 | Same | |
| Dial lock | 0x16 0x50 (0/1) | 0x16 0x50 (0/1) | Same | |
| Scan | 0x0E | 0x0E | Same | |
| Transceiver ID | 0x19 0x00 | 0x19 0x00 | Same | |

## Max TX Power

| Radio | Max Power | Notes |
|-------|-----------|-------|
| IC-7610 | 100W | HF/6m |
| IC-7300 | 100W | HF/6m |

## Capabilities Feature List — VERIFIED

### Common (both IC-7610 and IC-7300)
```
audio, scope, meters, tx, cw, attenuator, preamp, rf_gain, af_level,
squelch, nb, nr, rit, xit, tuner, split, notch, pbt, vox, compressor,
monitor, bsr, data_mode, power_control, break_in, apf, twin_peak,
dial_lock, scan, filter_shape, antenna
```

### IC-7610 only
```
dual_rx, digisel, ip_plus, dual_watch, rx_antenna, drive_gain
```

### Parameterized differences

| Parameter | IC-7610 | IC-7300 | TOML section |
|-----------|---------|---------|-------------|
| ATT values | [0, 6, 12, 18] | [0, 20] | `[attenuator]` |
| PRE values | [0, 1, 2] | [0, 1, 2] | `[preamp]` |
| AGC modes | [1, 2, 3] | [1, 2, 3] | `[agc]` |
| TX antennas | 2 | 1 | `[antenna] tx_count` |
| RX antenna | yes | no | `[antenna] has_rx_ant` |
| Max power W | 100 | 100 | `[power] max_watts` |
| NR mode | ON/OFF | ON/OFF | (both simple, no NR1/2/3 via CI-V) |
| RIT range | ±9999 Hz | ±9999 Hz | `[rit] range_hz` |
| CW pitch | 300-900 Hz | 300-900 Hz | `[cw] pitch_range` |
| Receivers | 2 | 1 | `[radio] receiver_count` |
| VFO scheme | main_sub | ab | `[vfo] scheme` |
| Command29 | yes | no | `[cmd29]` section |
