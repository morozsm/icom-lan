import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import type { ComponentProps } from 'svelte';
import DspPanel from '../DspPanel.svelte';
import { isCwMode, buildNrOptions, buildNotchOptions } from '../dsp-utils';

vi.mock('$lib/stores/capabilities.svelte', () => ({
  hasCapability: vi.fn(() => true),
}));

// ---------------------------------------------------------------------------
// isCwMode
// ---------------------------------------------------------------------------

describe('isCwMode', () => {
  it('returns true for "CW"', () => {
    expect(isCwMode('CW')).toBe(true);
  });

  it('returns true for "CW-R"', () => {
    expect(isCwMode('CW-R')).toBe(true);
  });

  it('returns false for "USB"', () => {
    expect(isCwMode('USB')).toBe(false);
  });

  it('returns false for "LSB"', () => {
    expect(isCwMode('LSB')).toBe(false);
  });

  it('returns false for empty string', () => {
    expect(isCwMode('')).toBe(false);
  });

  it('returns false for "AM"', () => {
    expect(isCwMode('AM')).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// buildNrOptions
// ---------------------------------------------------------------------------

describe('buildNrOptions', () => {
  it('returns 2 options (toggle)', () => {
    expect(buildNrOptions()).toHaveLength(2);
  });

  it('first option is OFF with value 0', () => {
    expect(buildNrOptions()[0]).toEqual({ value: 0, label: 'OFF' });
  });

  it('second option is ON with value 1', () => {
    expect(buildNrOptions()[1]).toEqual({ value: 1, label: 'ON' });
  });

  it('returns options in order OFF/ON', () => {
    const labels = buildNrOptions().map((o) => o.label);
    expect(labels).toEqual(['OFF', 'ON']);
  });

  it('all option values are numbers', () => {
    buildNrOptions().forEach((o) => expect(typeof o.value).toBe('number'));
  });
});

// ---------------------------------------------------------------------------
// buildNotchOptions
// ---------------------------------------------------------------------------

describe('buildNotchOptions', () => {
  it('returns 3 options', () => {
    expect(buildNotchOptions()).toHaveLength(3);
  });

  it('first option is OFF with value "off"', () => {
    expect(buildNotchOptions()[0]).toEqual({ value: 'off', label: 'OFF' });
  });

  it('second option is AUTO with value "auto"', () => {
    expect(buildNotchOptions()[1]).toEqual({ value: 'auto', label: 'AUTO' });
  });

  it('third option is manual with value "manual"', () => {
    expect(buildNotchOptions()[2]).toEqual({ value: 'manual', label: 'MAN' });
  });
});

// ---------------------------------------------------------------------------
// DspPanel component
// ---------------------------------------------------------------------------

let components: ReturnType<typeof mount>[] = [];

function mountPanel(props: ComponentProps<typeof DspPanel>) {
  const t = document.createElement('div');
  document.body.appendChild(t);
  const component = mount(DspPanel, { target: t, props });
  flushSync();
  components.push(component);
  return t;
}

beforeEach(() => {
  components = [];
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

const baseProps: ComponentProps<typeof DspPanel> = {
  nrMode: 0,
  nrLevel: 128,
  nbActive: false,
  nbLevel: 128,
  notchMode: 'off',
  notchFreq: 1000,
  cwAutoTune: false,
  cwPitch: 600,
  currentMode: 'USB',
  onNrModeChange: vi.fn(),
  onNrLevelChange: vi.fn(),
  onNbToggle: vi.fn(),
  onNbLevelChange: vi.fn(),
  onNotchModeChange: vi.fn(),
  onNotchFreqChange: vi.fn(),
  onCwAutoTuneToggle: vi.fn(),
  onCwPitchChange: vi.fn(),
};

describe('panel structure', () => {
  it('renders the DSP header label', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.panel-header')?.textContent).toBe('DSP');
  });

  it('renders NB toggle as OFF when NB is inactive', () => {
    const t = mountPanel(baseProps);
    const buttons = Array.from(t.querySelectorAll('button')).map((el) => el.textContent?.trim());
    expect(buttons).toContain('OFF');
  });

  it('renders NB toggle as ON when NB is active', () => {
    const t = mountPanel({ ...baseProps, nbActive: true });
    const buttons = Array.from(t.querySelectorAll('button')).map((el) => el.textContent?.trim());
    expect(buttons).toContain('ON');
  });

  it('renders the Notch section', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.section-label')).map((el) => el.textContent);
    expect(labels).toContain('Notch');
  });
});

describe('CW section visibility', () => {
  it('does not render CW section when mode is USB', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.vc-label')).map((el) => el.textContent);
    expect(labels).not.toContain('CW Pitch');
  });

  it('renders CW section when mode is CW', () => {
    const t = mountPanel({ ...baseProps, currentMode: 'CW' });
    const labels = Array.from(t.querySelectorAll('.vc-label')).map((el) => el.textContent);
    expect(labels).toContain('CW Pitch');
  });

  it('renders CW section when mode is CW-R', () => {
    const t = mountPanel({ ...baseProps, currentMode: 'CW-R' });
    const labels = Array.from(t.querySelectorAll('.vc-label')).map((el) => el.textContent);
    expect(labels).toContain('CW Pitch');
  });
});

describe('Notch freq slider visibility', () => {
  it('does not render Notch Freq slider when notchMode is "off"', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.vc-label')).map((el) => el.textContent);
    expect(labels).not.toContain('Notch Freq');
  });

  it('does not render Notch Freq slider when notchMode is "auto"', () => {
    const t = mountPanel({ ...baseProps, notchMode: 'auto' });
    const labels = Array.from(t.querySelectorAll('.vc-label')).map((el) => el.textContent);
    expect(labels).not.toContain('Notch Freq');
  });

  it('renders Notch Freq slider when notchMode is "manual"', () => {
    const t = mountPanel({ ...baseProps, notchMode: 'manual' });
    const labels = Array.from(t.querySelectorAll('.vc-label')).map((el) => el.textContent);
    expect(labels).toContain('Notch Freq');
  });
});

describe('CW Pitch slider constraints', () => {
  it('CW Pitch slider has min=300, max=900', () => {
    const t = mountPanel({ ...baseProps, currentMode: 'CW' });
    const sliders = t.querySelectorAll<HTMLElement>('[role="slider"]');
    const pitchSlider = Array.from(sliders).at(-1)!;
    expect(pitchSlider.getAttribute('aria-valuemin')).toBe('300');
    expect(pitchSlider.getAttribute('aria-valuemax')).toBe('900');
  });
});

describe('callbacks', () => {
  it('calls onNotchModeChange when Notch segmented button changes', () => {
    const onNotchModeChange = vi.fn();
    const t = mountPanel({ ...baseProps, onNotchModeChange });
    const buttons = t.querySelectorAll<HTMLButtonElement>('button');
    // Click the AUTO button (second notch button)
    const autoBtn = Array.from(buttons).find((b) => b.textContent?.trim() === 'AUTO');
    autoBtn?.click();
    flushSync();
    expect(onNotchModeChange).toHaveBeenCalledWith('auto');
  });

  it('calls onCwPitchChange when CW Pitch slider changes', () => {
    const onCwPitchChange = vi.fn();
    const t = mountPanel({ ...baseProps, currentMode: 'CW', onCwPitchChange });
    const sliders = t.querySelectorAll<HTMLElement>('[role="slider"]');
    const pitchSlider = Array.from(sliders).at(-1)!;
    pitchSlider.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }));
    expect(onCwPitchChange).toHaveBeenCalled();
  });
});
