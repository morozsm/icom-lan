/**
 * QSY history — local ring buffer of recent frequency changes.
 *
 * Not persisted, not sent to the backend. Lives for the browser
 * session only (cleared on reload). Used by LCD aux-row widgets
 * (#836 AmberMemoryStrip) to show "where was I?" chips.
 *
 * We record frequency transitions only when they look intentional:
 * - Require a minimum delta (> 500 Hz) to skip dial-hunting within
 *   the same slice of the band.
 * - Debounce ~1.5s — commit only after the frequency has been stable
 *   that long, so hold-to-spin tuning doesn't fill the buffer.
 *
 * Drop-in API:
 *   - `qsyHistory.recent` — reactive array, oldest-first.
 *   - `qsyHistory.record(freqHz, mode)` — caller-driven (an effect in
 *     the layout polls radio state and calls this).
 *   - `qsyHistory.clear()`.
 */

export interface QsyEntry {
  freqHz: number;
  mode: string;
  at: number; // Date.now() when recorded
}

const MAX_ENTRIES = 10;
const MIN_DELTA_HZ = 500;
const DEBOUNCE_MS = 1500;

let recent = $state<QsyEntry[]>([]);

// Pending commit state — the "candidate" next entry. When the frequency
// stays here for DEBOUNCE_MS we commit it; otherwise the latest value
// replaces the candidate.
let pendingFreqHz = 0;
let pendingMode = '';
let pendingTimer: ReturnType<typeof setTimeout> | null = null;

function commitPending() {
  if (pendingFreqHz <= 0) return;
  const last = recent.length > 0 ? recent[recent.length - 1] : null;
  if (last && Math.abs(last.freqHz - pendingFreqHz) < MIN_DELTA_HZ) return;
  const entry: QsyEntry = {
    freqHz: pendingFreqHz,
    mode: pendingMode,
    at: Date.now(),
  };
  const next = recent.length >= MAX_ENTRIES ? recent.slice(1) : [...recent];
  next.push(entry);
  recent = next;
}

export const qsyHistory = {
  get recent(): readonly QsyEntry[] {
    return recent;
  },

  /**
   * Record a potential QSY. Caller passes live frequency + mode;
   * the store debounces internally and only commits stable values.
   */
  record(freqHz: number, mode: string): void {
    if (!Number.isFinite(freqHz) || freqHz <= 0) return;
    // If the same freq is already the last committed entry, skip.
    const last = recent.length > 0 ? recent[recent.length - 1] : null;
    if (last && Math.abs(last.freqHz - freqHz) < MIN_DELTA_HZ) {
      return;
    }
    // Skip if the pending candidate already matches — otherwise a reactive
    // effect that re-fires on every frame keeps restarting the debounce
    // window and `commitPending()` never runs (codex P1 on PR #932).
    if (freqHz === pendingFreqHz && mode === pendingMode) return;
    // Update the candidate; reset the debounce timer.
    pendingFreqHz = freqHz;
    pendingMode = mode;
    if (pendingTimer !== null) clearTimeout(pendingTimer);
    pendingTimer = setTimeout(() => {
      pendingTimer = null;
      commitPending();
    }, DEBOUNCE_MS);
  },

  clear(): void {
    recent = [];
    pendingFreqHz = 0;
    pendingMode = '';
    if (pendingTimer !== null) {
      clearTimeout(pendingTimer);
      pendingTimer = null;
    }
  },
};
