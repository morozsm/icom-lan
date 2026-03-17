export interface MonitorOption {
  value: string;
  label: string;
}

/**
 * Builds the options array for the monitor mode SegmentedButton.
 *
 * LOCAL and MUTE are always present. LIVE is included only when the
 * WebSocket audio stream is available.
 */
export function buildMonitorOptions(hasLive: boolean): MonitorOption[] {
  const options: MonitorOption[] = [{ value: 'local', label: 'LOCAL' }];
  if (hasLive) {
    options.push({ value: 'live', label: 'LIVE' });
  }
  options.push({ value: 'mute', label: 'MUTE' });
  return options;
}

/**
 * Returns a human-readable status string for the current monitor mode.
 */
export function formatMonitorStatus(mode: string): string {
  switch (mode) {
    case 'local':
      return 'Radio speaker output';
    case 'live':
      return 'Browser audio stream';
    case 'mute':
      return 'Audio muted';
    default:
      return '';
  }
}
