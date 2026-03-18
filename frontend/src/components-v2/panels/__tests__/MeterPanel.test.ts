import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import type { ComponentProps } from 'svelte';
import MeterPanel from '../MeterPanel.svelte';
import {
  normalize,
  formatPowerWatts,
  formatSwr,
  formatAlc,
  getNeedleMarks,
} from '../meter-utils';

// ---------------------------------------------------------------------------
// normalize
// ---------------------------------------------------------------------------

describe('normalize', () => {
  it('maps 0 to 0', () => {
    expect(normalize(0)).toBe(0);
  });

  it('maps 255 to 1', () => {
    expect(normalize(255)).toBe(1);
  });

  it('maps 128 to ~0.502', () => {
    expect(normalize(128)).toBeCloseTo(128 / 255, 5);
  });

  it('clamps negative values to 0', () => {
    expect(normalize(-10)).toBe(0);
  });

  it('clamps values above 255 to 1', () => {
    expect(normalize(300)).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// formatPowerWatts
// ---------------------------------------------------------------------------

describe('formatPowerWatts', () => {
  it('returns 0W for raw 0', () => {
    expect(formatPowerWatts(0)).toBe('0W');
  });

  it('returns 100W for raw 255', () => {
    expect(formatPowerWatts(255)).toBe('100W');
  });

  it('returns 50W for raw 128', () => {
    expect(formatPowerWatts(128)).toBe('50W');
  });

  it('clamps negative raw to 0W', () => {
    expect(formatPowerWatts(-50)).toBe('0W');
  });
});

// ---------------------------------------------------------------------------
// formatSwr
// ---------------------------------------------------------------------------

describe('formatSwr', () => {
  it('returns 1.0 for raw 0', () => {
    expect(formatSwr(0)).toBe('1.0');
  });

  it('returns 1.5 for raw 49', () => {
    expect(formatSwr(49)).toBe('1.5');
  });

  it('returns 2.0 for raw 79', () => {
    expect(formatSwr(79)).toBe('2.0');
  });

  it('returns 3.0 for raw 112', () => {
    expect(formatSwr(112)).toBe('3.0');
  });

  it('returns 5.0 for raw 143', () => {
    expect(formatSwr(143)).toBe('5.0');
  });

  it('returns ∞ for raw 191', () => {
    expect(formatSwr(191)).toBe('∞');
  });

  it('returns ∞ for raw 255', () => {
    expect(formatSwr(255)).toBe('∞');
  });
});

// ---------------------------------------------------------------------------
// formatAlc
// ---------------------------------------------------------------------------

describe('formatAlc', () => {
  it('returns 0% for raw 0', () => {
    expect(formatAlc(0)).toBe('0%');
  });

  it('returns 100% for raw 255', () => {
    expect(formatAlc(255)).toBe('100%');
  });

  it('returns 50% for raw 128', () => {
    expect(formatAlc(128)).toBe('50%');
  });
});

// ---------------------------------------------------------------------------
// getNeedleMarks
// ---------------------------------------------------------------------------

describe('getNeedleMarks S-meter', () => {
  it('returns 7 marks for S source', () => {
    expect(getNeedleMarks('S')).toHaveLength(7);
  });

  it('first mark is S1 at 0.06', () => {
    const marks = getNeedleMarks('S');
    expect(marks[0]).toEqual({ pos: 0.06, label: 'S1' });
  });

  it('last mark is +40 at 0.94', () => {
    const marks = getNeedleMarks('S');
    expect(marks[6]).toEqual({ pos: 0.94, label: '+40' });
  });

  it('includes S9 at 0.56', () => {
    const marks = getNeedleMarks('S');
    expect(marks.some((m) => m.label === 'S9' && m.pos === 0.56)).toBe(true);
  });
});

describe('getNeedleMarks SWR', () => {
  it('returns 6 marks for SWR source', () => {
    expect(getNeedleMarks('SWR')).toHaveLength(6);
  });

  it('first mark is 1.0 at 0.06', () => {
    const marks = getNeedleMarks('SWR');
    expect(marks[0]).toEqual({ pos: 0.06, label: '1.0' });
  });

  it('last mark is ∞ at 0.75', () => {
    const marks = getNeedleMarks('SWR');
    expect(marks[5]).toEqual({ pos: 0.75, label: '∞' });
  });
});

describe('getNeedleMarks POWER', () => {
  it('returns 5 marks for POWER source', () => {
    expect(getNeedleMarks('POWER')).toHaveLength(5);
  });

  it('marks are 0, 25, 50, 75, 100', () => {
    const labels = getNeedleMarks('POWER').map((m) => m.label);
    expect(labels).toEqual(['0', '25', '50', '75', '100']);
  });
});

// ---------------------------------------------------------------------------
// MeterPanel component
// ---------------------------------------------------------------------------

vi.mock('$lib/stores/capabilities.svelte', () => ({
  hasTx: vi.fn(() => true),
}));

import { hasTx } from '$lib/stores/capabilities.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountPanel(props: ComponentProps<typeof MeterPanel>) {
  const t = document.createElement('div');
  document.body.appendChild(t);
  const component = mount(MeterPanel, { target: t, props });
  flushSync();
  components.push(component);
  return t;
}

beforeEach(() => {
  components = [];
  vi.mocked(hasTx).mockReturnValue(true);
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

const baseProps: ComponentProps<typeof MeterPanel> = {
  sValue: 120,
  rfPower: 100,
  swr: 50,
  alc: 64,
  txActive: false,
  meterSource: 'S',
  onMeterSourceChange: vi.fn(),
};

describe('panel structure', () => {
  it('renders the METERS header', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.panel-header')?.textContent?.trim()).toBe('METERS');
  });

  it('renders needle section', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.needle-section')).not.toBeNull();
  });

  it('renders source selector', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.source-selector')).not.toBeNull();
  });

  it('renders S source button', () => {
    const t = mountPanel(baseProps);
    const btns = Array.from(t.querySelectorAll('.source-btn'));
    expect(btns.some((b) => b.textContent?.trim() === 'S')).toBe(true);
  });

  it('renders SWR source button when hasTx is true', () => {
    const t = mountPanel(baseProps);
    const btns = Array.from(t.querySelectorAll('.source-btn'));
    expect(btns.some((b) => b.textContent?.trim() === 'SWR')).toBe(true);
  });

  it('renders Po source button when hasTx is true', () => {
    const t = mountPanel(baseProps);
    const btns = Array.from(t.querySelectorAll('.source-btn'));
    expect(btns.some((b) => b.textContent?.trim() === 'Po')).toBe(true);
  });

  it('marks S button as active when meterSource is S', () => {
    const t = mountPanel(baseProps);
    const sBtn = Array.from(t.querySelectorAll('.source-btn')).find(
      (b) => b.textContent?.trim() === 'S',
    );
    expect(sBtn?.classList.contains('active')).toBe(true);
  });

  it('marks SWR button as active when meterSource is SWR', () => {
    const t = mountPanel({ ...baseProps, meterSource: 'SWR' });
    const swrBtn = Array.from(t.querySelectorAll('.source-btn')).find(
      (b) => b.textContent?.trim() === 'SWR',
    );
    expect(swrBtn?.classList.contains('active')).toBe(true);
  });
});

describe('TX meters visibility', () => {
  it('does not render tx-meters section when txActive is false', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.tx-meters')).toBeNull();
  });

  it('renders tx-meters section when txActive is true', () => {
    const t = mountPanel({ ...baseProps, txActive: true });
    expect(t.querySelector('.tx-meters')).not.toBeNull();
  });
});

describe('TX source buttons visibility', () => {
  it('hides SWR and Po buttons when hasTx returns false', () => {
    vi.mocked(hasTx).mockReturnValue(false);
    const t = mountPanel(baseProps);
    const btns = Array.from(t.querySelectorAll('.source-btn'));
    expect(btns.every((b) => b.textContent?.trim() === 'S')).toBe(true);
    expect(btns).toHaveLength(1);
  });
});

describe('callbacks', () => {
  it('calls onMeterSourceChange with SWR when SWR button is clicked', () => {
    const onMeterSourceChange = vi.fn();
    const t = mountPanel({ ...baseProps, onMeterSourceChange });
    const swrBtn = Array.from(t.querySelectorAll<HTMLElement>('.source-btn')).find(
      (b) => b.textContent?.trim() === 'SWR',
    );
    swrBtn?.click();
    expect(onMeterSourceChange).toHaveBeenCalledWith('SWR');
  });

  it('calls onMeterSourceChange with S when S button is clicked', () => {
    const onMeterSourceChange = vi.fn();
    const t = mountPanel({ ...baseProps, meterSource: 'SWR', onMeterSourceChange });
    const sBtn = Array.from(t.querySelectorAll<HTMLElement>('.source-btn')).find(
      (b) => b.textContent?.trim() === 'S',
    );
    sBtn?.click();
    expect(onMeterSourceChange).toHaveBeenCalledWith('S');
  });

  it('calls onMeterSourceChange with POWER when Po button is clicked', () => {
    const onMeterSourceChange = vi.fn();
    const t = mountPanel({ ...baseProps, onMeterSourceChange });
    const poBtn = Array.from(t.querySelectorAll<HTMLElement>('.source-btn')).find(
      (b) => b.textContent?.trim() === 'Po',
    );
    poBtn?.click();
    expect(onMeterSourceChange).toHaveBeenCalledWith('POWER');
  });
});
