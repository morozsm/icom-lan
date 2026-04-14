import { describe, it, expect } from 'vitest';
import {
  BREAK_IN_LABELS,
  formatBreakIn,
  isBreakInActive,
  isApfActive,
} from '../cw-panel-logic';

describe('cw-panel-logic', () => {
  describe('BREAK_IN_LABELS', () => {
    it('has 3 entries', () => {
      expect(Object.keys(BREAK_IN_LABELS)).toHaveLength(3);
    });
  });

  describe('formatBreakIn', () => {
    it('returns OFF for 0', () => {
      expect(formatBreakIn(0)).toBe('OFF');
    });

    it('returns SEMI for 1', () => {
      expect(formatBreakIn(1)).toBe('SEMI');
    });

    it('returns FULL for 2', () => {
      expect(formatBreakIn(2)).toBe('FULL');
    });

    it('defaults to OFF for unknown', () => {
      expect(formatBreakIn(99)).toBe('OFF');
    });
  });

  describe('isBreakInActive', () => {
    it('returns false for 0', () => {
      expect(isBreakInActive(0)).toBe(false);
    });

    it('returns true for 1', () => {
      expect(isBreakInActive(1)).toBe(true);
    });

    it('returns true for 2', () => {
      expect(isBreakInActive(2)).toBe(true);
    });
  });

  describe('isApfActive', () => {
    it('returns false for 0', () => {
      expect(isApfActive(0)).toBe(false);
    });

    it('returns true for 1', () => {
      expect(isApfActive(1)).toBe(true);
    });

    it('returns true for 2', () => {
      expect(isApfActive(2)).toBe(true);
    });
  });
});
