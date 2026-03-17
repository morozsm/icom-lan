import { describe, it, expect } from 'vitest';
import { formatOffset, shouldShowPanel } from '../rit-utils';

// ---------------------------------------------------------------------------
// formatOffset
// ---------------------------------------------------------------------------

describe('formatOffset', () => {
  it('returns "±0 Hz" for zero', () => {
    expect(formatOffset(0)).toBe('±0 Hz');
  });

  it('returns "+120 Hz" for positive 120', () => {
    expect(formatOffset(120)).toBe('+120 Hz');
  });

  it('returns "+1 Hz" for positive 1', () => {
    expect(formatOffset(1)).toBe('+1 Hz');
  });

  it('returns Unicode minus for negative values', () => {
    expect(formatOffset(-50)).toBe('\u221250 Hz');
  });

  it('returns "−50 Hz" for -50 (Unicode minus sign)', () => {
    expect(formatOffset(-50)).toBe('−50 Hz');
  });

  it('returns "−1 Hz" for -1', () => {
    expect(formatOffset(-1)).toBe('−1 Hz');
  });

  it('handles large positive offset', () => {
    expect(formatOffset(9999)).toBe('+9999 Hz');
  });

  it('handles large negative offset', () => {
    expect(formatOffset(-9999)).toBe('−9999 Hz');
  });

  it('positive sign is ASCII + not Unicode', () => {
    expect(formatOffset(100)[0]).toBe('+');
  });

  it('negative sign is Unicode minus U+2212 not ASCII hyphen', () => {
    expect(formatOffset(-100).charCodeAt(0)).toBe(0x2212);
  });
});

// ---------------------------------------------------------------------------
// shouldShowPanel
// ---------------------------------------------------------------------------

describe('shouldShowPanel', () => {
  it('returns true when both hasRit and hasXit are true', () => {
    expect(shouldShowPanel(true, true)).toBe(true);
  });

  it('returns true when only hasRit is true', () => {
    expect(shouldShowPanel(true, false)).toBe(true);
  });

  it('returns true when only hasXit is true', () => {
    expect(shouldShowPanel(false, true)).toBe(true);
  });

  it('returns false when both hasRit and hasXit are false', () => {
    expect(shouldShowPanel(false, false)).toBe(false);
  });
});
