# Frontend Performance Audit

**Date:** 2026-03-23
**Audited commit:** `fa19804`
**Build tool:** Vite 7.3.1 + `@sveltejs/vite-plugin-svelte` 6.2.4
**Framework:** Svelte 5.54.0

---

## 1. Bundle Analysis

### 1.1 Output Sizes

| Asset | Raw | Gzip | Brotli |
|---|---|---|---|
| `index.js` | 357 KB | 107 KB | 90 KB |
| `index.css` | 279 KB | 40 KB | 30 KB |
| `index.html` | 0.9 KB | — | — |
| **Total transfer (gzip)** | | **~147 KB** | |
| **Total transfer (brotli)** | | | **~120 KB** |

The totals are reasonable for a real-time radio control application that ships two complete UI generations (v1 and v2) in one bundle. However, several specific areas inflate each asset unnecessarily.

### 1.2 Single JS Chunk

There is no code splitting. Everything — v1 components, v2 components, all themes, audio engine, spectrum renderers — compiles into one `index.js`. Vite's default `build.rollupOptions.output.manualChunks` is not configured. This means:

- First load must parse the entire ~357 KB script before any interaction.
- v1 and v2 UIs are both in the bundle even though only one is active at a time.
- The `ControlButtonDemo` demo component (`?demo=control-buttons`) is shipped to all users.

### 1.3 CSS Bundle (279 KB raw)

The CSS bundle is unusually large. Known contributors:

- **19 theme CSS files** bundled in full. All themes ship to all users, only one is ever active. Each theme override file averages ~215 lines × 19 = ~4,100 lines of theme tokens baked into the stylesheet.
- **`tokens.css`** declares ~277 CSS custom-property tokens (v2 design system) plus the legacy token set in `styles/tokens.css`.
- **`button-tokens.css`** contains 14 `color-mix()` computed custom properties — these cannot be evaluated at compile time and must be resolved per-element at paint time.
- Svelte scopes component styles via data attributes, so selector specificity is low and well-managed.

### 1.4 lucide-svelte — 30 MB Source, Minimal Runtime Cost

`lucide-svelte` installs 30 MB of source (7,310 icon files), but **only 9 icons** are actually used:

```
// StatusBar.svelte
Radio, Cable, Activity, Volume2, ArrowDownUp, Power, Unplug, Palette

// ThemePicker.svelte
Palette
```

Vite tree-shakes these correctly — only the 9 used icons appear in the bundle. The 30 MB install size is irrelevant at runtime but is a developer-experience annoyance (slow CI installs). The `lucide-svelte` package is also 5 major versions behind (`0.577.0` vs `1.0.1`).

---

## 2. Dependency Audit

### 2.1 Direct Dependencies

| Name | Version | Size on disk | Notes |
|---|---|---|---|
| `lucide-svelte` | 0.577.0 | 30 MB | Only 9 icons used; latest is 1.0.1 |
| `svelte` | 5.54.0 | 3.7 MB | Latest is 5.55.0 (minor lag) |
| `vite` | 7.3.1 | 2.4 MB | Latest is 8.0.2 (major behind) |
| `typescript` | 5.9.3 | — | Latest is 6.0.2 (major behind) |
| `@types/node` | 24.12.0 | — | Latest is 25.5.0 |
| `vite-plugin-pwa` | 1.2.0 | — | **Disabled in code**, but still installed and has 4 high-severity CVEs |

**Total `node_modules` packages:** 312

### 2.2 Security Vulnerabilities — 4 HIGH Severity

```
serialize-javascript  <=7.0.2   — RCE via RegExp.flags
@rollup/plugin-terser 0.2.0-0.4.4 — depends on above
workbox-build         >=7.1.0   — depends on above
vite-plugin-pwa       >=0.20.0  — depends on above
```

`vite-plugin-pwa` is **imported in `vite.config.ts` but commented out**:
```typescript
// PWA disabled — Service Worker interferes with fetch on iOS Safari via Tailscale
// import { VitePWA } from 'vite-plugin-pwa'
```

The package remains in `package.json` as a dev dependency, keeping the vulnerable chain installed. Because it is only a devDependency, it cannot reach production, but it is a false positive in any security scan and should be removed.

### 2.3 Outdated Packages Summary

| Package | Current | Latest | Type |
|---|---|---|---|
| `vite` | 7.3.1 | 8.0.2 | major |
| `typescript` | 5.9.3 | 6.0.2 | major |
| `lucide-svelte` | 0.577.0 | 1.0.1 | major |
| `@sveltejs/vite-plugin-svelte` | 6.2.4 | 7.0.0 | major |
| `jsdom` | 28.1.0 | 29.0.1 | major |
| `@types/node` | 24.12.0 | 25.5.0 | minor |
| `svelte` | 5.54.0 | 5.55.0 | patch |
| `vitest` | 4.1.0 | 4.1.1 | patch |
| `@vitest/coverage-v8` | 4.1.0 | 4.1.1 | patch |

---

## 3. Runtime Performance Analysis

### 3.1 Polling Strategy — Dual Redundancy

`App.svelte` calls `startPolling()` with `intervalMs = 1000` (1 second), while `http-client.ts` has a default of `200ms`. The App overrides the default to 1000ms, which is fine.

However, state arrives via **two independent paths**:
1. **HTTP polling** — `GET /api/v1/state` every 1000ms
2. **WebSocket push** — `state_update` events on `/api/v1/ws`

Both paths call `setRadioState()`. There is deduplication via `revision` comparison in `setRadioState()`, so both paths can coexist without double-renders. However, if the WebSocket is connected, the HTTP poll is redundant for state delivery (only used for connection health monitoring). This is intentional by design (comment in `ws-client.ts`), but worth noting for future optimization.

### 3.2 Scope WebSocket — High-Frequency Binary Data

`SpectrumPanel.svelte` opens a dedicated scope WebSocket (`/api/v1/scope`) that streams binary frames at the radio's scope update rate. IC-7610 scopes update at approximately 30–50 fps. Each frame is a `Uint8Array` of pixel amplitude values.

**Good practices observed:**
- Binary frames bypass Svelte reactivity entirely (`spectrumPush?.(frame.pixels)`) — this is the correct approach for high-frequency data.
- The spectrum canvas uses a single continuous `requestAnimationFrame` loop that reads `latestPixels` — decoupled from incoming frame rate.
- The waterfall renderer uses `ctx.drawImage(canvas, ...)` to shift rows without full redraws — `O(1)` per row.
- Tab visibility check (`document.hidden`) in `WaterfallCanvas.directPush()` skips rendering when the tab is hidden.

**Issue:** The spectrum `SpectrumCanvas.svelte` renders continuously even when no new scope data has arrived (the RAF loop always reschedules, regardless of whether `latestPixels` changed). When scope is connected, this wastes a full canvas render every 16ms even if data hasn't changed.

### 3.3 Concurrent `requestAnimationFrame` Loops

There are **5 independent RAF loops** running simultaneously during normal operation:

| Source | Loop | Purpose |
|---|---|---|
| `SpectrumCanvas.svelte` | 1 loop | Spectrum draw |
| `smoothing.svelte.ts` (NeedleGauge) | 1 loop per gauge | Needle exponential smoothing |
| `smoothing.svelte.ts` (LinearSMeter) | 1 loop per meter | Bar exponential smoothing |
| `LinearSMeter.svelte` | 1 extra loop | Peak hold decay |
| `smoothing.svelte.ts` (BarGauge) | 1 loop per gauge | Bar exponential smoothing |

In the v2 layout with `DockMeterPanel` displaying a `NeedleGauge` + 2× `LinearSMeter` + 3× `BarGauge`, there are at minimum **7 RAF loops** active at 60fps, all updating `$state` reactive values that trigger SVG re-renders. Each SVG is a Svelte reactive template with 10–30+ derived values.

The `LinearSMeter.svelte` uniquely runs **two separate RAF loops** per instance: one for the smoother (via `createSmoother`) and one for the peak hold logic. These could be merged into one loop.

### 3.4 Svelte `$effect` Usage and Stale-Capture Warnings

**26 `$effect` usages** across the codebase. Two warnings are emitted at build time:

```
DualParamRenderer.svelte:71: This reference only captures the initial value of `rfValue`.
DualParamRenderer.svelte:74: This reference only captures the initial value of `sqlValue`.
DiscreteRenderer.svelte:76: This reference only captures the initial value of `value`.
```

These are `state_referenced_locally` warnings — reactive state is captured in a `let` variable at module scope before the `$effect` closure, meaning the effect sees the initial value rather than the reactive one. In practice this appears compensated by tracking `prevRf`/`prevSql` inside the effect, but the pattern is fragile and should be fixed.

### 3.5 Module-Scoped Gradient Cache in `spectrum-renderer.ts`

```typescript
// spectrum-renderer.ts line 45
let _gradCache: { grad: CanvasGradient; height: number; fillColor: string } | null = null;
```

`_gradCache` is declared at **module scope**, meaning it is shared across all `SpectrumRenderer` instances. If two spectrum canvases exist (e.g., both v1 and v2 rendered simultaneously, or multiple spectrum panels in future), they would share the cache and corrupt each other's gradient. The `CanvasGradient` object is tied to the specific `CanvasRenderingContext2D` that created it — using it on a different context will silently produce wrong results.

### 3.6 DX Spots Array Growth

In `SpectrumPanel.svelte`:
```typescript
if (spot) dxSpots = [...dxSpots.slice(-49), spot];
```

Each new DX spot creates a new array (spread + slice). With rapid DX cluster feeds, this creates continuous GC pressure. The slice keeps the last 50 spots, which is correct, but a circular buffer would avoid the allocation.

### 3.7 Memory Leaks — None Found

All `addEventListener` registrations reviewed have corresponding `removeEventListener` in their cleanup:
- `SpectrumCanvas`: `visibilitychange` + `ResizeObserver` — both cleaned up in `onMount` return.
- `AppShell`: `resize` — cleaned up in `onMount` return.
- `DesktopLayout`: `keydown` — cleaned up in `onMount` return.
- `gesture-recognizer.ts`: 4 pointer events — the cleanup function removes all.
- `WsChannel`: keepalive `setInterval` + heartbeat `setTimeout` + reconnect `setTimeout` — all have `clearInterval`/`clearTimeout` in `_clearTimers()`.

No leaks detected.

### 3.8 Audio Engine

`RxPlayer.ts` uses the Web Audio API correctly:
- `AudioContext` is created lazily on `start()`.
- PCM16 frames create `AudioBuffer` objects without pooling. At 50 fps × 556–1364 bytes per frame, this is ~50 `AudioBuffer` allocations/second. Each allocation is GC'd after playback. A buffer pool would reduce GC pressure.
- Latency budget is capped at 150ms ahead of `currentTime` — reasonable for ham radio.
- Dropped frames are handled gracefully.

---

## 4. CSS Performance

### 4.1 Animation Properties — Compliant

All measured animations use GPU-compositable properties:
- `transform: rotate()` — spinner in error overlay
- `transform: translateX()/translateY()` — fade-in, slide-in-right
- `opacity` — pulse animations, reconnect indicators
- `box-shadow` — TX pulse glow

No animations on `top`, `left`, `width`, `height`, or `background-position` (except the `shimmer` skeleton loader which uses `background-position` — this is not compositable, but skeleton loaders are not performance-critical).

### 4.2 `backdrop-filter` — Potential Compositor Layer Cost

Three uses of `backdrop-filter: blur()`:
- `KeyboardHandler.svelte` (shortcut overlay): `blur(8px)` and `blur(10px)`
- `App.svelte` (error overlay): `blur(4px)`

`backdrop-filter` forces a new compositor layer and can be expensive on mobile GPUs. These are modal overlays that appear infrequently and are not animating blur, so cost is acceptable. However, on lower-powered devices (iOS Safari via Tailscale is the stated deployment target), these may cause visible jank when the overlay first appears.

### 4.3 `color-mix()` in CSS Custom Properties

`button-tokens.css` defines 14+ CSS custom properties using `color-mix(in srgb, ...)`. These are computed once by the browser's cascade engine per element instance and cached — not recalculated per frame. No performance concern.

### 4.4 Theme CSS Size (19 Themes)

All 19 theme CSS files are bundled and loaded unconditionally. Only one theme can be active at a time (set via `data-theme` attribute on `:root`). The inactive 18 theme definitions still participate in selector matching (`:root[data-theme="..."]` selectors) and contribute to stylesheet parse time.

At ~215 lines per theme × 19 = ~4,085 lines of CSS that the browser parses but uses at most ~215 lines of. This inflates the 279 KB CSS bundle significantly.

### 4.5 External Font Loading

`fonts.css` and `fonts-digital.css` are imported unconditionally via `theme/index.ts`:

```typescript
// theme/index.ts
import './fonts.css';
import './fonts-digital.css';
```

**`fonts.css`** loads `Roboto Mono` from Google Fonts (3 weights) — used throughout the application by nearly every component. This is a blocking render dependency.

**`fonts-digital.css`** loads 4 optional fonts from Google Fonts and jsDelivr:
- `Orbitron` (3 weights) — only used in Orbitron VFO theme
- `Share Tech Mono` — only used in digital VFO themes
- `VT323` — only used in CRT VFO themes
- `DSEG7 Classic` (2 weights) — only used in 7-segment VFO themes

These fonts are loaded unconditionally on every page load, even for users who never activate a digital VFO theme. Each Google Fonts request is an additional DNS + TLS + HTTP round trip (two requests: CSS descriptor + font file).

**`Roboto Mono`** has no local `@font-face` fallback — if Google Fonts is unreachable (e.g., regions where `fonts.googleapis.com` is blocked, or offline use via Tailscale), the UI falls back to the generic `monospace` stack, which changes the entire visual layout of frequency displays and meters.

---

## 5. Prioritized Recommendations

### P0 — Easy Wins (minutes, significant impact)

**P0.1 — Remove `vite-plugin-pwa` from `package.json`**
The plugin is commented out in `vite.config.ts` and contributes 4 high-severity CVE entries in `npm audit`. Removing it from `package.json` eliminates the vulnerability report and shrinks `node_modules` by its dependency subtree.
```
npm uninstall vite-plugin-pwa
```

**P0.2 — Fix `DiscreteRenderer.svelte` and `DualParamRenderer.svelte` Svelte warnings**
The `state_referenced_locally` warnings indicate potentially incorrect reactivity. The fix is to reference reactive values inside the `$effect` closure rather than capturing them in pre-effect `let` variables. This is both a correctness issue and a signal to Svelte's compiler to correctly track dependencies.

**P0.3 — Stop unconditionally loading digital VFO fonts**
Move the import of `fonts-digital.css` out of `theme/index.ts` into the theme-switcher, so digital fonts are only loaded when a digital VFO theme is actually activated. This removes 4 unnecessary network requests on every page load for users of the standard theme.

**P0.4 — Merge duplicate RAF loops in `LinearSMeter.svelte`**
`LinearSMeter` runs two separate RAF loops per instance: one for the smoother (`createSmoother`) and one for peak hold. These can be merged into a single RAF loop that updates both, halving the scheduler overhead for every S-Meter instance.

---

### P1 — Medium Effort (hours, noticeable improvement)

**P1.1 — Deduplicate the UI v1/v2 bundle via code splitting**
Since only one UI is active at a time (controlled by `uiVersion`), v1 and v2 can be split into separate dynamic chunks:
```typescript
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'ui-v1': ['./src/components/layout/AppShell.svelte', ...],
        'ui-v2': ['./src/components-v2/layout/RadioLayout.svelte', ...],
      }
    }
  }
}
```
Given both UIs share stores, transport, and types, the savings on initial JS parse time (roughly 50% of component code) would be meaningful on mobile devices.

**P1.2 — Lazy-load digital theme CSS**
Instead of bundling all 19 themes into the main CSS file, load theme CSS on demand when the user switches themes. This can be done with a dynamic `<link rel="stylesheet">` injection in `theme-switcher.ts`. The initial CSS bundle would drop to approximately 2 themes × 215 lines instead of 19 × 215.

**P1.3 — Throttle spectrum canvas rendering to actual data changes**
Currently `SpectrumCanvas.svelte` reschedules its RAF loop unconditionally every frame, even when `latestPixels` hasn't changed. Adding a dirty flag avoids wasting CPU on full canvas clears and redraws at 60 fps when data arrives at 30 fps:
```typescript
let dirty = false;

function draw(): void {
  if (!visible) { rafId = 0; return; }
  if (dirty && canvas && latestPixels) {
    // ... render ...
    dirty = false;
  }
  rafId = requestAnimationFrame(draw);
}

// In the push callback:
onRegisterPush?.((pixels: Uint8Array) => {
  latestPixels = pixels;
  dirty = true;
});
```

**P1.4 — Fix module-scoped gradient cache in `spectrum-renderer.ts`**
Move `_gradCache` from module scope into the `SpectrumRenderer` class as an instance property. This prevents the cache from being shared across instances (which would cause gradient corruption if two canvases exist):
```typescript
// Move from module scope to inside SpectrumRenderer class:
private _gradCache: { grad: CanvasGradient; height: number; fillColor: string } | null = null;
```

**P1.5 — Remove or tree-shake the `ControlButtonDemo` component from production**
`ControlButtonDemo.svelte` is imported in `App.svelte` and renders only when `?demo=control-buttons` is in the URL. It should be lazy-loaded (`import('./components-v2/controls/ControlButtonDemo.svelte')`) to avoid shipping demo code to all production users.

**P1.6 — Self-host `Roboto Mono` font**
The application is designed for LAN use via Tailscale. Loading fonts from `fonts.googleapis.com` on every page load introduces a latency dependency on an external service that may be unreachable in some deployments. Self-hosting the woff2 files in `/public/fonts/` and declaring local `@font-face` rules eliminates this dependency and ensures consistent UI appearance in offline/restricted network scenarios.

---

### P2 — Larger Effort (days, marginal or conditional improvement)

**P2.1 — Use an `AudioBuffer` pool in `RxPlayer`**
At 50 fps, `playPcm16` allocates one `AudioBuffer` per frame (~50/second). A pool of pre-allocated buffers (sized to the expected PCM frame length) would reduce GC pressure during extended audio sessions. This is only worthwhile if GC pauses are observed causing audio dropouts in practice.

**P2.2 — Replace DX spot array mutation with a circular buffer**
`dxSpots = [...dxSpots.slice(-49), spot]` allocates a new array on every spot. At high DX cluster rates this can produce frequent short-lived allocations. A fixed-size circular buffer with a head pointer would avoid allocation entirely. This is a micro-optimization worth considering only if profiling shows DX spot processing in hot paths.

**P2.3 — Consolidate v1 and v2 S-Meter implementations**
The v1 `SMeter.svelte` and v2 `LinearSMeter.svelte` are two separate implementations of the same S-Meter concept. Eliminating v1 once it is fully superseded would remove ~600 lines of duplicate meter code from the bundle.

**P2.4 — Evaluate switching HTTP polling to WebSocket-only state delivery**
Once the WS connection is established, the HTTP poll is redundant for state. Removing the HTTP poll when WS is connected would eliminate ~1 HTTP request per second (with its headers, auth token, and JSON parsing overhead). The poll is currently kept as a fallback and connection health signal — this trade-off is reasonable for now.

---

## 6. Summary Table

| ID | Issue | Effort | Impact | Category |
|---|---|---|---|---|
| P0.1 | Remove `vite-plugin-pwa` (4 high CVEs) | 1 min | Security | Dependencies |
| P0.2 | Fix Svelte `state_referenced_locally` warnings | 30 min | Correctness | Runtime |
| P0.3 | Stop loading digital fonts unconditionally | 15 min | 4 fewer HTTP requests | CSS |
| P0.4 | Merge dual RAF loops in `LinearSMeter` | 30 min | Halve meter loop overhead | Runtime |
| P1.1 | Code-split v1/v2 UI bundles | 2–4 h | ~25% faster initial parse | Bundle |
| P1.2 | Lazy-load theme CSS | 3–5 h | ~85% smaller initial CSS | Bundle |
| P1.3 | Throttle spectrum canvas to dirty frames | 1 h | Save ~50% spectrum renders | Runtime |
| P1.4 | Fix module-scoped gradient cache | 15 min | Correctness, future-proofing | Runtime |
| P1.5 | Lazy-load `ControlButtonDemo` | 30 min | Remove demo from prod bundle | Bundle |
| P1.6 | Self-host `Roboto Mono` | 2 h | Eliminate external font dependency | CSS |
| P2.1 | `AudioBuffer` pool in `RxPlayer` | 1 day | Reduce audio GC pressure | Runtime |
| P2.2 | Circular buffer for DX spots | 2 h | Reduce allocations at high DX rates | Runtime |
| P2.3 | Consolidate v1/v2 meter implementations | 1–2 days | Reduce bundle size | Bundle |
| P2.4 | WS-only state delivery | 1–2 days | Eliminate redundant HTTP polling | Runtime |
