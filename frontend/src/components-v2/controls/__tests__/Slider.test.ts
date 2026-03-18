import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import type { ComponentProps } from 'svelte';
import Slider from '../Slider.svelte';

const target = document.createElement('div');
document.body.appendChild(target);

let components: ReturnType<typeof mount>[] = [];

function mountSlider(props: ComponentProps<typeof Slider>) {
  const t = document.createElement('div');
  document.body.appendChild(t);
  const component = mount(Slider, { target: t, props });
  flushSync();
  components.push(component);
  return t;
}

function getInput(t: HTMLElement) {
  return t.querySelector('input[type="range"]') as HTMLInputElement;
}

function getLabel(t: HTMLElement) {
  return t.querySelector('.slider-label') as HTMLElement;
}

function getValueDisplay(t: HTMLElement) {
  return t.querySelector('.slider-value') as HTMLElement;
}

function getWrapper(t: HTMLElement) {
  return t.querySelector('.slider-wrapper') as HTMLElement;
}

beforeEach(() => {
  components = [];
});

afterEach(() => {
  components.forEach(c => unmount(c));
  document.body.innerHTML = '';
  const fresh = document.createElement('div');
  document.body.appendChild(fresh);
});

describe('rendering', () => {
  it('renders the label', () => {
    const t = mountSlider({ value: 128, label: 'RF Gain', onchange: vi.fn() });
    expect(getLabel(t).textContent).toBe('RF Gain');
  });

  it('renders the numeric value', () => {
    const t = mountSlider({ value: 64, label: 'AF Level', onchange: vi.fn() });
    expect(getValueDisplay(t).textContent).toContain('64');
  });

  it('renders value with unit when provided', () => {
    const t = mountSlider({ value: 80, label: 'Filter', unit: 'Hz', onchange: vi.fn() });
    expect(getValueDisplay(t).textContent).toContain('80');
    expect(getValueDisplay(t).textContent).toContain('Hz');
  });

  it('renders value without unit when not provided', () => {
    const t = mountSlider({ value: 100, label: 'Gain', onchange: vi.fn() });
    const text = getValueDisplay(t).textContent ?? '';
    expect(text.trim()).toBe('100');
  });

  it('renders input with correct min/max/step defaults', () => {
    const t = mountSlider({ value: 128, label: 'X', onchange: vi.fn() });
    const input = getInput(t);
    expect(input.min).toBe('0');
    expect(input.max).toBe('255');
    expect(input.step).toBe('1');
  });

  it('renders input with custom min/max/step', () => {
    const t = mountSlider({ value: 500, min: 100, max: 1000, step: 10, label: 'CW Pitch', onchange: vi.fn() });
    const input = getInput(t);
    expect(input.min).toBe('100');
    expect(input.max).toBe('1000');
    expect(input.step).toBe('10');
  });

  it('sets input value to the provided value', () => {
    const t = mountSlider({ value: 200, label: 'X', onchange: vi.fn() });
    expect(getInput(t).value).toBe('200');
  });
});

describe('onchange callback', () => {
  it('fires onchange when input event occurs', () => {
    const onchange = vi.fn();
    const t = mountSlider({ value: 50, label: 'Y', onchange });
    const input = getInput(t);
    input.value = '120';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    expect(onchange).toHaveBeenCalledOnce();
    expect(onchange).toHaveBeenCalledWith(120);
  });

  it('fires onchange with numeric value (not string)', () => {
    const onchange = vi.fn();
    const t = mountSlider({ value: 50, label: 'Y', onchange });
    const input = getInput(t);
    input.value = '77';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    expect(typeof onchange.mock.calls[0][0]).toBe('number');
  });

  it('fires onchange on every input event (continuous drag)', () => {
    const onchange = vi.fn();
    const t = mountSlider({ value: 0, label: 'Z', onchange });
    const input = getInput(t);
    for (const v of [10, 20, 30]) {
      input.value = String(v);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
    expect(onchange).toHaveBeenCalledTimes(3);
  });
});

describe('disabled state', () => {
  it('disables the input when disabled=true', () => {
    const t = mountSlider({ value: 50, label: 'X', onchange: vi.fn(), disabled: true });
    expect(getInput(t).disabled).toBe(true);
  });

  it('does not disable input by default', () => {
    const t = mountSlider({ value: 50, label: 'X', onchange: vi.fn() });
    expect(getInput(t).disabled).toBe(false);
  });

  it('wrapper has disabled class when disabled', () => {
    const t = mountSlider({ value: 50, label: 'X', onchange: vi.fn(), disabled: true });
    expect(getWrapper(t).classList.contains('disabled')).toBe(true);
  });

  it('wrapper does not have disabled class when enabled', () => {
    const t = mountSlider({ value: 50, label: 'X', onchange: vi.fn() });
    expect(getWrapper(t).classList.contains('disabled')).toBe(false);
  });
});

describe('compact mode', () => {
  it('wrapper has compact class when compact=true', () => {
    const t = mountSlider({ value: 50, label: 'X', onchange: vi.fn(), compact: true });
    expect(getWrapper(t).classList.contains('compact')).toBe(true);
  });

  it('wrapper does not have compact class by default', () => {
    const t = mountSlider({ value: 50, label: 'X', onchange: vi.fn() });
    expect(getWrapper(t).classList.contains('compact')).toBe(false);
  });
});

describe('accent color', () => {
  it('applies custom accent color as CSS variable', () => {
    const t = mountSlider({ value: 50, label: 'X', onchange: vi.fn(), accentColor: '#FF6600' });
    const style = getWrapper(t).getAttribute('style') ?? '';
    expect(style).toContain('#FF6600');
  });

  it('uses default cyan accent when not specified', () => {
    const t = mountSlider({ value: 50, label: 'X', onchange: vi.fn() });
    const style = getWrapper(t).getAttribute('style') ?? '';
    expect(style).toContain('#00D4FF');
  });
});

describe('ARIA attributes', () => {
  it('has aria-label matching the label prop', () => {
    const t = mountSlider({ value: 50, label: 'RF Gain', onchange: vi.fn() });
    expect(getInput(t).getAttribute('aria-label')).toBe('RF Gain');
  });

  it('has aria-valuemin and aria-valuemax', () => {
    const t = mountSlider({ value: 50, min: 10, max: 90, label: 'X', onchange: vi.fn() });
    const input = getInput(t);
    expect(input.getAttribute('aria-valuemin')).toBe('10');
    expect(input.getAttribute('aria-valuemax')).toBe('90');
  });

  it('has aria-valuenow matching value', () => {
    const t = mountSlider({ value: 75, label: 'X', onchange: vi.fn() });
    expect(getInput(t).getAttribute('aria-valuenow')).toBe('75');
  });
});

describe('fill percentage', () => {
  it('sets --fill CSS variable based on value/range', () => {
    // value=128, min=0, max=255 → 50.19...%
    const t = mountSlider({ value: 128, min: 0, max: 255, label: 'X', onchange: vi.fn() });
    const style = getWrapper(t).getAttribute('style') ?? '';
    expect(style).toMatch(/--fill:\s*[\d.]+%/);
  });

  it('sets --fill to 0% at min value', () => {
    const t = mountSlider({ value: 0, min: 0, max: 100, label: 'X', onchange: vi.fn() });
    const style = getWrapper(t).getAttribute('style') ?? '';
    expect(style).toContain('--fill: 0%');
  });

  it('sets --fill to 100% at max value', () => {
    const t = mountSlider({ value: 100, min: 0, max: 100, label: 'X', onchange: vi.fn() });
    const style = getWrapper(t).getAttribute('style') ?? '';
    expect(style).toContain('--fill: 100%');
  });
});

describe('bipolar mode', () => {
  it('marks the wrapper as bipolar when the range crosses zero', () => {
    const t = mountSlider({ value: 0, min: -1200, max: 1200, label: 'IF Shift', onchange: vi.fn() });
    expect(getWrapper(t).classList.contains('bipolar')).toBe(true);
  });

  it('does not mark the wrapper as bipolar for unipolar ranges', () => {
    const t = mountSlider({ value: 2400, min: 50, max: 3600, label: 'Width', onchange: vi.fn() });
    expect(getWrapper(t).classList.contains('bipolar')).toBe(false);
  });

  it('sets centered fill variables when the range is bipolar', () => {
    const t = mountSlider({ value: -300, min: -1200, max: 1200, label: 'IF Shift', onchange: vi.fn() });
    const style = getWrapper(t).getAttribute('style') ?? '';
    expect(style).toContain('--center: 50%');
    expect(style).toContain('--fill-start: 37.5%');
    expect(style).toContain('--fill-end: 50%');
  });

  it('fills from the center toward the positive side for positive bipolar values', () => {
    const t = mountSlider({ value: 600, min: -1200, max: 1200, label: 'PBT Inner', onchange: vi.fn() });
    const style = getWrapper(t).getAttribute('style') ?? '';
    expect(style).toContain('--fill-start: 50%');
    expect(style).toContain('--fill-end: 75%');
  });
});
