import { describe, it, expect } from 'vitest';
import {
  formatAttLabel,
  formatPreLabel,
  buildAttOptions,
  buildPreOptions,
  shouldShowPanel,
} from '../rf-frontend-utils';

describe('formatAttLabel', () => {
  it('returns OFF for 0', () => {
    expect(formatAttLabel(0)).toBe('OFF');
  });

  it('returns 6dB for 6', () => {
    expect(formatAttLabel(6)).toBe('6dB');
  });

  it('returns 12dB for 12', () => {
    expect(formatAttLabel(12)).toBe('12dB');
  });

  it('returns 18dB for 18', () => {
    expect(formatAttLabel(18)).toBe('18dB');
  });

  it('returns 20dB for 20', () => {
    expect(formatAttLabel(20)).toBe('20dB');
  });
});

describe('formatPreLabel', () => {
  it('returns OFF for 0', () => {
    expect(formatPreLabel(0)).toBe('OFF');
  });

  it('returns P1 for 1', () => {
    expect(formatPreLabel(1)).toBe('P1');
  });

  it('returns P2 for 2', () => {
    expect(formatPreLabel(2)).toBe('P2');
  });

  it('returns P3 for 3', () => {
    expect(formatPreLabel(3)).toBe('P3');
  });
});

describe('buildAttOptions', () => {
  it('builds options array with correct length', () => {
    const opts = buildAttOptions([0, 6, 12, 18]);
    expect(opts).toHaveLength(4);
  });

  it('first option is OFF with value 0', () => {
    const opts = buildAttOptions([0, 6, 12, 18]);
    expect(opts[0]).toEqual({ value: 0, label: 'OFF' });
  });

  it('remaining options have dB labels', () => {
    const opts = buildAttOptions([0, 6, 12, 18]);
    expect(opts[1]).toEqual({ value: 6, label: '6dB' });
    expect(opts[2]).toEqual({ value: 12, label: '12dB' });
    expect(opts[3]).toEqual({ value: 18, label: '18dB' });
  });

  it('works with two-value [0, 20] set', () => {
    const opts = buildAttOptions([0, 20]);
    expect(opts).toEqual([
      { value: 0, label: 'OFF' },
      { value: 20, label: '20dB' },
    ]);
  });
});

describe('buildPreOptions', () => {
  it('builds options array with correct length', () => {
    const opts = buildPreOptions([0, 1, 2]);
    expect(opts).toHaveLength(3);
  });

  it('first option is OFF with value 0', () => {
    const opts = buildPreOptions([0, 1]);
    expect(opts[0]).toEqual({ value: 0, label: 'OFF' });
  });

  it('builds P1 and P2 labels correctly', () => {
    const opts = buildPreOptions([0, 1, 2]);
    expect(opts[1]).toEqual({ value: 1, label: 'P1' });
    expect(opts[2]).toEqual({ value: 2, label: 'P2' });
  });
});

describe('shouldShowPanel', () => {
  it('returns false when all capabilities are absent', () => {
    expect(shouldShowPanel(false, false, false)).toBe(false);
  });

  it('returns true when rf_gain is present', () => {
    expect(shouldShowPanel(true, false, false)).toBe(true);
  });

  it('returns true when attenuator is present', () => {
    expect(shouldShowPanel(false, true, false)).toBe(true);
  });

  it('returns true when preamp is present', () => {
    expect(shouldShowPanel(false, false, true)).toBe(true);
  });

  it('returns true when all capabilities are present', () => {
    expect(shouldShowPanel(true, true, true)).toBe(true);
  });
});
