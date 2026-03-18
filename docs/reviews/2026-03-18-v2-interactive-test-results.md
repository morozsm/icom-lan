# v2 UI Interactive Test Results - 2026-03-18

## Summary
- Total tests: 28
- Passed: 25
- Known failures: 1
- New failures: 2 (#306, #307)
- Console errors: 1

## RF FRONT END
| Control | Action | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| RF Gain | set 200 | set_rf_gain { level: 200, receiver: 0 } | set_rf_gain {"level":200,"receiver":0} | PASS |
| ATT | click 6dB | set_attenuator { db: 6, receiver: 0 } | set_attenuator {"db":6,"receiver":0} | PASS |
| PRE | click P1 | set_preamp { level: 1, receiver: 0 } | set_preamp {"level":1,"receiver":0} | PASS |

## FILTER
| Control | Action | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| Width | set 1500 | set_filter_width { width: 1500, receiver: 0 } | set_filter_width {"width":1500,"receiver":0} ([screenshot](screenshots/2026-03-18-v2-filter-width.png)) | KNOWN FAIL |
> Known backend failure (#304). Console errors: [ws] command 7589c0da-543a-4120-a7b4-e890ed0ae062 failed: unknown command: 'set_filter_width'
| IF Shift | set 300 | set_pbt_inner + set_pbt_outer | set_pbt_inner {"value":293,"receiver":0}; set_pbt_outer {"value":306,"receiver":0} | PASS |

## AGC
| Control | Action | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| Mode | click FAST | set_agc { mode: 1, receiver: 0 } | set_agc {"mode":1,"receiver":0} | PASS |
| Decay | set 100 | set_agc_time_constant { value: 100, receiver: 0 } | set_agc_time_constant {"value":100,"receiver":0} | PASS |

## RIT / XIT
| Control | Action | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| RIT | toggle | set_rit_status { on: true } | set_rit_status {"on":false} | PASS |
| XIT | toggle | set_rit_tx_status { on: true } | set_rit_tx_status {"on":true} | PASS |
| Offset | set 500 | set_rit_frequency { freq: 500 } | control missing from DOM ([screenshot](screenshots/2026-03-18-v2-rit-xit-offset.png)) | FAIL |
> RitXitPanel.svelte exposes onRitOffsetChange/onXitOffsetChange props but renders no offset slider. Tracked in #306.
| Clear | click CLEAR | set_rit_frequency { freq: 0 } | set_rit_frequency {"freq":0} | PASS |

## BAND
| Control | Action | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| 20m | click 20m | set_band { band: 5 } | (none) ([screenshot](screenshots/2026-03-18-v2-band-20m.png)) | FAIL |
> BandSelector.svelte currently drops bsrCode and only forwards (bandName, defaultFreq), so makeBandHandlers() never emits set_band. Tracked in #307.

## RX AUDIO
| Control | Action | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| AF Level | set 150 | set_af_level { level: 150, receiver: 0 } | set_af_level {"level":150,"receiver":0} | PASS |

## DSP
| Control | Action | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| NR | click NR1 | set_nr { on: true, receiver: 0 } | set_nr {"on":true,"receiver":0} | PASS |
| NR Level | set 5 | set_nr_level { level: 5, receiver: 0 } | set_nr_level {"level":5,"receiver":0} | PASS |
| NB | toggle | set_nb { on: true, receiver: 0 } | set_nb {"on":true,"receiver":0} | PASS |
| NB Level | set 5 | set_nb_level { level: 5, receiver: 0 } | set_nb_level {"level":5,"receiver":0} | PASS |
| Notch | click AUTO | set_auto_notch { on: true, receiver: 0 } | set_auto_notch {"on":true,"receiver":0} | PASS |
| CW Pitch | set 700 | set_cw_pitch { value: 700 } | set_cw_pitch {"value":700} | PASS |

## TX
| Control | Action | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| Mic Gain | set 100 | set_mic_gain { level: 100 } | set_mic_gain {"level":100} | PASS |
| VOX | toggle | set_vox { on: true/false } | set_vox {"on":false} | PASS |
| COMP | toggle | set_compressor { on: true/false } | set_compressor {"on":true} | PASS |
| Comp Level | set 5 | set_compressor_level { level: 5 } | set_compressor_level {"level":5} | PASS |
| MON | toggle | set_monitor { on: true/false } | set_monitor {"on":false} | PASS |
| Mon Level | set 100 | set_monitor_gain { level: 100 } | set_monitor_gain {"level":100} | PASS |

## VFO OPS
| Control | Action | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| Copy | click M→S | vfo_equalize {} | vfo_equalize {} | PASS |
| Split | toggle | set_split { on: true/false } | set_split {"on":true} | PASS |
| Swap | click M↔S | vfo_swap {} | vfo_swap {} | PASS |

## Console Errors
- [console] [ws] command 7589c0da-543a-4120-a7b4-e890ed0ae062 failed: unknown command: 'set_filter_width'

## Notes
- Live target: `http://192.168.55.152:8080?ui=v2`
- Safety guard: PTT and ATU TUNE were intentionally excluded.
- The current frontend source sends WebSocket frames with `type: "cmd"`; the issue description still references `type: "command"`.
- Cleanup restores radio state after each interaction using direct WS commands where a UI action is not safely invertible.
- New bugs filed from this audit: #306 and #307.
