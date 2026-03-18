import { describe, expect, it } from 'vitest';

import {
  canResizeFromRightEdge,
  getFilterWidthFromRightEdgePx,
  getPassbandEdgesHz,
  getPassbandGeometry,
} from '../passband-geometry';

describe('getPassbandEdgesHz', () => {
  it('places USB passband above carrier', () => {
    expect(getPassbandEdgesHz('USB', 2400, 0)).toEqual({ leftHz: 0, rightHz: 2400 });
  });

  it('places LSB passband below carrier', () => {
    expect(getPassbandEdgesHz('LSB', 2400, 0)).toEqual({ leftHz: -2400, rightHz: 0 });
  });

  it('centers AM passband around carrier', () => {
    expect(getPassbandEdgesHz('AM', 3000, 0)).toEqual({ leftHz: -1500, rightHz: 1500 });
  });

  it('applies IF shift to both passband edges', () => {
    expect(getPassbandEdgesHz('USB', 2400, 300)).toEqual({ leftHz: 300, rightHz: 2700 });
  });
});

describe('getPassbandGeometry', () => {
  it('converts passband width into pixels', () => {
    expect(getPassbandGeometry('USB', 2400, 0, 12000, 600)).toEqual({
      leftPx: 300,
      rightPx: 420,
      widthPx: 120,
    });
  });

  it('moves the overlay right when IF shift is positive', () => {
    expect(getPassbandGeometry('USB', 2400, 300, 12000, 600)).toEqual({
      leftPx: 315,
      rightPx: 435,
      widthPx: 120,
    });
  });

  it('clamps geometry to the visible span', () => {
    expect(getPassbandGeometry('USB', 2400, 6000, 12000, 600)).toEqual({
      leftPx: 600,
      rightPx: 600,
      widthPx: 0,
    });
  });
});

describe('getFilterWidthFromRightEdgePx', () => {
  it('derives USB width from the dragged right edge', () => {
    expect(getFilterWidthFromRightEdgePx('USB', 0, 12000, 600, 420)).toBe(2400);
  });

  it('accounts for IF shift when resizing USB passband', () => {
    expect(getFilterWidthFromRightEdgePx('USB', 300, 12000, 600, 435)).toBe(2400);
  });

  it('derives symmetric AM width from the right edge', () => {
    expect(getFilterWidthFromRightEdgePx('AM', 0, 12000, 600, 375)).toBe(3000);
  });

  it('disables right-edge resize for LSB', () => {
    expect(canResizeFromRightEdge('LSB')).toBe(false);
    expect(getFilterWidthFromRightEdgePx('LSB', 0, 12000, 600, 300)).toBeNull();
  });
});