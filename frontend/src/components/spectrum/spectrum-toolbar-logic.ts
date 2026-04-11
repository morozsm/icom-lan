/**
 * Pure functions and constants extracted from SpectrumToolbar.svelte.
 * All functions are side-effect-free and independently testable.
 */

/* ── Constants ── */

export const SPAN_LABELS: Record<number, string> = {
  0: '\u00b12.5k', 1: '\u00b15k', 2: '\u00b110k', 3: '\u00b125k',
  4: '\u00b150k', 5: '\u00b1100k', 6: '\u00b1250k', 7: '\u00b1500k',
};

export const SPEED_LABELS: Record<number, string> = { 0: 'FST', 1: 'MID', 2: 'SLO' };

/** Scope mode buttons: [modeIndex, label] */
export const MODE_BUTTONS: [number, string][] = [[0, 'CTR'], [1, 'FIX'], [2, 'S-C'], [3, 'S-F']];

/* ── Layer visibility ── */

export function toggleLayer(hiddenLayers: string[], layer: string): string[] {
  return hiddenLayers.includes(layer)
    ? hiddenLayers.filter(l => l !== layer)
    : [...hiddenLayers, layer];
}

export function isLayerVisible(hiddenLayers: string[], layer: string): boolean {
  return !hiddenLayers.includes(layer);
}

/* ── Scope mode predicates ── */

/** SPAN is only meaningful in center modes (0=CTR, 2=S-C) */
export function isSpanApplicable(mode: number | undefined): boolean {
  return mode === 0 || mode === 2;
}

/** EDGE selector is shown in FIX (1) and SCROLL-F (3) modes */
export function isEdgeApplicable(mode: number | undefined): boolean {
  return mode === 1 || mode === 3;
}

/* ── Range clamps ── */

export function clampSpan(current: number, delta: number): number {
  return Math.max(0, Math.min(7, current + delta));
}

/**
 * Clamp speed value after applying delta.
 * Note: delta is inverted — higher speed value = slower sweep.
 */
export function clampSpeed(current: number, delta: number): number {
  return Math.max(0, Math.min(2, current - delta));
}

export function clampBrt(current: number, delta: number): number {
  return Math.max(-30, Math.min(30, current + delta));
}

export function clampRef(current: number, delta: number): number {
  return Math.max(-30, Math.min(10, current + delta));
}
