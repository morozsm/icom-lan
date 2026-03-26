/**
 * S-meter scale mapping utilities.
 *
 * FTX-1 calibration (from ftx1.toml):
 *   raw 0=S0, 26=S1, 52=S3, 78=S5, 103=S7, 130=S9
 *   165=S9+10, 200=S9+20, 240=S9+40, 255=max
 *
 * TODO: Load calibration from /api/v1/capabilities instead of hardcoding.
 */

const S9_RAW = 130;
const MAX_RAW = 255;

const CAL_POINTS: ReadonlyArray<{ raw: number; sUnit: number }> = [
  { raw: 0, sUnit: 0 },
  { raw: 26, sUnit: 1 },
  { raw: 39, sUnit: 2 },
  { raw: 52, sUnit: 3 },
  { raw: 65, sUnit: 4 },
  { raw: 78, sUnit: 5 },
  { raw: 91, sUnit: 6 },
  { raw: 103, sUnit: 7 },
  { raw: 117, sUnit: 8 },
  { raw: 130, sUnit: 9 },
];

const S9_PLUS_BREAKPOINTS: ReadonlyArray<{ raw: number; label: string; db: number }> = [
  { raw: 130, label: 'S9', db: 0 },
  { raw: 165, label: 'S9+10', db: 10 },
  { raw: 200, label: 'S9+20', db: 20 },
  { raw: 240, label: 'S9+40', db: 40 },
  { raw: 255, label: 'S9+50', db: 50 },
];

const DBM_BREAKPOINTS: ReadonlyArray<{ raw: number; dbm: number }> = [
  { raw: 0, dbm: -54 },
  { raw: 26, dbm: -48 },
  { raw: 52, dbm: -42 },
  { raw: 78, dbm: -36 },
  { raw: 103, dbm: -18 },
  { raw: 130, dbm: 0 },
  { raw: 165, dbm: 10 },
  { raw: 200, dbm: 20 },
  { raw: 240, dbm: 40 },
  { raw: 255, dbm: 50 },
];

/** Map raw 0-255 to fractional S-unit (0.0 - 9.0 for S0-S9). */
function rawToSFloat(raw: number): number {
  const v = Math.max(0, Math.min(MAX_RAW, raw));
  if (v <= 0) return 0;
  if (v >= S9_RAW) return 9;
  // Piecewise linear interpolation through calibration points
  for (let i = 0; i < CAL_POINTS.length - 1; i++) {
    const p0 = CAL_POINTS[i];
    const p1 = CAL_POINTS[i + 1];
    if (v <= p1.raw) {
      const t = (v - p0.raw) / (p1.raw - p0.raw);
      return p0.sUnit + t * (p1.sUnit - p0.sUnit);
    }
  }
  return 9;
}

/** Map raw 0-255 to fractional segment count 0-20. */
export function rawToSegments(raw: number): number {
  const v = Math.max(0, Math.min(MAX_RAW, raw));
  if (v <= S9_RAW) {
    // S0-S9 maps to 0-11 segments
    return (rawToSFloat(v) / 9) * 11;
  }
  // S9+ maps to 11-20 segments
  return 11 + ((v - S9_RAW) / (MAX_RAW - S9_RAW)) * 9;
}

/** Map raw 0-255 to S-unit string, e.g. "S7", "S9+20". */
export function rawToSUnit(raw: number): string {
  const v = Math.max(0, Math.min(MAX_RAW, raw));
  if (v <= S9_RAW) {
    const s = Math.floor(rawToSFloat(v));
    return `S${Math.min(9, s)}`;
  }
  let label = 'S9+50';
  for (let i = S9_PLUS_BREAKPOINTS.length - 1; i >= 0; i--) {
    if (v >= S9_PLUS_BREAKPOINTS[i].raw) {
      label = S9_PLUS_BREAKPOINTS[i].label;
      break;
    }
  }
  return label;
}

/** Map raw 0-255 to dBm value (linear interpolation between breakpoints). */
export function rawToDbm(raw: number): number {
  const v = Math.max(0, Math.min(MAX_RAW, raw));
  for (let i = 0; i < DBM_BREAKPOINTS.length - 1; i++) {
    const p0 = DBM_BREAKPOINTS[i];
    const p1 = DBM_BREAKPOINTS[i + 1];
    if (v <= p1.raw) {
      const t = (v - p0.raw) / (p1.raw - p0.raw);
      return Math.round(p0.dbm + t * (p1.dbm - p0.dbm));
    }
  }
  return DBM_BREAKPOINTS[DBM_BREAKPOINTS.length - 1].dbm;
}

/** Format dBm value as display string, e.g. "−67 dBm". Uses Unicode minus. */
export function formatDbm(dbm: number): string {
  const sign = dbm < 0 ? '\u2212' : '+';
  return `${sign}${Math.abs(dbm)} dBm`;
}
