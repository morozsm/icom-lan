# Audio Backend Abstraction + Smarter Audio Bridge

**Date:** 2026-04-09
**Status:** Design (not implemented)
**Scope:** Variant A (near-term) + Variant B extension seam

---

## 1. Problem Statement

The current `AudioBridge` (`audio_bridge.py`) routes PCM between the radio and a virtual audio device (e.g. BlackHole) so that third-party apps (WSJT-X, fldigi, JS8Call) can use the radio as a sound card. It works, but has several pain points:

### Device-name coupling
- `find_loopback_device()` does substring matching on display names (`"BlackHole"`, `"Loopback"`, `"VB-Audio"`, `"Virtual"`).
- Display names are locale-dependent and change across OS updates. A user who upgrades macOS or installs a second virtual device may silently get the wrong device.
- There is no concept of a **stable device ID** (CoreAudio UID, PipeWire object-id, WASAPI endpoint-id) — only the integer `index` returned by `sounddevice.query_devices()`, which is session-ephemeral.

### No auto-detect / auto-connect
- If the device disappears mid-session (e.g. BlackHole unloaded), the bridge crashes with a sounddevice `PortAudioError`. No reconnect.
- If the user omits `--device`, the bridge tries four hardcoded name patterns. If none match, the user must know the exact substring.

### Sample-rate mismatch potential
- `AudioBridge` hardcodes `SAMPLE_RATE = 48000`. The radio always sends 48 kHz, but some virtual devices default to 44.1 kHz. If the user's system audio graph disagrees, CoreAudio silently resamples — adding latency and potential artefacts.
- No explicit sample-rate negotiation or mismatch detection.

### No level normalization
- Radio PCM levels vary by radio model and mode. WSJT-X expects roughly -26 dB FS for proper decode.
- There is a basic noise gate (`silence_threshold = 10`) in the TX path, but no RX level management, no limiter, no configurable target.

### Metrics are minimal
- `stats` tracks frame counts, drops, and inter-frame intervals. No underrun/overrun counters from the audio backend, no jitter measurement, no latency breakdown (radio→bridge, bridge→device).

### Two separate audio subsystems
- `AudioBridge` (LAN path) and `UsbAudioDriver` (serial path) both open `sounddevice` streams, both do device selection, but share no code.
- `UsbAudioDriver` already has a better device model (`UsbAudioDevice` dataclass, `select_usb_audio_devices()` with override + auto-pick, topology resolution). `AudioBridge` duplicates this logic poorly.

---

## 2. Proposed Architecture

### 2.1 Core Interfaces

```python
# src/icom_lan/audio/backend.py

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Callable, AsyncIterator


class AudioDeviceId:
    """Stable, platform-specific device identifier.

    Wraps the native persistent ID (CoreAudio UID string, PipeWire
    object-id, WASAPI endpoint-id) alongside the ephemeral integer index
    used by sounddevice/PortAudio.
    """
    __slots__ = ("platform_uid", "index", "display_name")

    def __init__(self, platform_uid: str, index: int, display_name: str) -> None:
        self.platform_uid = platform_uid  # stable across sessions
        self.index = index                # ephemeral, used by sounddevice
        self.display_name = display_name  # human-readable


class StreamDirection(enum.Enum):
    INPUT = "input"    # capture (device → app)
    OUTPUT = "output"  # playback (app → device)


@dataclass(frozen=True, slots=True)
class AudioDeviceInfo:
    """Normalized device descriptor — superset of current UsbAudioDevice."""
    id: AudioDeviceId
    input_channels: int
    output_channels: int
    default_samplerate: int = 48_000
    supported_samplerates: tuple[int, ...] = (48_000,)
    is_virtual: bool = False         # True for BlackHole, Loopback, etc.
    is_default_input: bool = False
    is_default_output: bool = False

    @property
    def supports_rx(self) -> bool:
        return self.input_channels > 0

    @property
    def supports_tx(self) -> bool:
        return self.output_channels > 0

    @property
    def duplex(self) -> bool:
        return self.supports_rx and self.supports_tx


@runtime_checkable
class RxStream(Protocol):
    """Inbound audio stream contract (device → app)."""

    async def read(self, num_frames: int) -> tuple[bytes, bool]:
        """Read PCM frames. Returns (pcm_data, overflowed)."""
        ...

    def stop(self) -> None: ...
    def close(self) -> None: ...

    @property
    def active(self) -> bool: ...
    @property
    def device(self) -> AudioDeviceId: ...


@runtime_checkable
class TxStream(Protocol):
    """Outbound audio stream contract (app → device)."""

    async def write(self, pcm_data: bytes) -> int:
        """Write PCM frames. Returns frames written."""
        ...

    def stop(self) -> None: ...
    def close(self) -> None: ...

    @property
    def active(self) -> bool: ...
    @property
    def device(self) -> AudioDeviceId: ...


@runtime_checkable
class AudioBackend(Protocol):
    """Abstract audio backend — the main extension point."""

    @property
    def name(self) -> str:
        """Backend identifier (e.g. 'portaudio', 'coreaudio', 'pipewire')."""
        ...

    def list_devices(self) -> list[AudioDeviceInfo]: ...

    def find_device(
        self,
        *,
        name: str | None = None,
        uid: str | None = None,
        virtual_only: bool = False,
    ) -> AudioDeviceInfo | None: ...

    async def open_rx_stream(
        self,
        device: AudioDeviceId,
        *,
        sample_rate: int = 48_000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> RxStream: ...

    async def open_tx_stream(
        self,
        device: AudioDeviceId,
        *,
        sample_rate: int = 48_000,
        channels: int = 1,
        frame_ms: int = 20,
    ) -> TxStream: ...
```

### 2.2 Backend Implementations

#### `PortAudioBackend` (default, cross-platform)

- Wraps `sounddevice` (PortAudio bindings) — the dependency we already have.
- Implements `AudioBackend` by delegating to `sd.InputStream` / `sd.OutputStream`.
- `AudioDeviceId.platform_uid`: on macOS, query CoreAudio `kAudioDevicePropertyDeviceUID` via `ctypes` call to `AudioObjectGetPropertyData`. On Linux/Windows, fall back to `f"{name}:{hostapi}"` as a semi-stable identifier (PortAudio does not expose native IDs).
- Virtual device detection: check name against known patterns + check `hostapi` for loopback-class APIs.
- This replaces both `find_loopback_device()` in `audio_bridge.py` and `list_usb_audio_devices()` in `usb_driver.py` with a single implementation.

#### `CoreAudioLoopbackBackend` (macOS, future Variant A enhancement)

- Not a new driver — just a `PortAudioBackend` subclass that filters to virtual/loopback devices and uses CoreAudio-native UIDs for stable identification.
- Can query `kAudioDevicePropertyDeviceIsAlive` for hotplug detection.
- Can read/set device sample rate via `kAudioDevicePropertyNominalSampleRate`.

#### Future placeholders (Variant B extension seam)

```python
# These are NOT implemented — only the Protocol seam exists.

class PipeWireBackend:
    """Linux: native PipeWire integration (avoids PortAudio overhead)."""
    name = "pipewire"
    # Would use pw-cli / libpipewire via ctypes or subprocess

class WasapiBackend:
    """Windows: native WASAPI loopback capture."""
    name = "wasapi"
    # Would use comtypes or pyaudiowpatch
```

### 2.3 Backend Registry and Selection

```python
# src/icom_lan/audio/backends/__init__.py

_BACKENDS: dict[str, type[AudioBackend]] = {}

def register_backend(name: str, cls: type[AudioBackend]) -> None:
    _BACKENDS[name] = cls

def get_backend(name: str | None = None) -> AudioBackend:
    """Get backend by name, or auto-detect the best available."""
    if name:
        return _BACKENDS[name]()
    # Auto-detect: try platform-specific first, fall back to portaudio
    for candidate in ("coreaudio", "pipewire", "wasapi", "portaudio"):
        if candidate in _BACKENDS:
            return _BACKENDS[candidate]()
    raise RuntimeError("No audio backend available")
```

### 2.4 Unified Architecture Diagram

```
                  ┌─────────────────────────┐
                  │     AudioBridge v2       │
                  │  (bridge + DSP pipeline) │
                  └────────┬────────────────┘
                           │
              ┌────────────▼────────────────┐
              │       AudioBackend          │  ← Protocol
              │  list_devices()             │
              │  find_device()              │
              │  open_rx_stream()           │
              │  open_tx_stream()           │
              └────────────┬────────────────┘
                           │
          ┌────────────────┼────────────────────┐
          │                │                    │
  PortAudioBackend   CoreAudioBackend    (PipeWire/WASAPI)
  (sounddevice)      (macOS loopback)     future stubs
```

Both `AudioBridge` (LAN path) and `UsbAudioDriver` (serial path) would use the same `AudioBackend` interface, eliminating the duplicated device enumeration and stream management code.

---

## 3. Bridge Behavior (Variant A)

### 3.1 Auto-detect Device Selection

Priority order when `--device` is not specified:

1. **Saved preference**: check `~/.config/icom-lan/audio.toml` for `bridge.device_uid`.
2. **Virtual device heuristic**: scan `list_devices()`, filter `is_virtual == True`, prefer devices with "BlackHole" or "Loopback" in name.
3. **Most-recently-used**: if multiple virtual devices exist, prefer the one used in the last session (stored in config).
4. **Fail with actionable error**: list available virtual devices and suggest `brew install blackhole-2ch`.

When `--device` is specified, resolve it as:
- Exact UID match → use directly
- Substring of display name → resolve to UID, warn if ambiguous
- Integer index → use as ephemeral fallback, warn about instability

### 3.2 Auto-connect / Reconnect

```
State machine:

  IDLE ──start()──► CONNECTING ──device_found──► RUNNING
                        │                           │
                        │                     device_lost/error
                        │                           │
                        ◄───── RECONNECTING ◄───────┘
                              (backoff: 1s, 2s, 4s, max 30s)
                              │
                        max_retries (10)
                              │
                              ▼
                          FAILED ──start()──► CONNECTING
```

- On device disappearance: close streams, enter RECONNECTING.
- On each retry: re-enumerate devices, try to find the same UID.
- Emit a `bridge_state_changed` event (for Web UI status display).
- Log at WARNING on each retry, ERROR on FAILED.

### 3.3 Sample-rate Policy

**Default:** match radio (48 kHz). Always.

**Mismatch handling:**
1. Query device's supported sample rates via backend.
2. If 48 kHz is supported → use it (most virtual devices support this).
3. If not supported → insert a resampler in the pipeline. Use `samplerate` library (already available via numpy ecosystem) or `scipy.signal.resample_poly`.
4. Warn the user: `"Device 'X' does not support 48kHz natively; resampling from 48kHz to 44.1kHz (adds ~5ms latency)."`.

**CLI override:** `--bridge-sample-rate 44100` forces a specific rate (user takes responsibility for quality).

### 3.4 Level Normalization

DSP pipeline (optional, off by default to preserve existing behavior):

```
Radio PCM ──► [Noise Gate] ──► [Normalizer] ──► [Limiter] ──► Device
Device PCM ──► [Noise Gate] ──► [Normalizer] ──► [Limiter] ──► Radio
```

**Components:**

| Stage | Default | Description |
|-------|---------|-------------|
| **Noise gate** | threshold=-60 dBFS, hold=50ms | Suppress silence/noise during RX gaps. TX already has this (threshold=10 ≈ -70 dBFS). |
| **Normalizer** | target=-26 dBFS RMS | Slow-tracking RMS normalizer (attack 100ms, release 1s). -26 dBFS is the WSJT-X sweet spot. |
| **Limiter** | ceiling=-1 dBFS | Hard limiter to prevent clipping. Lookahead 1ms for transparent limiting. |

**CLI flags:**
- `--bridge-normalize` — enable the DSP pipeline (off by default)
- `--bridge-level-target -26` — target RMS in dBFS
- `--bridge-noise-gate -60` — noise gate threshold in dBFS
- `--bridge-no-limiter` — disable the limiter

All DSP operates on int16 PCM in numpy. No additional dependencies needed.

### 3.5 Metrics & Observability

Extend `bridge.stats` to include:

```python
@dataclass
class BridgeMetrics:
    # Existing
    rx_frames: int = 0
    tx_frames: int = 0
    rx_drops: int = 0
    uptime_seconds: float = 0.0

    # New: backend-reported
    rx_underruns: int = 0       # sounddevice xrun count
    tx_overruns: int = 0
    rx_latency_ms: float = 0.0  # sounddevice reported latency
    tx_latency_ms: float = 0.0

    # New: bridge-measured
    rx_jitter_ms: float = 0.0   # stddev of inter-frame intervals
    tx_jitter_ms: float = 0.0
    rx_peak_dbfs: float = -96.0 # current peak level
    tx_peak_dbfs: float = -96.0
    rx_rms_dbfs: float = -96.0  # current RMS level
    tx_rms_dbfs: float = -96.0

    # State
    state: str = "idle"         # idle/connecting/running/reconnecting/failed
    device_name: str = ""
    device_uid: str = ""
    sample_rate_actual: int = 0
    resampling: bool = False
```

Expose via:
- `bridge.metrics` property (for CLI periodic logging)
- WebSocket event `bridge_metrics` (for Web UI level meters)
- Structured JSON log at INFO every 60s when running

---

## 4. Configuration Surface

### 4.1 CLI Changes

**New flags (on `audio bridge` subcommand):**

| Flag | Type | Description |
|------|------|-------------|
| `--device-uid UID` | str | Select device by stable platform UID |
| `--device NAME` | str | Select device by display name (existing, kept) |
| `--auto` | flag | Auto-detect virtual device (default when no device specified) |
| `--sample-rate HZ` | int | Force output sample rate (default: match radio) |
| `--normalize` | flag | Enable level normalization pipeline |
| `--level-target DB` | float | Target RMS in dBFS (default: -26) |
| `--noise-gate DB` | float | Noise gate threshold in dBFS (default: -60) |
| `--no-limiter` | flag | Disable hard limiter |
| `--backend NAME` | str | Force audio backend (portaudio/coreaudio/pipewire) |
| `--reconnect` | flag | Auto-reconnect on device loss (default: on) |
| `--no-reconnect` | flag | Disable auto-reconnect |

**Deprecation:**
- `--bridge "BlackHole 2ch"` on the `web` subcommand → emits deprecation warning, maps to `--bridge-device "BlackHole 2ch"`. Remove in v1.0.

**New on `web` subcommand:**
- `--bridge-device-uid`, `--bridge-normalize`, `--bridge-level-target` (mirror the `audio bridge` flags).

### 4.2 Config File

```toml
# ~/.config/icom-lan/audio.toml

[bridge]
device_uid = "BlackHole2ch_UID"   # stable platform UID
auto_detect = true                 # fall back to heuristic if UID not found
reconnect = true
reconnect_max_retries = 10

[bridge.levels]
normalize = false
target_rms_dbfs = -26.0
noise_gate_dbfs = -60.0
limiter = true
limiter_ceiling_dbfs = -1.0

[bridge.sample_rate]
policy = "match_radio"  # "match_radio" | "force"
force_rate = 48000       # only used when policy = "force"
```

CLI flags override config file values. Config file overrides defaults.

### 4.3 RadioProfile Integration

The existing `RadioProfile` (per-radio persistent config) gains an optional `[audio_bridge]` section:

```toml
[audio_bridge]
preferred_sample_rate = 48000
default_normalize = true
default_level_target = -26.0
```

This allows per-radio tuning (e.g., IC-705 may need different levels than IC-7610).

---

## 5. Testing Plan

### 5.1 FakeAudioBackend

```python
# tests/fakes/fake_audio_backend.py

class FakeAudioBackend:
    """Deterministic audio backend for unit tests.

    - Devices are injected at construction time
    - Streams record all writes and return canned reads
    - No sounddevice/numpy dependency
    """

    def __init__(self, devices: list[AudioDeviceInfo]) -> None:
        self._devices = devices
        self.opened_streams: list[tuple[str, AudioDeviceId]] = []
        self.rx_data: list[bytes] = []  # canned RX data
        self.tx_written: list[bytes] = []  # captured TX data

    # ... implements AudioBackend protocol
```

### 5.2 Unit Tests

| Test file | Coverage |
|-----------|----------|
| `tests/test_audio_backend.py` | `AudioDeviceId` creation, `AudioDeviceInfo` properties, backend registry |
| `tests/test_audio_bridge_v2.py` | Bridge state machine (IDLE→CONNECTING→RUNNING→RECONNECTING→FAILED), device selection priority, reconnect backoff |
| `tests/test_audio_dsp.py` | Noise gate (silence vs. signal), normalizer (convergence to target RMS), limiter (ceiling enforcement), passthrough when disabled |
| `tests/test_audio_levels.py` | dBFS conversion helpers, RMS calculation, peak detection — pure math, no audio deps |
| `tests/test_audio_metrics.py` | Metrics accumulation, jitter calculation, level tracking |
| `tests/test_audio_samplerate.py` | Resampler correctness (48k→44.1k round-trip within tolerance), passthrough when rates match |
| `tests/test_portaudio_backend.py` | PortAudioBackend with mocked `sounddevice` module — device enumeration, UID extraction, virtual detection |

### 5.3 Integration Tests

```python
@pytest.mark.integration
@pytest.mark.skipif(not HAS_SOUNDDEVICE, reason="sounddevice not installed")
class TestPortAudioBackendReal:
    """Run against real system audio devices — never in CI."""

    def test_list_devices_returns_nonempty(self): ...
    def test_open_and_close_stream(self): ...
    def test_write_silence_no_error(self): ...
```

### 5.4 Optional Dependency Gating

Tests that import `sounddevice` or `numpy` must be gated:

```python
HAS_SOUNDDEVICE = importlib.util.find_spec("sounddevice") is not None
HAS_NUMPY = importlib.util.find_spec("numpy") is not None

pytestmark = pytest.mark.skipif(
    not (HAS_SOUNDDEVICE and HAS_NUMPY),
    reason="requires icom-lan[bridge]",
)
```

---

## 6. Migration / Compatibility

### Phase 1: Add AudioBackend, keep old bridge working

1. Introduce `AudioBackend` protocol and `PortAudioBackend` in `src/icom_lan/audio/backend.py`.
2. Refactor `UsbAudioDriver` to use `PortAudioBackend` internally (it already has the cleanest device model — start here).
3. `AudioBridge` remains unchanged externally. Internally, replace `find_loopback_device()` with `PortAudioBackend.find_device(virtual_only=True)`.
4. `--bridge "BlackHole 2ch"` continues to work identically.

### Phase 2: New bridge features

5. Add `--device-uid`, `--normalize`, `--reconnect` flags.
6. Add DSP pipeline (off by default).
7. Add `BridgeMetrics` and WebSocket events.
8. Deprecation warning on `--bridge` positional argument in `web` subcommand.

### Phase 3: Consolidation

9. `UsbAudioDriver` becomes a thin wrapper around `AudioBackend` + topology resolver.
10. Remove `find_loopback_device()` and `list_audio_devices()` from `audio_bridge.py` (moved to backend).

### Backward Compatibility Guarantees

- `AudioBridge(radio, device_name="BlackHole 2ch")` API unchanged through all phases.
- `--bridge "BlackHole 2ch"` CLI flag works through v1.0 (deprecation warning in Phase 2).
- `icom-lan[bridge]` extras unchanged (`sounddevice`, `numpy`).
- No new required dependencies. `samplerate` library is optional (graceful fallback to scipy or skip resampling with warning).

---

## 7. Risks / Non-Goals

**Repo boundary note:** Any future **native virtual audio device** implementation (HAL/PipeWire/WASAPI) can be kept proprietary in `icom-lan-pro`. `icom-lan` should only define the backend abstraction + integration seam, and continue to support existing third-party virtual devices (BlackHole/Loopback/VB-Cable) as backends.

### Risks

| Risk | Mitigation |
|------|-----------|
| **CoreAudio UID extraction requires ctypes** | Isolate in a `_macos_uid.py` module. Fall back to name-based ID on failure. Test on macOS 13+. |
| **Resampler quality** | Use `samplerate` (libsamplerate bindings, high quality). Fall back to scipy. Document that resampling adds latency. |
| **PortAudio hotplug is unreliable** | Don't rely on PortAudio callbacks for device loss. Instead, poll `device_is_alive` every 2s in the reconnect watchdog. |
| **DSP pipeline adds latency** | Measure and document. Noise gate + normalizer + limiter on a 960-sample frame should be <0.1ms on any modern CPU. Keep it optional. |
| **Config file proliferation** | Use a single `audio.toml` rather than adding to the main config. Keep it optional — CLI flags and defaults are sufficient. |

### Non-Goals

- **Writing a virtual audio driver** (HAL plugin, PipeWire module, WASAPI loopback capture driver). We only define the integration seam (`AudioBackend` protocol) for a future implementation.
- **Multi-radio bridge** (bridging multiple radios to different virtual devices simultaneously). Out of scope — would require a bridge manager.
- **Audio effects** (EQ, compression, DSP beyond normalization). The pipeline is extensible but we only implement gate + normalizer + limiter.
- **Replacing sounddevice** with a different PortAudio binding. `sounddevice` is mature and well-maintained.
- **Android/iOS support.** Mobile platforms have entirely different audio APIs.

---

## 8. Follow-up Issues Checklist (Variant A Implementation)

1. **[ ] `AudioBackend` protocol + `PortAudioBackend`** — Define `AudioBackend`, `AudioDeviceId`, `AudioDeviceInfo`, `RxStream`, `TxStream` protocols in `src/icom_lan/audio/backend.py`. Implement `PortAudioBackend` wrapping `sounddevice`. Include `FakeAudioBackend` for tests.

2. **[ ] Stable device UIDs on macOS** — Add `_macos_uid.py` that queries `kAudioDevicePropertyDeviceUID` via ctypes. Integrate into `PortAudioBackend.list_devices()`. Fall back to `"{name}:{hostapi}"` on non-macOS.

3. **[ ] Refactor `UsbAudioDriver` to use `AudioBackend`** — Replace internal `sounddevice` calls with `PortAudioBackend`. Keep `select_usb_audio_devices()` logic and topology resolver, but delegate stream open/close to the backend.

4. **[ ] Refactor `AudioBridge` to use `AudioBackend`** — Replace `find_loopback_device()`, `list_audio_devices()`, and direct `sd.OutputStream`/`sd.InputStream` usage with `AudioBackend` calls. Add `virtual_only=True` filtering.

5. **[ ] Bridge reconnect state machine** — Implement IDLE→CONNECTING→RUNNING→RECONNECTING→FAILED states. Add exponential backoff. Emit `bridge_state_changed` events. Add tests with `FakeAudioBackend` that simulates device disappearance.

6. **[ ] Sample-rate negotiation** — Query device supported rates from backend. Add resampler (optional `samplerate` dep) when 48 kHz not natively supported. Add `--bridge-sample-rate` CLI flag.

7. **[ ] Level normalization DSP pipeline** — Implement noise gate, RMS normalizer, hard limiter operating on int16 numpy arrays. Add `--bridge-normalize`, `--bridge-level-target`, `--bridge-noise-gate` CLI flags. All off by default.

8. **[ ] `BridgeMetrics` + WebSocket events** — Replace `bridge.stats` dict with typed `BridgeMetrics` dataclass. Add underrun/overrun tracking, jitter, peak/RMS levels. Emit `bridge_metrics` WebSocket event for Web UI level meters.

9. **[ ] CLI flag updates + deprecations** — Add `--device-uid`, `--backend`, `--reconnect`/`--no-reconnect` flags. Add deprecation warning for `--bridge DEVICE` positional on `web` subcommand. Update help text and docs.

10. **[ ] Config file support (`audio.toml`)** — Define schema. Implement load/save in `src/icom_lan/config/audio_config.py`. Wire into `AudioBridge` constructor (CLI flags > config file > defaults). Store last-used device UID.
