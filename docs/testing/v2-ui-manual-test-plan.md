# v2 UI Manual Test Plan

**URL:** http://192.168.55.152:8080?ui=v2  
**Prerequisites:** IC-7610 connected, backend running  
**Duration:** 30-60 minutes

---

## Pre-Test Checklist

1. ✅ Backend running: `ps aux | grep "icom-lan.*web"`
2. ✅ Radio connected: `curl http://192.168.55.152:8080/api/v1/state | jq .main.freqHz`
3. 🌐 Open browser: http://192.168.55.152:8080?ui=v2
4. 🔍 Open DevTools: F12 → Console tab (watch for errors)
5. 🌐 Open Network tab: Monitor WebSocket connection + API calls

---

## Test Sections

### 1. Initial Load & Layout ✅

**Check:**
- [ ] Page loads without errors
- [ ] Console shows no red errors
- [ ] WebSocket connected: `WS /api/v1/ws [101 Switching Protocols]`
- [ ] Three-column layout visible: Left sidebar, Spectrum, Right sidebar
- [ ] Top VFO header visible with MAIN VFO
- [ ] Bottom dock visible with meters

**Expected:**
- Dark theme (bg `#0B0E12`)
- Cyan accents (`#00D4FF`)
- No white/blank screen
- No "Failed to fetch" errors

**If fails:** Screenshot + console errors → create bug issue

---

### 2. Top VFO Header 🎛️

#### MAIN VFO Panel

**Test:**
1. [ ] Frequency display shows current freq (e.g., "7.175")
2. [ ] Mode shows (e.g., "USB")
3. [ ] Filter shows (e.g., "FIL1")
4. [ ] S-meter bar animates with signal
5. [ ] Badges visible (NB, NR, etc. if active)

**Interact:**
- Click frequency → Does anything happen? (Pencil mockup shows edit modal)
- Click mode → Mode selector? (Or nothing expected?)

**Check Console:** Any errors when clicking?

#### SUB VFO Panel (if dual_rx)

**Test:**
- [ ] SUB VFO visible next to MAIN (IC-7610 has dual RX)
- [ ] SUB freq/mode/filter different from MAIN
- [ ] SUB S-meter works independently

#### VFO Operations

**Test buttons (between VFOs):**
1. [ ] **A↔B (Swap)** → Click → Freqs swap? Console errors?
2. [ ] **A→B (Copy)** → Click → SUB copies MAIN? Errors?
3. [ ] **SPLIT** toggle → Click → Activates? Badge appears?
4. [ ] **TX VFO** selector → Switch between MAIN/SUB

**Expected:** Commands sent via WebSocket, optimistic UI update

**Check Network tab:** See `{"type":"command","name":"vfo_swap"}` etc.

---

### 3. Left Sidebar Panels 📻

#### RF Front End

**Test sliders:**
1. [ ] **RF Gain** (0-255) → Drag → Value changes? Command sent?
2. [ ] **ATT** buttons (0/6/12/18 dB) → Click → Switches? Sends `set_attenuator`?
3. [ ] **Preamp** buttons (OFF/1/2) → Click → Works?

**Console check:** No errors? WebSocket commands visible?

#### Filter Panel ⚠️ CRITICAL TEST

**Test sliders:**
1. [ ] **Width** (50-3600 Hz) → Drag → **EXPECT ERROR** (#304 bug!)
   - Console should show: `ValueError: unhandled command: 'set_filter_width'`
   - **Document exact error message**
2. [ ] **IF Shift** (-1200 to +1200 Hz) → Drag → Works? (Maps to PBT)
3. [ ] **PBT Inner/Outer** (if visible) → Drag → Works?

**Expected:** Width slider FAILS, others work.

#### AGC Panel

**Test:**
1. [ ] **AGC Mode** buttons (FAST/MID/SLOW) → Click → Switches?
2. [ ] **AGC Gain** slider → Drag → Value changes?

#### RIT/XIT Panel

**Test:**
1. [ ] **RIT** toggle → Click → Activates? Badge in VFO?
2. [ ] **XIT** toggle → Click → Activates?
3. [ ] **Offset** slider → Drag → RIT freq changes?
4. [ ] **Clear** button → Click → Resets to 0?

#### Band Selector

**Test:**
1. [ ] Band buttons visible (160m, 80m, 40m, 30m, 20m, etc.)
2. [ ] Click "40m" → VFO jumps to 7 MHz?
3. [ ] Click "20m" → VFO jumps to 14 MHz?

**Check:** Frequency updates immediately (optimistic) then confirms

---

### 4. Right Sidebar Panels 🔊

#### RX Audio Panel

**Test:**
1. [ ] **Monitor mode** selector (local/live/mute)
   - Switch to "live" → Browser audio starts?
   - Switch to "mute" → Audio stops?
2. [ ] **AF Level** slider → Drag → Volume changes?

**Expected:** Live audio requires WebCodecs support (check browser support)

#### DSP Panel

**Test:**
1. [ ] **NR** toggle → Click → Badge appears in VFO?
2. [ ] **NR Level** slider → Drag → Works?
3. [ ] **NB** toggle → Click → Badge appears?
4. [ ] **NB Level** slider → Drag → Works?
5. [ ] **Notch** mode (off/auto/manual) → Click → Switches?
6. [ ] **CW Pitch** slider → Drag → Value changes?

#### TX Panel

**Test:**
1. [ ] **Mic Gain** slider → Drag → Value updates?
2. [ ] **ATU** toggle → Click → Activates? (Careful: tunes antenna!)
3. [ ] **ATU Tune** button → Click → Starts tuning? (Don't press if on air!)
4. [ ] **VOX** toggle → Click → Activates?
5. [ ] **COMP** toggle → Click → Activates?
6. [ ] **COMP Level** slider → Drag → Works?
7. [ ] **MON** toggle → Click → Activates?
8. [ ] **MON Level** slider → Drag → Works?

**WARNING:** ATU Tune will actually tune antenna! Only test if safe.

---

### 5. Bottom Dock Meters 📊

#### Receiver Summary Cards

**Test:**
1. [ ] **RX 1 (MAIN)** card shows:
   - Current freq
   - Mode / Filter
   - S-meter bar (animates?)
2. [ ] **RX 2 (SUB)** card shows (if dual_rx):
   - SUB freq
   - SUB mode
   - SUB S-meter

#### Meter Panel

**Test:**
1. [ ] **Needle gauge** visible (Power/SWR)
2. [ ] **Bar gauges** visible (Po/SWR/ALC)
3. [ ] **Meter source selector** → Switch S/SWR/POWER → Changes?

**During TX (if safe):**
- [ ] Press PTT → Meters switch to TX mode (Power/SWR/ALC animate)

---

### 6. Spectrum & Waterfall 📡

**Test:**
1. [ ] Spectrum displays (top of center area)
2. [ ] Waterfall scrolls below spectrum
3. [ ] Click on waterfall → VFO tunes to clicked freq?
4. [ ] Passband overlay visible?

**Expected:** Existing v1 SpectrumPanel reused, should work

---

### 7. State Updates & Optimistic UI ⚡

**Test live state sync:**

1. **Change freq via v1 UI** (open in another tab):
   - Does v2 UI update automatically?
   - Frequency display changes?
   - Spectrum re-centers?

2. **Change mode via physical radio knob** (if possible):
   - Does v2 UI update?
   - Mode label changes?

3. **Move RF Gain slider in v2**:
   - Does UI respond immediately (optimistic)?
   - Or waits for backend confirmation?

**Expected:** Optimistic updates = instant UI response, backend confirms later

---

### 8. Capability Gating (IC-7300 simulation)

**Cannot test directly without IC-7300, but check logic:**

**In browser console, run:**
```javascript
// Check dual_rx capability
console.log(window.__RADIO_CAPS__?.capabilities?.includes('dual_rx'));
```

**Expected:** `true` for IC-7610, `false` for IC-7300

**If false:** SUB VFO should be hidden

---

### 9. Responsive Layout 📱

**Test different window sizes:**

1. [ ] **Desktop (1920×1080)** → Three columns visible
2. [ ] **Tablet (1024×768)** → Layout adapts?
3. [ ] **Mobile (375×667)** → Mobile nav? (Or breaks?)

**Known issue:** #290-294 → VFO S-meter too small on 4K

**Test on 4K (if available):**
- [ ] Open on 4K display
- [ ] Is S-meter readable? Or too small?
- [ ] Does layout look balanced?

---

### 10. Keyboard Shortcuts ⌨️

**Test (if implemented):**
- [ ] **Space** → PTT (press & hold)
- [ ] **A** → Switch to VFO A
- [ ] **B** → Switch to VFO B
- [ ] **R** → RIT toggle
- [ ] **T** → Split toggle

**Expected:** May not be implemented yet (Phase 4 polish)

---

## Bug Documentation Template

**For each bug found:**

```markdown
### Bug: [Short description]

**URL:** http://192.168.55.152:8080?ui=v2
**Panel:** [e.g., FilterPanel]
**Action:** [e.g., Drag width slider]

**Expected:** [What should happen]
**Actual:** [What actually happened]

**Console Error:**
```
[Paste exact error from console]
```

**Network Error (if any):**
```
[Paste failed WebSocket command or HTTP error]
```

**Screenshot:** [Attach if visual issue]
```

---

## Success Criteria

**v2 UI is "working" if:**
- ✅ No console errors (except known #304)
- ✅ All sliders send commands
- ✅ State updates propagate to UI
- ✅ Optimistic updates feel instant
- ✅ VFO freq/mode/meter display correctly
- ⚠️ Known issue: Filter width slider fails (#304)
- ⚠️ Known issue: VFO S-meter small on 4K (#290-294)

**v2 UI needs work if:**
- ❌ Multiple controls throw errors
- ❌ State updates don't propagate
- ❌ UI feels laggy/broken
- ❌ Layout breaks on mobile

---

## After Testing

**Create issues for:**
1. Each unique console error (not #304)
2. Controls that don't send commands
3. Visual glitches (layout, colors, sizing)
4. State sync problems

**Update audit report:**
- `docs/reviews/2026-03-18-v2-ui-audit.md`
- Add "Runtime Testing Results" section
- List confirmed bugs vs false positives

**Comment on Epic #289:**
- Manual test complete ✅
- X bugs found
- Y bugs are blockers
- Z bugs are polish

---

## Quick Start

```bash
# 1. Ensure backend running
ps aux | grep "icom-lan.*web"

# 2. Check radio connected
curl -s http://192.168.55.152:8080/api/v1/state | jq '.main.freqHz, .connected'

# 3. Open browser
open "http://192.168.55.152:8080?ui=v2"

# 4. Open DevTools
# macOS: Cmd+Opt+I
# Windows: F12

# 5. Start testing!
```

Good luck! 🚀
