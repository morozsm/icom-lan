/**
 * Returns the CSS color string for the ATU tune button based on ATU state.
 *
 * @param active - Whether the ATU is enabled
 * @param tuning - Whether the ATU is currently tuning
 * @returns CSS color string
 */
export function txStatusColor(active: boolean, tuning: boolean): string {
  if (tuning) return 'var(--v2-tx-tuning)';
  if (active) return 'var(--v2-tx-active)';
  return 'var(--v2-tx-idle)';
}
