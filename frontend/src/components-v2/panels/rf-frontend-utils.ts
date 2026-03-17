/**
 * Utility functions for the RF Front End panel.
 */

export interface AttOption {
  value: number;
  label: string;
}

export interface PreOption {
  value: number;
  label: string;
}

/** Format an ATT value in dB to a display label. */
export function formatAttLabel(dB: number): string {
  return dB === 0 ? 'OFF' : `${dB}dB`;
}

/** Format a PRE level to a display label (0=OFF, 1=P1, 2=P2, …). */
export function formatPreLabel(level: number): string {
  return level === 0 ? 'OFF' : `P${level}`;
}

/** Build SegmentedButton options for the ATT control from a list of dB values. */
export function buildAttOptions(values: number[]): AttOption[] {
  return values.map((v) => ({ value: v, label: formatAttLabel(v) }));
}

/** Build SegmentedButton options for the PRE control from a list of levels. */
export function buildPreOptions(values: number[]): PreOption[] {
  return values.map((v) => ({ value: v, label: formatPreLabel(v) }));
}

/**
 * Determine whether the RF Front End panel should be visible at all.
 * The panel is hidden when none of its three controls are available.
 */
export function shouldShowPanel(hasRfGain: boolean, hasAtt: boolean, hasPre: boolean): boolean {
  return hasRfGain || hasAtt || hasPre;
}
