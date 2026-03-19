import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('$lib/transport/ws-client', () => ({
  sendCommand: vi.fn(),
}));

vi.mock('$lib/stores/radio.svelte', () => ({
  getActiveReceiver: vi.fn(() => null),
  getRadioState: vi.fn(() => null),
  patchActiveReceiver: vi.fn(),
  patchRadioState: vi.fn(),
}));

vi.mock('$lib/stores/capabilities.svelte', () => ({
  getCapabilities: vi.fn(() => ({
    freqRanges: [
      {
        start: 1,
        end: 2,
        label: 'HF',
        bands: [
          { name: '160m', start: 1800000, end: 2000000, default: 1825000, bsrCode: 1 },
          { name: '80m', start: 3500000, end: 4000000, default: 3573000, bsrCode: 2 },
        ],
      },
    ],
    attValues: [0, 6, 12],
    preValues: [0, 1, 2],
    agcModes: [1, 2, 3],
    filters: ['FIL1', 'FIL2', 'FIL3'],
    dataModeCount: 3,
  })),
}));

vi.mock('$lib/stores/tuning.svelte', () => ({
  getTuningStep: vi.fn(() => 1_000),
  adjustTuningStep: vi.fn(),
}));

import { sendCommand } from '$lib/transport/ws-client';
import { getRadioState, getActiveReceiver, patchActiveReceiver, patchRadioState } from '$lib/stores/radio.svelte';
import { adjustTuningStep } from '$lib/stores/tuning.svelte';
import { makeKeyboardHandlers } from '../command-bus';

describe('makeKeyboardHandlers', () => {
  beforeEach(() => {
    vi.mocked(sendCommand).mockClear();
    vi.mocked(patchActiveReceiver).mockClear();
    vi.mocked(patchRadioState).mockClear();
  });

  it('cycles to the next band by index', () => {
    makeKeyboardHandlers().dispatch({ action: 'band_select', params: { index: 2 } });

    expect(sendCommand).toHaveBeenCalledWith('set_band', { band: 2 });
  });

  it('cycles preamp values from capabilities', () => {
    vi.mocked(getRadioState).mockReturnValue({ active: 'MAIN' } as any);
    vi.mocked(getActiveReceiver).mockReturnValue({ preamp: 1 } as any);

    makeKeyboardHandlers().dispatch({ action: 'cycle_preamp' });

    expect(sendCommand).toHaveBeenCalledWith('set_preamp', { level: 2, receiver: 0 });
  });

  it('toggles split using radio state', () => {
    vi.mocked(getRadioState).mockReturnValue({ split: false } as any);

    makeKeyboardHandlers().dispatch({ action: 'toggle_split' });

    expect(patchRadioState).toHaveBeenCalledWith({ split: true });
    expect(sendCommand).toHaveBeenCalledWith('set_split', { on: true });
  });

  it('cycles data mode values based on capability count', () => {
    vi.mocked(getRadioState).mockReturnValue({ active: 'MAIN' } as any);
    vi.mocked(getActiveReceiver).mockReturnValue({ dataMode: 3 } as any);

    makeKeyboardHandlers().dispatch({ action: 'cycle_data_mode' });

    expect(sendCommand).toHaveBeenCalledWith('set_data_mode', { mode: 0, receiver: 0 });
  });

  it('emits a filter-settings UI event when requested', () => {
    const listener = vi.fn();
    window.addEventListener('icom-lan:open-filter-settings', listener as EventListener);

    makeKeyboardHandlers().dispatch({ action: 'open_filter_settings' });

    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener('icom-lan:open-filter-settings', listener as EventListener);
  });

  it('tunes frequency by the current frontend step', () => {
    vi.mocked(getRadioState).mockReturnValue({ active: 'MAIN' } as any);
    vi.mocked(getActiveReceiver).mockReturnValue({ freqHz: 14_074_000 } as any);

    makeKeyboardHandlers().dispatch({ action: 'tune', params: { direction: 'up' }, id: 'tune-up', section: 'Tuning', sequence: ['ArrowRight'] });

    expect(patchActiveReceiver).toHaveBeenCalledWith({ freqHz: 14_075_000 }, true);
    expect(sendCommand).toHaveBeenCalledWith('set_freq', { freq: 14_075_000, receiver: 0 });
  });

  it('adjusts the frontend tuning step without sending a backend command', () => {
    makeKeyboardHandlers().dispatch({ action: 'adjust_tuning_step', params: { direction: 'down' }, id: 'step-down', section: 'Tuning', sequence: ['ArrowDown'] });

    expect(adjustTuningStep).toHaveBeenCalledWith('down');
  });
});