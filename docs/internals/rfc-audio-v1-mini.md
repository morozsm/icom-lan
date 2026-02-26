# Mini RFC: Audio API v1 (PCM-first + explicit low-level API)

Status: Draft (for approval)

Related issues: #1, #2, #3, #4, #5, #6, #7, #8, #10  
Already in progress: #9 via PR #11

## 1) Problem
Current audio surface mixes low-level Opus-oriented operations and user-facing PCM workflows.
This makes API naming ambiguous, CLI scope unclear, and recovery/testing behavior under-specified.

## 2) Goals
- Provide a **PCM-first high-level API** for common workflows.
- Keep a clear **explicit low-level Opus API** for advanced users.
- Define deterministic defaults and capability introspection.
- Add runtime stats and predictable recovery semantics.
- Preserve backward compatibility with a deprecation window.

## 3) Non-goals
- No protocol redesign.
- No breaking changes in one release.
- No broad refactor outside audio/CLI/test/doc scope.

## 4) Decisions

### D1. API split: explicit low-level vs high-level

#### Low-level (Opus, explicit naming)
- `start_audio_rx_opus(callback, *, jitter_depth=5)`
- `stop_audio_rx_opus()`
- `start_audio_tx_opus()`
- `push_audio_tx_opus(opus_bytes)`
- `stop_audio_tx_opus()`

#### High-level (PCM)
- `start_audio_rx_pcm(callback, *, sample_rate=48000, channels=1, frame_ms=20)`
- `stop_audio_rx_pcm()`
- `start_audio_tx_pcm(*, sample_rate=48000, channels=1, frame_ms=20)`
- `push_audio_tx_pcm(pcm_bytes)`
- `stop_audio_tx_pcm()`

### D2. Backward compatibility + deprecation
- Keep current methods (`start_audio_rx`, `start_audio_tx`, `push_audio_tx`, etc.) as aliases to low-level behavior.
- Emit `DeprecationWarning` with replacement hints.
- Deprecation window: two minor releases.
- Remove ambiguous aliases at next major.

### D3. Internal transcoder layer
- Add internal PCM<->Opus transcoder abstraction.
- Use `opuslib` when available (`pip install icom-lan[audio]`).
- If missing, high-level PCM APIs raise actionable error:
  `Audio codec backend unavailable; install icom-lan[audio]`.

### D4. Capabilities model + deterministic defaults
Add `AudioCaps` model and API:
- `get_audio_caps()` returns:
  - supported codecs
  - supported sample rates
  - supported channel counts
  - default codec/rate/channels

CLI:
- `icom-lan audio caps [--json]`

Default selection (deterministic):
1. Prefer Opus mono 48k
2. Else Opus stereo 48k
3. Else best PCM mode
4. If no valid combo -> clear validation error

### D5. Runtime stats contract
Add `get_audio_stats()` shape (JSON-friendly):
- `packet_loss_pct` (0..100)
- `jitter_ms`
- `underruns`
- `overruns`
- `est_latency_ms`
- `rx_packets`, `tx_packets`

Stats availability: during active stream and for a short terminal window after stop.

### D6. Recovery model
Optional auto-recover after reconnect:
- config: `auto_recover=True`, `recover_max_attempts=5`
- state events: `recovering`, `recovered`, `failed`
- single active stream invariant (no duplicate RX/TX tasks)

### D7. CLI scope
Add `icom-lan audio` command group:
- `audio rx --out rx.wav --seconds 10`
- `audio tx --in tx.wav`
- `audio loopback --seconds 10`
- `audio caps`

Common flags:
- `--sample-rate`, `--channels`, `--json`, `--stats`

## 5) Delivery plan (by issue dependency)

### Phase A (foundation)
- #1 Transcoder layer
- #10 Naming + deprecation map

### Phase B (public APIs)
- #2 RX high-level PCM API
- #3 TX high-level PCM API
- #8 Capability introspection + defaults

### Phase C (CLI + observability)
- #4 CLI audio subcommands
- #6 Runtime stats API + `--stats`

### Phase D (resilience + CI)
- #7 Auto-recover behavior
- #5 E2E + CI stabilization

## 6) Test strategy
- Unit tests for transcoder adapters and validation.
- Integration tests for RX/TX/loopback (normal + reconnect).
- CLI smoke tests for all new subcommands.
- CI split:
  - Fast smoke on each PR
  - Heavier integration profile on schedule/manual

## 7) Risks
- Opus backend differences across platforms.
- Reconnect race conditions in async tasks.
- Stats drift if metric units are not fixed in docs/tests.

Mitigation:
- strict typed errors,
- state machine invariants,
- unit-tested metric contract and fixtures.

## 8) Acceptance mapping
- #1/#2/#3: high-level PCM APIs operational and tested
- #4: CLI audio workflow commands work end-to-end
- #5: CI smoke/integration split stable
- #6: `get_audio_stats()` + CLI stats output
- #7: reconnect recovery behavior deterministic
- #8: `audio caps` + safe defaults
- #10: naming map + deprecation warnings + migration notes

## 9) Open questions for maintainer approval
1. Deprecation window length: exactly 2 minor releases OK?
2. Keep current ambiguous names as low-level aliases or add hard warnings immediately?
3. Should `--stats` print periodic stream stats (live) or end-of-run summary by default?
4. Is `opuslib` optional dependency acceptable as the default high-level backend?
