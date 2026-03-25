# FTX-1 CAT Command Reference (extracted from FTX-1_CAT_OM_ENG_2508-C.pdf)

## Communication Parameters
- Baud rates: 4800 / 9600 / 19200 / **38400** (default CAT-1) / 115200
- Data bits: 8, Parity: None, Stop bits: 1 (default)
- Terminator: `;`
- Three ports: CAT-1 (USB Enhanced COM), CAT-2 (USB Standard COM), CAT-3 (UART mini-DIN)

## Command Format
- 2 ASCII letters + parameters (fixed digit fields) + `;`
- SET: `FAxxxxxxxxx;` (command + params + `;`)
- READ: `FA;` (command + `;`)
- ANSWER: `FAxxxxxxxxx;` (same as SET format)

## Command List

### Core Frequency/Mode/VFO
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| FA | Freq MAIN | `FA{freq:09d};` | `FA;` | freq: 000030000-470000000 Hz |
| FB | Freq SUB | `FB{freq:09d};` | `FB;` | freq: 000030000-470000000 Hz |
| MD | Mode | `MD{rx}{mode};` | `MD{rx};` | rx: 0=MAIN,1=SUB; mode: 1=LSB,2=USB,3=CW-U,4=FM,5=AM,6=RTTY-L,7=CW-L,8=DATA-L,9=RTTY-U,A=DATA-FM,B=FM-N,C=DATA-U,D=AM-N,E=PSK,F=DATA-FM-N,H=C4FM-DN,I=C4FM-VW |
| FR | Function RX | `FR{mode:02d};` | `FR;` | 00=Dual RX, 01=Single RX |
| FT | Function TX | `FT{vfo};` | `FT;` | 0=MAIN TX, 1=SUB TX |
| VS | VFO Select | `VS{vfo};` | `VS;` | 0=MAIN, 1=SUB |
| AB | MAIN→SUB copy | `AB;` | — | |
| BA | SUB→MAIN copy | `BA;` | — | |
| BS | Band Select | `BS{rx}{band:02d};` | `BS{rx};` | rx: 0=MAIN,1=SUB; band: 00=1.8M..14=430M |
| BD | Band Down | `BD{rx};` | — | rx: 0=MAIN,1=SUB |
| BU | Band Up | `BU{rx};` | — | rx: 0=MAIN,1=SUB |

### PTT / TX
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| TX | Transmit | `TX{mode};` | `TX;` | 0=OFF(RX), 1=ON(TX), 2=Tuner TX |
| PC | RF Power | `PC{pwr:03d};` | `PC;` | 000-100 (watts percentage) |
| MG | Mic Gain | `MG{gain:03d};` | `MG;` | 000-100 |

### Meters
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| SM | S-Meter | — | `SM{rx};` | rx: 0=MAIN,1=SUB; answer: `SM{rx}{raw:03d};` raw 000-255 |
| RM | Various Meters | — | `RM{meter};` | meter: 1=COMP,2=ALC,3=PO,4=SWR,5=IDD,6=VDD; answer: `RM{meter}{raw:03d};` raw 000-255 |

### Audio / AF / RF
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| AG | AF Gain | `AG{rx}{gain:03d};` | `AG{rx};` | rx: 0=MAIN,1=SUB; gain: 000-255 |
| RG | RF Gain | `RG{rx}{gain:03d};` | `RG{rx};` | rx: 0=MAIN,1=SUB; gain: 000-255 |
| SQ | Squelch | `SQ{rx}{level:03d};` | `SQ{rx};` | rx: 0=MAIN,1=SUB; level: 000-255 |
| ML | Monitor Level | `ML{level:03d};` | `ML;` | 000-255 |

### RF Front End
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| RA | Attenuator | `RA{rx}{att:02d};` | `RA{rx};` | rx: 0=MAIN,1=SUB; att: 00=OFF,01-03=levels |
| PA | Preamp | `PA{rx}{pre};` | `PA{rx};` | rx: 0=MAIN,1=SUB; pre: 0=OFF,1=IPO,2=AMP1,3=AMP2 |

### DSP / Noise
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| NB | Noise Blanker | `NB{rx}{state};` | `NB{rx};` | rx: 0=MAIN,1=SUB; state: 0=OFF,1=ON |
| NL | NB Level | `NL{rx}{level:03d};` | `NL{rx};` | rx: 0=MAIN,1=SUB; level: 000-010 |
| NR | Noise Reduction | `NR{rx}{state};` | `NR{rx};` | rx: 0=MAIN,1=SUB; state: 0=OFF,1=ON |
| RL | NR Level | `RL{rx}{level:02d};` | `RL{rx};` | rx: 0=MAIN,1=SUB; level: 01-15 |
| BC | Auto Notch (DNF) | `BC{rx}{state};` | `BC{rx};` | rx: 0=MAIN,1=SUB; state: 0=OFF,1=ON |
| BP | Manual Notch | `BP{rx}{func}{val:03d};` | `BP{rx}{func};` | rx: 0/1; func: 0=ON/OFF(000/001),1=freq(001-320 = x10Hz) |

### Filter / IF
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| SH | IF Width/Shift | `SH{rx}{func}{val:02d};` | `SH{rx}{func};` | rx: 0/1; func: 0=Width,1=Shift; val: mode-dependent table |
| IS | IF Shift | `IS{rx}0{sign}{offset:04d};` | `IS{rx};` | rx: 0/1; sign: +/-; offset: 0000-1200 Hz (20Hz steps) |
| NA | Narrow | `NA{rx}{state};` | `NA{rx};` | rx: 0/1; state: 0=OFF,1=ON |

### AGC
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| GT | AGC | `GT{rx}{mode};` | `GT{rx};` | rx: 0/1; mode: 0=OFF,1=FAST,2=MID,3=SLOW,4=AUTO-F,5=AUTO-M,6=AUTO-S |

### CW
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| KS | Keyer Speed | `KS{wpm:03d};` | `KS;` | 004-060 WPM |
| KP | Key Pitch | `KP{idx:02d};` | `KP;` | 00-75 → 300-1050 Hz (10Hz steps) |
| BI | Break-in | `BI{state};` | `BI;` | 0=OFF,1=ON |
| CS | CW Spot | `CS{state};` | `CS;` | 0=OFF,1=ON |
| KY | CW Keying | `KY{type}{mem};` | — | type: 0=TEXT,1=MSG; mem: 0=STOP,1-5=play |
| SD | CW Break-in Delay | `SD{delay:04d};` | `SD;` | 0030-3000 ms |

### RIT / Clarifier
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| CF | Clarifier | `CF{rx}0{func}{params};` | `CF{rx}0{func};` | func=0: P4=rxClar(0/1),P5=txClar(0/1),P6-P8=000; func=1: sign(+/-)+offset(0000-9999 Hz) |

### Split / Dual
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| ST | Split | `ST{state};` | `ST;` | 0=OFF,1=ON (likely — confirm from later pages) |

### Tone / TSQL
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| CT | SQL Type | `CT{rx}{type};` | `CT{rx};` | rx: 0/1; type: 0=OFF,1=CTCSS ENC,2=CTCSS ENC+DEC,3=DCS,4=PR FREQ,5=REV TONE |
| CN | CTCSS/DCS Number | `CN{rx}{type}{num:03d};` | `CN{rx}{type};` | rx: 0/1; type: 0=CTCSS,1=DCS; num: tone/code index |

### Tuner
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| AC | Antenna Tuner | `AC{p1}{p2}{p3};` | `AC;` | p1: 0=int,1=ext; p2: 0=ATU,2=ATAS; p3: 0=OFF,1=ON,2=tune(start),3=tuneStart |

### System
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| ID | Identification | — | `ID;` | answer: `ID0840;` (fixed FTX-1 ID) |
| AI | Auto Info | `AI{state};` | `AI;` | 0=OFF,1=ON |
| PS | Power Switch | `PS{state};` | `PS;` | 0=OFF,1=ON |
| LK | Lock | `LK{state};` | `LK;` | 0=OFF,1=ON |
| IF | Information | — | `IF;` | Multi-field VFO status packet |
| DA | Dimmer | `DA00{tft_c:02d}{tft_b:02d}{led:02d};` | `DA;` | contrast/brightness/LED: 00-20 each |

### Contour / APF
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| CO | Contour/APF | `CO{rx}{func}{val:04d};` | `CO{rx}{func};` | func: 0=contour on/off, 1=contour freq(10-3200Hz), 2=APF on/off, 3=APF freq |

### Misc
| Cmd | Description | SET format | READ format | Parameters |
|-----|-------------|-----------|-------------|------------|
| AO | AMC Output Level | `AO{level:03d};` | `AO;` | 001-100 |
| DN | Mic DOWN | `DN;` | — | |
| UP | Mic UP | `UP;` | — | |
| RC | Clarifier Clear | `RC;` | — | |
| VX | VOX | `VX{state};` | `VX;` | 0=OFF,1=ON |
| PL | Speech Processor Level | `PL{p1:03d}{p2:03d};` | `PL;` | p1: drive gain 000-100, p2: processor level 000-100 |
| PR | Speech Processor | `PR{state};` | `PR;` | 0=OFF,1=ON |
| MC | Memory Channel | `MC{rx}{ch:05d};` | `MC{rx};` | rx: 0/1; ch: memory channel number |
| MR | Memory Read | complex multi-field | `MR{params};` | Memory channel data |
| SC | Scan | `SC{mode};` | `SC;` | 0=OFF,1=UP,2=DOWN |
| TS | ToneSQL | `TS{rx}{state};` | `TS{rx};` | rx: 0/1; state: 0=OFF,1=ON |

## Notes
- FTX-1 ID: `0840`
- Dual receiver (MAIN/SUB) — most commands take P1 = 0 (MAIN) or 1 (SUB)
- FTX-1 uses RIT/XIT via CF (Clarifier) command, NOT separate RT/XT commands
- Mode codes are hex characters (A-I for extended modes like DATA-FM, C4FM)
- Frequency is always 9 digits in Hz
- Source: FTX-1_CAT_OM_ENG_2508-C.pdf (Yaesu official)
