# Code review: P1 Slim Radio Protocol + P2 Audio Bridge tx_executor + test fix

**Scope:** Uncommitted changes (P1 issue 207, P2, test_audio_rx_tx_transition).  
**Reviewed:** 2026-03-11.  
**Artifacts:** `radio_protocol.py`, CLI, web (poller, server, handlers), rigctld handler, sync, `__init__.py`, `audio_bridge.py`, docs, tests.

---

## 1. Summary

The change set implements the P1 “slim” Radio protocol by introducing four new capability protocols (`LevelsCapable`, `MetersCapable`, `PowerControlCapable`, `StateNotifyCapable`), moving optional methods off the core `Radio` protocol, and updating all consumers (CLI, web, rigctld, sync) to use `isinstance` checks before calling capability-specific methods. P2 adds an optional `tx_executor` to `AudioBridge` for tuning under load. A test fix extends the mock in `test_audio_rx_tx_transition` so the poller runs PTT audio transitions. The design is consistent, capability guards are applied where needed, and tests pass. No critical or important issues were found; a few minor suggestions are listed below.

---

## 2. Critical (must fix before commit)

**None.** No bugs, wrong behaviour, or broken contracts were identified.

---

## 3. Important (should fix)

**None.** No logic gaps, inconsistent error handling, or missing checks were found.

- **Capability guards:** CLI, web handlers, web poller, rigctld handler, and sync wrapper all check the appropriate capability (e.g. `isinstance(radio, PowerControlCapable)`) before calling moved methods. When the radio does not support a capability, CLI/handlers return a clear error; rigctld falls back to cache or `ENIMPL`; sync raises `AttributeError` with a clear message.
- **Radio without capability in poller:** For `SetPowerstat`, `SetPower`, `SetRfGain`, `SetAfLevel`, `SetSquelch`, the poller does a silent no-op when the radio does not implement the capability. This is acceptable (command is dropped without failing the poller). Optionally, a debug log could be added for “command X not supported by this radio” for observability; not required for correctness.

---

## 4. Minor / suggestions

- **Poller silent no-op:** When the poller processes e.g. `SetPowerstat` or `SetRfGain` and the radio is not `PowerControlCapable` / `LevelsCapable`, consider a single debug log line (e.g. “radio does not support power/levels, skipping”) to make troubleshooting easier. Not blocking.

- **CLI `_cmd_meter` and ALC:** Using `hasattr(radio, "get_alc")` to optionally add ALC to meter getters is consistent with “optional beyond MetersCapable.” If `get_alc` is ever standardised on a protocol, consider a small protocol (e.g. `AlcCapable`) or document that ALC remains an optional extension; current approach is fine.

- **Type safety (mypy):** `radio_poller.py` and other modified files are in a codebase that already has mypy errors elsewhere (e.g. `Radio` has no attribute `set_antenna_1`, `start_audio_tx_opus` / `stop_audio_tx` on `AudioCapable`). The new capability checks and protocol usage do not introduce new type errors; existing issues are outside this change set. No change required in this PR.

- **Ruff:** Pre-existing ruff findings (e.g. TID251 in `__init__.py`, E402 in `_shared_state_runtime.py`) are unrelated to the modified code. No new style issues were introduced.

- **Docstrings:** `radio_protocol.py` docstrings for the new protocols are clear. `audio_bridge.py` documents `tx_executor` and its default (`None` = default pool) well. Optional: in `sync.py`, the `get_swr` docstring says “0-255” but the protocol returns `float`; the implementation correctly normalises with `int(raw) if isinstance(raw, float) else raw`. A short note in the docstring that the protocol may return float could avoid confusion.

- **Tests:**  
  - `test_bridge_tx_loop_uses_custom_executor` correctly patches `run_in_executor` and asserts the custom executor is used; timing with `asyncio.sleep(0.08)` is a bit brittle but acceptable.  
  - `_capable_radio()` in `test_handlers_coverage.py` correctly provides the capability methods needed for enqueue tests.  
  - `test_audio_rx_tx_transition` mock now includes `audio_bus`, `start_audio_rx_opus`, `stop_audio_rx_opus`, `push_audio_tx_opus` so the poller runs PTT audio transitions; the comment explaining `isinstance(radio, AudioCapable)` is helpful.

- **Backward compatibility:** `IcomRadio` keeps `power_control(on)` as a thin wrapper around `set_powerstat(on)`. Callers (including tests and sync’s `power_control()`) continue to work. No change needed.

---

## 5. Positive

- **Protocol design:** Clean split of core `Radio` vs optional capabilities; `@runtime_checkable` and `isinstance` are used consistently. Plan document (`docs/plans/p1-radio-protocol-slim-plan.md`) matches the implementation and is a good reference.

- **Consistency across consumers:** Same pattern everywhere: check capability → call method or return/raise with a clear message. CLI uses stderr and exit code 1; handlers raise `ValueError` with a descriptive message; rigctld returns cache or `ENIMPL`; sync raises `AttributeError` with a message that names the required protocol.

- **Rigctld fallback:** When the radio is not `MetersCapable`, `_cmd_get_level` uses cached S-meter, RF power, and SWR when available before returning `ENIMPL`, which is correct for servers that receive state from the web layer.

- **Web server:** Registration of state-change and reconnect callbacks is correctly gated on `StateNotifyCapable`, avoiding attribute errors on minimal backends.

- **Audio bridge (P2):** Optional `tx_executor` is backward compatible (`None` = default pool), documented in the docstring and in `docs/guide/audio-recipes.md` (heavy usage section). The test that asserts the custom executor is used is clear and targeted.

- **Docs:** `docs/api/public-api-surface.md` lists the new protocols and the note about using `isinstance` before calling capability methods. Audio recipes explain when and how to pass a dedicated executor and recommend process separation for heavy deployments.

- **Test fix:** Extending the mock in `test_audio_rx_tx_transition` so the poller actually runs PTT-on/off audio transitions (by satisfying `AudioCapable`) improves coverage of the real code path without changing production code.

---

**Conclusion:** The change set is ready to commit from a correctness and consistency perspective. No critical or important issues; only optional minor improvements are suggested.
