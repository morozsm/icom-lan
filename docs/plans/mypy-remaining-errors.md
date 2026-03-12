# Remaining mypy errors (post-P0 fix)

After the 2026-03 mypy pass, the following categories of errors remain. Prefer real type fixes over broad `type: ignore`.

## Summary

- **Count:** 202 errors in 8 files (down from ~394 in 22 files).
- **Strategy:** Extend `radio_protocol.Radio` / `AudioCapable` / `ScopeCapable` with missing method stubs, or narrow types at call sites (e.g. cast to `IcomRadio` where backend is known).

## By file

| File | Main issues |
|------|-------------|
| **radio.py** | `CivFrame \| None` passed to parsers; `no-any-return`; untyped `_scope_controls`; `int(object)` overload; protocol arg-type for `CivRuntime`/`ControlPhaseRuntime`. |
| **cli.py** | `Radio` has no `__aenter__`/`__aexit__`; `AudioCapable` missing `start_audio_rx_pcm`, `stop_audio_rx_pcm`, `start_audio_tx_pcm`, `stop_audio_tx_pcm`, `push_audio_tx_pcm`, `get_audio_stats`; `Radio` missing many optional methods (antenna, date/time, dual_watch, tuner, attenuator, preamp, send_cw_text); `ScopeCapable` missing `capture_scope_frame`, `capture_scope_frames`. |
| **web/radio_poller.py** | Same as cli: `AudioCapable`/`ScopeCapable`/`Radio` missing methods. |
| **web/handlers.py** | `Radio` missing `get_system_date`, `get_system_time`, `get_dual_watch`, `get_tuner_status`, `set_tuner_status`. |
| **audio_bridge.py** | `Radio` has no `audio_bus`; optional streams/subscription/decoder (`None`); `find_loopback_device` return; `_silence` annotation. |
| **backends/icom7610/serial.py** | `SerialControlTransport`/`SerialCivTransport` assigned to `IcomTransport`; `Icom7610SerialRadio` missing mixin-style methods (`_advance_civ_generation`, `_start_civ_rx_pump`, etc.); task `None` check. |
| **civ.py** | Assignment between `_PendingRequest` and `_AckWaiter`; `Future[CivFrame] \| None` attribute access. |
| **scope_render.py** | `THEMES` / colormap values typed as `object`; index/cast for RGB tuples. |
| **_control_phase.py** | — (fixed) |

## Recommended next steps

1. **radio_protocol:** Add optional method stubs to `Radio`, `AudioCapable`, `ScopeCapable` (and optionally a single “extended” protocol) for all IC-7610-specific methods used by web/cli/audio_bridge, so that `Radio`-typed call sites type-check when given `IcomRadio`.
2. **Backends/serial:** Either make `Icom7610SerialRadio` inherit or compose the same control-phase/civ helpers as LAN (so it satisfies the same protocol), or introduce a shared protocol that both LAN and serial implement.
3. **radio.py:** Add `assert frame is not None` or narrow types before calling parse_*; type `_scope_controls`; fix `int()` overload with explicit cast or guard.
4. **civ.py:** Use a union type or separate variables for ack vs pending state so assignment is consistent.
5. **scope_render:** Use typed dict or cast for THEMES/colormap entries (e.g. `tuple[int, int, int]`).
