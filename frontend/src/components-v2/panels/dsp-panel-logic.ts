/** Notch width index → display label */
export const NOTCH_WIDTH_LABELS: Record<number, string> = { 0: 'WIDE', 1: 'MID', 2: 'NARROW' };

/** AGC time constant index → display label (seconds) */
export const AGC_TIME_LABELS: Record<number, string> = {
  0: '0.1', 1: '0.3', 2: '0.6', 3: '1.0', 4: '1.5',
  5: '2.0', 6: '3.0', 7: '4.0', 8: '5.0', 9: '6.0',
};

/** Format AGC time for display */
export function formatAgcTime(index: number): string {
  return AGC_TIME_LABELS[index] ?? String(index);
}

/** Long-press duration threshold in ms */
export const LONG_PRESS_MS = 500;

/** Compute next NR mode on short toggle: off→on, on→off */
export function toggleNrMode(current: number): number {
  return current === 0 ? 1 : 0;
}

/** Compute next notch mode on short toggle: off→auto, auto/manual→off */
export function toggleNotchMode(current: 'off' | 'auto' | 'manual'): 'off' | 'auto' | 'manual' {
  return current === 'off' ? 'auto' : 'off';
}

/** Whether NR is active (mode > 0) */
export function isNrActive(mode: number): boolean {
  return mode > 0;
}

/** Whether notch is in an active state */
export function isNotchActive(mode: 'off' | 'auto' | 'manual'): boolean {
  return mode === 'auto' || mode === 'manual';
}
