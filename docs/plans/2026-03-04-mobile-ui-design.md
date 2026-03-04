# Mobile-Responsive UI Design — Issue #102

**Date:** 2026-03-04
**Author:** Жора + Сергей
**Status:** Approved

## Summary

Responsive mobile layout for icom-lan web UI. Single HTML file, media queries at `<768px`. Desktop layout unchanged. Portrait-first, one-handed operation.

## Requirements (from brainstorming)

- All functions available on mobile (freq, mode, spectrum, meters, PTT, audio)
- Portrait (vertical) primary orientation
- Compact waterfall (~30% screen) with fullscreen toggle
- Swipe-to-tune + tap-to-tune on waterfall
- RX audio + TX via phone mic (PTT hold-to-talk)
- PWA deferred to later phase
- One VFO visible at a time (MAIN/SUB toggle)

## Mobile Layout (<768px, portrait)

```
┌─────────────────────────┐
│ HEADER: IC-7610 · 🟢 · UTC │
├─────────────────────────┤
│ VFO A        14.074.000 │  swipe L/R = tune
│ USB · FIL1    [MAIN|sub]│  tap = switch VFO
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │   SPECTRUM          │ │  ~30% screen
│ │   ═══════════════   │ │  tap → fullscreen
│ │   WATERFALL         │ │  tap-to-tune
│ └─────────────────────┘ │
├─────────────────────────┤
│ [BAND▾] [MODE▾] [FIL▾] [FEAT▾] │
│                         │
│  S ████████░░░░  S7     │  compact S-meter
│  SWR 1.0  PWR 50W      │  meters inline
├─────────────────────────┤
│ 🔊 Audio  │ [===PTT===] │  fixed bottom bar
│  on/off   │  hold-to-TX │  height: 56px
└─────────────────────────┘
```

## Grouped Controls (dropdowns)

Four dropdown buttons in a row:

### BAND dropdown
- Shows current band: `BAND: 20m▾`
- Options: 160m, 80m, 60m, 40m, 30m, 20m, 17m, 15m, 12m, 10m, 6m
- Current band highlighted
- Tap = select + close

### MODE dropdown
- Shows current mode: `MODE: USB▾`
- Options: USB, LSB, CW, CWR, AM, FM, RTTY
- Tap = select + close

### FILTER dropdown
- Shows current filter: `FIL: 1▾`
- Options: FIL1, FIL2, FIL3 with bandwidth shown (e.g. "FIL1 (300-3000)")
- Tap = select + close

### FEATURES dropdown
- Shows active count: `FEAT (2)▾`
- Options: NB, NR, ATT, PRE, DSEL, IP+
- Toggle switches — on/off without closing dropdown
- Tap outside = close

### Implementation
- Custom overlays (not `<select>`), dark theme consistent
- `position: fixed`, backdrop blur, tap outside = close
- One dropdown open at a time

## VFO Tuning (touch)

### Swipe-to-tune
- Horizontal swipe on frequency display = VFO knob
- Swipe right → freq up, swipe left → freq down
- Velocity-dependent: slow swipe = 100 Hz step, fast = 1-5 kHz
- Step depends on mode (CW: 100Hz, SSB: 1kHz, FM: 5kHz)

### Tap-to-tune
- Tap on waterfall = set frequency (existing desktop behavior)
- Works in both compact and fullscreen waterfall

### VFO A/B toggle
```
[MAIN | sub ]  ← tap "sub" → shows SUB frequency
[main | SUB ]  ← active highlighted (cyan/orange)
```
- Switching updates: frequency, mode, filter, feature badges
- Internally = VFO Swap (0x07 0xB0)

## Audio + PTT

### Audio button (bottom bar, left)
- First tap = `AudioContext.resume()` + send `audio_start` via WS
- Solves iOS autoplay policy (requires user gesture)
- Toggle: tap again = mute/stop
- Visual: gray = off, green glow = on

### PTT button (bottom bar, right, ~60% width)
- **Hold-to-talk**: touchstart → PTT ON, touchend → PTT OFF
- Phone mic → WebSocket → icom-lan → radio TX
- `getUserMedia()` for microphone (browser permission on first use)
- Anti-bounce: tap < 200ms ignored
- Visual: gray in RX, red glow during TX

### Bottom bar
- Fixed at bottom, always visible over content
- Height: 56px (iOS safe area aware)
- `padding-bottom: env(safe-area-inset-bottom)` for iPhone notch

## Fullscreen Waterfall

### Activation
- Tap on compact waterfall → fullscreen overlay

### Layout
```
┌─────────────────────────┐
│ 14.074.000   USB   [✕]  │  semi-transparent header
├─────────────────────────┤
│                         │
│       SPECTRUM          │  100% screen
│   ═══════════════════   │
│       WATERFALL         │
│                         │
├─────────────────────────┤
│ 🔊 Audio │    ● PTT     │  bottom bar stays
└─────────────────────────┘
```

- Tap on waterfall = tune
- Frequency + mode overlay: semi-transparent, auto-hide after 3s, tap to show
- Close: ✕ button or swipe down
- Bottom bar (Audio + PTT) stays on top
- DX spots overlay works as on desktop

## Desktop (≥768px)

No changes. Current layout preserved. Media queries only affect `<768px`.

## Technical Approach

- **Single file**: all changes in `index.html` (inline CSS + JS)
- **Tailwind**: use existing Tailwind classes + `@media (max-width: 767px)` custom CSS
- **No framework**: vanilla JS, consistent with current codebase
- **Canvas resize**: spectrum/waterfall canvas adapts to container width
- **Touch events**: `touchstart`/`touchmove`/`touchend` for swipe-tune and PTT

## Implementation Phases

1. **Viewport + base responsive** — meta tag, CSS grid restructure for mobile
2. **VFO display** — single VFO, MAIN/SUB toggle, large frequency
3. **Grouped dropdowns** — BAND, MODE, FILTER, FEATURES
4. **Compact waterfall** — resize canvas, tap-to-fullscreen
5. **Fullscreen waterfall** — overlay, auto-hide header
6. **Swipe-to-tune** — touch gesture on frequency display
7. **Bottom bar + Audio fix** — fixed bar, iOS AudioContext, Start Audio button
8. **PTT hold-to-talk** — getUserMedia, touchstart/end, anti-bounce
9. **Meters compact** — inline S-meter, SWR/PWR row
10. **Polish** — safe-area insets, transitions, edge cases
