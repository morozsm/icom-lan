import { describe, it, expect } from 'vitest';
import { buildAgcOptions } from '../agc-utils';

// ---------------------------------------------------------------------------
// buildAgcOptions
// ---------------------------------------------------------------------------

describe('buildAgcOptions', () => {
  // --- OFF prepending ---

  it('prepends OFF (value 0) when 0 is not in modes', () => {
    const options = buildAgcOptions([1, 2, 3], { '1': 'FAST', '2': 'MID', '3': 'SLOW' });
    expect(options[0]).toEqual({ value: 0, label: 'OFF' });
  });

  it('does not duplicate OFF when 0 is already in modes', () => {
    const options = buildAgcOptions([0, 1, 2], { '0': 'OFF', '1': 'FAST', '2': 'MID' });
    const offOptions = options.filter((o) => o.value === 0);
    expect(offOptions).toHaveLength(1);
  });

  it('uses the label from modes list when 0 is already present', () => {
    const options = buildAgcOptions([0, 1], { '0': 'OFF', '1': 'FAST' });
    expect(options[0]).toEqual({ value: 0, label: 'OFF' });
  });

  it('returns only OFF for empty modes list', () => {
    const options = buildAgcOptions([], {});
    expect(options).toEqual([{ value: 0, label: 'OFF' }]);
  });

  // --- Labels ---

  it('maps mode values to labels from the labels record', () => {
    const options = buildAgcOptions([1, 2, 3], { '1': 'FAST', '2': 'MID', '3': 'SLOW' });
    expect(options.map((o) => o.label)).toContain('FAST');
    expect(options.map((o) => o.label)).toContain('MID');
    expect(options.map((o) => o.label)).toContain('SLOW');
  });

  it('falls back to String(mode) when label is missing', () => {
    const options = buildAgcOptions([1, 99], { '1': 'FAST' });
    const unknown = options.find((o) => o.value === 99);
    expect(unknown).toEqual({ value: 99, label: '99' });
  });

  it('falls back to String(mode) for all modes when labels is empty', () => {
    const options = buildAgcOptions([1, 2], {});
    // OFF is prepended, then 1 → '1', 2 → '2'
    expect(options).toEqual([
      { value: 0, label: 'OFF' },
      { value: 1, label: '1' },
      { value: 2, label: '2' },
    ]);
  });

  // --- Order preservation ---

  it('preserves the order of modes', () => {
    const options = buildAgcOptions([3, 1, 2], { '1': 'FAST', '2': 'MID', '3': 'SLOW' });
    // OFF first, then modes in given order
    expect(options.map((o) => o.value)).toEqual([0, 3, 1, 2]);
  });

  it('returns correct total length: modes.length + 1 when 0 absent', () => {
    const options = buildAgcOptions([1, 2, 3], { '1': 'FAST', '2': 'MID', '3': 'SLOW' });
    expect(options).toHaveLength(4);
  });

  it('returns correct total length: modes.length when 0 is present', () => {
    const options = buildAgcOptions([0, 1, 2, 3], {
      '0': 'OFF', '1': 'FAST', '2': 'MID', '3': 'SLOW',
    });
    expect(options).toHaveLength(4);
  });

  // --- Value types ---

  it('all option values are numbers', () => {
    const options = buildAgcOptions([1, 2, 3], { '1': 'FAST', '2': 'MID', '3': 'SLOW' });
    options.forEach((o) => expect(typeof o.value).toBe('number'));
  });

  it('handles a single mode without 0', () => {
    const options = buildAgcOptions([2], { '2': 'MID' });
    expect(options).toEqual([
      { value: 0, label: 'OFF' },
      { value: 2, label: 'MID' },
    ]);
  });

  it('handles a single mode equal to 0', () => {
    const options = buildAgcOptions([0], { '0': 'OFF' });
    expect(options).toEqual([{ value: 0, label: 'OFF' }]);
  });

  // --- Standard IC-7610 AGC modes ---

  it('produces expected options for standard IC-7610 AGC [1,2,3]', () => {
    const options = buildAgcOptions(
      [1, 2, 3],
      { '1': 'FAST', '2': 'MID', '3': 'SLOW' },
    );
    expect(options).toEqual([
      { value: 0, label: 'OFF' },
      { value: 1, label: 'FAST' },
      { value: 2, label: 'MID' },
      { value: 3, label: 'SLOW' },
    ]);
  });
});
