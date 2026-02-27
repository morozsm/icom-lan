# Web UI

icom-lan includes a built-in web interface that provides real-time spectrum/waterfall display,
radio control, audio streaming, and meter readouts — accessible from any browser on your local network.

## Quick Start

```bash
# Connect to your radio and start the web server
icom-lan web --port 8080

# Or specify a custom host/port
icom-lan web --host 0.0.0.0 --port 9090
```

Then open `http://your-ip:8080` in a browser.

## Features

### Spectrum & Waterfall Display

- **Real-time spectrum graph** — amplitude vs. frequency with gradient fill
- **Scrolling waterfall** — color-mapped signal history (dark blue → cyan → yellow → red → white)
- **Click-to-tune** — click anywhere on the waterfall to set the VFO frequency
- **Hover tooltip** — shows frequency at cursor position
- **Frequency axis** — auto-scaling MHz labels

### Radio Controls

- **VFO A/B** — select, swap (A↔B), equalize (A=B)
- **Frequency entry** — click the frequency display to type a frequency in MHz
- **Mode selector** — USB, LSB, CW, CW-R, AM, FM, RTTY, RTTY-R, PSK, PSK-R
- **Filter selector** — FIL1, FIL2, FIL3
- **Power level** — adjustable TX power
- **Attenuator** — OFF, 6, 12, 18 dB
- **Preamp** — OFF, 1, 2
- **PTT** — press-and-hold button (or hold Space bar)

### Real-Time Meters

Eight meter bars with live updates at up to 20 fps:

| Meter | Description |
|-------|-------------|
| S-Meter | Signal strength (S0–S9, S9+dB) |
| Power | TX output power |
| SWR | Standing wave ratio (TX only) |
| ALC | Automatic level control (TX only) |
| COMP | Speech compressor level |
| Id | PA drain current |
| Vd | PA drain voltage |
| TEMP | PA temperature |

### Audio Streaming

- **RX audio** — listen to the radio in your browser (Opus codec via WebCodecs API)
- **TX audio** — transmit from your microphone (requires browser permission)
- **Volume control** — adjustable RX volume slider
- PTT automatically starts/stops TX audio capture

!!! note "Browser Requirements"
    Audio features require a modern browser with WebCodecs API support:
    Chrome 94+, Edge 94+, Firefox 130+, Safari 17.4+.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | PTT (hold to transmit) |
| `A` | Select VFO A |
| `B` | Select VFO B |
| `R` | Toggle RX audio |
| `F` | Open frequency entry |
| `T` | Toggle light/dark theme |

### Theme Support

- **Dark theme** (default) — easy on the eyes for nighttime operation
- **Light theme** — toggle with the 🌙/☀️ button or press `T`
- Theme preference is saved in localStorage

## Architecture

The web UI uses a multi-channel WebSocket architecture for optimal performance:

| Channel | Endpoint | Format | Purpose |
|---------|----------|--------|---------|
| Control | `/api/v1/ws` | JSON text | Commands, events, state sync |
| Scope | `/api/v1/scope` | Binary | Spectrum/waterfall data (15-30 fps) |
| Meters | `/api/v1/meters` | Binary | Meter readings (10-20 fps) |
| Audio | `/api/v1/audio` | Binary | Opus RX/TX audio |

### HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI (single HTML file) |
| `GET` | `/api/v1/info` | Server version, radio model, protocol version |
| `GET` | `/api/v1/capabilities` | Radio capabilities |

### Design Principles

- **Single HTML file** — no build step, no framework, no external dependencies
- **Zero npm/pip dependencies** — pure asyncio server, vanilla JavaScript frontend
- **Binary protocol** — efficient scope and meter data (< 15 KB/s for dual waterfall)
- **Backpressure** — server drops frames when client can't keep up, never drops commands
- **Auto-reconnect** — exponential backoff (1s → 30s max) on connection loss

## Configuration

```bash
# CLI options
icom-lan web --host 0.0.0.0     # Listen address (default: 0.0.0.0)
icom-lan web --port 8080         # HTTP/WebSocket port (default: 8080)
icom-lan web --static-dir ./ui   # Custom static files directory
```

## Custom Static Files

To serve a modified or completely custom UI:

```bash
# Extract the built-in index.html
python -c "
from importlib.resources import files
html = files('icom_lan.web.static').joinpath('index.html').read_text()
open('my-ui/index.html', 'w').write(html)
"

# Edit my-ui/index.html to your liking, then serve it
icom-lan web --static-dir ./my-ui
```

The WebSocket protocol is documented in the [RFC](../internals/rfc-web-ui-v1.md) and is
designed to survive backend rewrites — you can build any frontend you want.

## Limitations (v1)

- **LAN only** — no authentication, not safe for internet exposure
- **Single user** — multiple browsers can connect but may conflict on PTT
- **No WebRTC** — audio latency is higher than native; for low-latency remote use, consider VPN + native client
- **Canvas2D** — sufficient for 475px scope at 30fps; WebGL deferred to v2
