# Raw CI-V Transactions

Raw CI-V transactions are the response-capable counterpart to the
fire-and-forget `send_civ` command path. They are intentionally scoped to one
frame and one explicit expectation.

## Ownership

`CoreRadio.send_civ_transaction()` claims the existing external CAT-session
guard before sending the frame. While the guard is active, cooperating pollers
pause through `external_cat_session_active`, preventing background CI-V reads
or writes from consuming the caller's response. The guard is released in a
`finally` block on success, timeout, cancellation, and errors.

`begin_external_cat_session()` remains idempotent when the external CAT owner
already holds the guard, and `end_external_cat_session()` remains idempotent.
A transaction rejects overlapping ownership instead of interrupting an existing
external CAT session; external CAT begin likewise fails cleanly while a raw
transaction owns the guard.

## Response Matching

Transactions run on `CivRuntime`, not `RadioPoller`. They reuse the existing
CI-V RX pump and `CivRequestTracker`:

- `expect="none"` sends once and returns `status: "sent"`.
- `expect="ack"` drops orphan ACK/NAK backlog, then registers an ACK waiter
  and resolves only a fresh ACK or NAK from the active transaction.
- `expect="data"` registers a keyed response waiter and a NAK-only waiter, so
  a radio NAK returns `status: "nak"` without allowing unrelated ACK frames to
  satisfy the data expectation.

The runtime does not infer response behavior from `_civ_expects_response()` for
transactions. Callers must choose the expectation mode so vendor-specific
commands remain explicit.

## HTTP Surface

`POST /api/v1/civ/transaction` is the only HTTP endpoint that waits for raw
CI-V responses. `/api/v1/commands` and `/api/v1/commands/batch` remain queued
fire-and-forget surfaces for `send_civ`, and `wait_response=true` stays
rejected there.
