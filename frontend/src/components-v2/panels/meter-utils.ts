export type MeterSource = 'S' | 'SWR' | 'POWER';

export interface Mark {
  pos: number;
  label: string;
  color?: string;
}

/**
 * Clamps and normalizes a raw 0-255 value to 0-1.
 */
export function normalize(raw: number): number {
  return Math.max(0, Math.min(255, raw)) / 255;
}

/**
 * Formats raw RF power (0-255) as watts string.
 * Maps linearly to 0-100W.
 */
export function formatPowerWatts(raw: number): string {
  const watts = Math.round((Math.max(0, Math.min(255, raw)) / 255) * 100);
  return `${watts}W`;
}

/**
 * Formats raw SWR value (0-255) as SWR ratio string.
 * Uses piecewise linear interpolation over calibrated knot points.
 */
export function formatSwr(raw: number): string {
  const clamped = Math.max(0, Math.min(255, raw));
  if (clamped >= 191) return '∞';

  // Knot points: [raw, swr_ratio]
  const knots: [number, number][] = [
    [0, 1.0],
    [49, 1.5],
    [79, 2.0],
    [112, 3.0],
    [143, 5.0],
    [191, 5.0], // boundary (never reached due to check above)
  ];

  for (let i = 0; i < knots.length - 1; i++) {
    const [r0, s0] = knots[i];
    const [r1, s1] = knots[i + 1];
    if (clamped <= r1) {
      const t = (clamped - r0) / (r1 - r0);
      return (s0 + t * (s1 - s0)).toFixed(1);
    }
  }
  return '∞';
}

/**
 * Formats raw ALC value (0-255) as a percentage string.
 */
export function formatAlc(raw: number): string {
  const pct = Math.round((Math.max(0, Math.min(255, raw)) / 255) * 100);
  return `${pct}%`;
}

/**
 * Formats raw S-meter value (0-255) as an S-unit string.
 * S0-S9 for the lower range, S9+dB for above S9.
 */
export function formatSMeter(raw: number): string {
  const norm = Math.max(0, Math.min(255, raw)) / 255;

  if (norm >= 0.56) {
    // S9+ range: 0.56–0.94 → 0–40 dB over S9
    const db = Math.round(((norm - 0.56) / (0.94 - 0.56)) * 40);
    return `S9+${db}`;
  }

  const s = Math.round((norm / 0.56) * 9);
  return `S${s}`;
}

/**
 * Returns needle gauge mark positions and labels for the given meter source.
 */
export function getNeedleMarks(source: MeterSource): Mark[] {
  switch (source) {
    case 'S':
      return [
        { pos: 0.06, label: 'S1' },
        { pos: 0.19, label: 'S3' },
        { pos: 0.31, label: 'S5' },
        { pos: 0.44, label: 'S7' },
        { pos: 0.56, label: 'S9' },
        { pos: 0.75, label: '+20' },
        { pos: 0.94, label: '+40' },
      ];
    case 'SWR':
      return [
        { pos: 0.06, label: '1.0' },
        { pos: 0.19, label: '1.5' },
        { pos: 0.31, label: '2.0' },
        { pos: 0.44, label: '3.0' },
        { pos: 0.56, label: '5.0' },
        { pos: 0.75, label: '∞' },
      ];
    case 'POWER':
      return [
        { pos: 0.0, label: '0' },
        { pos: 0.25, label: '25' },
        { pos: 0.5, label: '50' },
        { pos: 0.75, label: '75' },
        { pos: 1.0, label: '100' },
      ];
  }
}
