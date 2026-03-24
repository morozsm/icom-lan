import { describe, it, expect } from 'vitest';
import { ARRL_HF_BANDS, getVisibleSegments } from '../arrl-band-plan';

describe('ARRL_HF_BANDS', () => {
  it('all segments have valid frequencies (startHz < endHz, all > 0)', () => {
    for (const band of ARRL_HF_BANDS) {
      expect(band.startHz).toBeGreaterThan(0);
      expect(band.endHz).toBeGreaterThan(band.startHz);
      for (const seg of band.segments) {
        expect(seg.startHz).toBeGreaterThan(0);
        expect(seg.endHz).toBeGreaterThan(seg.startHz);
      }
    }
  });

  it('all segments are non-overlapping within each band', () => {
    for (const band of ARRL_HF_BANDS) {
      const segs = [...band.segments].sort((a, b) => a.startHz - b.startHz);
      for (let i = 1; i < segs.length; i++) {
        expect(segs[i].startHz).toBeGreaterThanOrEqual(segs[i - 1].endHz);
      }
    }
  });

  it('contains expected bands', () => {
    const names = ARRL_HF_BANDS.map((b) => b.band);
    expect(names).toContain('20m');
    expect(names).toContain('40m');
    expect(names).toContain('10m');
    expect(names).toContain('160m');
  });
});

describe('getVisibleSegments', () => {
  it('returns correct segments for 20m range', () => {
    const result = getVisibleSegments(14_000_000, 14_350_000);
    expect(result.length).toBe(3);
    const modes = result.map((r) => r.segment.mode);
    expect(modes).toContain('cw');
    expect(modes).toContain('digital');
    expect(modes).toContain('phone');
  });

  it('returns empty for out-of-range frequencies (below all bands)', () => {
    const result = getVisibleSegments(500_000, 1_000_000);
    expect(result).toHaveLength(0);
  });

  it('returns empty for out-of-range frequencies (above all bands)', () => {
    const result = getVisibleSegments(50_000_000, 100_000_000);
    expect(result).toHaveLength(0);
  });

  it('returns partial segments when range partially overlaps a band', () => {
    // Only the CW portion of 20m should be visible
    const result = getVisibleSegments(14_000_000, 14_050_000);
    expect(result.length).toBeGreaterThan(0);
    expect(result.every((r) => r.band === '20m')).toBe(true);
    expect(result[0].segment.mode).toBe('cw');
  });

  it('returns segments from multiple bands when range spans them', () => {
    // Range covering both 20m and 17m
    const result = getVisibleSegments(14_000_000, 18_200_000);
    const bands = new Set(result.map((r) => r.band));
    expect(bands.has('20m')).toBe(true);
    expect(bands.has('17m')).toBe(true);
  });
});
