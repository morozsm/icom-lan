# Mobile-Responsive UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make icom-lan web UI fully usable on mobile phones (portrait, <768px) while preserving desktop layout.

**Architecture:** CSS media queries + JS touch handlers in single `index.html` file. Mobile layout restructures 12-col grid to single column, replaces button rows with dropdown overlays, adds swipe-to-tune and hold-to-talk PTT. Desktop (≥768px) unchanged.

**Tech Stack:** Tailwind CSS (existing), vanilla JS, Web Audio API, getUserMedia

**Design doc:** `docs/plans/2026-03-04-mobile-ui-design.md`

**Current file:** `src/icom_lan/web/static/index.html` (2695 lines, inline HTML+CSS+JS)

---

### Task 1: Viewport Meta + Base Responsive Grid

**Files:**
- Modify: `src/icom_lan/web/static/index.html`

**Step 1: Add viewport meta tag**

In `<head>`, add:
```html
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
```

**Step 2: Add mobile CSS block**

Add `<style>` block with media queries after existing styles:
```css
@media (max-width: 767px) {
  /* Override grid to single column */
  main { grid-template-columns: 1fr !important; padding: 0.5rem !important; gap: 0.5rem !important; }
  /* Header compact */
  header { padding: 0 0.75rem !important; height: 2.5rem !important; }
  /* Hide desktop-only elements on mobile */
  .desktop-only { display: none !important; }
  /* Show mobile-only elements */
  .mobile-only { display: flex !important; }
}
/* Hide mobile elements on desktop */
.mobile-only { display: none !important; }
```

**Step 3: Restructure VFO panels**

On mobile, VFO A panel takes full width, VFO B panel hidden (replaced by MAIN/SUB toggle). Meters panel hidden (replaced by compact inline meters).

Wrap VFO B panel and meters center panel with class `desktop-only`:
- `id="vfoBPanel"` → add `desktop-only` class
- Center meters panel (col-span-2) → add `desktop-only` class

**Step 4: Verify**

Open in browser, resize to <768px. VFO A should fill width, VFO B and meters hidden.

**Step 5: Commit**

```bash
git commit -am "feat(mobile): viewport meta + base responsive grid (#102)"
```

---

### Task 2: Mobile VFO Display + MAIN/SUB Toggle

**Files:**
- Modify: `src/icom_lan/web/static/index.html`

**Step 1: Add MAIN/SUB toggle to VFO A panel**

Inside VFO A panel header, add toggle (mobile-only):
```html
<div class="mobile-only items-center gap-1">
  <button id="mobileVfoMain" class="px-2 py-0.5 rounded text-xs font-bold bg-vfo-a text-icom-dark">MAIN</button>
  <button id="mobileVfoSub" class="px-2 py-0.5 rounded text-xs font-bold bg-slate-800 text-slate-400">SUB</button>
</div>
```

**Step 2: JS for toggle**

When tapping SUB: send VFO swap command, update frequency/mode/badges display to show SUB state. When tapping MAIN: swap back. Reuse existing `selectVfo()` function.

**Step 3: Mobile frequency font size**

```css
@media (max-width: 767px) {
  #vfoAfreq { font-size: 2.5rem !important; }
  #vfoAPanel { border-left-width: 3px !important; }
  /* Hide VFO A badges row on mobile — features shown in FEAT dropdown */
  #vfoAbadges { display: none !important; }
}
```

**Step 4: Verify**

Mobile view: large freq, MAIN/SUB toggle visible, badges hidden. Tap SUB → freq changes.

**Step 5: Commit**

```bash
git commit -am "feat(mobile): VFO display + MAIN/SUB toggle (#102)"
```

---

### Task 3: Grouped Dropdown Controls (BAND, MODE, FILTER, FEATURES)

**Files:**
- Modify: `src/icom_lan/web/static/index.html`

**Step 1: Add dropdown container (mobile-only)**

After VFO panel, before spectrum section:
```html
<div class="mobile-only w-full gap-2 px-1" id="mobileControls">
  <button class="flex-1 bg-slate-800 border border-slate-700 text-xs font-bold py-2 px-2 rounded" id="mobileBandBtn">BAND: 20m</button>
  <button class="flex-1 bg-slate-800 border border-slate-700 text-xs font-bold py-2 px-2 rounded" id="mobileModeBtn">MODE: USB</button>
  <button class="flex-1 bg-slate-800 border border-slate-700 text-xs font-bold py-2 px-2 rounded" id="mobileFilBtn">FIL: 1</button>
  <button class="flex-1 bg-slate-800 border border-slate-700 text-xs font-bold py-2 px-2 rounded" id="mobileFeatBtn">FEAT</button>
</div>
```

**Step 2: Add overlay templates**

Four overlay divs (hidden by default), position fixed, dark theme:
```html
<div id="mobileOverlay" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 hidden items-center justify-center">
  <div class="bg-slate-900 border border-slate-700 rounded-xl p-4 w-72 max-h-[80vh] overflow-y-auto" id="mobileOverlayContent">
  </div>
</div>
```

Single overlay, content populated dynamically by JS.

**Step 3: JS — dropdown logic**

```javascript
function openMobileDropdown(type) {
  // Populate overlay based on type: 'band', 'mode', 'filter', 'features'
  // For band/mode/filter: list of options, tap = select + close + send command
  // For features: toggle switches, tap outside = close
}
```

Band options: `['160m','80m','60m','40m','30m','20m','17m','15m','12m','10m','6m']` mapped to CI-V band codes.

Mode options: `['USB','LSB','CW','CWR','AM','FM','RTTY']` — reuse existing mode button handler.

Filter options: `['FIL1','FIL2','FIL3']` with bandwidth labels.

Features: `['NB','NR','ATT','PRE','DSEL','IP+']` — toggle state from current badges.

**Step 4: Hide desktop controls on mobile**

```css
@media (max-width: 767px) {
  /* Hide desktop mode/filter/features button rows */
  #controlsPanel .desktop-controls { display: none !important; }
}
```

Wrap existing desktop mode buttons, filter buttons, feature buttons with `desktop-controls` class.

**Step 5: Verify**

Mobile: 4 dropdown buttons visible. Tap BAND → overlay with band list. Select → changes band. Desktop: unchanged.

**Step 6: Commit**

```bash
git commit -am "feat(mobile): grouped dropdown controls — BAND/MODE/FILTER/FEAT (#102)"
```

---

### Task 4: Compact Waterfall + Fullscreen Toggle

**Files:**
- Modify: `src/icom_lan/web/static/index.html`

**Step 1: Mobile waterfall sizing**

```css
@media (max-width: 767px) {
  #scopeSection { height: 35vh !important; min-height: 150px !important; }
  #scopeSection canvas { width: 100% !important; }
}
```

**Step 2: Fullscreen overlay**

Add fullscreen container:
```html
<div id="scopeFullscreen" class="fixed inset-0 bg-icom-dark z-40 hidden flex-col">
  <div class="absolute top-0 left-0 right-0 z-10 flex justify-between items-center p-3 bg-gradient-to-b from-black/80 to-transparent" id="scopeFullHeader">
    <span class="text-lg font-digital text-vfo-a" id="scopeFullFreq">14.074.000</span>
    <span class="text-xs text-slate-400" id="scopeFullMode">USB</span>
    <button class="text-2xl text-slate-400" id="scopeFullClose">✕</button>
  </div>
  <div class="flex-1" id="scopeFullBody">
    <!-- Canvas moves here in fullscreen -->
  </div>
</div>
```

**Step 3: JS — fullscreen toggle**

- Tap on compact waterfall → move canvas into `#scopeFullBody`, show `#scopeFullscreen`
- Resize canvas to full viewport
- ✕ or swipe down → move canvas back, hide overlay
- Auto-hide header after 3s, tap to show again
- Tap-to-tune works in fullscreen (reuse existing click handler)

**Step 4: Verify**

Mobile: compact waterfall ~35vh. Tap → fullscreen. Tap frequency on waterfall → tunes. ✕ → back to compact.

**Step 5: Commit**

```bash
git commit -am "feat(mobile): compact waterfall + fullscreen toggle (#102)"
```

---

### Task 5: Swipe-to-Tune

**Files:**
- Modify: `src/icom_lan/web/static/index.html`

**Step 1: Touch event handlers on frequency display**

```javascript
// On #vfoAfreq element (mobile only)
let tuneStartX = 0;
let tuneLastX = 0;
const TUNE_THRESHOLD = 10; // px before tuning starts

el.addEventListener('touchstart', (e) => {
  tuneStartX = tuneLastX = e.touches[0].clientX;
});

el.addEventListener('touchmove', (e) => {
  e.preventDefault(); // prevent scroll
  const x = e.touches[0].clientX;
  const dx = x - tuneLastX;
  if (Math.abs(dx) > TUNE_THRESHOLD) {
    const step = getModeStep(state.mode); // CW:100, SSB:1000, FM:5000
    const direction = dx > 0 ? 1 : -1;
    const velocity = Math.min(Math.abs(dx) / 20, 5); // 1x-5x multiplier
    const freqDelta = direction * step * Math.round(velocity);
    sendCommand('set_freq', { freq: state.freq + freqDelta });
    tuneLastX = x;
  }
});
```

**Step 2: Visual feedback**

Brief glow on frequency when tuning (CSS transition).

**Step 3: Verify**

Swipe right on frequency → freq increases. Swipe left → decreases. Fast swipe = bigger steps.

**Step 4: Commit**

```bash
git commit -am "feat(mobile): swipe-to-tune gesture (#102)"
```

---

### Task 6: Bottom Bar — Audio Fix + PTT

**Files:**
- Modify: `src/icom_lan/web/static/index.html`

**Step 1: Bottom bar HTML (mobile-only)**

```html
<div class="mobile-only fixed bottom-0 left-0 right-0 z-30 bg-slate-900/95 border-t border-slate-700 items-center gap-2 p-2" id="mobileBottomBar" style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom))">
  <button class="w-24 h-12 bg-slate-800 border border-slate-700 rounded-lg text-sm font-bold flex items-center justify-center gap-2" id="mobileAudioBtn">
    🔇 Audio
  </button>
  <button class="flex-1 h-12 bg-slate-800 border border-red-900 rounded-lg text-lg font-bold text-slate-400" id="mobilePttBtn">
    ● PTT
  </button>
</div>
```

**Step 2: Audio button — iOS fix**

```javascript
mobileAudioBtn.addEventListener('click', async () => {
  if (!audioActive) {
    // User gesture → resume AudioContext (iOS requirement)
    if (audioCtx && audioCtx.state === 'suspended') {
      await audioCtx.resume();
    }
    // Connect audio WebSocket
    startAudioRx();
    mobileAudioBtn.innerHTML = '🔊 Audio';
    mobileAudioBtn.classList.add('border-green-500', 'text-green-400');
  } else {
    stopAudioRx();
    mobileAudioBtn.innerHTML = '🔇 Audio';
    mobileAudioBtn.classList.remove('border-green-500', 'text-green-400');
  }
  audioActive = !audioActive;
});
```

**Step 3: PTT — hold-to-talk**

```javascript
let pttTimer = null;

mobilePttBtn.addEventListener('touchstart', (e) => {
  e.preventDefault();
  pttTimer = setTimeout(async () => {
    // Anti-bounce: only activate after 200ms hold
    sendCommand('ptt', { state: true });
    mobilePttBtn.classList.add('bg-red-900', 'text-red-300', 'glow-red');
    // Start mic capture if not already
    if (!micStream) {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      startMicTx(micStream);
    }
  }, 200);
});

mobilePttBtn.addEventListener('touchend', () => {
  clearTimeout(pttTimer);
  sendCommand('ptt', { state: false });
  mobilePttBtn.classList.remove('bg-red-900', 'text-red-300', 'glow-red');
});
```

**Step 4: Add padding to main content for bottom bar**

```css
@media (max-width: 767px) {
  body { padding-bottom: 4rem !important; }
}
```

**Step 5: Verify**

Mobile: bottom bar visible. Tap Audio → sound starts (iOS too). Hold PTT → red glow, TX active. Release → RX.

**Step 6: Commit**

```bash
git commit -am "feat(mobile): bottom bar — audio fix + PTT hold-to-talk (#102)"
```

---

### Task 7: Compact Meters

**Files:**
- Modify: `src/icom_lan/web/static/index.html`

**Step 1: Mobile meters section**

After dropdowns, before bottom bar:
```html
<div class="mobile-only w-full flex-col gap-1 px-2 text-xs" id="mobileMeterSection">
  <div class="flex items-center gap-2">
    <span class="text-slate-500 w-4 font-bold">S</span>
    <div class="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden flex">
      <div class="bg-meter-green transition-all duration-150" id="smeterMobile" style="width:0%"></div>
      <div class="bg-meter-red opacity-70 transition-all duration-150" id="smeterMobileRed" style="width:0%"></div>
    </div>
    <span class="text-meter-green font-bold font-digital w-8" id="smeterMobileVal">S0</span>
  </div>
  <div class="flex gap-4 text-[10px] text-slate-400">
    <span>SWR <span class="text-green-400" id="swrMobileVal">1.0</span></span>
    <span>PWR <span class="text-slate-200" id="pwrMobileVal">0W</span></span>
    <span>Vd <span class="text-cyan-400" id="vdMobileVal">0V</span></span>
  </div>
</div>
```

**Step 2: JS — sync mobile meters with existing meter updates**

In the meter update callback, also update mobile meter elements:
```javascript
// In existing meter update handler
if (window.innerWidth < 768) {
  smeterMobile.style.width = ...;
  swrMobileVal.textContent = ...;
  // etc.
}
```

**Step 3: Verify**

Mobile: compact S-meter bar + SWR/PWR/Vd inline.

**Step 4: Commit**

```bash
git commit -am "feat(mobile): compact inline meters (#102)"
```

---

### Task 8: Polish + Edge Cases

**Files:**
- Modify: `src/icom_lan/web/static/index.html`

**Step 1: iOS safe area insets**

```css
@supports (padding: max(0px)) {
  #mobileBottomBar {
    padding-bottom: max(0.5rem, env(safe-area-inset-bottom));
  }
}
html { -webkit-text-size-adjust: 100%; }
```

**Step 2: Prevent zoom on double-tap**

Already handled by `user-scalable=no` in viewport meta + `touch-action: manipulation` on buttons.

```css
@media (max-width: 767px) {
  button, [role="button"] { touch-action: manipulation; }
}
```

**Step 3: Scroll behavior**

Main content scrolls vertically, bottom bar stays fixed. Prevent horizontal scroll:
```css
@media (max-width: 767px) {
  body { overflow-x: hidden !important; }
}
```

**Step 4: Transitions for dropdowns**

Overlay: fade in 150ms, fade out 100ms. Dropdown content: slide up 200ms.

**Step 5: Test on real iPhone**

- Safari iOS: AudioContext, PTT, swipe, fullscreen waterfall
- Chrome Android: same
- Landscape: gracefully falls back to regular layout if >768px

**Step 6: Final commit**

```bash
git commit -am "feat(mobile): polish — safe areas, transitions, edge cases (#102)"
```

---

## Summary

8 tasks, each independently committable. Estimated 3-4 hours total for an agent. Desktop layout unchanged — all changes gated behind `@media (max-width: 767px)` or `.mobile-only` class.
