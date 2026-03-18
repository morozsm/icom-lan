import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import BipolarSlider from '../BipolarSlider.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountSlider(props: Record<string, unknown>) {
  const target = document.createElement('div');
  document.body.appendChild(target);
  const component = mount(BipolarSlider, { target, props });
  flushSync();
  components.push(component);
  return target;
}

function getWrapper(target: HTMLElement) {
  return target.querySelector('.bipolar-slider-wrapper') as HTMLElement;
}

function getValueDisplay(target: HTMLElement) {
  return target.querySelector('.slider-value') as HTMLElement;
}

beforeEach(() => {
  components = [];
});

afterEach(() => {
  components.forEach(component => unmount(component));
  document.body.innerHTML = '';
});

describe('BipolarSlider', () => {
  it('renders signed positive values', () => {
    const target = mountSlider({
      value: 300,
      min: -1200,
      max: 1200,
      label: 'IF Shift',
      unit: 'Hz',
      onchange: vi.fn(),
    });

    expect(getValueDisplay(target).textContent).toContain('+300');
    expect(getValueDisplay(target).textContent).toContain('Hz');
  });

  it('renders zero without a sign', () => {
    const target = mountSlider({
      value: 0,
      min: -1200,
      max: 1200,
      label: 'PBT Inner',
      onchange: vi.fn(),
    });

    expect(getValueDisplay(target).textContent?.trim()).toBe('0');
  });

  it('renders polarity markers', () => {
    const target = mountSlider({
      value: -150,
      min: -1200,
      max: 1200,
      label: 'PBT Outer',
      onchange: vi.fn(),
    });

    const axis = target.querySelector('.slider-axis')?.textContent ?? '';
    expect(axis).toContain('-');
    expect(axis).toContain('0');
    expect(axis).toContain('+');
  });

  it('sets centered fill variables around zero', () => {
    const target = mountSlider({
      value: -300,
      min: -1200,
      max: 1200,
      label: 'IF Shift',
      onchange: vi.fn(),
    });

    const style = getWrapper(target).getAttribute('style') ?? '';
    expect(style).toContain('--center: 50%');
    expect(style).toContain('--fill-start: 37.5%');
    expect(style).toContain('--fill-end: 50%');
  });

  it('fires onchange with numeric values', () => {
    const onchange = vi.fn();
    const target = mountSlider({
      value: 0,
      min: -1200,
      max: 1200,
      label: 'IF Shift',
      onchange,
    });

    const input = target.querySelector('input[type="range"]') as HTMLInputElement;
    input.value = '450';
    input.dispatchEvent(new Event('input', { bubbles: true }));

    expect(onchange).toHaveBeenCalledWith(450);
  });
});