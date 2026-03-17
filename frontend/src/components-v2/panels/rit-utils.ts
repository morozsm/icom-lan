/**
 * Utility functions for RIT/XIT panel.
 */

/**
 * Formats a frequency offset in Hz for display.
 * Positive: '+120 Hz', negative: '−50 Hz' (Unicode minus), zero: '±0 Hz'.
 */
export function formatOffset(hz: number): string {
  if (hz === 0) return '±0 Hz';
  if (hz > 0) return `+${hz} Hz`;
  return `\u2212${Math.abs(hz)} Hz`;
}

/**
 * Returns true when the RIT/XIT panel should be shown.
 */
export function shouldShowPanel(hasRit: boolean, hasXit: boolean): boolean {
  return hasRit || hasXit;
}
