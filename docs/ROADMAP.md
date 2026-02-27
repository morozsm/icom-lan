# Roadmap

## Current State: v0.7.0 (Python)

- ✅ Phase 1 — Transport (UDP, auth, keep-alive, dual-port)
- ✅ Phase 2 — CI-V Commands (frequency, mode, power, meters, PTT, CW, VFO, split)
- ✅ Phase 3 — Audio Streaming
- ✅ Phase 4 — Polish & Publish (PyPI + releases + docs)
- ⬜ Phase 5 — Rust Core
- ✅ Phase 6 — Spectrum & Waterfall (API + CLI + rendering)
- ⬜ Phase 7 — Web UI (full wfview/RS-BA1 replacement)
- ⬜ Phase 8 — Virtual Audio Bridge (network audio for WSJT-X / digital modes)

**Next focus:** Phase 7.1 (Web UI MVP) with optional parallel spike for Phase 5.1 (Rust core).

---

## Phase 3 — Audio Streaming (Python)

**Goal:** RX/TX audio via Opus codec on port 50003.

**Status:** ✅ Implemented (core RX/TX/full-duplex API available in current releases).

### Tasks

- [ ] Study `icomudpaudio.cpp` — audio packet format, headers, sequence
- [ ] Open audio stream (OpenClose on audio port, similar to CI-V)
- [ ] RX: receive Opus packets → decode → callback API
- [ ] TX: PCM input → Opus encode → send to radio
- [ ] Buffering and jitter buffer (compensate for UDP delivery irregularity)
- [ ] Sample rate negotiation (8/16/24/48 kHz — set in conninfo)
- [ ] Tests with real radio

### API Design

```python
# RX — callback-based
def on_audio(pcm_data: bytes, sample_rate: int):
    # process audio...

async with IcomRadio(...) as radio:
    radio.start_audio_rx(callback=on_audio)
    await asyncio.sleep(10)
    radio.stop_audio_rx()

# TX — push-based
async with IcomRadio(...) as radio:
    radio.start_audio_tx(sample_rate=48000)
    radio.push_audio(pcm_data)
    radio.stop_audio_tx()

# Full duplex
async with IcomRadio(...) as radio:
    radio.start_audio(rx_callback=on_audio, tx_sample_rate=48000)
```

### Dependencies

- `opuslib` — Python bindings for libopus (optional dependency, `pip install icom-lan[audio]`)

---

## Phase 4 — Polish & Publish (Python)

**Goal:** Production-ready library on PyPI.

**Status:** ✅ Implemented (sync API, reconnect/token renewal, docs, GitHub releases, PyPI).

### Tasks

- [ ] Sync API wrapper (for those who don't want async)
- [ ] Autodiscovery improvement (multicast, timeout config)
- [ ] Multi-model support (CI-V address presets for IC-705, IC-7300, IC-9700)
- [ ] Token renewal timer (wfview: TOKEN_RENEWAL = 60s, sends `sendToken(0x05)`)
- [ ] Reconnect logic (auto-reconnect on connection loss)
- [ ] Proper integration test suite (`@pytest.mark.integration`)
- [ ] PyPI publication (`uv publish` / `twine upload`)
- [ ] GitHub Release with changelog
- [ ] MkDocs documentation site (GitHub Pages) — ✅ done
- [ ] Badges: PyPI version, downloads, CI status

### Sync API Design

```python
from icom_lan.sync import IcomRadio

# Blocking API (wraps asyncio internally)
with IcomRadio("192.168.1.100", username="u", password="p") as radio:
    freq = radio.get_frequency()
    radio.set_frequency(14_074_000)
```

---

## Phase 5 — Rust Core 🦀

**Goal:** Rewrite the core in Rust. Python API remains, but internally — native code. Plus standalone CLI and WASM.

### Motivation

| Feature | Why Rust |
|---------|----------|
| **Audio latency** | No GIL, no GC pauses → predictable real-time audio |
| **Single binary** | Download → run. No Python, pip, venv |
| **Memory safety** | Binary UDP packet parsing with compiler guarantees |
| **Multi-platform FFI** | One codebase → Python, Node.js, C/C++, Swift, WASM |
| **Tokio async** | 3 ports + pings + retransmit + audio — more efficient than asyncio |
| **WASM** | Control the radio from a browser (!) |
| **Embedded** | Raspberry Pi, embedded Linux without Python runtime |

### Architecture

```
┌──────────────────────────────────────────────────┐
│              icom-lan-core (Rust)                 │
│                                                   │
│  ┌───────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Transport │  │ Protocol │  │ Audio (Opus)  │  │
│  │  (tokio)  │  │ (CI-V)   │  │ (decode/enc)  │  │
│  └─────┬─────┘  └────┬─────┘  └──────┬────────┘  │
│        └──────────────┴───────────────┘           │
│                       │                           │
│  ┌────────────────────┴───────────────────────┐   │
│  │           Public Rust API                  │   │
│  │  IcomRadio::connect / get_freq / set_mode  │   │
│  └────────────────────────────────────────────┘   │
└───────┬──────────┬──────────┬──────────┬──────────┘
        │          │          │          │
   ┌────┴───┐ ┌───┴────┐ ┌───┴───┐ ┌───┴────┐
   │ PyO3   │ │  CLI   │ │ WASM  │ │ C FFI  │
   │(Python)│ │(clap)  │ │(wasm- │ │(cbind- │
   │        │ │        │ │ pack) │ │ gen)   │
   └────────┘ └────────┘ └───────┘ └────────┘
```

### Crates (Rust dependencies)

```toml
[dependencies]
tokio = { version = "1", features = ["full"] }       # async runtime
bytes = "1"                                            # efficient byte buffers
opus = "0.3"                                           # Opus codec
tracing = "0.1"                                        # structured logging
thiserror = "2"                                        # error types

# Bindings
pyo3 = { version = "0.24", features = ["extension-module"], optional = true }
wasm-bindgen = { version = "0.2", optional = true }
clap = { version = "4", features = ["derive"], optional = true }

[features]
python = ["pyo3"]
wasm = ["wasm-bindgen"]
cli = ["clap"]
ffi = []
```

### Phased Plan

#### Phase 5.1 — Rust Core (transport + protocol)

- [ ] Cargo workspace setup (`icom-lan-core`, `icom-lan-cli`, `icom-lan-py`)
- [ ] UDP transport on tokio (connect, ping, retransmit, sequence tracking)
- [ ] Discovery handshake (Are You There → I Am Here → Are You Ready)
- [ ] Authentication (credential encoding, login, token, conninfo)
- [ ] CI-V command encoding/decoding (BCD, frame builder/parser)
- [ ] IcomRadio struct with async API
- [ ] Unit tests (tokio::test)
- [ ] Integration test with IC-7610

#### Phase 5.2 — CLI (standalone binary)

- [ ] `clap` CLI with the same commands as Python CLI
- [ ] `icom-lan status / freq / mode / meter / ptt / cw / discover`
- [ ] Cross-compile: macOS (arm64, x86_64), Linux (arm64, x86_64), Windows
- [ ] GitHub Releases with binaries
- [ ] Homebrew formula: `brew install morozsm/tap/icom-lan`

#### Phase 5.3 — Python bindings (PyO3)

- [ ] PyO3 + maturin setup
- [ ] `IcomRadio` class with async support (pyo3-asyncio)
- [ ] Drop-in replacement for Python version: same API, same `from icom_lan import IcomRadio`
- [ ] PyPI publish as native wheel (`pip install icom-lan` → Rust binary inside)
- [ ] Benchmarks: Python-pure vs Rust+PyO3

#### Phase 5.4 — Audio (Rust-native Opus)

- [ ] Opus decode/encode via `opus` crate (or `audiopus`)
- [ ] Audio port (50003) handling in transport
- [ ] Jitter buffer
- [ ] Callback API for RX, push API for TX
- [ ] Full-duplex audio
- [ ] Latency benchmark vs Python+opuslib

#### Phase 5.5 — WASM (browser control)

- [ ] `wasm-bindgen` + `wasm-pack` build
- [ ] WebSocket → UDP proxy (WASM cannot do UDP directly)
- [ ] Minimal web UI: frequency, mode, S-meter, waterfall (?)
- [ ] npm package: `@icom-lan/web`

#### Phase 5.6 — C FFI

- [ ] `cbindgen` for C header generation
- [ ] Shared library (.so / .dylib / .dll)
- [ ] Example integration with GNU Radio
- [ ] Example integration with SDR++

### Effort Estimates

| Phase | Complexity | Time (estimate) |
|-------|------------|-----------------|
| 5.1 Core | Medium | 2–3 weeks |
| 5.2 CLI | Easy | 2–3 days |
| 5.3 PyO3 | Medium | 1 week |
| 5.4 Audio | High | 2–3 weeks |
| 5.5 WASM | High | 2 weeks |
| 5.6 C FFI | Medium | 3–5 days |

### Repository Structure (Rust)

```
icom-lan/
├── crates/
│   ├── icom-lan-core/        # Core: transport, protocol, commands, audio
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── transport.rs
│   │   │   ├── protocol.rs
│   │   │   ├── commands.rs
│   │   │   ├── auth.rs
│   │   │   ├── audio.rs
│   │   │   └── error.rs
│   │   └── Cargo.toml
│   ├── icom-lan-cli/         # CLI binary
│   │   ├── src/main.rs
│   │   └── Cargo.toml
│   ├── icom-lan-py/          # Python bindings (PyO3)
│   │   ├── src/lib.rs
│   │   ├── pyproject.toml
│   │   └── Cargo.toml
│   └── icom-lan-wasm/        # WASM bindings
│       ├── src/lib.rs
│       └── Cargo.toml
├── Cargo.toml                # workspace
├── Cargo.lock
├── docs/                     # shared documentation (current)
├── tests/                    # integration tests
└── README.md
```

### Open Questions

- **Mono-repo or separate repo?** Option: `icom-lan` (Python, current) + `icom-lan-rs` (Rust). Or mono-repo with Python in `python/` subdir.
- **Minimum Rust version (MSRV)?** Suggesting 1.75+ (async fn in traits stabilized).
- **Async runtime:** tokio (de facto standard) or async-std? → tokio.
- **Opus crate:** `opus` (C bindings) or `opus-rs` or pure-Rust `symphonia`? → C bindings (`opus`) for libopus compatibility.

---

## Phase 6 — Spectrum & Waterfall

**Goal:** Parse waterfall/spectrum data that the radio already sends (cmd `0x27`).

**Status:** ✅ Implemented in v0.6.0 (scope parsing/assembly, callbacks, CLI capture, PNG rendering).

### Context

The IC-7610 continuously sends spectrum data through the CI-V port (50002) — these are the packets with `cmd=0x27` that we filter. They contain:
- Scope data (FFT bin amplitudes)
- Center frequency, span
- Display metadata (ref level, edge frequencies)
- Two scopes — Main and Sub (the IC-7610 has two independent receivers)

### Key wfview References

- `rigcommander.cpp` → `parseSpectrum()` — spectrum packet parsing
- CI-V cmd `0x27`, sub `0x00` — scope data
- CI-V cmd `0x27`, sub `0x10`/`0x11` — scope on/off
- Format: header (division, center freq, span) + byte array (amplitudes 0-200)

### Tasks

- [ ] Study spectrum packet format in `rigcommander.cpp` → `parseSpectrum()`
- [ ] Reverse-engineer `0x27` sub-commands (scope enable/disable, mode, speed)
- [ ] Spectrum data parser → `SpectrumFrame(center_freq, span, data: list[int])` structure
- [ ] Callback API: `radio.on_spectrum(callback)` — continuous stream
- [ ] Scope control: `radio.set_scope(enabled=True, mode="center", span=100_000)`
- [ ] Dual scope support (Main + Sub for IC-7610)
- [ ] Ring buffer for last N frames (for waterfall display)
- [ ] Benchmark: how many spectrum packets per second does the IC-7610 send

### API Design

```python
from icom_lan import IcomRadio, SpectrumFrame

def on_spectrum(frame: SpectrumFrame):
    print(f"Center: {frame.center_freq/1e6:.3f} MHz, "
          f"Span: {frame.span/1e3:.0f} kHz, "
          f"Bins: {len(frame.data)}, "
          f"Peak: {max(frame.data)}")

async with IcomRadio(...) as radio:
    # Enable spectrum stream
    await radio.set_scope(enabled=True)
    radio.on_spectrum(on_spectrum)

    # ... do work, spectrum data flows via callback ...

    await radio.set_scope(enabled=False)
```

### Data Structure

```python
@dataclass
class SpectrumFrame:
    scope: int              # 0 = Main, 1 = Sub
    center_freq: int        # Hz
    span: int               # Hz
    edge_low: int           # Hz (left edge)
    edge_high: int          # Hz (right edge)
    data: list[int]         # amplitude values (0-200 per bin)
    division: int           # number of divisions
    out_of_range: bool      # scope data out of range flag
```

---

## Phase 7 — Web UI 🌐

**Goal:** Full-featured web interface for radio control. Replacement for RS-BA1 / wfview — open source, in the browser.

### Why

- **RS-BA1** — paid ($100+), Windows only, closed source
- **wfview** — GPLv3, Qt desktop app, heavyweight
- **icom-lan Web UI** — MIT, in the browser, zero install, works from your phone

### Architecture

```
┌──────────────┐     WebSocket      ┌──────────────────┐
│   Browser    │◄──────────────────►│   icom-lan       │
│              │                    │   server          │
│  ┌────────┐  │                    │  ┌────────────┐   │     UDP
│  │ React/ │  │                    │  │ WebSocket  │   │◄──────────►  Radio
│  │ Canvas │  │                    │  │ ↔ UDP      │   │   50001-3
│  │ WebGL  │  │                    │  │ proxy      │   │
│  └────────┘  │                    │  └────────────┘   │
└──────────────┘                    └──────────────────┘
```

Or with WASM (Phase 5.5):

```
┌────────────────────────────────────┐
│          Browser               │
│  ┌──────────┐  ┌────────────┐  │     WebSocket→UDP
│  │ WASM     │  │ UI         │  │◄────────────────►  Radio
│  │ icom-lan │  │ (React/    │  │     (proxy)
│  │ core     │  │  Canvas)   │  │
│  └──────────┘  └────────────┘  │
└────────────────────────────────────┘
```

### Features

#### MVP (Phase 7.1)

- [ ] Frequency display + tuning (click/drag/scroll/keyboard)
- [ ] Mode selector (USB/LSB/CW/AM/FM)
- [ ] S-meter bar (real-time)
- [ ] PTT button (with safety confirm)
- [ ] Power/SWR/ALC meters
- [ ] VFO A/B switch, split indicator
- [ ] Mobile-responsive layout

#### Waterfall (Phase 7.2)

- [ ] Real-time spectrum display (Canvas 2D or WebGL)
- [ ] Waterfall (scrolling history)
- [ ] Click-to-tune on waterfall
- [ ] Frequency zoom/pan
- [ ] Color schemes (classic, viridis, plasma)
- [ ] Dual waterfall for IC-7610 (Main + Sub)
- [ ] FPS control (10/20/30 fps)

#### Audio (Phase 7.3)

- [ ] RX audio via Web Audio API (Opus → PCM → speakers)
- [ ] TX audio via getUserMedia() (mic → Opus → radio)
- [ ] VOX mode (auto PTT on audio)
- [ ] Audio level meters (RX/TX)
- [ ] Noise reduction (Web Audio filters)

#### Advanced (Phase 7.4)

- [ ] Band stack (quick band switching with memory)
- [ ] Memory channels (saved frequency list)
- [ ] Logbook integration (ADIF export)
- [ ] DX cluster overlay on waterfall
- [ ] Multi-user (multiple browsers to one server)
- [ ] PWA (installable, offline capable)
- [ ] Dark/light theme

### Tech Stack (preliminary)

| Component | Technology |
|-----------|-----------|
| Frontend | React + TypeScript (or Svelte) |
| Waterfall | Canvas 2D / WebGL (gpu-accelerated) |
| Audio | Web Audio API + Opus.js (or WASM decoder) |
| Transport | WebSocket (browser ↔ server) |
| Server | Rust (axum) or Python (FastAPI + websockets) |
| State | Zustand / signals (reactive) |
| Build | Vite |

### Inspiration

- [OpenWebRX](https://www.openwebrx.de/) — web SDR with waterfall (excellent UX)
- [WebSDR](http://www.websdr.org/) — pioneer web-based radio
- [KiwiSDR](http://kiwisdr.com/) — browser-based SDR receiver
- [wfview](https://wfview.org/) — desktop reference (feature set)
- [RS-BA1](https://www.icomjapan.com/lineup/products/RS-BA1/) — Icom's official (UX anti-pattern 😅)

### Estimates

| Phase | Complexity | Time |
|-------|------------|------|
| 7.1 MVP (controls) | Medium | 1–2 weeks |
| 7.2 Waterfall | High | 2–3 weeks |
| 7.3 Audio | High | 2–3 weeks |
| 7.4 Advanced | Very high | ongoing |

---

## Phase 8 — Virtual Audio Bridge 🎧

**Goal:** Create a virtual soundcard that bridges WSJT-X (and other digital mode software) audio to the radio over LAN — no USB cable, no physical sound card needed. Full remote operation: CAT via rigctld + audio via virtual device.

### Why

Currently, `icom-lan serve` provides rigctld-compatible CAT control over the network. But WSJT-X, JS8Call, and fldigi still need a **sound card** for audio. This means you need either:

- A USB cable to the radio (defeats the purpose of LAN control)
- RS-BA1 + virtual audio cable (paid, Windows-only, painful)
- wfview's audio passthrough (GPL, heavy)

With a virtual audio bridge, the setup becomes:

```
WSJT-X                          IC-7610
  ├── CAT ──► rigctld ──► icom-lan ──► UDP :50001-2
  └── Audio ► Virtual Soundcard ──► icom-lan ──► UDP :50003
```

**Zero cables. Zero extra software. Full remote.**

### Architecture

```
┌─────────────────────────────────────────────┐
│  icom-lan audio bridge                       │
│                                              │
│  ┌──────────────┐      ┌──────────────────┐  │
│  │ Virtual      │ PCM  │  icom-lan        │  │
│  │ Soundcard    │◄────►│  AudioStream     │  │
│  │ (OS-level)   │      │  (Opus ↔ PCM)    │  │
│  └──────┬───────┘      └────────┬─────────┘  │
│         │                       │ UDP         │
└─────────┼───────────────────────┼─────────────┘
          │                       │
     WSJT-X / JS8Call        Icom Radio
     sees "icom-lan"         192.168.x.x
     as sound device         :50003 audio
```

### Platform-specific virtual audio

| Platform | Approach | Complexity |
|----------|----------|------------|
| **Linux** | PipeWire / PulseAudio virtual sink/source | Low — `pw-loopback` or module-pipe-sink |
| **macOS** | BlackHole / CoreAudio HAL plugin | Medium — BlackHole as dependency, or custom HAL plugin |
| **Windows** | Virtual Audio Cable / WASAPI loopback | Medium — may need a signed driver |

### CLI

```bash
# Start the audio bridge (creates virtual soundcard + connects to radio)
icom-lan audio bridge --device "icom-lan Audio"

# Combined: rigctld + audio bridge (full remote setup)
icom-lan serve --audio-bridge
```

### Phases

#### Phase 8.1 — Linux (PipeWire/PulseAudio)
- [ ] Virtual sink/source via PipeWire (`pw-loopback` or pipe module)
- [ ] PCM ↔ icom-lan AudioStream bridge
- [ ] Tested with WSJT-X on Linux

#### Phase 8.2 — macOS (BlackHole / CoreAudio)
- [ ] BlackHole integration (or custom CoreAudio HAL plugin)
- [ ] PCM routing to/from icom-lan
- [ ] Tested with WSJT-X on macOS

#### Phase 8.3 — Windows
- [ ] Virtual Audio Cable or custom WASAPI loopback
- [ ] Tested with WSJT-X on Windows

### Effort Estimate

| Phase | Complexity | Time |
|-------|-----------|------|
| 8.1 Linux | Low–Medium | 3–5 days |
| 8.2 macOS | Medium | 1 week |
| 8.3 Windows | Medium–High | 1–2 weeks |

---

## The Grand Vision 🔭

```
Phase 1-2:  Python CLI + API          ✅ Done
Phase 3:    Audio streaming            ✅ Done
Phase 4:    PyPI, polish               ✅ Done
Phase 5:    Rust core + bindings       ⬜ Planned
Phase 6:    Spectrum/waterfall data    ✅ Done
Phase 7:    Web UI — the full package  ⬜ Planned
Phase 8:    Virtual Audio Bridge       ⬜ Planned  ← killer feature
            ─────────────────────────
            Open-source RS-BA1 killer
            In your browser
            From your phone
            Zero cables, zero extra software
            MIT licensed
            73 de KN4KYD
```

---

*Created: 2026-02-25*
*Last updated: 2026-02-25*
