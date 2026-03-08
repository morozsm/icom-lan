# icom-lan Frontend

Svelte 5 + TypeScript + Vite UI for the icom-lan radio controller.

## Development

```bash
cd frontend
pnpm install
pnpm dev        # Vite dev server at http://localhost:5173 with HMR
                # Proxies /api and /ws to backend at http://localhost:8080
```

## Build

```bash
pnpm build      # → dist/ (optimized bundle)
pnpm preview    # Preview the production build locally
```

## Type Check

```bash
pnpm check      # svelte-check + tsc
```

## Structure

```
src/
├── App.svelte                  # Root — mounts AppShell
├── app.css                     # Global styles (imports tokens)
├── styles/
│   └── tokens.css              # CSS design system tokens (--bg, --accent, …)
├── components/
│   ├── layout/                 # AppShell, DesktopLayout, MobileLayout
│   ├── vfo/                    # VfoDisplay
│   ├── spectrum/               # SpectrumPanel, SpectrumCanvas, WaterfallCanvas
│   ├── meters/                 # SMeter, PowerMeter
│   ├── controls/               # BandSelector, ModeSelector, FilterSelector, …
│   ├── audio/                  # AudioControls, PttButton
│   ├── dx/                     # DxClusterPanel
│   ├── shared/                 # Toast, StatusBar, BottomBar
│   └── settings/               # SettingsPanel
└── lib/
    ├── stores/                 # Svelte 5 $state stores (radio, ui, commands, …)
    ├── transport/              # WebSocket client, HTTP client, protocol types
    ├── types/                  # TypeScript interfaces (state, capabilities, protocol)
    ├── renderers/              # Framework-agnostic canvas renderers (future)
    └── utils/                  # Helpers (frequency formatting, BCD, …)
```

## Architecture

See `docs/plans/2026-03-07-ui-architecture.md` for the full architecture document.

### Key Principles

- **Server state is the single source of truth** — UI never treats DOM state as truth
- **Rendered UI = server_state + pending_actions + local_ui_state**
- **Mobile/Desktop layouts** switch automatically at 768px breakpoint
- **Commands** are sent via WebSocket and reconciled with server state on next poll
