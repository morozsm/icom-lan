import { describe, it, expect } from 'vitest';
import { formatFrequency, formatFrequencyString } from '../frequency-format';

// ── formatFrequency — group splitting ──────────────────────────────────────

describe('formatFrequency', () => {
  it('returns "0", "000", "000" for 0 Hz', () => {
    expect(formatFrequency(0)).toEqual({ mhz: '0', khz: '000', hz: '000' });
  });

  it('returns "0", "000", "001" for 1 Hz', () => {
    expect(formatFrequency(1)).toEqual({ mhz: '0', khz: '000', hz: '001' });
  });

  it('returns "0", "000", "999" for 999 Hz', () => {
    expect(formatFrequency(999)).toEqual({ mhz: '0', khz: '000', hz: '999' });
  });

  it('returns "0", "001", "000" for 1000 Hz (1 kHz)', () => {
    expect(formatFrequency(1000)).toEqual({ mhz: '0', khz: '001', hz: '000' });
  });

  it('returns "0", "999", "999" for 999999 Hz', () => {
    expect(formatFrequency(999999)).toEqual({ mhz: '0', khz: '999', hz: '999' });
  });

  it('returns "1", "000", "000" for 1000000 Hz (1 MHz)', () => {
    expect(formatFrequency(1_000_000)).toEqual({ mhz: '1', khz: '000', hz: '000' });
  });

  it('returns "7", "074", "000" for 7074000 Hz (40m FT8)', () => {
    expect(formatFrequency(7_074_000)).toEqual({ mhz: '7', khz: '074', hz: '000' });
  });

  it('returns "14", "235", "000" for 14235000 Hz (20m SSB)', () => {
    expect(formatFrequency(14_235_000)).toEqual({ mhz: '14', khz: '235', hz: '000' });
  });

  it('returns "14", "074", "000" for 14074000 Hz (20m FT8)', () => {
    expect(formatFrequency(14_074_000)).toEqual({ mhz: '14', khz: '074', hz: '000' });
  });

  it('returns "144", "200", "000" for 144200000 Hz (2m calling)', () => {
    expect(formatFrequency(144_200_000)).toEqual({ mhz: '144', khz: '200', hz: '000' });
  });

  it('returns "435", "000", "000" for 435000000 Hz (70cm)', () => {
    expect(formatFrequency(435_000_000)).toEqual({ mhz: '435', khz: '000', hz: '000' });
  });

  it('returns "999", "999", "999" for 999999999 Hz (max)', () => {
    expect(formatFrequency(999_999_999)).toEqual({ mhz: '999', khz: '999', hz: '999' });
  });

  it('clamps negative input to 0', () => {
    expect(formatFrequency(-1)).toEqual({ mhz: '0', khz: '000', hz: '000' });
    expect(formatFrequency(-100_000)).toEqual({ mhz: '0', khz: '000', hz: '000' });
  });

  it('floors floating-point input', () => {
    expect(formatFrequency(14_235_000.9)).toEqual({ mhz: '14', khz: '235', hz: '000' });
    expect(formatFrequency(1_000_999.999)).toEqual({ mhz: '1', khz: '000', hz: '999' });
  });

  it('never produces leading zeros in the MHz group', () => {
    const { mhz } = formatFrequency(7_100_000);
    expect(mhz).toBe('7'); // not "07"
  });

  it('always zero-pads kHz group to 3 digits', () => {
    expect(formatFrequency(7_001_000).khz).toBe('001');
    expect(formatFrequency(7_010_000).khz).toBe('010');
  });

  it('always zero-pads Hz group to 3 digits', () => {
    expect(formatFrequency(14_235_001).hz).toBe('001');
    expect(formatFrequency(14_235_010).hz).toBe('010');
  });

  it('handles 1234567 Hz (1.234.567) correctly', () => {
    expect(formatFrequency(1_234_567)).toEqual({ mhz: '1', khz: '234', hz: '567' });
  });
});

// ── formatFrequencyString — full dot-separated string ─────────────────────

describe('formatFrequencyString', () => {
  it('formats 14235000 as "14.235.000"', () => {
    expect(formatFrequencyString(14_235_000)).toBe('14.235.000');
  });

  it('formats 0 as "0.000.000"', () => {
    expect(formatFrequencyString(0)).toBe('0.000.000');
  });

  it('formats 7074000 as "7.074.000"', () => {
    expect(formatFrequencyString(7_074_000)).toBe('7.074.000');
  });

  it('formats 144200000 as "144.200.000"', () => {
    expect(formatFrequencyString(144_200_000)).toBe('144.200.000');
  });

  it('formats 999999999 as "999.999.999"', () => {
    expect(formatFrequencyString(999_999_999)).toBe('999.999.999');
  });

  it('formats 1 Hz as "0.000.001"', () => {
    expect(formatFrequencyString(1)).toBe('0.000.001');
  });
});
