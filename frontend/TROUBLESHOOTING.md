# Frontend Troubleshooting

## "Works on desktop, broken on mobile"

**First step: add global error handler to `index.html`:**

```html
<script>
window.onerror = function(msg, url, line) {
  document.title = 'ERR:' + line + ':' + msg;
};
</script>
```

Then check the tab title on mobile. If it shows an error — that's your bug.

### 2026-03-08: ReferenceError in MobileLayout killed entire Svelte runtime

**Symptoms:** VFO shows "Connecting...", controls don't respond, `setInterval` doesn't tick, fetch/XHR appear to hang. Desktop works perfectly.

**Root cause:** `MobileLayout.svelte` referenced bare variables `sub` and `main` instead of `radio.current?.sub` / `radio.current?.main`. This threw a `ReferenceError` that killed the Svelte 5 runtime entirely.

**Why desktop worked:** `MobileLayout` only renders on screens <768px. Desktop renders `DesktopLayout` which had no errors.

**False leads investigated (all wrong):**
- Service Worker caching API responses
- Tailscale MTU fragmentation
- iOS Safari 6-connection limit
- `fetch()` vs `XMLHttpRequest` differences
- `{ cache: 'no-store' }` option
- Svelte 5 signal scheduler (queueMicrotask)
- `$state` reactivity from external callbacks

**Lesson:** Always check for JS errors before investigating network/platform issues. A single ReferenceError in any component can silently kill the entire Svelte app.

## Architecture: State polling

State polling uses a two-layer approach:

1. **`index.html` plain `<script>`:** XHR polls `/api/v1/state` every 200ms, writes to `window.__RADIO_STATE__`
2. **Svelte `onMount` setInterval (150ms):** Reads `window.__RADIO_STATE__`, calls `setRadioState()` when revision changes

This pattern exists because it was developed during debugging, but it's actually robust — the index.html XHR starts before Svelte loads, providing faster initial state.

## PWA / Service Worker

PWA is **disabled** (`VitePWA` commented out in `vite.config.ts`). Old Service Workers from previous builds may still be cached on devices. The `index.html` includes SW unregistration code. A `/clearcache` endpoint sends `Clear-Site-Data` header for nuclear cleanup.
