import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';

import AttenuatorControl from '../AttenuatorControl.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountControl(props: Record<string, unknown>) {
  const target = document.createElement('div');
  document.body.appendChild(target);
  const component = mount(AttenuatorControl, { target, props });
  flushSync();
  components.push(component);
  return target;
}

beforeEach(() => {
  components = [];
});

afterEach(() => {
  components.forEach((component) => unmount(component));
  document.body.innerHTML = '';
});

describe('AttenuatorControl', () => {
  it('renders all available values directly when the attenuator only has two positions', () => {
    const target = mountControl({
      values: [0, 20],
      selected: 0,
      onchange: vi.fn(),
    });

    const segments = Array.from(target.querySelectorAll('.segment')).map((button) => button.textContent?.trim());
    expect(segments).toEqual(['OFF', '20dB']);
    expect(target.querySelector('.more-button')).toBeNull();
  });

  it('renders quick OFF/6/12/18 picks for dense attenuator ladders', () => {
    const target = mountControl({
      values: [0, 3, 6, 9, 12, 15, 18],
      selected: 0,
      onchange: vi.fn(),
    });

    const segments = Array.from(target.querySelectorAll('.segment')).map((button) => button.textContent?.trim());
    expect(segments).toEqual(['OFF', '6dB', '12dB', '18dB']);
    expect(target.querySelector('.more-button')?.textContent?.trim()).toBe('MORE');
  });

  it('shows the selected overflow value on the more button when ATT is on a non-quick step', () => {
    const target = mountControl({
      values: [0, 3, 6, 9, 12, 15, 18],
      selected: 15,
      onchange: vi.fn(),
    });

    const moreButton = target.querySelector('.more-button');
    expect(moreButton?.textContent?.trim()).toBe('15dB');
    expect(moreButton?.classList.contains('active')).toBe(true);
  });

  it('opens the overflow menu and selects a non-quick value', () => {
    const onchange = vi.fn();
    const target = mountControl({
      values: [0, 3, 6, 9, 12, 15, 18],
      selected: 0,
      onchange,
    });

    (target.querySelector('.more-button') as HTMLButtonElement).click();
    flushSync();

    const menuItems = Array.from(document.querySelectorAll('.menu-item'));
    expect(menuItems.map((item) => item.textContent?.trim())).toEqual(['3dB', '9dB', '15dB']);

    (menuItems[2] as HTMLButtonElement).click();
    flushSync();

    expect(onchange).toHaveBeenCalledWith(15);
    expect(document.querySelector('.menu')).toBeNull();
  });
});