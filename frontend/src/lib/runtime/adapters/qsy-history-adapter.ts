/**
 * QSY history adapter — façade over the qsy-history store.
 *
 * Lets LCD aux-row panels (e.g. AmberMemoryStrip, AmberCockpit) consume
 * and update the recent-QSY ring buffer through the runtime adapter layer
 * instead of importing `$lib/stores/qsy-history.svelte` directly
 * (CLAUDE.md → "Frontend layering").
 *
 * Read side: `deriveQsyRecent()` (Tier 2 batch 4, #1247).
 * Write side: `recordQsy(freqHz, mode)` (Tier 2 batch 5, #1248).
 *
 * The write side is a thin passthrough — debounce semantics (≥ 500 Hz
 * delta + 1.5s stability, see issue #836) live inside `qsyHistory.record()`
 * itself and are preserved unchanged.
 *
 * See `docs/plans/2026-04-29-panel-adapter-migration.md` Cluster D.
 */

import { qsyHistory, type QsyEntry } from '$lib/stores/qsy-history.svelte';

export type { QsyEntry };

/** Latest QSY entries, oldest-first (same shape as `qsyHistory.recent`). */
export function deriveQsyRecent(): readonly QsyEntry[] {
  return qsyHistory.recent;
}

/**
 * Record a potential QSY (frequency / mode). Thin passthrough to
 * `qsyHistory.record()` — the store internally debounces and filters
 * by Δ ≥ 500 Hz so dial-hunting doesn't pollute the buffer (#836).
 */
export function recordQsy(freqHz: number, mode: string): void {
  qsyHistory.record(freqHz, mode);
}
