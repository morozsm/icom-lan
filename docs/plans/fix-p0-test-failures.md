# Plan: 100% test pass after P0 decomposition

**Goal:** All tests pass when running `pytest -v -m "not integration"` (no real radio).

**Root cause:** After P0, many methods moved from IcomRadio/Icom7610CoreRadio to composed runtimes (ControlPhaseRuntime, CivRuntime, AudioRecoveryRuntime). Tests still call them on the radio instance or the class.

---

## 1. Delegation shims on Icom7610CoreRadio (radio.py)

Add host methods so that ControlPhaseRuntime and Icom7610SerialRadio can call them; serial backend already calls `self._advance_civ_generation`, `self._start_civ_rx_pump`, etc.

Add to **Icom7610CoreRadio** (in radio.py, after __init__ or in a clear "host shims" block):

```python
def _advance_civ_generation(self, reason: str) -> None:
    self._civ_runtime.advance_generation(reason)

def _start_civ_rx_pump(self) -> None:
    self._civ_runtime.start_pump()

def _start_civ_data_watchdog(self) -> None:
    self._civ_runtime.start_data_watchdog()

def _start_civ_worker(self) -> None:
    self._civ_runtime.start_worker()
```

Icom7610SerialRadio already implements `_stop_civ_data_watchdog` and uses the above for connect; with these on the core, serial will inherit them.

---

## 2. _flush_queue (class-level)

Tests call `await IcomRadio._flush_queue(mock_transport)`. The implementation is `ControlPhaseRuntime._flush_queue(transport)` (static).

**Option A:** Add to IcomRadio (or Icom7610CoreRadio) a class method that delegates:

```python
@staticmethod
async def _flush_queue(transport: IcomTransport, max_pkts: int = 200) -> int:
    from ._control_phase import ControlPhaseRuntime
    return await ControlPhaseRuntime._flush_queue(transport, max_pkts)
```

**Option B:** Change tests to use a radio instance: `await radio._control_phase._flush_queue(mock_transport)` (tests need a fixture that creates a radio).

Prefer **Option A** so existing test signatures stay.

---

## 3. Test file mapping: call runtime instead of radio

Replace calls on `radio` with the correct runtime. Use the table below.

| Test calls | Replace with |
|------------|--------------|
| `radio._wrap_civ(civ)` | `radio._civ_runtime._wrap_civ(civ)` |
| `radio._start_watchdog()` | `radio._control_phase._start_watchdog()` |
| `radio._stop_watchdog()` | `radio._control_phase._stop_watchdog()` |
| `radio._stop_reconnect()` | `radio._control_phase._stop_reconnect()` |
| `radio._start_token_renewal()` | `radio._control_phase._start_token_renewal()` |
| `radio._stop_civ_data_watchdog` (patch or call) | patch `radio._civ_runtime.stop_data_watchdog` or `await radio._civ_runtime.stop_data_watchdog()` |
| `radio._start_civ_rx_pump` (patch or call) | patch `radio._civ_runtime.start_pump` or `radio._civ_runtime.start_pump()` |
| `radio._capture_audio_snapshot` (patch or call) | patch `radio._audio_runtime._capture_audio_snapshot` or `radio._audio_runtime._capture_audio_snapshot()` |

**Files to edit:**

- **test_radio_connect.py:** _flush_queue → keep IcomRadio._flush_queue if shim added (1), else use radio._control_phase._flush_queue with fixture.
- **test_radio_extended.py:** test_wrap_civ → radio._civ_runtime._wrap_civ(civ). test_flush_queue_* → keep class call if shim added.
- **test_reconnect.py:** All _start_watchdog, _stop_watchdog, _stop_reconnect → radio._control_phase.*
- **test_token_renewal.py:** _start_token_renewal → radio._control_phase._start_token_renewal()
- **test_scope_stress.py:** _start_civ_rx_pump() → radio._civ_runtime.start_pump()
- **test_radio_coverage.py:** All patch.object(radio, "_stop_watchdog") → patch.object(radio._control_phase, "_stop_watchdog"). Same for _stop_reconnect, _stop_civ_data_watchdog (patch radio._civ_runtime.stop_data_watchdog or the method used in disconnect). _start_civ_rx_pump → patch radio._civ_runtime.start_pump. _capture_audio_snapshot → patch radio._audio_runtime._capture_audio_snapshot.
- **test_audio_recovery.py:** radio._capture_audio_snapshot() → radio._audio_runtime._capture_audio_snapshot()

---

## 4. Icom7610SerialRadio (backends/icom7610/serial.py)

Serial backend calls `self._advance_civ_generation`, `self._start_civ_rx_pump`, `self._start_civ_data_watchdog`, `self._start_civ_worker`. After adding these to Icom7610CoreRadio (1), serial will inherit them. Ensure serial’s `_start_civ_data_watchdog` does not override the core’s in a way that breaks (serial has its own watchdog loop; it may override and call super or its own implementation). Current code shows serial defines `_start_civ_data_watchdog` and `_stop_civ_data_watchdog` locally. So serial does not inherit _start_civ_data_watchdog from core; it has its own. So the only missing on serial are _advance_civ_generation and _start_civ_rx_pump and _start_civ_worker. Adding those to the core gives serial those three. Serial already has _start_civ_data_watchdog. So we only need the four methods on the core; serial will use _advance_civ_generation, _start_civ_rx_pump, _start_civ_worker from core and keep its own _start_civ_data_watchdog.

---

## 5. Timeout / connection-dependent tests

- **test_radio_connect.py::test_connect_raises_on_status_rejection_after_retries** — TimeoutError: login response timed out. Likely needs a mock that simulates rejection without real network; adjust mock or skip in CI.
- **test_radio_coverage.py::test_soft_reconnect_does_full_connect_when_ctrl_dead** — same.
- **test_sync_coverage.py::test_sync_wrappers_delegate_and_return_values** — ConnectionError: Not connected. Test probably needs a connected radio mock or to mock at a lower level so that sync wrappers get values without a real connection.

Fix by improving mocks (e.g. ensure transport/connect mocks return or resolve so that “login” does not time out) or by marking as integration if they require real network.

---

## 6. test_server_wire (RPRT -4)

Tests expect numeric values but get `b'RPRT -4\n'` (Hamlib error). The mock radio or poller does not provide level/strength/SWR; the handler returns an error. Adjust the test’s mock so that the poller (or radio) returns valid level data when the handler asks, so that the response is numeric. Alternatively relax the assertion if RPRT -4 is the intended behavior when levels are unavailable.

---

## 7. test_web_server_coverage::test_start_and_stop_with_radio_sets_callbacks

Assertion: `set_state_change_callback` expected to be called once, called 0 times. The web server or poller is supposed to call `set_state_change_callback` on the radio when starting. After P0, the place that sets the callback might have changed. Find where the server/poller sets the state change callback and ensure it is still invoked when the test starts the server with a radio; or update the test to assert the actual current behavior (e.g. callback set on a different object).

---

## Execution order

1. Add delegation shims to Icom7610CoreRadio and _flush_queue class method (radio.py).
2. Update all unit tests to use runtimes (table in §3) and fix patches in test_radio_coverage.
3. Fix or isolate timeout/connection tests (§5).
4. Fix test_server_wire mocks or expectations (§6).
5. Fix test_web_server_coverage callback assertion (§7).
6. Run `pytest -v -m "not integration"` until 100% of non-skipped tests pass.
