export interface DspOption {
  value: string | number;
  label: string;
}

/**
 * Returns true when the given mode string is a CW mode.
 */
export function isCwMode(mode: string): boolean {
  return mode === 'CW' || mode === 'CW-R';
}

/**
 * Builds the options array for the NR mode SegmentedButton.
 * Values: 0=OFF, 1=NR1, 2=NR2, 3=NR3
 */
export function buildNrOptions(): DspOption[] {
  return [
    { value: 0, label: 'OFF' },
    { value: 1, label: 'NR1' },
    { value: 2, label: 'NR2' },
    { value: 3, label: 'NR3' },
  ];
}

/**
 * Builds the options array for the Notch mode SegmentedButton.
 */
export function buildNotchOptions(): DspOption[] {
  return [
    { value: 'off', label: 'OFF' },
    { value: 'auto', label: 'AUTO' },
    { value: 'manual', label: 'MAN' },
  ];
}
