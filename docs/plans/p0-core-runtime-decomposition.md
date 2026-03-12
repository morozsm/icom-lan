# P0 Core Runtime Decomposition — Design (Issue 207)

**Goal:** Replace mixin inheritance on `Icom7610CoreRadio` with composed runtime components (ControlPhaseRuntime, CivRuntime, AudioRecoveryRuntime). Core holds instances and delegates; state remains on the host for the first iteration.

---

## 1. Method assignment to runtimes

### ControlPhaseRuntime (from _control_phase.py + disconnect/soft_reconnect from radio.py)

| Method | Origin | Public API |
|--------|--------|------------|
| `connect()` | _ControlPhaseMixin | yes |
| `disconnect()` | radio.py (move into runtime) | yes |
| `soft_reconnect()` | radio.py (move into runtime) | yes |
| `_send_token_ack()` | _ControlPhaseMixin | no |
| `_receive_guid()` | _ControlPhaseMixin | no |
| `_send_conninfo()` | _ControlPhaseMixin | no |
| `_receive_civ_port()` | _ControlPhaseMixin | no |
| `_status_retry_pause()` | _ControlPhaseMixin | no |
| `_send_open_close()` | _ControlPhaseMixin | no |
| `_send_audio_open_close()` | _ControlPhaseMixin | no |
| `_send_open_close_on_transport()` | _ControlPhaseMixin | no |
| `_wait_for_packet()` | _ControlPhaseMixin | no |
| `_flush_queue()` | _ControlPhaseMixin (static) | no |
| `_start_token_renewal()` | _ControlPhaseMixin | no |
| `_stop_token_renewal()` | _ControlPhaseMixin | no |
| `_token_renewal_loop()` | _ControlPhaseMixin | no |
| `_send_token()` | _ControlPhaseMixin | no |
| `_start_watchdog()` | _ControlPhaseMixin | no |
| `_stop_watchdog()` | _ControlPhaseMixin | no |
| `_stop_reconnect()` | _ControlPhaseMixin | no |

Note: `_force_cleanup_civ()` and `soft_disconnect()` live in radio.py and call civ_runtime/control_phase; they can remain on core and call `host._civ_runtime.stop_pump()` etc., or move into ControlPhaseRuntime. This design keeps them on core and have them call runtimes.

### CivRuntime (from _civ_rx.py)

| Method | Public API |
|--------|------------|
| `start_pump()` | yes (replaces _start_civ_rx_pump) |
| `stop_pump()` | yes (replaces _stop_civ_rx_pump) |
| `start_data_watchdog()` | yes |
| `stop_data_watchdog()` | yes |
| `start_worker()` | yes |
| `stop_worker()` | yes |
| `execute_civ_raw()` | yes (replaces _execute_civ_raw) |
| `advance_generation(reason)` | yes |
| `_advance_civ_generation()` | internal → advance_generation |
| `_cleanup_stale_civ_waiters()` | no |
| `_civ_data_watchdog_loop()` | no |
| `_ensure_civ_runtime()` | no |
| `_civ_rx_loop()` | no |
| `_route_civ_frame()` | no |
| `_update_state_cache_from_frame()` | no |
| `_update_radio_state_from_frame()` | no |
| `_notify_change()` | no |
| `_publish_scope_frame()` | no |
| `_publish_civ_event()` | no |
| `_check_connected()` | no |
| `_wait_for_civ_transport_recovery()` | no |
| `_wrap_civ()` | no |
| `_send_civ_raw()` | no |
| `_civ_expects_response()` | static |
| `_drain_ack_sinks_before_blocking()` | no |

Scope assembly and scope-related logic remain inside CivRuntime (no separate ScopeRuntime).

### AudioRecoveryRuntime (from _audio_recovery.py)

| Method | Public API |
|--------|------------|
| `capture_snapshot()` | yes (replaces _capture_audio_snapshot) |
| `recover(snapshot)` | yes (replaces _recover_audio) |

---

## 2. Attributes read/write on host (no moves)

### ControlPhaseRuntime reads/writes (ControlPhaseHost)

- _host, _port, _username, _password
- _conn_state, _has_connected_once, _auto_reconnect
- _ctrl_transport, _civ_transport, _audio_transport
- _civ_port, _audio_port, _civ_local_port, _audio_local_port
- _token, _tok_request, _auth_seq, _audio_codec, _audio_sample_rate
- _last_status_error, _last_status_disconnected
- _token_task, _watchdog_task, _reconnect_task
- _WATCHDOG_HEALTH_LOG_INTERVAL, _STATUS_RETRY_PAUSE, _STATUS_REJECT_COOLDOWN, TOKEN_RENEWAL_INTERVAL, TOKEN_PACKET_SIZE
- _civ_stream_ready, _civ_recovering, _civ_last_waiter_gc_monotonic
- Calls on host: _advance_civ_generation → host._civ_runtime.advance_generation; _start_civ_rx_pump → host._civ_runtime.start_pump(); _start_civ_data_watchdog → host._civ_runtime.start_data_watchdog(); _start_civ_worker → host._civ_runtime.start_worker(); _stop_* → host._civ_runtime.stop_*; _start_token_renewal, _stop_token_renewal, _start_watchdog, _stop_watchdog, _stop_reconnect (these stay inside ControlPhaseRuntime as internal)

### CivRuntime reads/writes (CivRuntimeHost)

- All attributes listed in CivRuntimeHost: _civ_transport, _commander, _civ_request_tracker, _civ_epoch, _civ_ack_sink_grace, _civ_get_timeout, _civ_send_seq, _last_civ_send_monotonic, _civ_min_interval, _civ_rx_task, _civ_data_watchdog_task, _civ_stream_ready, _civ_recovering, _civ_recovery_lock, _civ_recovery_wait_timeout, _last_civ_data_received, _scope_assembler, _scope_frame_queue, _scope_callback, _scope_activity_counter, _scope_activity_event, _civ_event_queue, _state_cache, _last_freq_hz, _last_mode, _filter_width, _last_vfo, _civ_retry_slice_timeout, _radio_addr, _radio_state, _on_state_change, _connected
- Calls on host: disconnect(), connect(), soft_reconnect(), _force_cleanup_civ(), _send_open_close() — these are provided by host (core) or ControlPhaseRuntime

### AudioRecoveryRuntime reads/writes (AudioRuntimeHost)

- _audio_transport, _audio_stream, _pcm_rx_user_callback, _opus_rx_user_callback, _pcm_tx_fmt, _pcm_transcoder_fmt, _pcm_rx_jitter_depth, _opus_rx_jitter_depth, _auto_recover_audio, _on_audio_recovery
- Calls on host: start_audio_rx_pcm, start_audio_rx_opus, start_audio_tx_pcm, start_audio_tx_opus (host implements these)

---

## 3. Public interface of each runtime

### ControlPhaseRuntime

- `__init__(self, host: ControlPhaseHost)`
- `async def connect(self) -> None`
- `async def disconnect(self) -> None`
- `async def soft_reconnect(self) -> None`

(Internal methods stay as private; core only calls connect/disconnect/soft_reconnect.)

### CivRuntime

- `__init__(self, host: CivRuntimeHost)`
- `def start_pump(self) -> None`  # was _start_civ_rx_pump
- `async def stop_pump(self) -> None`  # was _stop_civ_rx_pump
- `def start_data_watchdog(self) -> None`
- `async def stop_data_watchdog(self) -> None`
- `def start_worker(self) -> None`
- `async def stop_worker(self) -> None`
- `def advance_generation(self, reason: str) -> None`
- `async def execute_civ_raw(self, ...) -> Any`  # same signature as _execute_civ_raw

Core and ControlPhaseRuntime call these; other CivRuntime methods stay internal.

### AudioRecoveryRuntime

- `__init__(self, host: AudioRuntimeHost)`
- `def capture_snapshot(self) -> _AudioSnapshot | None`
- `async def recover(self, snapshot: _AudioSnapshot) -> None`

---

## 4. Call flow

### connect()

1. `core.connect()` → `await self._control_phase.connect()`
2. `ControlPhaseRuntime.connect()` runs FSM (control port, login, conninfo, CI-V port, open CI-V transport, _send_open_close).
3. At end of connect: `self._host._civ_runtime.start_pump()`, `self._host._civ_runtime.start_data_watchdog()`, `self._host._civ_runtime.start_worker()`; then token renewal and watchdog on control_phase.
4. `_send_open_close` is implemented by ControlPhaseRuntime and uses host._civ_transport; it may call host._civ_runtime for nothing (open_close is send-only). So ControlPhaseRuntime needs to call host methods: for _send_open_close the runtime can call a host method that sends open/close (could stay on host as _send_open_close and host = core implements it by building packet and using _civ_transport). So we keep _send_open_close logic inside ControlPhaseRuntime and it uses self._host._civ_transport (and self._host._send_open_close if we put that on host). Actually _send_open_close in _control_phase uses self (the mixin), so it's on the mixin. So when we move to ControlPhaseRuntime, _send_open_close will be in ControlPhaseRuntime and will use self._host._civ_transport. So no change. And at the end it calls self._host._start_civ_rx_pump() which becomes self._host._civ_runtime.start_pump().

### disconnect()

1. `core.disconnect()` → `await self._control_phase.disconnect()`
2. ControlPhaseRuntime.disconnect() stops watchdog, reconnect, token renewal; stops audio (uses host._audio_stream etc.); calls host._send_audio_open_close (must be on host or passed to runtime); then host._civ_runtime.stop_data_watchdog(), stop_worker(), stop_pump(); then civ_transport.disconnect(); then send token, ctrl_transport.disconnect(). So _send_audio_open_close and _send_open_close need to be callable from ControlPhaseRuntime — they are currently on the mixin, so they move into ControlPhaseRuntime and use host._civ_transport / host._audio_transport. So we're good.

### soft_reconnect()

1. `core.soft_reconnect()` → `await self._control_phase.soft_reconnect()`
2. ControlPhaseRuntime.soft_reconnect() does the logic currently in radio.soft_reconnect(); at end calls host._civ_runtime.start_pump(), start_worker(), etc.

### CI-V commands (e.g. get_frequency)

1. `core.get_frequency()` → eventually `await self._execute_civ_raw(...)` which becomes `return await self._civ_runtime.execute_civ_raw(...)`.

### Audio recovery (after reconnect)

1. Core or control phase calls `snapshot = self._audio_runtime.capture_snapshot()` before disconnect and `await self._audio_runtime.recover(snapshot)` after reconnect.

---

## 5. Creation order and host requirements

- Core creates `self._civ_runtime = CivRuntime(self)` first (so that control_phase can call host._civ_runtime.start_pump()).
- Then `self._control_phase = ControlPhaseRuntime(self)`.
- Then `self._audio_runtime = AudioRecoveryRuntime(self)`.

ControlPhaseHost protocol must include a method or attribute so that control_phase can start/stop civ: e.g. `_civ_runtime: CivRuntime`. So the core will have `_civ_runtime` and `_control_phase`; ControlPhaseHost is the core, so the core has _civ_runtime. So when we add ControlPhaseRuntime, the core (host) already has _civ_runtime. So we need CivRuntime to exist and be created before ControlPhaseRuntime. Order in __init__: create _civ_runtime, then _control_phase, then _audio_runtime.

---

## 6. Implementation status

Implementation complete (P0 decomposition).

- [x] Phase 2: ControlPhaseRuntime extracted; core delegates connect/disconnect/soft_reconnect; mixin removed from inheritance.
- [x] Phase 3: CivRuntime extracted; all CI-V/scope logic moved into CivRuntime (host holds state); _CivRxMixin class removed; core delegates _send_civ_raw, _check_connected, _execute_civ_raw, _update_state_cache_from_frame to runtime.
- [x] Phase 4: AudioRecoveryRuntime extracted; core delegates capture_snapshot/recover to _audio_runtime; _AudioRecoveryMixin removed from inheritance.
- [x] Phase 5: _runtime_protocols docstrings updated to reference runtimes; ControlPhaseHost now has _civ_runtime: CivRuntime; CivRuntimeHost no longer lists pump/watchdog methods (they live on CivRuntime); full test suite (non-integration) passes.
