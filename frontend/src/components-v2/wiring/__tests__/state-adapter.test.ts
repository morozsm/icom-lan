import { describe, it, expect } from 'vitest';

import { toFilterProps, toModeProps, toVfoProps } from '../state-adapter';

describe('toModeProps', () => {
  it('derives the active receiver mode and numeric data mode from state', () => {
    const props = toModeProps(
      {
        active: 'SUB',
        main: { mode: 'USB', dataMode: 0 },
        sub: { mode: 'RTTY', dataMode: 2 },
      } as any,
      {
        modes: ['USB', 'LSB', 'RTTY'],
        capabilities: ['data_mode'],
        dataModeCount: 3,
        dataModeLabels: { '0': 'OFF', '1': 'D1', '2': 'D2', '3': 'D3' },
      } as any,
    );

    expect(props.currentMode).toBe('RTTY');
    expect(props.dataMode).toBe(2);
    expect(props.hasDataMode).toBe(true);
    expect(props.dataModeCount).toBe(3);
    expect(props.dataModeLabels).toEqual({ '0': 'OFF', '1': 'D1', '2': 'D2', '3': 'D3' });
  });

  it('falls back to defaults when state or capabilities are missing', () => {
    const props = toModeProps(null, null);

    expect(props.currentMode).toBe('USB');
    expect(props.modes).toEqual(['USB', 'LSB', 'CW', 'CW-R', 'AM', 'FM', 'RTTY', 'RTTY-R', 'PSK', 'PSK-R']);
    expect(props.dataMode).toBe(0);
    expect(props.hasDataMode).toBe(false);
  });
});

describe('toVfoProps', () => {
  it('adds a DATA badge when numeric data mode is active', () => {
    const props = toVfoProps(
      {
        active: 'MAIN',
        split: false,
        main: {
          freqHz: 14_074_000,
          mode: 'USB',
          filter: 1,
          dataMode: 3,
          sMeter: 0,
          att: 0,
          preamp: 0,
          nb: false,
          nr: false,
          afLevel: 0,
          rfGain: 0,
          squelch: 0,
        },
        sub: {
          freqHz: 7_074_000,
          mode: 'LSB',
          filter: 1,
          dataMode: 0,
          sMeter: 0,
          att: 0,
          preamp: 0,
          nb: false,
          nr: false,
          afLevel: 0,
          rfGain: 0,
          squelch: 0,
        },
      } as any,
      'main',
    );

    expect(props.badges).toMatchObject({ DATA: true });
  });
});

describe('toFilterProps', () => {
  it('resolves data-mode specific filter config for the active receiver', () => {
    const props = toFilterProps(
      {
        active: 'MAIN',
        main: { mode: 'USB', dataMode: 1, filter: 2, filterWidth: 1200, pbtInner: 0, pbtOuter: 0 },
        sub: { mode: 'LSB', dataMode: 0, filter: 1, filterWidth: 2400, pbtInner: 0, pbtOuter: 0 },
      } as any,
      {
        capabilities: ['pbt'],
        filters: ['FIL1', 'FIL2', 'FIL3'],
        filterConfig: {
          'USB-D': { defaults: [3000, 1200, 500], fixed: false, minHz: 50, maxHz: 3600, stepHz: 50 },
        },
      } as any,
    );

    expect(props.currentFilter).toBe(2);
    expect(props.filterLabels).toEqual(['FIL1', 'FIL2', 'FIL3']);
    expect(props.filterConfig?.defaults).toEqual([3000, 1200, 500]);
    expect(props.filterWidthMin).toBe(50);
    expect(props.filterWidthMax).toBe(3600);
  });
});