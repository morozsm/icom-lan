import { clamp } from '$lib/utils/meter-utils';

/** Arc starts at 210° (lower-left) and ends at 330° (lower-right), sweeping
 *  clockwise through 270° (straight up in SVG coords). */
export const GAUGE_START_DEG = 210;
export const GAUGE_END_DEG = 330;
export const GAUGE_SWEEP_DEG = GAUGE_END_DEG - GAUGE_START_DEG; // 120

/**
 * Map a normalized value (0–1) to a needle angle in SVG degrees.
 * 0 → 210° (left), 0.5 → 270° (top), 1 → 330° (right).
 */
export function valueToNeedleAngle(v: number): number {
  return GAUGE_START_DEG + clamp(v, 0, 1) * GAUGE_SWEEP_DEG;
}

/**
 * Color for a position on the active arc relative to the danger zone.
 * Transitions: green → yellow (at 87.5% of dangerZone) → red (at dangerZone).
 */
export function gaugeArcColor(pos: number, dangerZone = 0.8): string {
  if (pos >= dangerZone) return '#F14C42';
  if (pos >= dangerZone * 0.875) return '#F2CF4A';
  return '#14A665';
}

/** Position (0–1) where the yellow warning zone begins. */
export function yellowZoneStart(dangerZone: number): number {
  return dangerZone * 0.875;
}
