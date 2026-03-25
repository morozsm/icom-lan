/**
 * TX permission check based on US amateur radio band allocations.
 * Returns whether transmission is permitted at the given frequency.
 *
 * Based on ARRL band plan — Extra class (full privileges).
 * Covers HF bands 160m through 6m.
 */

interface TxBand {
  start: number; // Hz
  end: number;   // Hz
  modes?: string[]; // optional mode restriction
}

// US Amateur Extra class TX allocations (Hz)
// Source: ARRL band plan / FCC Part 97
const US_TX_BANDS: TxBand[] = [
  // 160m
  { start: 1_800_000, end: 2_000_000 },
  // 80m
  { start: 3_500_000, end: 4_000_000 },
  // 60m (5 channels, simplified as range)
  { start: 5_330_500, end: 5_405_000 },
  // 40m
  { start: 7_000_000, end: 7_300_000 },
  // 30m
  { start: 10_100_000, end: 10_150_000 },
  // 20m
  { start: 14_000_000, end: 14_350_000 },
  // 17m
  { start: 18_068_000, end: 18_168_000 },
  // 15m
  { start: 21_000_000, end: 21_450_000 },
  // 12m
  { start: 24_890_000, end: 24_990_000 },
  // 10m
  { start: 28_000_000, end: 29_700_000 },
  // 6m
  { start: 50_000_000, end: 54_000_000 },
];

export type TxPermit = 'allowed' | 'denied';

/**
 * Check if TX is permitted at the given frequency (Hz).
 */
export function getTxPermit(freqHz: number): TxPermit {
  for (const band of US_TX_BANDS) {
    if (freqHz >= band.start && freqHz <= band.end) {
      return 'allowed';
    }
  }
  return 'denied';
}
