/**
 * BarGauge utility functions.
 *
 * Zone-based segment coloring for Po, SWR, ALC, COMP meters.
 * Value is normalized 0–1; segments are 0–N integers (fractional during animation).
 */

export interface Zone {
  /** Normalized end position, 0–1. */
  end: number;
  /** Active color hex string, e.g. '#14A665'. */
  color: string;
}

export const DEFAULT_ZONES: readonly Zone[] = [
  { end: 0.6, color: '#14A665' }, // green
  { end: 0.8, color: '#F2CF4A' }, // yellow
  { end: 1.0, color: '#F14C42' }, // red
];

/**
 * Map a normalized value (0–1) to a fractional segment count.
 * Clamps to [0, segCount].
 */
export function valueToSegments(value: number, segCount: number): number {
  return Math.max(0, Math.min(segCount, value * segCount));
}

/**
 * Find the zone that owns segment at index `segIndex` (0-indexed).
 * Uses the segment midpoint for zone lookup.
 */
export function getSegmentZone(
  segIndex: number,
  segCount: number,
  zones: readonly Zone[],
): Zone {
  const pos = (segIndex + 0.5) / segCount;
  return zones.find((z) => pos <= z.end) ?? zones[zones.length - 1];
}

/**
 * Return a darkened version of a hex color by blending with the panel
 * background (#07090D).
 *
 * @param hex    - Source color, e.g. '#14A665'
 * @param blend  - Fraction of source color to keep (default 0.12)
 */
export function dimColor(hex: string, blend = 0.12): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  // Panel background: #07090D
  const dr = Math.round(r * blend + 0x07 * (1 - blend));
  const dg = Math.round(g * blend + 0x09 * (1 - blend));
  const db = Math.round(b * blend + 0x0d * (1 - blend));
  return (
    '#' +
    dr.toString(16).padStart(2, '0') +
    dg.toString(16).padStart(2, '0') +
    db.toString(16).padStart(2, '0')
  );
}
