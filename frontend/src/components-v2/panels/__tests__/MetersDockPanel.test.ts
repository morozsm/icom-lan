import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import type { ComponentProps } from 'svelte';
import MetersDockPanel from '../MetersDockPanel.svelte';
import {
  formatAmps,
  formatVolts,
  formatCompDb,
  updatePeakHold,
} from '../meter-utils';

vi.mock('$lib/stores/capabilities.svelte', () => ({
  hasTx: vi.fn(() => true),
  getMeterCalibration: vi.fn(() => null),
  getMeterRedline: vi.fn(() => null),
}));

// ---------------------------------------------------------------------------
// New formatters
// ---------------------------------------------------------------------------

describe('formatAmps', () => {
  it('returns 0.0 A for raw 0', () => {
    expect(formatAmps(0)).toBe('0.0 A');
  });
  it('returns 10.0 A at knot raw=151', () => {
    expect(formatAmps(151)).toBe('10.0 A');
  });
  it('returns 15.0 A at knot raw=195', () => {
    expect(formatAmps(195)).toBe('15.0 A');
  });
  it('clamps raw 300 to last knot (25.0 A)', () => {
    expect(formatAmps(300)).toBe('25.0 A');
  });
});

describe('formatVolts', () => {
  it('returns 0.0 V for raw 0', () => {
    expect(formatVolts(0)).toBe('0.0 V');
  });
  it('returns 10.0 V at knot raw=13', () => {
    expect(formatVolts(13)).toBe('10.0 V');
  });
  it('returns 16.0 V at knot raw=241', () => {
    expect(formatVolts(241)).toBe('16.0 V');
  });
});

describe('formatCompDb', () => {
  it('returns 0 dB for raw 0', () => {
    expect(formatCompDb(0)).toBe('0 dB');
  });
  it('returns 15 dB at knot raw=75', () => {
    expect(formatCompDb(75)).toBe('15 dB');
  });
  it('returns 30 dB at knot raw=150', () => {
    expect(formatCompDb(150)).toBe('30 dB');
  });
});

describe('updatePeakHold', () => {
  it('initializes state when undefined', () => {
    const s = updatePeakHold(undefined, 42, 1000);
    expect(s).toEqual({ peak: 42, peakAt: 1000 });
  });
  it('latches a new higher peak and updates timestamp', () => {
    const s = updatePeakHold({ peak: 10, peakAt: 1000 }, 20, 1500);
    expect(s).toEqual({ peak: 20, peakAt: 1500 });
  });
  it('keeps peak unchanged when current is lower and decay not elapsed', () => {
    const s = updatePeakHold({ peak: 100, peakAt: 1000 }, 50, 1000);
    expect(s.peak).toBe(100);
    expect(s.peakAt).toBe(1000);
  });
  it('linearly decays toward current mid-window', () => {
    // halfway through 2s decay: peak 100, current 0 -> 50
    const s = updatePeakHold({ peak: 100, peakAt: 0 }, 0, 1000);
    expect(s.peak).toBeCloseTo(50, 5);
    expect(s.peakAt).toBe(0);
  });
  it('collapses to current once decay window elapses', () => {
    const s = updatePeakHold({ peak: 100, peakAt: 0 }, 25, 2000);
    expect(s).toEqual({ peak: 25, peakAt: 2000 });
  });
});

// ---------------------------------------------------------------------------
// MetersDockPanel component
// ---------------------------------------------------------------------------

let components: ReturnType<typeof mount>[] = [];
let roots: HTMLElement[] = [];

function mountPanel(props: ComponentProps<typeof MetersDockPanel>) {
  const t = document.createElement('div');
  document.body.appendChild(t);
  roots.push(t);
  const component = mount(MetersDockPanel, { target: t, props });
  flushSync();
  components.push(component);
  return t;
}

beforeEach(() => {
  components = [];
  roots = [];
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  roots.forEach((r) => r.remove());
  components = [];
  roots = [];
});

const fullProps: ComponentProps<typeof MetersDockPanel> = {
  sValue: 120,
  powerMeter: 143,
  swrMeter: 48,
  alcMeter: 60,
  txActive: false,
};

describe('MetersDockPanel structure', () => {
  it('renders the STATION METERS header', () => {
    const t = mountPanel(fullProps);
    expect(t.querySelector('.dock-title')?.textContent).toBe('STATION METERS');
  });

  it('renders four tiles when all four state fields are defined', () => {
    const t = mountPanel(fullProps);
    expect(t.querySelectorAll('.dock-tile')).toHaveLength(4);
  });

  it('renders tiles in fixed priority order Po, SWR, ALC, S', () => {
    const t = mountPanel(fullProps);
    const keys = Array.from(t.querySelectorAll('.dock-tile')).map((el) =>
      el.getAttribute('data-meter'),
    );
    expect(keys).toEqual(['po', 'swr', 'alc', 's']);
  });

  it('shows RX state label when txActive is false', () => {
    const t = mountPanel(fullProps);
    const state = t.querySelector('.dock-tx-state');
    expect(state?.textContent).toBe('RX');
    expect(state?.getAttribute('data-active')).toBe('false');
  });

  it('shows TX state label when txActive is true', () => {
    const t = mountPanel({ ...fullProps, txActive: true });
    const state = t.querySelector('.dock-tx-state');
    expect(state?.textContent).toBe('TX');
    expect(state?.getAttribute('data-active')).toBe('true');
  });
});

describe('MetersDockPanel capability gating', () => {
  it('hides Po tile when powerMeter is undefined', () => {
    const t = mountPanel({ ...fullProps, powerMeter: undefined });
    expect(t.querySelector('[data-meter="po"]')).toBeNull();
    expect(t.querySelectorAll('.dock-tile')).toHaveLength(3);
  });

  it('hides SWR tile when swrMeter is undefined', () => {
    const t = mountPanel({ ...fullProps, swrMeter: undefined });
    expect(t.querySelector('[data-meter="swr"]')).toBeNull();
  });

  it('hides ALC tile when alcMeter is undefined', () => {
    const t = mountPanel({ ...fullProps, alcMeter: undefined });
    expect(t.querySelector('[data-meter="alc"]')).toBeNull();
  });

  it('hides S tile when sValue is undefined', () => {
    const t = mountPanel({ ...fullProps, sValue: undefined });
    expect(t.querySelector('[data-meter="s"]')).toBeNull();
  });

  it('renders no tiles when all state fields are undefined', () => {
    const t = mountPanel({
      sValue: undefined,
      powerMeter: undefined,
      swrMeter: undefined,
      alcMeter: undefined,
      txActive: false,
    });
    expect(t.querySelectorAll('.dock-tile')).toHaveLength(0);
  });

  it('still renders the header when every tile is hidden', () => {
    const t = mountPanel({
      sValue: undefined,
      powerMeter: undefined,
      swrMeter: undefined,
      alcMeter: undefined,
      txActive: false,
    });
    expect(t.querySelector('.dock-title')?.textContent).toBe('STATION METERS');
  });

  it('renders Id tile when idMeter is defined', () => {
    const t = mountPanel({ ...fullProps, idMeter: 151 });
    const tile = t.querySelector('[data-meter="id"]');
    expect(tile).not.toBeNull();
    expect(tile?.querySelector('.tile-value')?.textContent).toBe('10.0 A');
  });

  it('hides Id tile when idMeter is undefined', () => {
    const t = mountPanel({ ...fullProps, idMeter: undefined });
    expect(t.querySelector('[data-meter="id"]')).toBeNull();
  });

  it('renders Vd tile when vdMeter is defined', () => {
    const t = mountPanel({ ...fullProps, vdMeter: 13 });
    const tile = t.querySelector('[data-meter="vd"]');
    expect(tile).not.toBeNull();
    expect(tile?.querySelector('.tile-value')?.textContent).toBe('10.0 V');
  });

  it('hides Vd tile when vdMeter is undefined', () => {
    const t = mountPanel({ ...fullProps, vdMeter: undefined });
    expect(t.querySelector('[data-meter="vd"]')).toBeNull();
  });

  it('renders COMP tile when compMeter is defined and compressorOn=true', () => {
    const t = mountPanel({ ...fullProps, compMeter: 75, compressorOn: true });
    const tile = t.querySelector('[data-meter="comp"]');
    expect(tile).not.toBeNull();
    expect(tile?.querySelector('.tile-value')?.textContent).toBe('15 dB');
  });

  it('hides COMP tile when compressorOn is false', () => {
    const t = mountPanel({ ...fullProps, compMeter: 75, compressorOn: false });
    expect(t.querySelector('[data-meter="comp"]')).toBeNull();
  });

  it('hides COMP tile when compressorOn is undefined (gating)', () => {
    const t = mountPanel({ ...fullProps, compMeter: 75 });
    expect(t.querySelector('[data-meter="comp"]')).toBeNull();
  });

  it('hides COMP tile when compMeter is undefined even with compressorOn=true', () => {
    const t = mountPanel({ ...fullProps, compMeter: undefined, compressorOn: true });
    expect(t.querySelector('[data-meter="comp"]')).toBeNull();
  });

  it('renders all seven tiles when all state fields are defined', () => {
    const t = mountPanel({
      ...fullProps,
      idMeter: 100,
      vdMeter: 13,
      compMeter: 75,
      compressorOn: true,
    });
    expect(t.querySelectorAll('.dock-tile')).toHaveLength(7);
    const keys = Array.from(t.querySelectorAll('.dock-tile')).map((el) =>
      el.getAttribute('data-meter'),
    );
    expect(keys).toEqual(['po', 'swr', 'alc', 'id', 'vd', 'comp', 's']);
  });
});

describe('MetersDockPanel relevance dimming', () => {
  it('marks TX tiles as relevant when txActive=true', () => {
    const t = mountPanel({ ...fullProps, txActive: true });
    expect(t.querySelector('[data-meter="po"]')?.getAttribute('data-relevant')).toBe('true');
    expect(t.querySelector('[data-meter="swr"]')?.getAttribute('data-relevant')).toBe('true');
    expect(t.querySelector('[data-meter="alc"]')?.getAttribute('data-relevant')).toBe('true');
    expect(t.querySelector('[data-meter="s"]')?.getAttribute('data-relevant')).toBe('false');
  });

  it('marks S tile as relevant when txActive=false', () => {
    const t = mountPanel({ ...fullProps, txActive: false });
    expect(t.querySelector('[data-meter="s"]')?.getAttribute('data-relevant')).toBe('true');
    expect(t.querySelector('[data-meter="po"]')?.getAttribute('data-relevant')).toBe('false');
  });
});

describe('MetersDockPanel formatted values', () => {
  it('displays Po in watts', () => {
    const t = mountPanel(fullProps);
    expect(t.querySelector('[data-meter="po"] .tile-value')?.textContent).toBe('50W');
  });

  it('displays SWR ratio', () => {
    const t = mountPanel(fullProps);
    expect(t.querySelector('[data-meter="swr"] .tile-value')?.textContent).toBe('1.5');
  });

  it('displays ALC percentage', () => {
    const t = mountPanel(fullProps);
    expect(t.querySelector('[data-meter="alc"] .tile-value')?.textContent).toBe('50%');
  });

  it('displays S-meter as S-units', () => {
    const t = mountPanel(fullProps);
    expect(t.querySelector('[data-meter="s"] .tile-value')?.textContent).toBe('S9');
  });
});
