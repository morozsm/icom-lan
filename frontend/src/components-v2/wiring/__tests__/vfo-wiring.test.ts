import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/transport/ws-client', () => ({
  sendCommand: vi.fn(),
}));

vi.mock('$lib/stores/radio.svelte', () => ({
  getActiveReceiver: vi.fn(() => null),
  getRadioState: vi.fn(() => null),
  patchActiveReceiver: vi.fn(),
  patchRadioState: vi.fn(),
}));

import { sendCommand } from '$lib/transport/ws-client';
import { getRadioState, patchRadioState } from '$lib/stores/radio.svelte';
import { toVfoOpsProps } from '../state-adapter';
import { makeVfoHandlers } from '../command-bus';

describe('toVfoOpsProps', () => {
  it('uses the active VFO as TX VFO when split is off', () => {
    expect(
      toVfoOpsProps(
        {
          active: 'MAIN',
          split: false,
          dualWatch: false,
          mainSubTracking: false,
        } as any,
        null,
      ).txVfo,
    ).toBe('main');

    expect(
      toVfoOpsProps(
        {
          active: 'SUB',
          split: false,
          dualWatch: false,
          mainSubTracking: false,
        } as any,
        null,
      ).txVfo,
    ).toBe('sub');
  });

  it('uses the opposite VFO as TX VFO when split is on', () => {
    expect(
      toVfoOpsProps(
        {
          active: 'MAIN',
          split: true,
          dualWatch: false,
          mainSubTracking: false,
        } as any,
        null,
      ).txVfo,
    ).toBe('sub');

    expect(
      toVfoOpsProps(
        {
          active: 'SUB',
          split: true,
          dualWatch: false,
          mainSubTracking: false,
        } as any,
        null,
      ).txVfo,
    ).toBe('main');
  });
});

describe('makeVfoHandlers', () => {
  beforeEach(() => {
    vi.mocked(sendCommand).mockClear();
    vi.mocked(patchRadioState).mockClear();
  });

  it('maps TX→MAIN to SUB active receiver when split is on', () => {
    vi.mocked(getRadioState).mockReturnValue({ split: true } as any);

    makeVfoHandlers().onTxVfoChange('main');

    expect(patchRadioState).toHaveBeenCalledWith({ active: 'SUB' });
    expect(sendCommand).toHaveBeenCalledWith('set_vfo', { vfo: 'SUB' });
  });

  it('maps TX→SUB to MAIN active receiver when split is on', () => {
    vi.mocked(getRadioState).mockReturnValue({ split: true } as any);

    makeVfoHandlers().onTxVfoChange('sub');

    expect(patchRadioState).toHaveBeenCalledWith({ active: 'MAIN' });
    expect(sendCommand).toHaveBeenCalledWith('set_vfo', { vfo: 'MAIN' });
  });

  it('maps TX target directly when split is off', () => {
    vi.mocked(getRadioState).mockReturnValue({ split: false } as any);

    makeVfoHandlers().onTxVfoChange('sub');

    expect(patchRadioState).toHaveBeenCalledWith({ active: 'SUB' });
    expect(sendCommand).toHaveBeenCalledWith('set_vfo', { vfo: 'SUB' });
  });

  it('sends explicit split=false when toggling from active split state', () => {
    vi.mocked(getRadioState).mockReturnValue({ split: true } as any);

    makeVfoHandlers().onSplitToggle();

    expect(patchRadioState).toHaveBeenCalledWith({ split: false });
    expect(sendCommand).toHaveBeenCalledWith('set_split', { on: false });
  });

  it('sends explicit split=true when toggling from inactive split state', () => {
    vi.mocked(getRadioState).mockReturnValue({ split: false } as any);

    makeVfoHandlers().onSplitToggle();

    expect(patchRadioState).toHaveBeenCalledWith({ split: true });
    expect(sendCommand).toHaveBeenCalledWith('set_split', { on: true });
  });
});