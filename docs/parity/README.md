# IC-7610 Parity Matrix

`ic7610_command_matrix.json` is the maintained source of truth for wfview parity work on IC-7610 command coverage.

Status rules:
- `implemented`: maintained support exists through a user-facing library/runtime surface or through an internal primitive that exposed features directly depend on.
- `partial`: tested low-level/runtime support exists, but parity is not fully exposed through `IcomRadio`, CLI, Web, or rigctld-facing state.
- `missing`: no maintained parity surface is claimed yet. Generic `send_civ()` access does not count as parity coverage.

Family mapping:
- `baseline_core` -> pre-M4 baseline (no open issue owner)
- `dsp_levels` -> `#130`
- `operator_toggles` -> `#131`
- `vfo_dualwatch_scan` -> `#132`
- `memory_bandstack` -> `#133`
- `tone_repeater` -> `#134`
- `system_config` -> `#135`
- `transceiver_status` -> `#136`
- `advanced_scope` -> `#137`

Update workflow:
1. Edit only the affected command entries in `ic7610_command_matrix.json`.
2. Update family counts and total counts in the same file.
3. Update the parity summary line in `docs/PROJECT.md`.
4. Run `PYTHONPATH=src pytest -q tests/test_ic7610_parity_matrix.py`.
5. Run the explicit parity smoke profile:
   `PYTHONPATH=src pytest -q tests/integration -m "integration and ic7610_parity"`.

Explicit parity smoke profile:
- Marker: `ic7610_parity`
- Current coverage focus:
  - `baseline_core` stateful smoke (`snapshot_state()` / `restore_state()`)
  - `advanced_scope` lifecycle smoke on LAN and serial backends
- Serial-only parity smoke continues to require `ICOM_SERIAL_DEVICE` and the usual
  scope gate (`ICOM_ALLOW_SERIAL_SCOPE=1` or `ICOM_ALLOW_SCOPE=1`).
