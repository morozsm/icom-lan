# CLAUDE.md — Claude Code Agent Instructions

> **Read this file first.** It exists to reduce the cost of codebase exploration.
> After this file, read `AGENTS.md` for full philosophy, then `docs/PROJECT.md` for current phase.

---

## Project snapshot

| | |
|---|---|
| **Name** | icom-lan |
| **Version** | 0.15.0 |
| **License** | MIT |
| **Python** | 3.11+ |
| **Primary radio** | Icom IC-7610 (LAN: `192.168.55.40`) |
| **LAN ports** | 50001 (control), 50002 (CI-V), 50003 (audio) |
| **Tests** | ~4400 unit + contract + regression; `tests/integration/` separately |

**What this is:** a Python asyncio library + Web UI for controlling Icom ham radio transceivers
directly over LAN/USB — without wfview, hamlib, or RS-BA1.

---

## Module boundaries

```
src/icom_lan/
│
├── radio_protocol.py        # Protocol contracts (Radio, LevelsCapable, MetersCapable,
│                            #   AudioCapable, ScopeCapable, DualReceiverCapable, etc.)
│                            # — backend-neutral; consumers program against these
│
├── radio.py                 # Backward-compatible IcomRadio wrapper → delegates to factory
├── radios.py                # CoreRadio shared base (commands/state/CI-V routing)
├── _scope_runtime.py        # ScopeRuntimeMixin (extracted from CoreRadio)
├── _audio_runtime_mixin.py  # AudioRuntimeMixin (extracted from CoreRadio)
├── _dual_rx_runtime.py      # DualRxRuntimeMixin (extracted from CoreRadio)
│
├── backends/                # One subdirectory per model family
│   ├── factory.py           #   create_radio() — routes by model string
│   ├── config.py            #   shared RadioConfig dataclass
│   ├── icom7610/            #   IC-7610: lan.py + serial.py + drivers/
│   ├── ic705/               #   IC-705 (code complete, blocked on hardware)
│   ├── ic7300/              #   IC-7300 (code complete, blocked on hardware)
│   ├── ic9700/              #   IC-9700 (code complete, blocked on hardware)
│   └── yaesu_cat/           #   Yaesu CAT backend
│
├── transport.py             # LAN UDP transport (auth, keep-alive, packet send/recv)
├── _control_phase.py        # Connection state machine (IDLE→AUTH→RUNNING→DISCONNECTED)
├── civ.py                   # CI-V frame encode/decode (BCD, struct, byte ops)
├── commands/                # CI-V command catalog (split from monolith)
│   ├── __init__.py          #   re-exports all 300+ symbols for backward compat
│   ├── _frame.py            #   CI-V frame kernel: builders, parser, constants
│   ├── _codec.py            #   BCD encode/decode helpers
│   ├── _builders.py         #   shared builder templates
│   ├── freq.py, mode.py, levels.py, meters.py, ptt.py, vfo.py,
│   │   dsp.py, scope.py, cw.py, power.py, speech.py, system.py,
│   │   tone.py, memory.py, antenna.py, config.py  # 16 leaf modules
│   └── (layering: _frame ← _codec ← _builders ← leaves)
├── commander.py             # CI-V dispatcher / executor
├── command_map.py           # CI-V opcode → command class mapping
├── command_spec.py          # Command metadata (cmd29 support, receiver routing)
├── exceptions.py            # IcomLanError hierarchy (ConnectionError, CommandError, …)
├── types.py                 # Public types (Mode, Meter, BandEdge, …)
├── profiles.py              # RadioProfile — model capabilities matrix (profile-driven routing)
├── profiles_runtime.py      # OperatingProfile / PRESETS — declarative runtime profiles
├── radio_state.py           # RadioState dataclass — canonical radio state
├── _state_cache.py          # StateCache — shared poller-populated state
├── _shared_state_runtime.py # Shared state runtime helpers
│
├── audio/                   # Audio subsystem
│   ├── backend.py           # AudioBackend protocol + PortAudioBackend + FakeAudioBackend
│   ├── _macos_uid.py        # macOS CoreAudio UID lookup (ctypes, Darwin only)
│   ├── usb_driver.py        # UsbAudioDriver — USB audio device management
│   ├── lan_stream.py        # LAN audio stream (PCM/Opus receive loop)
│   ├── resample.py          # PcmResampler with anti-aliasing FIR filter
│   ├── dsp.py               # NoiseGate, RmsNormalizer, Limiter, DspPipeline
│   └── config.py            # AudioConfig with TOML load/save/merge_cli
│
├── _audio_codecs.py         # ulaw/PCM codec tables (pure Python, no deps)
├── _audio_buffer_pool.py    # AudioBufferPool — lock-free reuse, reduces GC pressure
├── _audio_recovery.py       # AudioRecovery — reconnect / jitter handling
├── _audio_transcoder.py     # Audio format transcoding pipeline
├── audio_bridge.py          # AudioBridge — virtual device ↔ radio stream bridge
├── _bridge_state.py         # BridgeState enum + BridgeStateChange dataclass
├── _bridge_metrics.py       # BridgeMetrics dataclass with to_dict()
├── audio_bus.py             # AudioBus — multi-consumer audio distribution
├── audio_fft_scope.py       # Software FFT scope from audio stream
│
├── web/                     # Web server (aiohttp-based)
│   ├── server.py            #   startup / shutdown
│   ├── handlers/            #   REST API handlers (split from monolith)
│   │   ├── __init__.py      #     re-exports ControlHandler, ScopeHandler, AudioBroadcaster, AudioHandler
│   │   ├── control.py       #     ControlHandler (~1590 lines)
│   │   ├── scope.py         #     ScopeHandler + HIGH_WATERMARK
│   │   └── audio.py         #     AudioBroadcaster + AudioHandler
│   ├── websocket.py         #   WebSocket push (state/audio/scope/dx events)
│   ├── radio_poller.py      #   poller — periodic radio state polling
│   ├── _delta_encoder.py    #   DeltaEncoder — partial state diff, 10–50× payload reduction
│   ├── dx_cluster.py        #   DX cluster telnet client + spot overlay
│   └── static/              #   Frontend (JS/CSS/HTML)
│
├── rigctld/                 # Hamlib NET rigctld server
│   ├── server.py            #   TCP server
│   ├── handler.py           #   command dispatch
│   ├── routing.py           #   rigctld ↔ Radio protocol bridge
│   └── circuit_breaker.py   #   fault isolation
│
├── scope.py                 # Spectrum/waterfall scope processing
├── scope_render.py          # Scope rendering pipeline
├── discovery.py             # LAN radio discovery (UDP broadcast)
├── cli.py                   # CLI entry point (`icom-lan` command)
├── env_config.py            # Environment variable config (ICOM_*)
├── startup_checks.py        # Pre-flight checks (port available, device found, …)
├── proxy.py                 # Multi-client proxy for shared radio access
├── sync.py                  # Sync wrappers around async API
└── meter_cal.py             # S-meter / power / SWR calibration tables
```

---

## Dependencies

```toml
# core (always installed)
pyserial, pyserial-asyncio

# optional groups (install with uv sync --extra <group>)
[audio]   opuslib
[bridge]  opuslib, sounddevice, numpy
[scope]   pillow>=10.0
[webrtc]  aiortc>=1.9
```

Import guards for optional deps follow the pattern in `usb_driver.py` —
use a lazy `_require_*()` helper that raises `ImportError` with an install hint on first use.

---

## LightRAG knowledge base (MCP)

A LightRAG knowledge base is pre-configured as the `lightrag` MCP server in your Claude Code
installation. Use it **before** writing any protocol-level or architectural code.

```
# Search before implementing
mcp__lightrag__query_text(query="CI-V frequency set command IC-7610", mode="hybrid")
mcp__lightrag__query_text(query="Command29 dual receiver routing", mode="hybrid")
mcp__lightrag__query_text(query="audio codec negotiation PCM Opus", mode="hybrid")

# Save durable decisions / postmortems after significant work
mcp__lightrag__insert_text(text="[2026-04-09] AudioBackend protocol added: ...")
```

**When to query:**
- Before changing transport / CI-V frame handling
- Before adding a command that touches receiver routing
- Before audio codec / bridge changes
- When the issue references a prior bug or decision

**When to save:**
- Architectural decision made (and why)
- Confirmed hardware bug / firmware limitation
- Non-obvious protocol gotcha discovered during implementation

API key and endpoint are configured in `~/.claude.json` — no credentials needed here.

---

## Verification commands

```bash
# All tests (unit + contract + regression) — always use uv
uv run pytest tests/ -q --tb=short

# Skip slow/flaky tests (web_server, audio_bridge have optional-dep collection errors sometimes)
uv run pytest tests/ -q --tb=short --ignore=tests/integration

# Focus on a module area
uv run pytest tests/ -q -k "audio"
uv run pytest tests/ -q -k "transport or civ"

# Integration tests — require real IC-7610 at 192.168.55.40
uv run pytest tests/integration/ -m integration -v

# Type check
uv run mypy src/

# Lint + format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Run server locally (bind to 0.0.0.0 for normal access)
uv run icom-lan serve --host 0.0.0.0 --port 8080
```

> **Always use `uv run`** — not `python`, not `pytest` directly. The `.venv` inside the repo
> may be Python 3.11 (worktrees use a fresh venv; re-run `uv sync --all-extras` if tests fail on import).

---

## Architecture rules

### Layering (enforce this)
```
Consumers (CLI / Web / rigctld)
    ↓
radio_protocol.Radio  (+ capability protocols)
    ↓
backends.factory.create_radio()
    ↓
CoreRadio (shared command logic / CI-V routing)
    ↓
LAN transport  |  Serial transport
```

- **Never** let Web or rigctld call transport directly.
- **Never** let backends import from `web/` or `rigctld/`.
- New commands go in `commands.py` + `command_map.py` + `commander.py`.
- Public surface additions go in `radio_protocol.py` first, then the backend implements.

### Capability protocols
`radio_protocol.py` defines ~20 `Protocol` classes beyond `Radio`:
`LevelsCapable`, `MetersCapable`, `AudioCapable`, `ScopeCapable`, `DualReceiverCapable`,
`ModeInfoCapable`, `DspControlCapable`, `CwControlCapable`, `SystemControlCapable`, etc.

Check before implementing: if the method logically belongs to an existing capability, add it there.
If behavior is model-specific (e.g., unsupported on IC-705), use profile guards, not `if model ==`.

### cmd29 (dual-receiver Command29 wrapper)
- cmd29 works for: `0x07`, `0x11` (ATT), `0x14` (levels), `0x15` (meters), `0x16` (features), `0x1A`, `0x1B`
- **cmd29 does NOT work for `0x05` (Set Freq) or `0x06` (Set Mode) on IC-7610.**
  For SUB receiver changes, use the VFO-switch pattern (switch active receiver via `0x07 0xD0/0xD1`,
  then send `0x05`/`0x06` as normal).
- cmd29 support is tracked per-command in `command_spec.py`.

### CI-V encoding
- Most fields: **little-endian** (`struct.pack('<H', value)`)
- Frequencies: **BCD-encoded** (not standard int).
  14.074.000 Hz → `0x00 0x00 0x74 0x40 0x01` (right-to-left, digit pairs)
- CI-V frame format: `0xFE 0xFE [to] [from] [cmd] [...data] 0xFD`

### SET commands
CI-V SET commands are **fire-and-forget** (like wfview) — do not wait for ACK on normal
set operations. Use `_send_civ_expect()` only where a response is contractually required.

### Keep-alive
Radio drops connection without pings: ~500ms for control, ~100ms for audio.
Missing 3–5 pings = disconnect. **Do not remove or weaken the keep-alive loop.**

---

## Protocol domain gotchas

1. **Mock success ≠ hardware correctness.** MagicMock accepts any signature. Three bugs shipped
   this way (wrong `set_scope_fixed_edge` signature, Command29 wrapper in mock radio,
   TX Freq Monitor unsupported by firmware). Review signatures against real dataclasses.

2. **`cmd29` partial support.** Covered above. Key: IC-7610 silently ignores cmd29 for freq/mode.

3. **Fast reconnect can break IC-7610 session** → `civ_port=0`. Add delay on reconnect.

4. **`_civ_expects_response()` gotcha:** for GET commands with non-empty data (e.g. `0x07 0xC2`),
   the fallback may misclassify. Verify expected response type against wfview before assuming.

5. **Audio codec default:** `PCM_1CH_16BIT` (0x04). `start_audio_rx_opus` name is legacy —
   the stream delivers audio in the negotiated format. Use `_CODEC_MAP` for explicit negotiation.

6. **HTTP keepalive + WebSocket = anti-pattern.** Browser 6-connection limit kills audio WebSocket.
   Use `Connection: close` for REST endpoints.

7. **Mobile / web breakage:** check `window.onerror` first. A ReferenceError in a mobile-only
   component can silently kill the entire Svelte runtime. Scope errors ≠ network errors.

---

## Testing rules

- **TDD** — test first, then implementation. No exceptions.
- **Fix all failures in one pass.** Do not run pytest after each individual fix.
  Pattern: `uv run pytest tests/ --tb=short` → see all failures → fix all → run once.
- **Integration tests** live in `tests/integration/` and are marked `@pytest.mark.integration`.
  They require real hardware and are **never run in CI automatically**.
- Pre-existing failures are **not an excuse**. If you touch a module, the relevant suite must
  be green before claiming the work is done.
- `FakeAudioBackend` (from `audio/backend.py`) is the canonical backend for audio unit tests.
  Build on it — do not create one-off mock classes.

---

## Communication language

- **User-facing messages** (chat replies, progress updates, questions, summaries) → **Russian**
- **Code comments, docstrings, commit messages, docs, PR/issue text** → **English**

---

## Git conventions

```
feat(#NNN): short description       # new feature
fix(#NNN): short description        # bug fix
refactor: short description         # no behavior change
test: short description             # tests only
docs: short description             # docs only
chore: short description            # tooling, deps
```

- One logical change per commit.
- Do not touch unrelated files.
- Do not push/PR without running the full test suite.

---

## Completed epics (v0.14.x)

**Epic #513 — AudioBackend abstraction + smarter audio bridge** ✅ closed

All 10 issues (#514–#523) merged: AudioBackend protocol, PortAudio/FakeAudioBackend,
UsbAudioDriver refactor, AudioBridge with BridgeState machine, BridgeMetrics,
PcmResampler, DspPipeline, audio.toml config, CLI flags.

**Architecture review issues** ✅ closed

| Issue | What |
|-------|------|
| #499 | Eliminate TOCTOU race in UDP port allocation (pre-bound sockets) |
| #504 | Split commands.py into commands/ package (17 modules) |
| #505 | Decompose radio.py into scope/audio/dual-rx runtime mixins |
| #506 | Trim `__init__.py` public API from 150+ to ~30 symbols |
| #507 | Split web/handlers.py into handlers/ package |

**Epic #526 — Zero-config startup** ✅ closed

| Issue | What |
|-------|------|
| #527 | Auto-discovery integration into serve/web startup |
| #528 | CLI presets (hamradio, digimode, serial, headless) |
| #529 | Smart startup hints (banner, loopback detection) |
| #530 | Documentation — help epilog with usage examples |

**#112 — Audio bridge Linux/Windows support** ✅ closed

Cross-platform via PortAudio/sounddevice. Loopback candidates for Linux/Windows added.

---

## CLI zero-config notes

- `--host` omitted → LAN auto-discovery via UDP broadcast (3s)
- `--backend` omitted → inferred from `--serial-port` / `$ICOM_SERIAL_DEVICE`
- `--preset digimode` → bridge + rigctld + wsjtx-compat
- Startup banner shows radio/web/rigctld/bridge status + loopback hints

---

## Reference code (wfview)

`references/wfview/` — cloned for protocol research only (GPLv3, gitignored).
**Do not copy wfview code.** Study packet format and protocol logic, write independent code.

| File | What |
|------|------|
| `include/packettypes.h` | All packet structures — start here |
| `src/radio/icomudpbase.cpp` | Base UDP: connection, keep-alive, retransmit |
| `src/radio/icomudphandler.cpp` | Login / auth sequence |
| `src/radio/icomudpcivdata.cpp` | CI-V data over UDP |
| `src/radio/icomudpaudio.cpp` | Audio streaming |
| `src/radio/icomcommander.cpp` | CI-V command reference (3500+ lines, skim) |

---

## Hardware

| | |
|---|---|
| **Radio** | Icom IC-7610 |
| **LAN IP** | 192.168.55.40 |
| **USB serial** | `/dev/cu.usbserial-11320` (19200 baud) |
| **CI-V address** | 0x98 |
| **Credentials** | configured in IC-7610 network settings |
