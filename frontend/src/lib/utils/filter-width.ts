/**
 * IC-7610 default filter widths (Hz) by mode and filter number.
 * These are factory defaults — user may customize via radio menu.
 */
const FILTER_TABLE: Record<string, [number, number, number]> = {
  // [FIL1, FIL2, FIL3]
  'USB':    [2400, 1800, 500],
  'LSB':    [2400, 1800, 500],
  'CW':     [500,  250,  50],
  'CW-R':   [500,  250,  50],
  'RTTY':   [500,  250,  250],
  'RTTY-R': [500,  250,  250],
  'AM':     [9000, 6000, 3000],
  'FM':     [15000, 10000, 7000],
  'SSB':    [2400, 1800, 500],
};

/**
 * Get filter passband width in Hz for a given mode and filter number (1-3).
 * Returns 0 if mode/filter unknown.
 */
export function getFilterWidthHz(mode: string, filter: number): number {
  const entry = FILTER_TABLE[mode?.toUpperCase()];
  if (!entry) return 0;
  const idx = Math.max(0, Math.min(2, (filter || 1) - 1));
  return entry[idx];
}
