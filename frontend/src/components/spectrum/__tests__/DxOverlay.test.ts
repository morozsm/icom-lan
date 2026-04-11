import { describe, expect, it } from 'vitest';
import type { DxSpot } from '$lib/types/protocol';

/** Mirrors the $derived positioning logic in DxOverlay.svelte */
function positionSpots(spots: DxSpot[], startFreq: number, endFreq: number) {
  if (endFreq <= startFreq || spots.length === 0) return [];
  return spots
    .filter((s) => s.freq >= startFreq && s.freq <= endFreq)
    .map((s) => ({
      spot: s,
      pct: Math.max(2, Math.min(98, ((s.freq - startFreq) / (endFreq - startFreq)) * 100)),
    }));
}

const makeSpot = (o: Partial<DxSpot> = {}): DxSpot => ({
  spotter: 'W1AW', freq: 14_074_000, call: 'DL1ABC',
  comment: 'FT8', time_utc: '12:00', timestamp: 1_700_000_000, ...o,
});

describe('DxOverlay spot positioning', () => {
  const start = 14_000_000, end = 14_350_000;

  it('places a spot at the correct percentage', () => {
    const r = positionSpots([makeSpot({ freq: 14_175_000 })], start, end);
    expect(r).toHaveLength(1);
    expect(r[0].pct).toBeCloseTo(50, 0);
  });

  it('clamps left edge to 2%', () => {
    expect(positionSpots([makeSpot({ freq: start })], start, end)[0].pct).toBe(2);
  });

  it('clamps right edge to 98%', () => {
    expect(positionSpots([makeSpot({ freq: end })], start, end)[0].pct).toBe(98);
  });

  it('filters out spots outside the visible range', () => {
    const r = positionSpots([
      makeSpot({ freq: 14_100_000, call: 'IN' }),
      makeSpot({ freq: 13_999_999, call: 'BELOW' }),
      makeSpot({ freq: 14_350_001, call: 'ABOVE' }),
    ], start, end);
    expect(r).toHaveLength(1);
    expect(r[0].spot.call).toBe('IN');
  });

  it('returns empty when start >= end or no spots', () => {
    expect(positionSpots([makeSpot()], end, start)).toEqual([]);
    expect(positionSpots([makeSpot()], start, start)).toEqual([]);
    expect(positionSpots([], start, end)).toEqual([]);
  });

  it('positions multiple spots correctly', () => {
    const r = positionSpots([
      makeSpot({ freq: 14_087_500 }), makeSpot({ freq: 14_262_500 }),
    ], start, end);
    expect(r[0].pct).toBeCloseTo(25, 0);
    expect(r[1].pct).toBeCloseTo(75, 0);
  });

  it('preserves spot fields in output', () => {
    const r = positionSpots([makeSpot({ freq: 14_100_000, call: 'K1JT', spotter: 'N0AX' })], start, end);
    expect(r[0].spot.call).toBe('K1JT');
    expect(r[0].spot.spotter).toBe('N0AX');
  });
});
