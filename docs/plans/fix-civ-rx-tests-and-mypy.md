# Plan: Fix test_civ_rx_coverage + mypy

**Status:** Done (agents completed; one follow-up fix applied).

## Context

After P0 Core Runtime Decomposition (see `p0-core-runtime-decomposition.md`), methods that used to live on `IcomRadio` / `Icom7610CoreRadio` were moved into **CivRuntime** (`_civ_rx.py`). The host (radio) holds `_civ_runtime: CivRuntime(self)` and delegates. Tests in `tests/test_civ_rx_coverage.py` still call these methods on the radio instance, causing 111 failures (AttributeError).

Separately, **mypy** reports 394 errors in 22 files (strict zone `icom_lan.web.*`, optional deps without stubs, protocol/host attribute mismatches).

---

## Task 1: Fix test_civ_rx_coverage.py (agent 1)

**Goal:** All tests in `tests/test_civ_rx_coverage.py` pass by calling the right object.

**Strategy:** Call methods on `radio._civ_runtime` instead of `radio` where the method was moved to CivRuntime.

**Mapping (radio → radio._civ_runtime):**

| Test calls on radio | Correct call |
|---------------------|--------------|
| `radio._update_radio_state_from_frame(frame)` | `radio._civ_runtime._update_radio_state_from_frame(frame)` |
| `radio._notify_change(name, data)` | `radio._civ_runtime._notify_change(name, data)` |
| `radio._ensure_civ_runtime()` | `radio._civ_runtime._ensure_civ_runtime()` (no args) |
| `radio._publish_scope_frame(...)` | `radio._civ_runtime._publish_scope_frame(...)` |
| `radio._publish_civ_event(...)` | `radio._civ_runtime._publish_civ_event(...)` |
| `radio._start_civ_worker()` | `radio._civ_runtime.start_worker()` (public API) |
| `radio._drain_ack_sinks_before_blocking()` | `radio._civ_runtime._drain_ack_sinks_before_blocking()` |
| `radio._cleanup_stale_civ_waiters()` | `radio._civ_runtime._cleanup_stale_civ_waiters()` |
| `radio._stop_civ_rx_pump()` | `await radio._civ_runtime.stop_pump()` (async) |
| `radio._civ_expects_response(...)` | Likely static or on CivRuntime: check `_civ_rx.py` and use `CivRuntime._civ_expects_response(...)` or `radio._civ_runtime._civ_expects_response(...)` |

**Fixtures:** Keep `radio` and `radio_with_state` as IcomRadio; they already have `_civ_runtime` (set in `IcomRadio.__init__`). Ensure `radio_with_state` has `_radio_state` set (already does) because CivRuntime reads `self._host._radio_state` inside `_update_radio_state_from_frame`.

**Async:** Replace any sync call to `_stop_civ_rx_pump` with `await radio._civ_runtime.stop_pump()` and ensure the test is async where needed.

**Do not:** Change test logic or expectations; only change the object that receives the call (radio → radio._civ_runtime).

**Verification:** Run `pytest tests/test_civ_rx_coverage.py -v --tb=short` and ensure all tests pass.

---

## Task 2: Reduce mypy errors (agent 2)

**Goal:** Fix mypy errors so that `mypy src/` exits 0 or with a much smaller, documented allowlist.

**Scope (priority order):**

1. **Unused type: ignore / wrong error codes**  
   Remove or fix `type: ignore` comments that mypy reports as unused or that use wrong error codes (e.g. in `_control_phase.py`, `serial_civ_link.py`, `rigctld/server.py`, `radio.py`).

2. **Missing type parameters**  
   Add generic parameters where mypy complains (e.g. `dict` → `dict[K, V]`, `Task` → `Task[None]`, `Callable` → `Callable[..., T]`) in `radio_state.py`, `transport.py`, `radio.py`, `audio_bridge.py`, `_civ_rx.py`, `web/server.py`, etc.

3. **Protocol / host attribute errors**  
   Ensure `CivRuntimeHost` and `ControlPhaseHost` in `_runtime_protocols.py` declare all attributes that `_civ_rx.py` and `_control_phase.py` access on `self._host`. Add missing attributes or adjust code so host types satisfy the protocols.

4. **Optional third-party stubs**  
   For optional deps (`opuslib`, `PIL`, `sounddevice`): add `type: ignore[import-untyped]` or stub packages if available, or exclude those modules from strict checking so that the rest of the codebase is clean.

5. **Remaining files**  
   Fix `transport.py` override, `proxy.py` override, `civ.py` assignment/union, `web/radio_poller.py` and `web/handlers.py` missing attributes on `Radio`, `rigctld/handler.py`, `backends/icom7610` where feasible.

**Constraints:**  
- Prefer fixes that improve type safety; avoid broad `# type: ignore` without a comment.  
- For `icom_lan.web.*`, mypy is already strict; keep it that way and fix errors.

**Verification:** Run `mypy src/` and record remaining errors (if any) in a short comment or doc; aim for zero or a small, justified allowlist.

---

## Execution

- **Agent 1 (explore + edits):** Implement Task 1 in `tests/test_civ_rx_coverage.py` and run the test file until all tests pass.
- **Agent 2 (generalPurpose):** Implement Task 2 across `src/`; run `mypy src/` and fix errors in priority order; document any remaining issues.

Both agents work in the same repo; avoid conflicting edits (Agent 1 touches only tests, Agent 2 only src/ and possibly pyproject/tool.mypy overrides).
