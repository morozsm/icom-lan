# Web UI Architecture — Desktop + Mobile

**Date:** 2026-03-07
**Authors:** Сергей + Жора
**Status:** Approved
**Framework:** Svelte 5 + TypeScript
**Replaces:** `2026-03-07-ui-architecture-research.md`, `2026-03-04-mobile-ui-design.md`

---

## 1. Core Principle

**Server state is the single source of truth.**

The backend exposes authoritative system state via:
```
GET /api/v1/state         → full radio state (124 fields)
GET /api/v1/capabilities  → model, supported features, modes, filters
```

The frontend NEVER treats DOM state or local UI interactions as truth.

```
rendered UI = server_state + pending_actions + local_ui_state
```

---

## 2. Existing Backend API (already implemented)

### 2.1 `/api/v1/capabilities` — ✅ Already exists

```json
{
  "model": "IC-7610",
  "scope": true,
  "audio": true,
  "tx": true,
  "capabilities": [
    "af_level", "attenuator", "audio", "cw", "digisel",
    "dual_rx", "ip_plus", "meters", "nb", "nr",
    "preamp", "rf_gain", "scope", "squelch", "tx"
  ],
  "freq_ranges": [
    {"start": 30000, "end": 60000000, "label": "HF"},
    {"start": 50000000, "end": 54000000, "label": "6m"}
  ],
  "modes": ["USB", "LSB", "CW", "AM", "FM", "RTTY", "CWR"],
  "filters": ["FIL1", "FIL2", "FIL3"]
}
```

**Backend protocol layer** (`radio_protocol.py`) already defines:
- `Radio.capabilities -> set[str]` — runtime capability tags
- `AudioCapable`, `ScopeCapable`, `DualReceiverCapable` — Protocol classes
- `_runtime_capabilities()` — conservative capability resolution
- `RadioModel` dataclass with `receivers`, `has_lan`, `has_wifi`

**What to add for multi-radio support:**
```json
{
  "capabilities": {
    "hasSpectrum": true,
    "hasDualReceiver": true,
    "hasTx": true,
    "hasTuner": true,
    "hasCw": true,
    "maxReceivers": 2
  }
}
```
This is a frontend-friendly restructuring of existing backend data. No backend changes needed — the frontend can derive structured capabilities from the flat `capabilities[]` array.

### 2.2 `/api/v1/state` — ✅ Already exists

124 fields, including:
- `main.*` / `sub.*` — per-receiver state (freq, mode, filter, meters, DSP)
- `ptt`, `split`, `dual_watch`, `tuner_status`
- `scope_controls` — spectrum configuration
- `connected`, `radio_ready`, `control_connected`

**What to add:**
- `revision: number` — monotonic counter for stale packet detection
- `updatedAt: string` — ISO timestamp

### 2.3 WebSocket — ✅ Already exists

Current model: WS for commands + binary scope data. State via HTTP poll (200ms).

**Future optimization (Phase 3+):**
- WS delta push: `{ revision: 42, patch: { "main.freq": 14074000 } }`
- Gap detection: if `revision` gap > 1 → full re-fetch via GET
- Reduces mobile bandwidth

---

## 3. State Architecture

### 3.1 Server State (authoritative)

```typescript
interface ServerState {
  revision: number;
  updatedAt: string;

  active: "MAIN" | "SUB";
  ptt: boolean;
  split: boolean;
  dualWatch: boolean;
  tunerStatus: number;

  main: ReceiverState;
  sub: ReceiverState;

  connection: {
    rigConnected: boolean;
    radioReady: boolean;
    controlConnected: boolean;
  };
}

interface ReceiverState {
  freqHz: number;
  mode: string;
  filter: number;
  dataMode: boolean;
  sMeter: number;
  att: number;
  preamp: number;
  nb: boolean;
  nr: boolean;
  afLevel: number;
  rfGain: number;
  squelch: number;
  // ... etc
}
```

### 3.2 UI State (client-only)

```typescript
interface UiState {
  layout: "desktop" | "mobile";
  activePanel: "main" | "audio" | "memories" | "settings";
  spectrumFullscreen: boolean;
  freqEntryOpen: boolean;
  theme: "dark" | "light";
  gestures: {
    tuning: boolean;
    draggingSpectrum: boolean;
  };
}
```

UI state NEVER modifies server state directly.

### 3.3 Pending Commands

```typescript
interface PendingCommand {
  id: string;
  type: "set_freq" | "set_mode" | "set_filter" | "ptt_on" | "ptt_off";
  payload: unknown;
  createdAt: number;
  status: "pending" | "acked" | "failed";
  timeoutMs: number;
}
```

Commands are sent via WS, then reconciled with server state on next poll/push.

---

## 4. System Layers

### 4.1 Transport Layer

Networking, protocol, reconnection.

```
src/lib/transport/
├── ws-client.ts        # WebSocket connection + reconnect
├── http-client.ts      # REST API calls (state, capabilities)
└── protocol.ts         # Message types, serialization
```

### 4.2 Domain / State Layer

Pure data management. No DOM access.

```
src/lib/stores/
├── radio.ts            # Server state store ($radioState)
├── audio.ts            # Audio state + controls
├── ui.ts               # UI-only state ($uiState)
├── connection.ts       # Connection health
├── capabilities.ts     # Radio capabilities (from /api/v1/capabilities)
└── commands.ts         # Pending command queue
```

Svelte 5 runes (`$state`, `$derived`) for reactivity.

### 4.3 Rendering Engines (framework-agnostic)

Imperative Canvas rendering. Pure JS/TS, no Svelte dependencies.

```
src/lib/renderers/
├── spectrum-renderer.ts    # Spectrum line chart
├── waterfall-renderer.ts   # Waterfall bitmap
└── meter-renderer.ts       # S-meter, SWR, power bars
```

These are portable — can migrate to any framework or vanilla JS.

### 4.4 UI Components (Svelte)

```
src/components/
├── layout/
│   ├── AppShell.svelte         # Root layout switcher (desktop/mobile)
│   ├── DesktopLayout.svelte    # Desktop grid
│   └── MobileLayout.svelte     # Mobile stacked
├── vfo/
│   ├── VfoDisplay.svelte       # Frequency display + editing
│   ├── VfoDigit.svelte         # Individual digit (click-to-edit)
│   └── FreqEntry.svelte        # Direct frequency input modal
├── spectrum/
│   ├── SpectrumPanel.svelte    # Spectrum + waterfall container
│   ├── SpectrumCanvas.svelte   # Canvas wrapper for spectrum
│   ├── WaterfallCanvas.svelte  # Canvas wrapper for waterfall
│   └── DxOverlay.svelte        # DX cluster spots overlay
├── controls/
│   ├── BandSelector.svelte     # Band dropdown
│   ├── ModeSelector.svelte     # Mode dropdown
│   ├── FilterSelector.svelte   # Filter dropdown
│   ├── FeatureToggles.svelte   # NB, NR, ATT, PRE toggles
│   └── ReceiverSwitch.svelte   # MAIN/SUB toggle
├── meters/
│   ├── SMeter.svelte           # S-meter bar
│   ├── SwrMeter.svelte         # SWR bar
│   └── PowerMeter.svelte       # TX power bar
├── audio/
│   ├── AudioControls.svelte    # Volume, mute, audio status
│   └── PttButton.svelte        # Push-to-talk
├── dx/
│   └── DxClusterPanel.svelte   # DX spot list
├── shared/
│   ├── Toast.svelte            # Notification toasts
│   ├── StatusBar.svelte        # Connection status
│   └── BottomBar.svelte        # Mobile fixed bottom bar
└── settings/
    └── SettingsPanel.svelte    # Audio, display, connection settings
```

---

## 5. CSS Architecture

Design system with CSS custom properties:

```css
:root {
  /* Colors */
  --bg: #0b0f14;
  --panel: #121922;
  --panel-border: #1e293b;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --accent: #4db6ff;
  --accent-hover: #6dc6ff;
  --danger: #f85149;
  --warning: #d29922;
  --success: #3fb950;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;

  /* Typography */
  --font-mono: 'JetBrains Mono', 'SF Mono', monospace;
  --font-sans: system-ui, -apple-system, sans-serif;
  --font-vfo: 'Segment7', var(--font-mono);

  /* Layout */
  --radius: 8px;
  --radius-lg: 12px;
  --tap-target: 44px;        /* minimum touch target */
  --bottom-bar-height: 56px;

  /* Breakpoints (reference, actual in @media) */
  --mobile-max: 768px;
  --tablet-max: 1024px;
}
```

Component styles are scoped (Svelte `<style>`). Global tokens in `src/styles/`.

---

## 6. Desktop Layout

```
┌─────────────────────────────────────────────────────────┐
│  IC-7610 · 🟢 Connected · UTC 14:23                     │
├───────────────────────────────────┬─────────────────────┤
│                                   │  S ████████░░  S7   │
│  VFO A    14.074.000  USB FIL1    │  SWR  1.0           │
│  VFO B     3.573.000  USB FIL1    │  PWR  50W           │
│                                   │                     │
├───────────────────────────────────┤  [20m] [USB] [FIL1] │
│  ┌─────────────────────────────┐  │  [NB] [NR] [ATT]   │
│  │        SPECTRUM             │  │  [PRE] [COMP] [AGC] │
│  │  ═══════════════════════    │  │                     │
│  │                             │  ├─────────────────────┤
│  │        WATERFALL            │  │  🔊 Vol ═══════     │
│  │                             │  │  🎤 Mic ═══════     │
│  │    · DX spots overlay ·     │  │  [PTT]              │
│  └─────────────────────────────┘  │                     │
├───────────────────────────────────┤  DX Cluster         │
│  Band: 160 80 40 30 20 17 15 12  │  ├ W1AW   14.074    │
│                            10  6 │  ├ JA1XX  14.076    │
└───────────────────────────────────┴─────────────────────┘
```

Features:
- Resizable panels (CSS grid with drag handles)
- Keyboard shortcuts (F1-F12 bands, M mode, arrows tune)
- Dual VFO display (MAIN + SUB)
- Side panel: meters + controls + DX cluster

---

## 7. Mobile Layout (<768px, portrait)

```
┌─────────────────────────┐
│ IC-7610 · 🟢 · 14:23 UTC│
├─────────────────────────┤
│ VFO A        14.074.000 │  swipe L/R = tune
│ USB · FIL1    [MAIN|sub]│  tap digit = edit
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │   SPECTRUM          │ │  ~30% screen
│ │   ═══════════════   │ │  tap → fullscreen
│ │   WATERFALL         │ │  tap-to-tune
│ └─────────────────────┘ │
├─────────────────────────┤
│ S ████████░░░░  S7      │
│ [BAND▾] [MODE▾] [FIL▾] │
├─────────────────────────┤
│ 🔊 Vol  │ [===PTT===]  │  fixed bottom bar
│  on/off │  hold-to-TX  │  height: 56px
└─────────────────────────┘
```

Touch interactions:
- Swipe on VFO → tune (step configurable)
- Tap on waterfall → tune to frequency
- Pinch-zoom on waterfall → change span
- Hold PTT → transmit (release = RX)
- Pull-down → additional controls drawer

---

## 8. Critical UX Interactions

### 8.1 VFO Control

Primary interaction element.
- Large segmented frequency display
- Digit-based editing (tap digit → increment/decrement)
- Swipe tuning (horizontal gesture)
- Direct frequency entry (tap freq → numpad modal)
- Step size selector (1Hz, 10Hz, 100Hz, 1kHz, etc.)

### 8.2 Waterfall Interaction

- **Tap-to-tune**: touch → set frequency
- **Pinch-zoom**: change spectrum span
- **Drag to pan**: shift center frequency
- **DX spot overlay**: clickable callsign badges

### 8.3 PTT Handling

**Mobile:** Hold-to-talk with strong visual TX feedback (red border, pulsing indicator).

**Desktop:** Toggle button + keyboard hotkey (Space or configurable).

**PTT must NOT rely on optimistic UI.** Server confirmation determines TX state. Pending state shows "TX pending..." indicator.

### 8.4 Band Switching

Quick-access band buttons (desktop: horizontal bar, mobile: dropdown).
- Show current band highlighted
- Band stacking registers (remember freq/mode per band)
- One-tap switching

---

## 9. Data Flow

### Startup Sequence

```
1. Load shell (Svelte app)
2. GET /api/v1/capabilities → populate feature flags
3. GET /api/v1/state → initial render
4. Connect WebSocket
5. Subscribe: scope, dx_spots, notifications
6. Start HTTP poll (200ms) for state updates
```

### Command Flow

```
User action → create PendingCommand → send via WS
→ server processes → state changes
→ next poll/push → reconcile with pending
→ clear PendingCommand → re-render
```

### Stale Data Protection

State responses include `revision` (monotonic counter).
- If incoming `revision` ≤ current → discard
- If `revision` gap > 1 → full re-fetch
- `updatedAt` timestamp for debugging

---

## 10. Project Structure

```
frontend/
├── src/
│   ├── App.svelte
│   ├── main.ts
│   ├── app.css                 # Global styles + CSS tokens
│   ├── lib/
│   │   ├── transport/          # WS + HTTP clients
│   │   ├── stores/             # Svelte state stores
│   │   ├── renderers/          # Canvas engines (framework-agnostic)
│   │   ├── types/              # TypeScript interfaces
│   │   └── utils/              # Helpers (BCD, frequency formatting)
│   └── components/             # Svelte UI components (see §4.4)
├── static/
│   ├── fonts/                  # Segment display font
│   └── icons/                  # PWA icons
├── package.json
├── vite.config.ts
├── svelte.config.js
├── tsconfig.json
└── README.md
```

Build output → `frontend/dist/` → served by Python backend or embedded in package.

---

## 11. Build & Integration

### Development

```bash
cd frontend
pnpm install
pnpm dev          # Vite dev server with HMR, proxy to backend :8080
```

### Production

```bash
pnpm build        # → dist/ (single bundle.js + index.html)
```

Integration options:
1. **Embedded**: Copy `dist/` into `src/icom_lan/web/static/` at build time
2. **Separate**: Serve frontend separately, backend = pure API
3. **Both**: Dev uses Vite proxy, production embeds

Recommended: **Option 1** (embedded) — single `pip install icom-lan` includes everything.

---

## 12. Server-Side Improvements Needed

| Change | Priority | Effort |
|--------|----------|--------|
| Add `revision` counter to state | P1 | S (1h) |
| Add `updatedAt` to state | P1 | S (1h) |
| Restructure capabilities for frontend | P2 | S (2h) |
| WS delta push (instead of full poll) | P3 | M (1-2d) |
| Connection health metrics | P3 | S (2h) |

---

## 13. Implementation Roadmap

### Sprint 0: Foundation (2-3 days) 🏗️
*Parallelizable: 2 agents*

**Agent A: Frontend scaffold**
- [ ] Init Svelte 5 + TypeScript + Vite project
- [ ] CSS design system (tokens, base styles)
- [ ] AppShell with desktop/mobile layout switcher
- [ ] Empty component shells for all major components

**Agent B: Backend prep**
- [ ] Add `revision` counter to `/api/v1/state`
- [ ] Add `updatedAt` timestamp
- [ ] Create `GET /api/v1/info` (merged capabilities + connection health)
- [ ] Tests for new endpoints

### Sprint 1: Transport + State (2-3 days) 🔌
*Parallelizable: 2 agents*

**Agent A: Transport layer**
- [ ] WebSocket client with auto-reconnect
- [ ] HTTP client for state polling + capabilities fetch
- [ ] Protocol types (message schemas)
- [ ] Connection state management

**Agent B: State stores**
- [ ] `radioStore` — server state with revision tracking
- [ ] `uiStore` — layout, panels, gestures
- [ ] `commandStore` — pending commands queue
- [ ] `capabilitiesStore` — feature flags from backend
- [ ] Unit tests for stores

### Sprint 2: Core Rendering (3-4 days) 📊
*Parallelizable: 3 agents*

**Agent A: Spectrum + Waterfall**
- [ ] Port spectrum renderer to TypeScript
- [ ] Port waterfall renderer to TypeScript
- [ ] SpectrumCanvas.svelte + WaterfallCanvas.svelte wrappers
- [ ] DX overlay layer
- [ ] Responsive sizing

**Agent B: VFO + Meters**
- [ ] VfoDisplay component (segmented font, digit editing)
- [ ] FreqEntry modal (direct input)
- [ ] SMeter, SwrMeter, PowerMeter components
- [ ] ReceiverSwitch (MAIN/SUB)

**Agent C: Controls**
- [ ] BandSelector, ModeSelector, FilterSelector
- [ ] FeatureToggles (NB, NR, ATT, PRE, etc.)
- [ ] Audio controls (volume, mute)
- [ ] PttButton (desktop toggle)

### Sprint 3: Desktop Layout (2-3 days) 🖥️
*Sequential (integration)*

- [ ] Assemble DesktopLayout with all components
- [ ] Resizable panels (CSS grid + drag)
- [ ] Keyboard shortcuts
- [ ] DxClusterPanel integration
- [ ] StatusBar + Toast notifications
- [ ] Desktop testing + polish

### Sprint 4: Mobile Layout (2-3 days) 📱
*Parallelizable: 2 agents*

**Agent A: Mobile layout + components**
- [ ] MobileLayout with stacked design
- [ ] BottomBar (audio + PTT)
- [ ] Compact VFO display
- [ ] Grouped dropdown controls
- [ ] Fullscreen spectrum toggle

**Agent B: Touch interactions**
- [ ] Swipe-to-tune on VFO
- [ ] Tap-to-tune on waterfall
- [ ] Pinch-zoom span control
- [ ] Hold-to-talk PTT
- [ ] Pull-down controls drawer

### Sprint 5: PWA + Polish (2-3 days) ✨
*Parallelizable: 2 agents*

**Agent A: PWA**
- [ ] manifest.json + icons
- [ ] Service Worker (offline shell)
- [ ] Add-to-homescreen prompt
- [ ] Offline state indicator

**Agent B: UX Polish**
- [ ] Dark/light theme toggle
- [ ] Haptic feedback (navigator.vibrate)
- [ ] Settings panel (preferences)
- [ ] Loading states + error boundaries
- [ ] Performance optimization (lazy loading, memoization)

### Total: ~14-19 days

---

## 14. Conventions & Contracts

### Naming

| Layer | Convention | Example |
|-------|-----------|---------|
| Components | PascalCase | `VfoDisplay.svelte` |
| Stores | camelCase + `Store` suffix | `radioStore.ts` |
| Types/Interfaces | PascalCase, `I` prefix optional | `ServerState`, `ReceiverState` |
| CSS variables | kebab-case, `--` prefix | `--panel-border` |
| Events | kebab-case | `freq-change`, `ptt-toggle` |
| API endpoints | kebab-case, `/api/v1/` prefix | `/api/v1/state` |

### Component Contract

Every component:
1. Receives data via **props** (never fetches directly)
2. Dispatches user actions via **events** (`createEventDispatcher`)
3. Has **scoped CSS** (no global side effects)
4. Is **self-contained** (renders correctly in isolation)
5. Uses **TypeScript** for props interface

```svelte
<script lang="ts">
  interface Props {
    freq: number;
    mode: string;
    active: boolean;
  }

  let { freq, mode, active }: Props = $props();

  function handleTune(newFreq: number) {
    // dispatch to parent → command store → WS
  }
</script>
```

### State Contract

1. **Server state** — read-only in components (via store subscription)
2. **UI state** — read/write in components (via store)
3. **Commands** — write-only in components (dispatch action → store handles WS)
4. **Never** derive radio truth from UI interactions

### WS Message Contract

```typescript
// Outgoing (client → server)
interface WsCommand {
  type: string;           // "set_freq", "set_mode", etc.
  id: string;             // unique command ID
  [key: string]: unknown; // command-specific payload
}

// Incoming (server → client)
interface WsMessage {
  type: "scope_data" | "dx_spot" | "notification" | "ack" | "error";
  [key: string]: unknown;
}
```

### Testing Contract

- Stores: unit tests (vitest)
- Renderers: unit tests (canvas mocking)
- Components: component tests (svelte testing library)
- E2E: Playwright (Phase 3+)

---

*This document is the single source of truth for frontend architecture decisions.*
