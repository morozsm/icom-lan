export type MeterSource = 'S' | 'SWR' | 'POWER' | 'po';

export interface Mark {
  pos: number;
  label: string;
  color?: string;
}

/**
 * Clamps and normalizes a raw BCD meter value to 0-1.
 * IC-7610 CI-V meters use 0-255 BCD range (00 00 to 02 55).
 */
export function normalize(raw: number): number {
  return Math.max(0, Math.min(255, raw)) / 255;
}

/**
 * Piecewise linear interpolation over knot points.
 */
function piecewise(raw: number, knots: [number, number][]): number {
  const clamped = Math.max(knots[0][0], Math.min(knots[knots.length - 1][0], raw));
  for (let i = 0; i < knots.length - 1; i++) {
    const [r0, v0] = knots[i];
    const [r1, v1] = knots[i + 1];
    if (clamped <= r1) {
      const t = r1 === r0 ? 0 : (clamped - r0) / (r1 - r0);
      return v0 + t * (v1 - v0);
    }
  }
  return knots[knots.length - 1][1];
}

/**
 * Formats raw RF power (BCD 0-255) as watts string.
 * IC-7610 CI-V Reference p.4: 00 00=0%, 01 43=50%, 02 12=100%
 */
// Knot points: [bcd_raw, watts]
const PO_KNOTS: [number, number][] = [
  [0, 0],
  [143, 50],
  [212, 100],
];

export function formatPowerWatts(raw: number): string {
  const watts = Math.round(piecewise(raw, PO_KNOTS));
  return `${watts}W`;
}

/**
 * Normalizes RF power for bar gauge (0-1 scale).
 */
export function normalizePower(raw: number): number {
  return piecewise(raw, PO_KNOTS) / 100;
}

/**
 * Formats raw SWR value (BCD 0-255) as SWR ratio string.
 * IC-7610 CI-V Reference p.4: 00 00=1.0, 00 48=1.5, 00 80=2.0, 01 20=3.0
 */
const SWR_KNOTS: [number, number][] = [
  [0, 1.0],
  [48, 1.5],
  [80, 2.0],
  [120, 3.0],
];

export function formatSwr(raw: number): string {
  if (raw >= 255) return '∞';
  return piecewise(raw, SWR_KNOTS).toFixed(1);
}

/**
 * Formats raw ALC value (BCD 0-255) as percentage string.
 * IC-7610 CI-V Reference p.4: 00 00=Min, 01 20=Max
 */
export function formatAlc(raw: number): string {
  const pct = Math.round((Math.max(0, Math.min(120, raw)) / 120) * 100);
  return `${pct}%`;
}

/**
 * Formats raw S-meter value (BCD 0-255) as an S-unit string.
 * IC-7610 CI-V Reference p.4: 00 00=S0, 01 20=S9, 02 41=S9+60 dB
 */
export function formatSMeter(raw: number): string {
  if (raw >= 120) {
    // S9+ range: 120–241 → 0–60 dB over S9
    const db = Math.round(((raw - 120) / (241 - 120)) * 60);
    return db > 0 ? `S9+${db}` : 'S9';
  }
  // S0–S9 range: 0–120
  const s = Math.round((raw / 120) * 9);
  return `S${s}`;
}

/**
 * Returns needle gauge mark positions and labels for the given meter source.
 */
export function getNeedleMarks(source: MeterSource): Mark[] {
  // Positions based on IC-7610 CI-V Reference p.4 BCD values / 255
  switch (source) {
    case 'S':
      // 00 00=S0, 01 20=S9 (120/255≈0.47), 02 41=S9+60 (241/255≈0.95)
      return [
        { pos: 120 / 255 * (1 / 9), label: 'S1' },
        { pos: 120 / 255 * (3 / 9), label: 'S3' },
        { pos: 120 / 255 * (5 / 9), label: 'S5' },
        { pos: 120 / 255 * (7 / 9), label: 'S7' },
        { pos: 120 / 255, label: 'S9' },
        { pos: (120 + (241 - 120) * (20 / 60)) / 255, label: '+20' },
        { pos: (120 + (241 - 120) * (40 / 60)) / 255, label: '+40' },
      ];
    case 'SWR':
      // 00 00=1.0, 00 48=1.5, 00 80=2.0, 01 20=3.0
      return [
        { pos: 0 / 255, label: '1.0' },
        { pos: 48 / 255, label: '1.5' },
        { pos: 80 / 255, label: '2.0' },
        { pos: 120 / 255, label: '3.0' },
      ];
    case 'POWER':
    case 'po':
      return [
        { pos: 0.0, label: '0' },
        { pos: 0.25, label: '25' },
        { pos: 0.5, label: '50' },
        { pos: 0.75, label: '75' },
        { pos: 1.0, label: '100' },
      ];
  }
}
