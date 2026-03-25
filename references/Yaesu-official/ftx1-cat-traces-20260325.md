# FTX-1 Live CAT Traces (2026-03-25)

## Setup
- Port: `/dev/cu.usbserial-01AE340D0` (CAT-1, Enhanced COM, CP2105 Dual)
- Baud: 38400, 8N1
- Radio state: 14.278 MHz USB (MAIN), 144 MHz FM (SUB), 5W, NB=7, NR=5

## Port Mapping
| Port | Description | VID:PID | Serial | Function |
|------|-------------|---------|--------|----------|
| `/dev/cu.usbserial-01AE340D0` | CP2105 Dual USB to UART | 10C4:EA70 | 01AE340D | **CAT-1** (confirmed) |
| `/dev/cu.usbserial-01AE340D1` | CP2105 Dual USB to UART | 10C4:EA70 | 01AE340D | CAT-2 (PTT/CW keying) |
| `/dev/cu.usbmodem00000000000011` | CDC USB Demonstration | 26AA:0030 | 0000000000001 | USB Audio? TBD |

## Trace Log

### Identity + Core
```
ID;        => ID0840;                        # FTX-1 confirmed
FA;        => FA014278000;                   # VFO-A: 14.278 MHz
FB;        => FB144000000;                   # VFO-B: 144.000 MHz
MD0;       => MD02;                          # Mode MAIN: USB (2)
MD1;       => MD14;                          # Mode SUB: FM (4)
FR;        => FR01;                          # Single RX mode
FT;        => FT0;                           # TX on MAIN
```

### Meters
```
SM0;       => SM0123;                        # S-meter MAIN: raw 123 (~S9)
RM1;       => RM1113000;                     # S-meter MAIN=113, SUB=000
RM2;       => RM2000000;                     # S-meter SUB=000
RM3;       => RM3000000;                     # COMP=000 (not transmitting)
RM4;       => RM4000000;                     # ALC=000
RM5;       => RM5000000;                     # PO=000
RM6;       => RM6000000;                     # SWR=000
RM7;       => RM7000000;                     # IDD=000
RM8;       => RM8208000;                     # VDD=208 (battery voltage)
```

### Audio / RF Controls
```
AG0;       => AG0032;                        # AF gain MAIN: 32/255
RG0;       => RG0255;                        # RF gain MAIN: 255 (max)
SQ0;       => SQ0064;                        # Squelch MAIN: 64/255
```

### RF Front End
```
RA0;       => RA00;                          # ATT: OFF (P1=0 fixed, P2=0)
PA0;       => PA00;                          # Preamp HF/50: IPO (0)
PA1;       => PA11;                          # Preamp VHF: ON (1)
PA2;       => PA21;                          # Preamp UHF: ON (1)
```

### DSP / Noise
```
NB0;       => ?;                             # !! NB command NOT supported
NR0;       => ?;                             # !! NR command NOT supported
NL0;       => NL0007;                        # NB Level MAIN: 7 (ON, level 7/10)
NL1;       => NL1000;                        # NB Level SUB: OFF
RL0;       => RL005;                         # NR Level MAIN: 5 (ON, level 5/10)
RL1;       => RL100;                         # NR Level SUB: OFF
BC0;       => BC01;                          # Auto Notch MAIN: ON
```

### TX / Power
```
PC;        => PC2005;                        # Power: SPA-1 (2), 5W
PL;        => PL003;                         # Processor Level: 3
PR0;       => PR01;                          # Speech Processor: OFF (P2=1)
PR1;       => PR11;                          # Parametric EQ: OFF (P2=1)
```

### CW
```
BI;        => BI0;                           # Break-in: OFF
KS;        => KS020;                         # Keyer speed: 20 WPM
KP;        => KP40;                          # Key pitch: idx 40 → 700 Hz
```

### System
```
AI;        => AI0;                           # Auto info: OFF
VX;        => VX0;                           # VOX: OFF
LK;        => LK0;                           # Lock: OFF
RI0;       => RI00000000;                    # Radio Info: all normal
```

### Clarifier (RIT/XIT)
```
CF000;     => CF00000000;                    # Clarifier MAIN: RX/TX CLAR OFF
CF001;     => CF001+0100;                    # Clarifier MAIN: freq +100 Hz
```

### Tone
```
CT0;       => CT00;                          # SQL type MAIN: CTCSS OFF
```

## Key Findings

1. **No separate NB/NR on/off commands** — use NL (level=000=OFF) and RL (level=00=OFF)
2. **PC format** `PC{head}{power:03d}` — head 1=FTX-1 (5-10W), 2=SPA-1 (5-100W)
3. **RM format** `RM{type}{main:03d}{sub:03d}` — returns both MAIN and SUB readings
4. **PA (Preamp)** P1=band (0=HF/50,1=VHF,2=UHF), NOT receiver
5. **RA (ATT)** P1=0 fixed, P2=0/1 (simple toggle, not multi-level)
6. **`?;` response** means command not recognized (NB, NR are NOT valid commands)
7. **SM vs RM**: both work for S-meter; SM{rx} is simpler, RM gives MAIN+SUB at once
8. **VDD meter (RM8)**: raw=208 — battery/supply voltage indicator
9. **CAT-2 port** does not respond to CAT commands (used for PTT/CW keying only)
