# Mobile UI Roadmap — icom-lan Frontend

**Date:** 2026-03-23
**Based on:** `mobile-audit.md`

---

## Current State

The v2 layout system has a solid foundation: correct viewport meta, fluid typography, pointer events, touch targets, and a MobileNav bottom tab bar. The three main gaps are: (1) a handful of fixed-width popups that need mobile constraints, (2) incomplete PWA setup, and (3) no explicit small-phone (<480px) breakpoint.

---

## Phase 1 — Responsive Basics (1–2 days)

Fix the issues that break the layout on real mobile devices. No new features, just correctness.

### 1.1 Fix fixed-width popups (est. 30 min)

Three popups hardcode pixel widths with no mobile fallback. Replace with `min()`:

| File | Line | Current | Change to |
|------|------|---------|-----------|
| `DspPanel.svelte` | 430–431 | `width: 220px; max-width: 240px` | `width: min(220px, calc(100vw - 32px))` |
| `ThemePicker.svelte` | 160 | `width: 240px` | `width: min(240px, calc(100vw - 32px))` |
| `AttenuatorControl.svelte` | 142 | `min-width: 220px` | `min-width: min(220px, calc(100vw - 32px))` |

Also add `right: 0` or `left: 0` anchor logic so the popup doesn't clip the viewport edge.

### 1.2 Add 360px breakpoint in responsive.css (est. 20 min)

The smallest explicitly handled width is 768px (hide sidebars). Small phones (360–479px) get the 1-column layout but no further compression. Add to `responsive.css`:

```css
@media (max-width: 479px) {
  /* Reduce padding inside panels */
  .panel { padding: var(--space-2); }
  /* Stack VFO controls tighter */
  .vfo-row { gap: var(--space-1); }
  /* Frequency font — prevent overflow */
  .freq-display { font-size: clamp(1rem, 8vw, 1.4rem); }
}
```

Specific selectors to confirm after reading `RadioLayout.svelte` and `VfoPanel.svelte` grid class names.

### 1.3 Verify spectrum canvas resize handling (est. 1–2h)

Read `SpectrumCanvas.svelte` and `WaterfallCanvas.svelte`. Check whether a `ResizeObserver` or `window.onresize` handler updates canvas `width`/`height` attributes when the viewport changes. If not, add one — raw `<canvas>` does not auto-scale with CSS.

**Files to check:**
- `src/components-v2/spectrum/SpectrumCanvas.svelte`
- `src/components-v2/spectrum/WaterfallCanvas.svelte`

### 1.4 Test on real devices / emulator (est. 2–4h)

Using Chrome DevTools device emulation (or Playwright with mobile viewport):
- iPhone SE (375×667, portrait and landscape)
- iPhone 14 Pro (393×852, portrait)
- Samsung Galaxy S21 (360×800, portrait)
- iPad (768×1024, portrait and landscape)
- iPad Pro landscape (1366×1024)

Record failures, add regression tests or screenshots.

---

## Phase 2 — Touch Optimization (2–3 days)

Improve the experience for fingers specifically. Most of the groundwork (pointer events, long-press) is already done.

### 2.1 Swipe gestures for frequency tuning (est. 4–6h)

**Opportunity:** On mobile, the tuning wheel (`TuningWheel.svelte`) is small. A swipe-up/down gesture anywhere on the frequency display would be more ergonomic.

**Implementation:**
1. Add a swipe gesture handler in `src/lib/gestures/gesture-recognizer.ts` (already has long-press logic at line 44).
2. Wire it to `VfoPanel.svelte` — vertical swipe on the frequency area triggers `tuneStep`.
3. Swipe distance maps to step size (small swipe = 1 step, large swipe = 10 steps).
4. Expose sensitivity as a user setting.

**Files to modify:**
- `src/lib/gestures/gesture-recognizer.ts` — add swipe recognizer
- `src/components-v2/vfo/VfoPanel.svelte` — attach gesture to frequency area
- `src/components-v2/layout/MobileNav.svelte` — document gesture hint

### 2.2 Band switching via swipe (est. 2–3h)

**Opportunity:** Swipe left/right on the spectrum or band area to cycle bands.

Simpler than tuning swipe — just a left/right direction check on `SpectrumPanel.svelte`'s existing pointer handlers (lines 248, 265, 294). Threshold: >50px horizontal with <30px vertical drift.

### 2.3 Increase TuningWheel tap targets (est. 30 min)

`TuningWheel.svelte` line 114 sets `min-width: 40px`. Bump to `44px` to meet iOS standard. Also increase the clickable area via `padding` if needed without changing visual size.

### 2.4 Bottom sheet for DSP controls (est. 4–8h)

On mobile, DSP/filter popups (`DspPanel.svelte`, `FilterPanel.svelte`) open as centered overlays. A bottom sheet (slides up from bottom edge) is more ergonomic on phones — easier to reach with thumbs.

**Implementation sketch:**
- Add a `BottomSheet.svelte` component that wraps existing modal content.
- `AppShell.svelte` / `RadioLayout.svelte` decides at <768px to render modal slots as bottom sheets instead of centered overlays.
- Drag-to-dismiss via pointer events on the drag handle.
- Existing `FilterPanel.svelte` and `DspPanel.svelte` stay unchanged — just swap the container.

### 2.5 Haptic feedback (est. 2h)

Use `navigator.vibrate()` for:
- PTT press/release (short pulse, 10ms)
- Band change (double pulse, 10ms + 10ms)
- Tuning step (very short, 5ms — optional, can be noisy)

Add to a `haptics.ts` utility so it can be disabled in settings. Check `navigator.vibrate` availability (not available on iOS Safari — guard with feature detection).

---

## Phase 3 — PWA (1–2 days)

The PWA meta tags are present; the app is not yet installable.

### 3.1 Add manifest.json (est. 1–2h)

Create `public/manifest.json`:

```json
{
  "name": "icom-lan Radio Control",
  "short_name": "icom-lan",
  "description": "Remote control for Icom IC-7610 over LAN",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#0f172a",
  "orientation": "any",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/apple-touch-icon.png", "sizes": "180x180", "type": "image/png" }
  ]
}
```

Add `<link rel="manifest" href="/manifest.json">` to `index.html`.

**Icons needed:** 192×192 and 512×512 PNG. The `apple-touch-icon.png` may already exist (referenced in index.html but not confirmed present).

### 3.2 Add service worker (est. 4–6h)

Use `vite-plugin-pwa` (Workbox under the hood):

```bash
npm install -D vite-plugin-pwa
```

Register in `vite.config.ts`:

```ts
import { VitePWA } from 'vite-plugin-pwa'

// In plugins array:
VitePWA({
  registerType: 'autoUpdate',
  workbox: {
    // Cache app shell and static assets
    globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
    // Don't cache WebSocket/UDP traffic (can't anyway)
    navigateFallback: '/index.html',
  }
})
```

**Caching strategy:**
- App shell (HTML, JS, CSS): cache-first.
- Static assets (icons, fonts): cache-first.
- API/WebSocket calls: network-only (no offline radio control).
- Show an "offline" banner if WebSocket connection fails.

### 3.3 Install prompt (est. 1h)

The browser fires `beforeinstallprompt`. Capture it in `App.svelte` and show a subtle "Add to home screen" button in `MobileNav.svelte` when available.

```ts
let deferredPrompt: BeforeInstallPromptEvent | null = null;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e as BeforeInstallPromptEvent;
});
```

Don't show on iOS (no `beforeinstallprompt` support — show a manual instructions tooltip instead).

### 3.4 App icons (est. 30 min)

Generate icon set from existing logo/brand assets:
- `icon-192.png` — 192×192
- `icon-512.png` — 512×512
- `apple-touch-icon.png` — 180×180 (may already exist)
- `favicon.ico` — 32×32 (may already exist)

---

## Phase 4 — Mobile-First Features (optional, future)

These are non-trivial features that would make the app genuinely useful as a mobile-first radio control panel. Implement only after Phase 1–3 is solid.

### 4.1 Simplified mobile mode (est. 1–2 weeks)

A stripped-down layout optimized for one-handed phone use:

- Large frequency display (full screen width)
- Band/mode selectors as large tap targets
- PTT as a prominent hold button
- S-meter as a compact strip
- All advanced controls hidden behind a "More" menu

**Implementation:** New route or view mode in `AppShell.svelte`. New set of simplified components that use the same store/API layer.

### 4.2 Gesture-based tuning (est. 1 week)

Beyond the swipe tuning from Phase 2:

- **Pinch to zoom** spectrum display (change span)
- **Drag** on spectrum to click-tune (already partially implemented via passband drag)
- **Two-finger rotate** for RIT offset

### 4.3 Voice control (est. 2–3 weeks, experimental)

Use `SpeechRecognition` API:

- "Go to 14.074 MHz" → frequency change
- "USB mode" → mode change
- "Band up / band down" → band change

Requires careful command parser. High power consumption. iOS Safari support is limited (requires user gesture to start).

### 4.4 Push notifications for DX spots (est. 1–2 weeks)

Use Push API + service worker:

- Subscribe to DX cluster feed on the server
- Server sends push notification when interesting spots appear
- Notification includes frequency — tap to tune

Requires server-side work (cluster integration + push subscription management).

---

## Effort Summary

| Phase | Est. Time | Blocking? |
|-------|-----------|-----------|
| Phase 1 — Responsive Basics | 1–2 days | Yes — fix real bugs first |
| Phase 2 — Touch Optimization | 2–3 days | No — improvement |
| Phase 3 — PWA | 1–2 days | No — improvement |
| Phase 4 — Mobile-First Features | 4–10 weeks | No — future work |

Start with Phase 1. It has the highest impact-to-effort ratio and fixes real breakage on small phones.
