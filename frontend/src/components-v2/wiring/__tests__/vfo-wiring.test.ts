import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

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
import { getActiveReceiver, getRadioState, patchActiveReceiver, patchRadioState } from '$lib/stores/radio.svelte';
import { toVfoOpsProps } from '../state-adapter';
import { makeBandHandlers, makeFilterHandlers, makeModeHandlers, makeRitXitHandlers, makeVfoHandlers } from '../command-bus';

const originalDocumentQuerySelector = document.querySelector.bind(document);

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

  afterEach(() => {
    document.querySelector = originalDocumentQuerySelector;
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

  it('selects MAIN and scrolls the mode panel when the main mode badge is clicked', () => {
    const scrollIntoView = vi.fn();
    const modePanel = document.createElement('div');
    modePanel.scrollIntoView = scrollIntoView;
    document.querySelector = vi.fn((selector: string) => {
      if (selector === '[data-mode-panel="true"]') {
        return modePanel;
      }
      return originalDocumentQuerySelector(selector);
    }) as typeof document.querySelector;

    makeVfoHandlers().onMainModeClick();

    expect(patchRadioState).toHaveBeenCalledWith({ active: 'MAIN' });
    expect(sendCommand).toHaveBeenCalledWith('set_vfo', { vfo: 'MAIN' });
    expect(scrollIntoView).toHaveBeenCalled();
  });

  it('selects SUB and scrolls the mode panel when the sub mode badge is clicked', () => {
    const scrollIntoView = vi.fn();
    const modePanel = document.createElement('div');
    modePanel.scrollIntoView = scrollIntoView;
    document.querySelector = vi.fn((selector: string) => {
      if (selector === '[data-mode-panel="true"]') {
        return modePanel;
      }
      return originalDocumentQuerySelector(selector);
    }) as typeof document.querySelector;

    makeVfoHandlers().onSubModeClick();

    expect(patchRadioState).toHaveBeenCalledWith({ active: 'SUB' });
    expect(sendCommand).toHaveBeenCalledWith('set_vfo', { vfo: 'SUB' });
    expect(scrollIntoView).toHaveBeenCalled();
  });
});

describe('makeModeHandlers', () => {
  beforeEach(() => {
    vi.mocked(sendCommand).mockClear();
  });

  it('emits set_mode for the active receiver', () => {
    vi.mocked(getRadioState).mockReturnValue({ active: 'SUB' } as any);

    makeModeHandlers().onModeChange('CW');

    expect(sendCommand).toHaveBeenCalledWith('set_mode', { mode: 'CW', receiver: 1 });
  });

  it('emits numeric set_data_mode values for the active receiver', () => {
    vi.mocked(getRadioState).mockReturnValue({ active: 'MAIN' } as any);

    makeModeHandlers().onDataModeChange(3);

    expect(sendCommand).toHaveBeenCalledWith('set_data_mode', { mode: 3, receiver: 0 });
  });
});

describe('makeBandHandlers', () => {
  beforeEach(() => {
    vi.mocked(sendCommand).mockClear();
  });

  it('emits set_band when bsrCode is provided', () => {
    makeBandHandlers().onBandSelect('20m', 14_225_000, 5);

    expect(sendCommand).toHaveBeenCalledWith('set_band', { band: 5 });
  });

  it('does not emit a band command when bsrCode is missing', () => {
    makeBandHandlers().onBandSelect('20m', 14_225_000);

    expect(sendCommand).not.toHaveBeenCalled();
  });
});

describe('makeRitXitHandlers', () => {
  beforeEach(() => {
    vi.mocked(sendCommand).mockClear();
    vi.mocked(patchRadioState).mockClear();
  });

  it('emits set_rit_frequency for RIT offset changes', () => {
    makeRitXitHandlers().onRitOffsetChange(350);

    expect(patchRadioState).toHaveBeenCalledWith({ ritFreq: 350 });
    expect(sendCommand).toHaveBeenCalledWith('set_rit_frequency', { freq: 350 });
  });

  it('emits set_rit_frequency for XIT offset changes', () => {
    makeRitXitHandlers().onXitOffsetChange(-450);

    expect(patchRadioState).toHaveBeenCalledWith({ ritFreq: -450 });
    expect(sendCommand).toHaveBeenCalledWith('set_rit_frequency', { freq: -450 });
  });
});

describe('makeFilterHandlers', () => {
  beforeEach(() => {
    vi.mocked(sendCommand).mockClear();
    vi.mocked(patchActiveReceiver).mockClear();
  });

  it('emits set_filter_shape for the active receiver and patches optimistic state', () => {
    vi.mocked(getRadioState).mockReturnValue({ active: 'SUB' } as any);

    makeFilterHandlers().onFilterShapeChange?.(1);

    expect(patchActiveReceiver).toHaveBeenCalledWith({ filterShape: 1 }, true);
    expect(sendCommand).toHaveBeenCalledWith('set_filter_shape', { shape: 1, receiver: 1 });
  });

  it('restores the active filter width after resetting defaults', () => {
    vi.mocked(getRadioState).mockReturnValue({ active: 'MAIN' } as any);
    vi.mocked(getActiveReceiver).mockReturnValue({ filter: 2 } as any);

    makeFilterHandlers().onFilterDefaults?.([3000, 2400, 1800]);

    expect(sendCommand).toHaveBeenCalledWith('set_filter', { filter: 2, receiver: 0 });
    expect(patchActiveReceiver).toHaveBeenCalledWith({ filterWidth: 2400 }, true);
  });
});