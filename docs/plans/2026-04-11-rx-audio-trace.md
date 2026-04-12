# RX Audio Path Trace

**Date:** 2026-04-11
**Status:** Research in progress
**Issue:** `#642`
**Base commit:** `f0e78cc0ea0fcfbafdadbb4a20167ba0bc110d6a` (`origin/main`)

## Goal

Trace the current RX audio path from `LIVE` UI selection to browser playback and identify concrete failure points for the symptom:

- user can select `LIVE`
- backend sends audio frames over `/api/v1/audio`
- browser still produces no sound

## End-to-end path on current `origin/main`

### 1. UI presents `LIVE` only if capabilities include audio

`frontend/src/components-v2/wiring/state-adapter.ts:440-460`

- `toRxAudioProps(...)` sets `hasLiveAudio = hasCap(caps, 'audio')`
- `monitorMode` becomes `'live'` only when `audioState.rxEnabled && hasLiveAudio`

`frontend/src/components-v2/panels/RxAudioPanel.svelte:19-26`

- `buildMonitorOptions(hasLiveAudio)` includes `LIVE` only when `hasLiveAudio === true`

So if the UI shows `LIVE`, the frontend already believes runtime audio capability is present.

### 2. Selecting `LIVE` starts browser RX audio

`frontend/src/components-v2/wiring/command-bus.ts:536-547`

- `onMonitorModeChange('live')`
- clears mute state
- restores AF level if needed
- calls `audioManager.startRx()`

### 3. `audioManager` opens `/api/v1/audio` and forwards every binary frame to `RxPlayer`

`frontend/src/lib/audio/audio-manager.ts:79-85`

- `startRx()` sets `rxEnabled = true`
- starts `RxPlayer`
- opens audio WS via `connect()`

`frontend/src/lib/audio/audio-manager.ts:137-167`

- opens `ws://.../api/v1/audio`
- on open, sends `{ type: 'audio_start', direction: 'rx' }`
- on every `ArrayBuffer`, calls `this.rxPlayer.feed(ev.data)`

### 4. `RxPlayer` only understands two web transport codecs

`frontend/src/lib/audio/rx-player.ts:68-78`

- `CODEC_PCM16` -> `playPcm16(...)`
- `CODEC_OPUS` -> `decodeOpus(...)`

`frontend/src/lib/audio/constants.ts:3-10`

- web transport codec space is only:
  - `0x01` = Opus
  - `0x02` = PCM16

### 5. Backend maps radio codec to web codec before sending frames

`src/icom_lan/web/handlers/audio.py:172-215`

- radio codec is inspected via `radio.audio_codec`
- web codec is normalized to:
  - `AUDIO_CODEC_OPUS`
  - `AUDIO_CODEC_PCM16`

Important mappings:

- `PCM_1CH_16BIT` -> `PCM16`
- `PCM_2CH_16BIT` -> `PCM16`
- `ULAW_*` -> `PCM16` with decode in relay loop
- `PCM_1CH_8BIT` -> `PCM16` with comment `upcast in future`
- `PCM_2CH_8BIT` -> `PCM16`

### 6. Relay loop sends encoded web audio frames to browser clients

`src/icom_lan/web/handlers/audio.py:226-270`

- reads packets from the audio broadcaster subscription
- optionally decodes u-law to PCM16
- wraps payload with 8-byte web audio header
- sends it to connected clients

## Confirmed failure points

### 1. `AudioContext` can remain suspended

`frontend/src/lib/audio/rx-player.ts:35-52`

- `start()` creates `AudioContext`
- if suspended, it calls `resume()`
- playback functions still bail out when `ctx.state === 'suspended'`

`frontend/src/lib/audio/rx-player.ts:87-89`
`frontend/src/lib/audio/rx-player.ts:107-110`

Both PCM and Opus paths return immediately when the context is suspended.

Current weakness:

- no awaited resume confirmation
- no state logging
- no explicit user-gesture confirmation path

This can produce the exact symptom "frames arrive, no sound".

### 2. Opus decode silently depends on `AudioDecoder`

`frontend/src/lib/audio/rx-player.ts:107-110`

If `typeof AudioDecoder === 'undefined'`, Opus frames are ignored.

Current weakness:

- silent return
- no fallback decoder
- no user-visible error state

If backend sends Opus and the browser/runtime lacks WebCodecs `AudioDecoder`, frames can arrive with zero playback.

### 3. 8-bit PCM looks especially suspicious

`src/icom_lan/web/handlers/audio.py:177-187`

The backend explicitly maps `PCM_1CH_8BIT` and `PCM_2CH_8BIT` to web `PCM16`, but the comment says:

- `PCM_1CH_8BIT: AUDIO_CODEC_PCM16,  # upcast in future`

This is a strong red flag. The frontend `PCM16` path assumes signed 16-bit samples:

`frontend/src/lib/audio/rx-player.ts:94-102`

It reads payload using `new Int16Array(...)`.

If the payload is still 8-bit PCM but labeled as PCM16, playback can be garbage or effectively silent.

### 4. TX and RX paths are asymmetrical by design

`frontend/src/lib/audio/constants.ts:13-23`

Browser TX always sends Opus headers.

`src/icom_lan/web/handlers/audio.py:482-499`

Backend may transcode TX Opus to PCM for some radios, but RX path depends on radio codec normalization. So "TX works / RX fails" and "frames arrive / playback fails" are both plausible without a transport bug.

## Current strongest suspects

### Suspect A: AudioContext never reaches `running`

This is the simplest browser-side explanation when:

- `LIVE` is visible
- `/api/v1/audio` is connected
- frames arrive
- no sound is heard

### Suspect B: Browser receives Opus but lacks usable `AudioDecoder`

This is likely if:

- backend negotiates Opus on the radio side
- browser/runtime lacks WebCodecs `AudioDecoder`
- no console checks are in place

### Suspect C: Radio codec is 8-bit PCM, but web path labels it as PCM16

This is the strongest code-level mismatch currently visible in backend logic.

It would also fit the timeline "it worked a few days ago" if:

- the active radio/backend/codec changed
- default codec negotiation changed
- a different runtime path now feeds `PCM_1CH_8BIT`

## Supporting context

### Default codec preference is not Opus-first

`src/icom_lan/types.py:191-200`

Default preference order begins with:

- `PCM_1CH_16BIT`
- `PCM_2CH_16BIT`
- `ULAW_*`
- `PCM_*_8BIT`
- only then `OPUS_*`

So frontend behavior can differ substantially depending on which radio/backend is active, even though the WS API stays the same.

### Capability gating is separate from playback success

`src/icom_lan/web/runtime_helpers.py:17-58`

Runtime capability logic determines whether frontend exposes `LIVE`, but once `LIVE` is shown and selected, playback success depends on the browser audio pipeline above, not only on the backend transport.

## Next evidence needed

To turn the current suspects into a proven root cause, the next step should capture:

1. The first incoming RX frame header in the browser:
   - codec
   - sample rate
   - channels
2. `AudioContext.state` immediately after selecting `LIVE`
3. Whether `AudioDecoder` exists in the failing browser
4. The backend `radio.audio_codec` value on the failing radio/backend

## Current test gaps

Frontend coverage currently proves only the happy-path basics:

- `frontend/src/lib/audio/__tests__/rx-player.test.ts`
  covers `AudioContext` creation, suspended resume call, and PCM16 scheduling
- `frontend/src/components-v2/panels/__tests__/RxAudioPanel.test.ts`
  covers monitor option rendering

Important gaps:

- no tests for `audioManager` RX lifecycle or `/api/v1/audio` handling
- no tests for Opus decode path in `RxPlayer`
- no tests for `AudioDecoder === undefined`
- no tests for `ctx.state === 'suspended'` during incoming frames
- no tests for malformed or mislabeled PCM payloads
- no backend tests around `PCM_1CH_8BIT -> web PCM16` normalization

So the current code has multiple silent failure branches that are not guarded by tests.

## Minimal instrumentation plan

The next step should be a diagnostic-only patch, not a behavioral refactor.

### Frontend instrumentation

In `frontend/src/lib/audio/audio-manager.ts`:

- log the first few RX frames:
  - frame index
  - codec
  - sample rate
  - channels
  - payload length
- log when `RxPlayer.feed(...)` throws

In `frontend/src/lib/audio/rx-player.ts`:

- log `AudioContext.state` on `start()`
- log whether `resume()` was attempted and whether it resolved/rejected
- log when PCM/Opus playback is skipped because context is still suspended
- log when Opus playback is skipped because `AudioDecoder` is missing
- log decoder creation and first decode attempts

This proves whether the problem is:

- transport only
- browser audio unlock
- codec mismatch
- missing browser decoder support

### Backend instrumentation

Current backend already logs useful pieces in `src/icom_lan/web/handlers/audio.py`:

- negotiated `radio codec -> web codec`
- relay startup sample rate/channels
- packet counts

The missing piece is to make sure failing reports include those log lines from the same run.

### Evidence threshold for decision-making

After instrumentation, we should be able to classify the failure into one of these buckets:

1. `LIVE` selected, but `AudioContext` never reaches `running`
2. RX frames arrive as Opus, but browser lacks usable `AudioDecoder`
3. RX frames arrive as web `PCM16`, but negotiated radio codec is 8-bit PCM
4. RX frames never actually reach `audioManager` despite backend assumptions

Only after that classification should we choose between:

- browser playback fix
- codec normalization fix
- runtime architecture cleanup
- or a combination of the above

## Provisional conclusion

On current `origin/main`, the statement "backend sends WS audio frames" is not enough to prove the frontend should produce sound.

There are at least three plausible browser-side / codec-side failure points after transport:

- suspended `AudioContext`
- missing Opus decoder support
- backend-side codec normalization mismatch, especially for 8-bit PCM

The current code strongly suggests that the next step should be instrumentation, not speculative fixes.
