/**
 * S-meter scale mapping utilities.
 *
 * Raw CI-V value (0-255) to display units:
 *   0 = S0, 18 = S1, 36 = S2, ..., 162 = S9
 *   182 = S9+10, 202 = S9+20, 222 = S9+30, 241 = S9+40
 *   255 = max (~S9+50)
 */

const S9_RAW = 162;
const MAX_RAW = 255;
const S_STEP = 18; // raw units per S-unit

const S9_PLUS_BREAKPOINTS: ReadonlyArray<{ raw: number; label: string }> = [
  { raw: 162, label: 'S9' },
  { raw: 182, label: 'S9+10' },
  { raw: 202, label: 'S9+20' },
  { raw: 222, label: 'S9+30' },
  { raw: 241, label: 'S9+40' },
  { raw: 255, label: 'S9+50' },
];

const DBM_BREAKPOINTS: ReadonlyArray<{ raw: number; dbm: number }> = [
  { raw: 0, dbm: -127 },
  { raw: 18, dbm: -121 },
  { raw: 36, dbm: -115 },
  { raw: 54, dbm: -109 },
  { raw: 72, dbm: -103 },
  { raw: 90, dbm: -97 },
  { raw: 108, dbm: -91 },
  { raw: 126, dbm: -85 },
  { raw: 144, dbm: -79 },
  { raw: 162, dbm: -73 },
  { raw: 182, dbm: -63 },
  { raw: 202, dbm: -53 },
  { raw: 222, dbm: -43 },
  { raw: 241, dbm: -33 },
  { raw: 255, dbm: -23 },
];

/** Map raw 0-255 to fractional segment count 0-20. */
export function rawToSegments(raw: number): number {
  const v = Math.max(0, Math.min(MAX_RAW, raw));
  if (v <= S9_RAW) {
    return (v / S9_RAW) * 11;
  }
  return 11 + ((v - S9_RAW) / (MAX_RAW - S9_RAW)) * 9;
}

/** Map raw 0-255 to S-unit string, e.g. "S7", "S9+20". */
export function rawToSUnit(raw: number): string {
  const v = Math.max(0, Math.min(MAX_RAW, raw));
  if (v <= S9_RAW) {
    const s = Math.floor(v / S_STEP);
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
