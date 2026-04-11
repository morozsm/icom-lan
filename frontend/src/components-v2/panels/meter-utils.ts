import { getMeterCalibration, getMeterRedline } from '$lib/stores/capabilities.svelte';

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
 * Converts a capabilities MeterCalPoint[] to piecewise knots [raw, actual][].
 * Returns null if calibration data is unavailable.
 */
function calToKnots(meterType: string): [number, number][] | null {
  const cal = getMeterCalibration(meterType);
  if (!cal || cal.length < 2) return null;
  return cal.map((p) => [p.raw, p.actual] as [number, number]);
}

/**
 * Returns knots from capabilities, falling back to hardcoded defaults.
 */
function getKnots(meterType: string, fallback: [number, number][]): [number, number][] {
  return calToKnots(meterType) ?? fallback;
}

// ---- Hardcoded IC-7610 fallback constants ----

/**
 * IC-7610 CI-V Reference p.4: 00 00=0%, 01 43=50%, 02 12=100%
 */
const PO_KNOTS: [number, number][] = [
  [0, 0],
  [143, 50],
  [212, 100],
];

/**
 * IC-7610 CI-V Reference p.4: 00 00=1.0, 00 48=1.5, 00 80=2.0, 01 20=3.0
 */
const SWR_KNOTS: [number, number][] = [
  [0, 1.0],
  [48, 1.5],
  [80, 2.0],
  [120, 3.0],
];

/** IC-7610 ALC max raw value */
const ALC_MAX_DEFAULT = 120;

/** IC-7610 S-meter: S9 = raw 120, S9+60 = raw 241 */
const S9_RAW_DEFAULT = 120;
const S9_PLUS60_RAW_DEFAULT = 241;

// ---- Public formatters ----

/**
 * Formats raw RF power (BCD 0-255) as watts string.
 */
export function formatPowerWatts(raw: number): string {
  const knots = getKnots('power', PO_KNOTS);
  const watts = Math.round(piecewise(raw, knots));
  return `${watts}W`;
}

/**
 * Normalizes RF power for bar gauge (0-1 scale).
 */
export function normalizePower(raw: number): number {
  const knots = getKnots('power', PO_KNOTS);
  const maxWatts = knots[knots.length - 1][1];
  return maxWatts > 0 ? piecewise(raw, knots) / maxWatts : 0;
}

/**
 * Formats raw SWR value (BCD 0-255) as SWR ratio string.
 */
export function formatSwr(raw: number): string {
  if (raw >= 255) return '∞';
  const knots = getKnots('swr', SWR_KNOTS);
  return piecewise(raw, knots).toFixed(1);
}

/**
 * Formats raw ALC value (BCD 0-255) as percentage string.
 */
export function formatAlc(raw: number): string {
  const alcMax = getMeterRedline('alc') ?? ALC_MAX_DEFAULT;
  const pct = Math.round((Math.max(0, Math.min(alcMax, raw)) / alcMax) * 100);
  return `${pct}%`;
}

/**
 * Returns S-meter calibration boundaries: [s9Raw, s9Plus60Raw].
 */
function getSmeterBounds(): [number, number] {
  const cal = getMeterCalibration('s_meter');
  if (cal && cal.length >= 2) {
    // Find S9 and S9+60 calibration points
    const s9 = cal.find((p) => p.label === 'S9');
    const s9p60 = cal.find((p) => p.label === 'S9+60dB' || p.label === 'S9+60');
    if (s9 && s9p60) return [s9.raw, s9p60.raw];
    // Fallback: last two points as S9 boundary and max
    if (cal.length >= 2) return [cal[cal.length - 2].raw, cal[cal.length - 1].raw];
  }
  return [S9_RAW_DEFAULT, S9_PLUS60_RAW_DEFAULT];
}

/**
 * Formats raw S-meter value (BCD 0-255) as an S-unit string.
 */
export function formatSMeter(raw: number): string {
  const [s9Raw, s9Plus60Raw] = getSmeterBounds();
  if (raw >= s9Raw) {
    // S9+ range
    const span = s9Plus60Raw - s9Raw;
    const db = span > 0 ? Math.round(((raw - s9Raw) / span) * 60) : 0;
    return db > 0 ? `S9+${db}` : 'S9';
  }
  // S0-S9 range
  const s = s9Raw > 0 ? Math.round((raw / s9Raw) * 9) : 0;
  return `S${s}`;
}

/**
 * Returns needle gauge mark positions and labels for the given meter source.
 * Uses capabilities calibration data when available, IC-7610 defaults otherwise.
 */
export function getNeedleMarks(source: MeterSource): Mark[] {
  switch (source) {
    case 'S': {
      const [s9Raw, s9Plus60Raw] = getSmeterBounds();
      return [
        { pos: (s9Raw * (1 / 9)) / 255, label: 'S1' },
        { pos: (s9Raw * (3 / 9)) / 255, label: 'S3' },
        { pos: (s9Raw * (5 / 9)) / 255, label: 'S5' },
        { pos: (s9Raw * (7 / 9)) / 255, label: 'S7' },
        { pos: s9Raw / 255, label: 'S9' },
        { pos: (s9Raw + (s9Plus60Raw - s9Raw) * (20 / 60)) / 255, label: '+20' },
        { pos: (s9Raw + (s9Plus60Raw - s9Raw) * (40 / 60)) / 255, label: '+40' },
      ];
    }
    case 'SWR': {
      const knots = getKnots('swr', SWR_KNOTS);
      return knots.map(([rawVal, swrVal]) => ({
        pos: rawVal / 255,
        label: swrVal.toFixed(1),
      }));
    }
    case 'POWER':
    case 'po': {
      return [
        { pos: 0.0, label: '0' },
        { pos: 0.25, label: '25' },
        { pos: 0.5, label: '50' },
        { pos: 0.75, label: '75' },
        { pos: 1.0, label: '100' },
      ];
    }
  }
}
