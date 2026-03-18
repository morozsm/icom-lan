import { describe, expect, it } from 'vitest';

import { clampFilterWidth, deriveIfShift, mapIfShiftToPbt } from '../filter-controls';

describe('deriveIfShift', () => {
  it('returns zero when both PBT offsets are centered', () => {
    expect(deriveIfShift(0, 0)).toBe(0);
  });

  it('returns the shared shift when both PBT offsets move together', () => {
    expect(deriveIfShift(250, 250)).toBe(250);
    expect(deriveIfShift(-300, -300)).toBe(-300);
  });

  it('returns the midpoint when inner and outer are asymmetric', () => {
    expect(deriveIfShift(-200, 100)).toBe(-50);
  });
});

describe('mapIfShiftToPbt', () => {
  it('moves both PBT offsets together to reach the requested IF shift', () => {
    expect(mapIfShiftToPbt(300, 0, 0)).toEqual({ pbtInner: 300, pbtOuter: 300 });
  });

  it('preserves the relative PBT spread while shifting the window', () => {
    expect(mapIfShiftToPbt(200, -100, 100)).toEqual({ pbtInner: 100, pbtOuter: 300 });
  });

  it('clamps values to the valid bipolar range', () => {
    expect(mapIfShiftToPbt(1200, 900, 1100)).toEqual({ pbtInner: 1100, pbtOuter: 1200 });
  });
});

describe('clampFilterWidth', () => {
  it('snaps width to the nearest 50 Hz step', () => {
    expect(clampFilterWidth(2430)).toBe(2450);
  });

  it('clamps width to the allowed range', () => {
    expect(clampFilterWidth(0)).toBe(50);
    expect(clampFilterWidth(99999)).toBe(3600);
  });
});