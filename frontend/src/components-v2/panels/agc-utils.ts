export interface AgcOption {
  value: number;
  label: string;
}

/**
 * Builds the options array for the AGC mode SegmentedButton.
 *
 * Ensures OFF (value 0) is always the first option. If 0 is already present
 * in `modes`, it is used in place (not duplicated). Modes without a matching
 * label fall back to their string representation.
 */
export function buildAgcOptions(
  modes: number[],
  labels: Record<string, string>,
): AgcOption[] {
  const options: AgcOption[] = [];

  const hasOff = modes.includes(0);
  if (!hasOff) {
    options.push({ value: 0, label: 'OFF' });
  }

  for (const mode of modes) {
    const label = labels[String(mode)] ?? String(mode);
    options.push({ value: mode, label });
  }

  return options;
}
