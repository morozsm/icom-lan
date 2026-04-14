import { describe, it, expect } from 'vitest';
import {
  NOTCH_WIDTH_LABELS,
  AGC_TIME_LABELS,
  LONG_PRESS_MS,
  formatAgcTime,
  toggleNrMode,
  toggleNotchMode,
  isNrActive,
  isNotchActive,
} from '../dsp-panel-logic';

describe('dsp-panel-logic', () => {
  describe('NOTCH_WIDTH_LABELS', () => {
    it('has 3 entries', () => {
      expect(Object.keys(NOTCH_WIDTH_LABELS)).toHaveLength(3);
    });
  });

  describe('AGC_TIME_LABELS', () => {
    it('has 10 entries', () => {
      expect(Object.keys(AGC_TIME_LABELS)).toHaveLength(10);
    });
  });

  describe('LONG_PRESS_MS', () => {
    it('is 500', () => {
      expect(LONG_PRESS_MS).toBe(500);
    });
  });

  describe('formatAgcTime', () => {
    it('returns label for known indices', () => {
      expect(formatAgcTime(0)).toBe('0.1');
      expect(formatAgcTime(5)).toBe('2.0');
      expect(formatAgcTime(9)).toBe('6.0');
    });

    it('returns string of index for unknown indices', () => {
      expect(formatAgcTime(99)).toBe('99');
      expect(formatAgcTime(-1)).toBe('-1');
    });
  });

  describe('toggleNrMode', () => {
    it('toggles 0 → 1', () => {
      expect(toggleNrMode(0)).toBe(1);
    });

    it('toggles 1 → 0', () => {
      expect(toggleNrMode(1)).toBe(0);
    });

    it('toggles 2 → 0', () => {
      expect(toggleNrMode(2)).toBe(0);
    });
  });

  describe('toggleNotchMode', () => {
    it('toggles off → auto', () => {
      expect(toggleNotchMode('off')).toBe('auto');
    });

    it('toggles auto → off', () => {
      expect(toggleNotchMode('auto')).toBe('off');
    });

    it('toggles manual → off', () => {
      expect(toggleNotchMode('manual')).toBe('off');
    });
  });

  describe('isNrActive', () => {
    it('returns false for 0', () => {
      expect(isNrActive(0)).toBe(false);
    });

    it('returns true for 1', () => {
      expect(isNrActive(1)).toBe(true);
    });

    it('returns true for 2', () => {
      expect(isNrActive(2)).toBe(true);
    });
  });

  describe('isNotchActive', () => {
    it('returns false for off', () => {
      expect(isNotchActive('off')).toBe(false);
    });

    it('returns true for auto', () => {
      expect(isNotchActive('auto')).toBe(true);
    });

    it('returns true for manual', () => {
      expect(isNotchActive('manual')).toBe(true);
    });
  });
});
