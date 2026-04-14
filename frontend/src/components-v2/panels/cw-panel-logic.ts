/** Break-in mode index → display label */
export const BREAK_IN_LABELS: Record<number, string> = { 0: 'OFF', 1: 'SEMI', 2: 'FULL' };

/** Format break-in mode for display */
export function formatBreakIn(mode: number): string {
  return BREAK_IN_LABELS[mode] ?? 'OFF';
}

/** Whether break-in is active (mode > 0) */
export function isBreakInActive(mode: number): boolean {
  return mode > 0;
}

/** Whether APF is active (mode > 0) */
export function isApfActive(mode: number): boolean {
  return mode > 0;
}
