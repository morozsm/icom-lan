/**
 * Tests for BandPlanOverlay logic: position calculations, overlap suppression,
 * frequency formatting, hex-to-RGB conversion, and fetch debounce skip logic.
 *
 * Pure functions are re-implemented here to mirror the component's inline logic
 * since they cannot be imported from a .svelte file.
 */
import { describe, it, expect } from 'vitest';

// ── Re-implementations of BandPlanOverlay inline logic ──

interface RemoteSegment {
  start: number;
  end: number;
  mode: string;
  label: string;
  color: string;
  opacity: number;
  band: string;
  layer: string;
  priority: number;
  url?: string | null;
  notes?: string | null;
  license?: string | null;
}

function formatFreq(hz: number): string {
  if (hz >= 1_000_000) return `${(hz / 1_000_000).toFixed(3)} MHz`;
  if (hz >= 1_000) return `${(hz / 1_000).toFixed(1)} kHz`;
  return `${hz} Hz`;
}

function hexToRgb(hex: string): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `${r},${g},${b}`;
}

/** Compute segment position as left% and width% given a display range. */
function computePosition(
  segStart: number,
  segEnd: number,
  startFreq: number,
  endFreq: number,
): { leftPct: number; widthPct: number } {
  const span = endFreq - startFreq;
  const rawLeft = ((segStart - startFreq) / span) * 100;
  const rawRight = ((segEnd - startFreq) / span) * 100;
  const leftPct = Math.max(0, Math.min(100, rawLeft));
  const rightPct = Math.max(0, Math.min(100, rawRight));
  return { leftPct, widthPct: rightPct - leftPct };
}

/** Filter non-ham segments that overlap >30% with any ham segment. */
function filterOverlapping(segments: RemoteSegment[], startFreq: number, endFreq: number, hiddenLayers: string[] = []): RemoteSegment[] {
  const visible = segments.filter(
    (s) => s.end > startFreq && s.start < endFreq && !hiddenLayers.includes(s.layer),
  );
  const hamSegs = visible.filter((s) => s.layer === 'ham');
  return visible.filter((s) => {
    if (s.layer === 'ham') return true;
    return !hamSegs.some((h) => {
      const overlapStart = Math.max(s.start, h.start);
      const overlapEnd = Math.min(s.end, h.end);
      if (overlapEnd <= overlapStart) return false;
      const overlapRatio = (overlapEnd - overlapStart) / (s.end - s.start);
      return overlapRatio > 0.3;
    });
  });
}

/** Should the debounced fetch be skipped? (range moved less than 1% of span) */
function shouldSkipFetch(
  start: number,
  end: number,
  lastStart: number,
  lastEnd: number,
): boolean {
  if (lastStart === 0) return false; // first fetch always runs
  const span = end - start;
  return (
    Math.abs(start - lastStart) < span * 0.01 &&
    Math.abs(end - lastEnd) < span * 0.01
  );
}

// ── Tests ──

describe('formatFreq', () => {
  it('formats MHz correctly', () => {
    expect(formatFreq(14_074_000)).toBe('14.074 MHz');
    expect(formatFreq(7_000_000)).toBe('7.000 MHz');
    expect(formatFreq(28_500_000)).toBe('28.500 MHz');
  });

  it('formats kHz correctly', () => {
    expect(formatFreq(500_000)).toBe('500.0 kHz');
    expect(formatFreq(1_000)).toBe('1.0 kHz');
  });

  it('formats Hz correctly', () => {
    expect(formatFreq(500)).toBe('500 Hz');
    expect(formatFreq(0)).toBe('0 Hz');
  });
});

describe('hexToRgb', () => {
  it('converts hex with hash', () => {
    expect(hexToRgb('#FF6A00')).toBe('255,106,0');
    expect(hexToRgb('#000000')).toBe('0,0,0');
    expect(hexToRgb('#FFFFFF')).toBe('255,255,255');
  });

  it('converts hex without hash', () => {
    expect(hexToRgb('4ADE80')).toBe('74,222,128');
  });
});

describe('computePosition', () => {
  const start = 14_000_000;
  const end = 14_350_000;

  it('segment fully inside range', () => {
    const pos = computePosition(14_070_000, 14_150_000, start, end);
    expect(pos.leftPct).toBeCloseTo(20, 0);
    expect(pos.widthPct).toBeCloseTo(22.86, 1);
  });

  it('segment matches full range', () => {
    const pos = computePosition(start, end, start, end);
    expect(pos.leftPct).toBeCloseTo(0, 5);
    expect(pos.widthPct).toBeCloseTo(100, 5);
  });

  it('segment extends beyond left edge is clamped', () => {
    const pos = computePosition(13_900_000, 14_100_000, start, end);
    expect(pos.leftPct).toBe(0); // clamped
    expect(pos.widthPct).toBeCloseTo(28.57, 1);
  });

  it('segment extends beyond right edge is clamped', () => {
    const pos = computePosition(14_300_000, 14_500_000, start, end);
    expect(pos.widthPct).toBeGreaterThan(0);
    // rightPct clamped to 100
    const expectedLeft = ((14_300_000 - start) / (end - start)) * 100;
    expect(pos.leftPct).toBeCloseTo(expectedLeft, 1);
    expect(pos.leftPct + pos.widthPct).toBeCloseTo(100, 1);
  });

  it('segment fully outside returns zero width', () => {
    const pos = computePosition(15_000_000, 15_100_000, start, end);
    // both clamped to 100 → width = 0
    expect(pos.widthPct).toBe(0);
  });
});

describe('filterOverlapping (overlap suppression)', () => {
  const ham: RemoteSegment = {
    start: 14_000_000, end: 14_350_000, mode: 'phone', label: 'Phone',
    color: '#60A5FA', opacity: 0.2, band: '20m', layer: 'ham', priority: 1,
  };

  it('ham segments always pass', () => {
    const result = filterOverlapping([ham], 14_000_000, 14_350_000);
    expect(result).toHaveLength(1);
  });

  it('non-ham segment with >30% overlap is suppressed', () => {
    const broadcast: RemoteSegment = {
      start: 14_100_000, end: 14_300_000, mode: 'broadcast', label: 'BC',
      color: '#C084FC', opacity: 0.2, band: 'BC', layer: 'eibi', priority: 5,
    };
    const result = filterOverlapping([ham, broadcast], 14_000_000, 14_350_000);
    expect(result).toHaveLength(1);
    expect(result[0].layer).toBe('ham');
  });

  it('non-ham segment with <30% overlap is kept', () => {
    // 50kHz overlap out of 500kHz segment = 10%
    const broadcast: RemoteSegment = {
      start: 14_300_000, end: 14_800_000, mode: 'broadcast', label: 'BC',
      color: '#C084FC', opacity: 0.2, band: 'BC', layer: 'eibi', priority: 5,
    };
    const result = filterOverlapping([ham, broadcast], 14_000_000, 14_800_000);
    expect(result).toHaveLength(2);
  });

  it('non-ham segment with zero overlap is kept', () => {
    const broadcast: RemoteSegment = {
      start: 15_000_000, end: 15_500_000, mode: 'broadcast', label: 'BC',
      color: '#C084FC', opacity: 0.2, band: 'BC', layer: 'eibi', priority: 5,
    };
    const result = filterOverlapping([ham, broadcast], 14_000_000, 16_000_000);
    expect(result).toHaveLength(2);
  });

  it('hidden layers are excluded', () => {
    const result = filterOverlapping([ham], 14_000_000, 14_350_000, ['ham']);
    expect(result).toHaveLength(0);
  });

  it('segments outside display range are excluded', () => {
    const outside: RemoteSegment = {
      start: 7_000_000, end: 7_300_000, mode: 'cw', label: 'CW',
      color: '#FF6A00', opacity: 0.2, band: '40m', layer: 'ham', priority: 1,
    };
    const result = filterOverlapping([ham, outside], 14_000_000, 14_350_000);
    expect(result).toHaveLength(1);
    expect(result[0].band).toBe('20m');
  });
});

describe('shouldSkipFetch (debounce)', () => {
  it('first fetch is never skipped', () => {
    expect(shouldSkipFetch(14_000_000, 14_350_000, 0, 0)).toBe(false);
  });

  it('identical range is skipped', () => {
    expect(shouldSkipFetch(14_000_000, 14_350_000, 14_000_000, 14_350_000)).toBe(true);
  });

  it('small shift (<1% of span) is skipped', () => {
    const span = 350_000;
    const shift = span * 0.005; // 0.5% shift
    expect(shouldSkipFetch(
      14_000_000 + shift, 14_350_000 + shift,
      14_000_000, 14_350_000,
    )).toBe(true);
  });

  it('large shift (>1% of span) triggers fetch', () => {
    const span = 350_000;
    const shift = span * 0.02; // 2% shift
    expect(shouldSkipFetch(
      14_000_000 + shift, 14_350_000 + shift,
      14_000_000, 14_350_000,
    )).toBe(false);
  });
});
