# icom-lan 0.15.0

**Release date:** April 10, 2026

## Highlights

This release delivers complete CI-V command coverage for the IC-7610, significant scope and meter
calibration fixes verified against official Icom CI-V Reference documentation, drag-and-drop panel
reorder in the Web UI, and a full type-check / lint cleanup (499 mypy errors → 0, 188 ruff errors → 0).

## What's New

### Features
- **Complete CI-V command coverage** (Epic #535) — scope settings popover, VOX/CW/DSP control
  panels, TX band edge support, memory channel manager, scan modes, TX meters, and scope toolbar
- **Drag-and-drop panel reorder** (#557) — drag handles on right sidebar panels
- **Center dead zone for RF/SQL dual slider** — prevents accidental threshold jumps
- **Yaesu CAT backend** — full `--backend yaesu-cat` support with capability-based polling
- **TLS/HTTPS for Web UI** — automatic self-signed certificates (#205)
- **Audio FFT spectrum panel** — full-color AudioSpectrumPanel with variable bandwidth
- **Expanded command coverage** — VOX, tone/TSQL, CW text/stop, memory API, system/config

### Bug Fixes
- **Meter calibration** (#536) — S-meter, RF power, SWR, ALC tables from CI-V Reference p.4
- **Scope REF BCD encode/decode** (#553) — matched IC-7610 CI-V Reference p.15
- **CENTER Type polling** (#552) — stopped overwriting scope CENTER Type on every poll cycle
- **EnableScope deadlock** — await no longer blocks all commands during initial fetch
- **Click-to-tune** — only fires on waterfall (not spectrum), uses pointerup
- **Reliable shutdown** — 3-tier signal handling, TIME_WAIT fix, proper shutdown order
- **AF scope** — bandwidth tracking, crash fix when center_freq is 0

### Code Quality
- **Type-check cleanup** — 499 mypy errors → 0 across 132 source files
- **Lint cleanup** — 188 ruff errors → 0 (noqa for re-export modules, unused import removal)
- **Mixin typing** — TYPE_CHECKING base pattern for ScopeRuntime/AudioRuntime/DualRxRuntime
- **ControlPhaseHost protocol** — expanded with missing socket/disconnect declarations

## Breaking Changes

None.

## Install / Upgrade

```bash
pip install icom-lan==0.15.0
# or upgrade:
pip install --upgrade icom-lan
```

## Commits

```
befd1e7 feat(#557): drag handles to right side + reorder in right sidebar
3df8c38 refactor: remove VOX panel from right sidebar — already in TX panel
7dc8471 fix(#552): restore CTR mode indicator at center
aaf3f9b fix: stop overwriting scope CENTER Type to Filter on every poll cycle
0af6861 fix(#536): meter calibration from IC-7610 CI-V Reference p.4
3b37e3e fix(#553): scope REF BCD encode/decode
48a42af fix(#536): meter display — dim irrelevant rows + REF fixes
c15d773 test(#554): poller deadlock regression + state consistency tests
e8252b0 feat: add center dead zone to RF/SQL dual slider
982b5f3 fix: click-to-tune only on waterfall, not spectrum area
daf8299 fix(#552): tuning indicator proportional positioning + scope REF display
6d385f3 fix: deadlock — EnableScope await blocked all commands
2e5e9cf refactor: clean spectrum/waterfall interaction architecture
9f6ae4f fix: "Port 8080 already in use" after clean shutdown (TIME_WAIT)
6bdbdbb fix: reliable shutdown — reuse_address + 3-tier signal handling
be0493c feat(#535): memory manager + scan modes (#542, #543)
4ed9de5 feat(#535): VOX/CW/DSP panels + TX band edge + speech (#540, #541)
b8bbcbd feat(#535): scope settings popover + missing polling (#538, #539)
0b1f7d3 feat(#535): TX meters + scope toolbar controls (#536, #537)
```
