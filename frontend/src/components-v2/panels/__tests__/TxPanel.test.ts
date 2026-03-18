import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import type { ComponentProps } from 'svelte';
import TxPanel from '../TxPanel.svelte';
import { txStatusColor } from '../tx-utils';

// ---------------------------------------------------------------------------
// txStatusColor
// ---------------------------------------------------------------------------

describe('txStatusColor', () => {
  it('returns danger red when tuning', () => {
    expect(txStatusColor(true, true)).toBe('#FF2020');
  });

  it('returns danger red when tuning even if active is false', () => {
    expect(txStatusColor(false, true)).toBe('#FF2020');
  });

  it('returns TX orange when active and not tuning', () => {
    expect(txStatusColor(true, false)).toBe('#FF6A00');
  });

  it('returns muted color when inactive and not tuning', () => {
    expect(txStatusColor(false, false)).toBe('#3A4A5A');
  });

  it('tuning takes priority over active', () => {
    // tuning=true always wins, regardless of active
    expect(txStatusColor(true, true)).toBe('#FF2020');
    expect(txStatusColor(false, true)).toBe('#FF2020');
  });
});

// ---------------------------------------------------------------------------
// TxPanel component
// ---------------------------------------------------------------------------

// Mock hasTx so we can control its return value
vi.mock('$lib/stores/capabilities.svelte', () => ({
  hasTx: vi.fn(() => true),
  hasCapability: vi.fn(() => true),
}));

import { hasTx } from '$lib/stores/capabilities.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountPanel(props: ComponentProps<typeof TxPanel>) {
  const t = document.createElement('div');
  document.body.appendChild(t);
  const component = mount(TxPanel, { target: t, props });
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

const baseProps: ComponentProps<typeof TxPanel> = {
  txActive: false,
  micGain: 128,
  atuActive: false,
  atuTuning: false,
  voxActive: false,
  compActive: false,
  compLevel: 64,
  monActive: false,
  monLevel: 64,
  onMicGainChange: vi.fn(),
  onAtuToggle: vi.fn(),
  onAtuTune: vi.fn(),
  onVoxToggle: vi.fn(),
  onCompToggle: vi.fn(),
  onCompLevelChange: vi.fn(),
  onMonToggle: vi.fn(),
  onMonLevelChange: vi.fn(),
};

describe('panel structure', () => {
  it('renders the TX header label', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.panel-header')?.textContent?.trim()).toBe('TX');
  });

  it('renders TX IDLE badge when txActive is false', () => {
    const t = mountPanel(baseProps);
    const badge = t.querySelector('.tx-indicator .badge');
    expect(badge?.textContent?.trim()).toBe('TX IDLE');
  });

  it('renders TX ACTIVE badge when txActive is true', () => {
    const t = mountPanel({ ...baseProps, txActive: true });
    const badge = t.querySelector('.tx-indicator .badge');
    expect(badge?.textContent?.trim()).toBe('TX ACTIVE');
  });

  it('renders Mic Gain slider', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.slider-label'));
    expect(labels.some((el) => el.textContent === 'Mic Gain')).toBe(true);
  });

  it('renders ATU badge', () => {
    const t = mountPanel(baseProps);
    const badges = Array.from(t.querySelectorAll('.badge'));
    expect(badges.some((el) => el.textContent?.trim() === 'ATU')).toBe(true);
  });

  it('renders TUNE button', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.tune-button')?.textContent?.trim()).toBe('TUNE');
  });

  it('renders VOX badge', () => {
    const t = mountPanel(baseProps);
    const badges = Array.from(t.querySelectorAll('.badge'));
    expect(badges.some((el) => el.textContent?.trim() === 'VOX')).toBe(true);
  });

  it('renders COMP badge', () => {
    const t = mountPanel(baseProps);
    const badges = Array.from(t.querySelectorAll('.badge'));
    expect(badges.some((el) => el.textContent?.trim() === 'COMP')).toBe(true);
  });

  it('renders MON badge', () => {
    const t = mountPanel(baseProps);
    const badges = Array.from(t.querySelectorAll('.badge'));
    expect(badges.some((el) => el.textContent?.trim() === 'MON')).toBe(true);
  });
});

describe('hasTx gating', () => {
  it('renders panel content when hasTx returns true', () => {
    vi.mocked(hasTx).mockReturnValue(true);
    const t = mountPanel(baseProps);
    expect(t.querySelector('.panel')).not.toBeNull();
  });

  it('hides panel content when hasTx returns false', () => {
    vi.mocked(hasTx).mockReturnValue(false);
    const t = mountPanel(baseProps);
    expect(t.querySelector('.panel')).toBeNull();
  });
});

describe('COMP slider visibility', () => {
  it('does not render Comp Level slider when compActive is false', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.slider-label')).map((el) => el.textContent);
    expect(labels).not.toContain('Comp Level');
  });

  it('renders Comp Level slider when compActive is true', () => {
    const t = mountPanel({ ...baseProps, compActive: true });
    const labels = Array.from(t.querySelectorAll('.slider-label')).map((el) => el.textContent);
    expect(labels).toContain('Comp Level');
  });
});

describe('MON slider visibility', () => {
  it('does not render Mon Level slider when monActive is false', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.slider-label')).map((el) => el.textContent);
    expect(labels).not.toContain('Mon Level');
  });

  it('renders Mon Level slider when monActive is true', () => {
    const t = mountPanel({ ...baseProps, monActive: true });
    const labels = Array.from(t.querySelectorAll('.slider-label')).map((el) => el.textContent);
    expect(labels).toContain('Mon Level');
  });
});

describe('tuning state', () => {
  it('adds tuning class to TUNE button when atuTuning is true', () => {
    const t = mountPanel({ ...baseProps, atuTuning: true });
    expect(t.querySelector('.tune-button')?.classList.contains('tuning')).toBe(true);
  });

  it('does not add tuning class when atuTuning is false', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.tune-button')?.classList.contains('tuning')).toBe(false);
  });
});

describe('callbacks', () => {
  it('calls onAtuTune when TUNE button is clicked', () => {
    const onAtuTune = vi.fn();
    const t = mountPanel({ ...baseProps, onAtuTune });
    const btn = t.querySelector<HTMLElement>('.tune-button');
    btn?.click();
    expect(onAtuTune).toHaveBeenCalledOnce();
  });

  it('calls onMicGainChange when Mic Gain slider changes', () => {
    const onMicGainChange = vi.fn();
    const t = mountPanel({ ...baseProps, onMicGainChange });
    const input = t.querySelector<HTMLInputElement>('input[type="range"]');
    if (input) {
      input.value = '200';
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
    expect(onMicGainChange).toHaveBeenCalledWith(200);
  });
});
