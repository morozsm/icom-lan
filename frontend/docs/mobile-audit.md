# Mobile Responsiveness Audit — icom-lan Frontend

**Date:** 2026-03-23
**Scope:** All Svelte components and CSS files in `frontend/src/`

---

## Executive Summary

The frontend has **two parallel UI systems**: a legacy v1 (`AppShell` / `DesktopLayout` / `MobileLayout`) and the current v2 (`RadioLayout` with `responsive.css`). V2 is significantly more mobile-aware with a proper CSS-grid-based responsive system. The viewport meta tag, touch event handling, and font sizing are all solid. The main gaps are a handful of fixed-width popups/dropdowns that lack mobile constraints, no explicit support for phones under ~360px, and untested landscape tablet behavior.

---

## 1. Viewport and PWA Basics

**File:** `index.html` lines 4–9

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
<meta name="theme-color" content="#0f172a" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
```

- `viewport-fit=cover` handles notched/Dynamic Island iPhones.
- Apple PWA meta tags are present.
- **No manifest.json found** — PWA installability is incomplete.
- **No service worker** — no offline support.

---

## 2. Media Queries — Full Inventory

19 `@media` rules found across the codebase.

### V2 Layout System (current)

| File | Line | Query | Purpose |
|------|------|-------|---------|
| `responsive.css` | 6 | `(min-width: 768px) and (max-width: 1024px)` | Tablet: 2-column layout, VFO stacks |
| `responsive.css` | 28 | `(max-width: 767px)` | Mobile: 1-column, sidebars hidden |
| `RadioLayout.svelte` | 357 | `(max-width: 1200px)` | Sidebar width 228px → 208px |
| `RadioLayout.svelte` | 363 | `(max-width: 1024px)` | 1-column, flex-column dock |
| `VfoHeader.svelte` | 201 | `(max-width: 1024px)` | Dual VFO stacks vertically |
| `DockMeterPanel.svelte` | 323 | `(max-width: 1200px)` | Meter panel full width |
| `FilterPanel.svelte` | 499 | `(max-width: 640px)` | Modal header stacks, 100vw − margin |
| `VfoPanel.svelte` | 322 | `(max-width: 1280px)` | Frequency font-size: 44px |
| `VfoPanel.svelte` | 328 | `(max-width: 1024px)` | Display row wraps |
| `KeyboardHandler.svelte` | 302 | `(max-width: 640px)` | Keyboard help header stacks |
| `ControlButtonDemo.svelte` | 1601 | `(max-width: 700px)` | Demo grid 2-col → 1-col |

### V1 Legacy System

| File | Line | Query | Purpose |
|------|------|-------|---------|
| `BandSelector.svelte` | 83 | `(max-width: 600px)` | Button grid 4-col → 2-col |
| `BandSelector.svelte` | 127 | `(max-width: 640px)` | Toggle button visibility |
| `VfoDigit.svelte` | 92 | `(max-width: 1200px)` | Font-size: 1.5rem |
| `VfoDigit.svelte` | 99 | `(max-width: 768px)` | Font-size: 1.25rem |
| `StepMenu.svelte` | 59 | `(max-width: 480px)` | Grid 3-col → 2-col |
| `VfoDisplay.svelte` | 277 | `(max-width: 1200px)` | Separator font: 1.5rem |
| `VfoDisplay.svelte` | 283 | `(max-width: 768px)` | Separator font: 1.25rem |
| `CapabilityMenu.svelte` | 65 | `(max-width: 480px)` | Grid 3-col → 2-col |

### Accessibility

| File | Line | Query | Purpose |
|------|------|-------|---------|
| `animations.css` | 59 | `(prefers-reduced-motion: reduce)` | Disable animations |
| `Skeleton.svelte` | 25 | `(prefers-reduced-motion: reduce)` | Disable shimmer |

---

## 3. Breakpoints Summary

| Breakpoint | System | Where used |
|------------|--------|-----------|
| 480px | V1 | `StepMenu.svelte`, `CapabilityMenu.svelte` |
| 600px | V1 | `BandSelector.svelte` |
| 640px | V2 | `FilterPanel.svelte`, `KeyboardHandler.svelte` |
| 700px | V2 demo | `ControlButtonDemo.svelte` |
| **768px** | **Both** | Primary mobile threshold (`AppShell`, `responsive.css`) |
| 1024px | V2 | Layout restructure (`RadioLayout`, `VfoHeader`) |
| 1200px | V2 | Sidebar reduction, meter panels |
| 1280px | V2 | VFO font sizing |

**Primary mobile threshold is 768px**, used consistently in v2.

---

## 4. Layout Behavior by Breakpoint

| Viewport | Layout | Sidebars | VFO | Dock |
|----------|--------|----------|-----|------|
| ≥1200px | 3-column grid, sidebars 228px | Visible | Side-by-side | Flex row |
| 1024–1199px | 3-column, sidebars 208px | Visible | Stacked vertically | Flex row |
| 768–1023px | 2-column (spectrum top, panels below) | Visible below | Stacked | Stacked |
| <768px | 1-column, full width | **Hidden** (`display:none`) | Stacked | Cards |

On mobile, sidebar content is accessed via `MobileNav.svelte` — a fixed 56px bottom tab bar.

---

## 5. Fixed Widths — Issues

### Acceptable (responsive constraints present)
- `FreqEntry.svelte` line 129: `320px` with `max-width: 95vw` ✓
- `FilterPanel.svelte` line 382: `min(560px, calc(100vw - 24px))` ✓
- `Toast.svelte` line 65: `max-width: 360px` ✓

### Problematic (no mobile constraint)

| Component | File | Line | Width | Risk |
|-----------|------|------|-------|------|
| DSP popup | `DspPanel.svelte` | 62, 430–431 | `220px` / `max-width: 240px` | Overflows on phones ≤280px |
| Theme picker | `ThemePicker.svelte` | 160 | `width: 240px` | Overflows on phones ≤280px |
| Attenuator popup | `AttenuatorControl.svelte` | 142 | `min-width: 220px` | Overflows on phones ≤240px |
| Left sidebar | `RadioLayout.svelte` | 225 | `228px` / `208px` | Hidden at <768px, fine for now |
| Mobile overlay sidebar | `MobileLayout.svelte` | 438 | `220px` | Fixed on very small screens |

**Fix pattern:** `min(220px, calc(100vw - 32px))`

---

## 6. Touch and Pointer Events

**Status: comprehensive.** The codebase uses modern `pointer*` events (not `touch*`) throughout.

| Component | Events | Long-press? |
|-----------|--------|-------------|
| `SpectrumPanel.svelte` (lines 248, 265, 294) | `onpointermove/down/up/cancel` | No |
| `PttButton.svelte` (lines 85–86) | `onpointerdown/up` | No |
| `TuningWheel.svelte` (lines 82–84) | `onpointermove/down/up` | No |
| `FeatureToggles.svelte` (lines 145–157) | `onpointerdown/up` | Yes |
| `StepSelector.svelte` (lines 46–47) | `onpointerdown/up` | Yes |
| `DspPanel.svelte` (lines 186–187, 215–216, 243–244) | `onpointerdown/up` | Yes |
| All `ValueControl` renderers | Full pointer suite | No |

`touch-action: none` is set on all interactive sliders and rotary controls.

Long-press gesture recognizer: `src/lib/gestures/gesture-recognizer.ts` line 44.

---

## 7. Button / Tap Target Sizes

`--tap-target: 44px` is defined in `tokens.css` and applied to interactive elements.

- PTT, mute, RX buttons: `min-width: 44px` ✓
- Audio controls: `min-width: 80px` ✓
- `TuningWheel.svelte` line 114: `min-width: 40px` — 4px below the 44px standard. Acceptable for a rotary control but marginal.

No buttons found below 40px.

---

## 8. Font Sizing

**Status: excellent.** `src/styles/tokens.css` lines 24–29 use CSS `clamp()`:

```css
--font-size-xs:   clamp(0.625rem, 1.5vw, 0.75rem);
--font-size-sm:   clamp(0.75rem, 2vw, 0.875rem);
--font-size-base: clamp(0.875rem, 2.5vw, 1rem);
--font-size-lg:   clamp(1rem, 3vw, 1.25rem);
--font-size-xl:   clamp(1.25rem, 4vw, 1.5rem);
--font-size-freq: clamp(1.25rem, 5vw, 1.75rem);
```

All font sizes scale fluidly. Individual components also add media-query overrides for extreme sizes.

---

## 9. Overflow Patterns

28 overflow declarations found — all appropriate:

- `overflow: hidden` (15 instances) — panels, canvas containers.
- `overflow-y: auto` / `overflow-x: hidden` (2) — sidebar scroll.
- `overflow: auto` (2) — modal internal scroll.
- Scrollbars hidden via `scrollbar-width: none` + `-webkit-scrollbar` pattern.
- No problematic `overflow: scroll` (always-shown scrollbar) found.

---

## 10. Spacing Tokens

`src/styles/tokens.css` defines fixed spacing:

```css
--space-1: 4px;   --space-2: 8px;   --space-3: 12px;
--space-4: 16px;  --space-5: 20px;  --space-6: 24px;
```

**No responsive spacing.** Gaps are constant across breakpoints. On a 320px phone, `--space-4: 16px` side padding leaves only 288px of content width — tight but workable.

---

## 11. Issues by Priority

### High

1. **Fixed-width popups** — `DspPanel`, `ThemePicker`, `AttenuatorControl` use hardcoded pixel widths with no mobile constraint. On phones ≤280px (Samsung Galaxy A series, older iPhones) these overflow the viewport.

2. **No PWA manifest** — `apple-mobile-web-app-capable` is set but no `manifest.json` exists. The app cannot be installed as a PWA on Android or show an install prompt on desktop.

### Medium

3. **No explicit <480px breakpoint in v2** — The v2 layout jumps from 768px (hide sidebars) straight to no further adaptation. Small phones (360px, 375px iPhone SE) get the same 1-column layout as a 767px tablet but with much less space.

4. **Spectrum canvas responsive behavior unknown** — `SpectrumCanvas.svelte` and `WaterfallCanvas.svelte` use `<canvas>` elements. No media-query or resize-observer handling is visible; canvas may render at wrong dimensions on rotate/resize.

5. **Landscape tablet (820–1023px) not explicitly addressed** — An iPad in landscape hits the 768–1023px 2-column breakpoint, but the layout may look odd at 1024px boundary.

### Low

6. **No service worker / offline support** — Already noted under PWA.

7. **`TuningWheel` buttons at 40px** — 4px below iOS accessibility target. Not a blocker but worth noting.

8. **Spacing tokens not responsive** — Could be compressed for mobile but functional as-is.

---

## 12. Quick Wins

| Change | File | Effort | Impact |
|--------|------|--------|--------|
| Add mobile constraint to DSP popup | `DspPanel.svelte` line 430 | 5 min | Prevents overflow on small phones |
| Add mobile constraint to ThemePicker | `ThemePicker.svelte` line 160 | 5 min | Prevents overflow |
| Add mobile constraint to Attenuator | `AttenuatorControl.svelte` line 142 | 5 min | Prevents overflow |
| Add `manifest.json` | `index.html` + new file | 30 min | Enables PWA install |
| Add 360px breakpoint in responsive.css | `responsive.css` | 20 min | Better small-phone layout |

---

## 13. What's Already Good

- Viewport meta tag: correct and complete.
- `clamp()`-based fluid typography.
- `pointer*` events throughout (works on both touch and mouse).
- `touch-action: none` on all draggable controls.
- Long-press gestures implemented.
- `--tap-target: 44px` standard applied.
- Scrollbar hiding done correctly.
- MobileNav bottom tab bar exists and is active.
- `prefers-reduced-motion` respected.
