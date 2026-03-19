import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import type { ComponentProps } from 'svelte';

import ModePanel from '../ModePanel.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountPanel(props: ComponentProps<typeof ModePanel>) {
  const target = document.createElement('div');
  document.body.appendChild(target);
  const component = mount(ModePanel, { target, props });
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

const baseProps: ComponentProps<typeof ModePanel> = {
  currentMode: 'USB',
  modes: ['USB', 'LSB', 'CW', 'CW-R', 'AM', 'FM', 'RTTY', 'RTTY-R', 'PSK', 'PSK-R'],
  dataMode: 0,
  hasDataMode: true,
  dataModeCount: 3,
  dataModeLabels: { '0': 'OFF', '1': 'D1', '2': 'D2', '3': 'D3' },
  onModeChange: vi.fn(),
  onDataModeChange: vi.fn(),
};

describe('ModePanel', () => {
  it('renders mode buttons from capabilities', () => {
    const target = mountPanel(baseProps);
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('[data-mode]')).map((button) => button.textContent?.trim());
    expect(buttons).toEqual(['USB', 'LSB', 'CW', 'CW-R', 'RTTY', 'RTTY-R', 'PSK', 'PSK-R', 'AM', 'FM']);
  });

  it('highlights the active mode button', () => {
    const target = mountPanel({ ...baseProps, currentMode: 'CW' });
    const button = target.querySelector<HTMLButtonElement>('[data-mode="CW"]');
    expect(button?.classList.contains('active')).toBe(true);
  });

  it('calls onModeChange when a mode button is clicked', () => {
    const onModeChange = vi.fn();
    const target = mountPanel({ ...baseProps, onModeChange });
    target.querySelector<HTMLButtonElement>('[data-mode="LSB"]')?.click();
    flushSync();
    expect(onModeChange).toHaveBeenCalledWith('LSB');
  });

  it('renders DATA mode controls when supported', () => {
    const target = mountPanel(baseProps);
    const dataButtons = Array.from(target.querySelectorAll<HTMLButtonElement>('[data-data-mode]')).map((button) => button.textContent?.trim());
    expect(dataButtons).toEqual(['OFF', 'D1', 'D2', 'D3']);
  });

  it('does not render DATA mode controls when unsupported', () => {
    const target = mountPanel({ ...baseProps, hasDataMode: false });
    expect(target.querySelector('[data-data-mode]')).toBeNull();
  });

  it('calls onDataModeChange with numeric modes', () => {
    const onDataModeChange = vi.fn();
    const target = mountPanel({ ...baseProps, onDataModeChange });
    target.querySelector<HTMLButtonElement>('[data-data-mode="3"]')?.click();
    flushSync();
    expect(onDataModeChange).toHaveBeenCalledWith(3);
  });
});