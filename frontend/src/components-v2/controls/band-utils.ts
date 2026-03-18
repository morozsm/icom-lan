import type { FreqRange } from '$lib/types/capabilities';

export interface FlatBand {
  name: string;
  defaultFreq: number;
  start: number;
  end: number;
  bsrCode?: number;
}

/**
 * Flatten all bands from all freq ranges into a single ordered array.
 * Ranges and bands within each range appear in the order defined in the config.
 */
export function flattenBands(freqRanges: FreqRange[]): FlatBand[] {
  const result: FlatBand[] = [];
  for (const range of freqRanges) {
    for (const band of range.bands ?? []) {
      result.push({
        name: band.name,
        defaultFreq: band.default,
        start: band.start,
        end: band.end,
        bsrCode: band.bsrCode,
      });
    }
  }
  return result;
}

/**
 * Find the band name whose [start, end] range contains `freq`.
 * Returns null if no band matches.
 */
export function findActiveBand(freq: number, freqRanges: FreqRange[]): string | null {
  for (const range of freqRanges) {
    for (const band of range.bands ?? []) {
      if (freq >= band.start && freq <= band.end) {
        return band.name;
      }
    }
  }
  return null;
}
