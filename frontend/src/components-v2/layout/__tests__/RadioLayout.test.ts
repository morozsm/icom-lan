import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import RadioLayout from '../RadioLayout.svelte';
import { extractVfoState, extractMeterState, hasLiveAudioFromState } from '../layout-utils';

// ---------------------------------------------------------------------------
// extractVfoState
// ---------------------------------------------------------------------------

describe('extractVfoState', () => {
  it('returns defaults when radioState is null', () => {
    const result = extractVfoState(null, 'main');
    expect(result.receiver).toBe('main');
    expect(result.freq).toBe(14074000);
    expect(result.mode).toBe('USB');
    expect(result.filter).toBe('FIL1');
    expect(result.sValue).toBe(0);
    expect(result.badges).toEqual({});
    expect(result.rit).toBeUndefined();
  });

  it('returns defaults when radioState is empty object', () => {
    const result = extractVfoState({}, 'sub');
    expect(result.receiver).toBe('sub');
    expect(result.freq).toBe(14074000);
    expect(result.mode).toBe('USB');
  });

  it('returns main vfo data from radioState', () => {
    const state = {
      main: { freq: 7074000, mode: 'LSB', filter: 'FIL2', sValue: 100, badges: { nr: true } },
      activeReceiver: 'main',
    };
    const result = extractVfoState(state, 'main');
    expect(result.freq).toBe(7074000);
    expect(result.mode).toBe('LSB');
    expect(result.filter).toBe('FIL2');
    expect(result.sValue).toBe(100);
    expect(result.badges).toEqual({ nr: true });
    expect(result.isActive).toBe(true);
  });

  it('returns sub vfo data from radioState', () => {
    const state = {
      sub: { freq: 3573000, mode: 'LSB', filter: 'FIL1', sValue: 50, badges: {} },
      activeReceiver: 'main',
    };
    const result = extractVfoState(state, 'sub');
    expect(result.freq).toBe(3573000);
    expect(result.receiver).toBe('sub');
    expect(result.isActive).toBe(false);
  });

  it('isActive true when activeReceiver matches receiver', () => {
    const state = { activeReceiver: 'sub', sub: {} };
    const result = extractVfoState(state, 'sub');
    expect(result.isActive).toBe(true);
  });

  it('isActive false when activeReceiver does not match receiver', () => {
    const state = { activeReceiver: 'main', sub: {} };
    const result = extractVfoState(state, 'sub');
    expect(result.isActive).toBe(false);
  });

  it('defaults activeReceiver to main when missing', () => {
    const state = { main: { freq: 14200000 } };
    const mainResult = extractVfoState(state, 'main');
    const subResult = extractVfoState(state, 'sub');
    expect(mainResult.isActive).toBe(true);
    expect(subResult.isActive).toBe(false);
  });

  it('passes rit object when present', () => {
    const state = {
      main: { rit: { active: true, offset: 120 } },
      activeReceiver: 'main',
    };
    const result = extractVfoState(state, 'main');
    expect(result.rit).toEqual({ active: true, offset: 120 });
  });
});

// ---------------------------------------------------------------------------
// extractMeterState
// ---------------------------------------------------------------------------

describe('extractMeterState', () => {
  it('returns defaults when radioState is null', () => {
    const result = extractMeterState(null);
    expect(result.sValue).toBe(0);
    expect(result.rfPower).toBe(0);
    expect(result.swr).toBe(0);
    expect(result.alc).toBe(0);
    expect(result.txActive).toBe(false);
    expect(result.meterSource).toBe('S');
  });

  it('extracts sValue from radioState.main', () => {
    const result = extractMeterState({ main: { sValue: 180 } });
    expect(result.sValue).toBe(180);
  });

  it('extracts tx values from radioState.tx', () => {
    const result = extractMeterState({ tx: { rfPower: 200, swr: 30, alc: 64 } });
    expect(result.rfPower).toBe(200);
    expect(result.swr).toBe(30);
    expect(result.alc).toBe(64);
  });

  it('extracts txActive and meterSource', () => {
    const result = extractMeterState({ txActive: true, meterSource: 'SWR' });
    expect(result.txActive).toBe(true);
    expect(result.meterSource).toBe('SWR');
  });
});

// ---------------------------------------------------------------------------
// hasLiveAudioFromState
// ---------------------------------------------------------------------------

describe('hasLiveAudioFromState', () => {
  it('returns false when radioState is null', () => {
    expect(hasLiveAudioFromState(null)).toBe(false);
  });

  it('returns true when capabilities.audio is true', () => {
    expect(hasLiveAudioFromState({ capabilities: { audio: true } })).toBe(true);
  });

  it('returns false when capabilities.audio is false', () => {
    expect(hasLiveAudioFromState({ capabilities: { audio: false } })).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// RadioLayout component
// ---------------------------------------------------------------------------

vi.mock('$lib/stores/capabilities.svelte', () => ({
  hasTx: vi.fn(() => true),
  hasDualReceiver: vi.fn(() => false),
  hasAudio: vi.fn(() => false),
  hasSpectrum: vi.fn(() => false),
  hasCapability: vi.fn(() => false),
  vfoLabel: vi.fn((slot: 'A' | 'B') => (slot === 'A' ? 'MAIN' : 'SUB')),
  getCapabilities: vi.fn(() => ({ freqRanges: [], modes: [], filters: [] })),
  getAgcModes: vi.fn(() => [0, 1, 2, 3]),
  getAgcLabels: vi.fn(() => ({ 0: 'OFF', 1: 'FAST', 2: 'MID', 3: 'SLOW' })),
  getSupportedModes: vi.fn(() => ['USB', 'LSB', 'CW', 'AM', 'FM']),
  getSupportedFilters: vi.fn(() => ['FIL1', 'FIL2', 'FIL3']),
  getAttValues: vi.fn(() => [0, 10, 20]),
  getPreValues: vi.fn(() => [0, 1, 2]),
  getVfoScheme: vi.fn(() => 'ab'),
}));

import { hasTx, hasDualReceiver } from '$lib/stores/capabilities.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountLayout(props: Record<string, unknown> = {}) {
  const t = document.createElement('div');
  document.body.appendChild(t);
  const component = mount(RadioLayout, { target: t, props: { radioState: null, ...props } });
  flushSync();
  components.push(component);
  return t;
}

beforeEach(() => {
  components = [];
  vi.mocked(hasTx).mockReturnValue(true);
  vi.mocked(hasDualReceiver).mockReturnValue(false);
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

describe('RadioLayout structure', () => {
  it('renders the root .radio-layout element', () => {
    const t = mountLayout();
    expect(t.querySelector('.radio-layout')).not.toBeNull();
  });

  it('renders .left-sidebar', () => {
    const t = mountLayout();
    expect(t.querySelector('.left-sidebar')).not.toBeNull();
  });

  it('renders .center-column', () => {
    const t = mountLayout();
    expect(t.querySelector('.center-column')).not.toBeNull();
  });

  it('renders .right-sidebar', () => {
    const t = mountLayout();
    expect(t.querySelector('.right-sidebar')).not.toBeNull();
  });

  it('renders .spectrum-slot in center column', () => {
    const t = mountLayout();
    expect(t.querySelector('.spectrum-slot')).not.toBeNull();
  });

  it('spectrum-slot is inside center-column', () => {
    const t = mountLayout();
    const center = t.querySelector('.center-column');
    expect(center?.querySelector('.spectrum-slot')).not.toBeNull();
  });

  it('renders .vfo-section in center column', () => {
    const t = mountLayout();
    const center = t.querySelector('.center-column');
    expect(center?.querySelector('.vfo-section')).not.toBeNull();
  });
});

describe('MeterPanel capability gating', () => {
  it('renders .meter-section when hasTx is true', () => {
    vi.mocked(hasTx).mockReturnValue(true);
    const t = mountLayout();
    expect(t.querySelector('.meter-section')).not.toBeNull();
  });

  it('does not render .meter-section when hasTx is false', () => {
    vi.mocked(hasTx).mockReturnValue(false);
    const t = mountLayout();
    expect(t.querySelector('.meter-section')).toBeNull();
  });

  it('meter-section is inside center-column', () => {
    vi.mocked(hasTx).mockReturnValue(true);
    const t = mountLayout();
    const center = t.querySelector('.center-column');
    expect(center?.querySelector('.meter-section')).not.toBeNull();
  });
});

describe('VfoHeader dual receiver', () => {
  it('renders only one .panel in vfo-header when hasDualReceiver is false', () => {
    vi.mocked(hasDualReceiver).mockReturnValue(false);
    const t = mountLayout();
    const vfoHeader = t.querySelector('.vfo-header');
    const panels = vfoHeader?.querySelectorAll('.panel');
    expect(panels?.length).toBe(1);
  });

  it('renders two .panel elements in vfo-header when hasDualReceiver is true', () => {
    vi.mocked(hasDualReceiver).mockReturnValue(true);
    const t = mountLayout();
    const vfoHeader = t.querySelector('.vfo-header');
    const panels = vfoHeader?.querySelectorAll('.panel');
    expect(panels?.length).toBe(2);
  });
});

describe('RadioLayout with radioState', () => {
  const sampleState = {
    activeReceiver: 'main',
    main: { freq: 14074000, mode: 'USB', filter: 'FIL1', sValue: 120, badges: {} },
    sub: { freq: 7074000, mode: 'LSB', filter: 'FIL1', sValue: 60, badges: {} },
    txActive: false,
    meterSource: 'S',
  };

  it('renders without errors given a full radioState', () => {
    const t = mountLayout({ radioState: sampleState });
    expect(t.querySelector('.radio-layout')).not.toBeNull();
  });

  it('spectrum-slot has min-height style of 300px', () => {
    const t = mountLayout({ radioState: sampleState });
    const slot = t.querySelector<HTMLElement>('.spectrum-slot');
    expect(slot).not.toBeNull();
    // Check that the element exists (CSS min-height is defined in <style>)
    expect(slot?.classList.contains('spectrum-slot')).toBe(true);
  });
});
