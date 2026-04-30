/**
 * QSY history adapter — read-only façade over the qsy-history store.
 *
 * Lets LCD aux-row panels (e.g. AmberMemoryStrip) consume the recent-QSY
 * ring buffer through the runtime adapter layer instead of importing
 * `$lib/stores/qsy-history.svelte` directly (CLAUDE.md → "Frontend
 * layering").
 *
 * Read-side only this batch. The write side (`recordQsy(freqHz, mode)`)
 * lands in batch 5 with AmberCockpit. See
 * `docs/plans/2026-04-29-panel-adapter-migration.md` Cluster D.
 *
 * Tier 2 batch 4 of #1063. Issue #1247.
 */

import { qsyHistory, type QsyEntry } from '$lib/stores/qsy-history.svelte';

export type { QsyEntry };

/** Latest QSY entries, oldest-first (same shape as `qsyHistory.recent`). */
export function deriveQsyRecent(): readonly QsyEntry[] {
  return qsyHistory.recent;
}
