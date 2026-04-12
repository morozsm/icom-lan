import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';

const mockProps = {
  currentMode: 'USB',
  modes: ['USB', 'LSB', 'CW', 'CW-R', 'AM', 'FM', 'RTTY', 'RTTY-R', 'PSK', 'PSK-R'],
  dataMode: 0,
  hasDataMode: true,
  dataModeCount: 3,
  dataModeLabels: { '0': 'OFF', '1': 'D1', '2': 'D2', '3': 'D3' } as Record<string, string>,
};

const mockHandlers = {
  onModeChange: vi.fn(),
  onDataModeChange: vi.fn(),
};

vi.mock('$lib/runtime/adapters/panel-adapters', () => ({
  deriveModeProps: () => mockProps,
  getModeHandlers: () => mockHandlers,
}));

import ModePanel from '../ModePanel.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountPanel(overrides?: Partial<typeof mockProps>) {
  if (overrides) Object.assign(mockProps, overrides);
  const target = document.createElement('div');
  document.body.appendChild(target);
  const component = mount(ModePanel, { target });
  flushSync();
  components.push(component);
  return target;
}

beforeEach(() => {
  components = [];
  mockProps.currentMode = 'USB';
  mockProps.modes = ['USB', 'LSB', 'CW', 'CW-R', 'AM', 'FM', 'RTTY', 'RTTY-R', 'PSK', 'PSK-R'];
  mockProps.dataMode = 0;
  mockProps.hasDataMode = true;
  mockProps.dataModeCount = 3;
  mockProps.dataModeLabels = { '0': 'OFF', '1': 'D1', '2': 'D2', '3': 'D3' };
  mockHandlers.onModeChange = vi.fn();
  mockHandlers.onDataModeChange = vi.fn();
});

afterEach(() => {
  components.forEach((component) => unmount(component));
  document.body.innerHTML = '';
});

describe('ModePanel', () => {
  it('renders mode buttons from capabilities', () => {
    const target = mountPanel();
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('.mode-grid .v2-control-button')).map((button) => button.textContent?.trim());
    expect(buttons).toEqual(['USB', 'LSB', 'CW', 'CW-R', 'RTTY', 'RTTY-R', 'PSK', 'PSK-R', 'AM', 'FM']);
  });

  it('highlights the active mode button', () => {
    const target = mountPanel({ currentMode: 'CW' });
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('.mode-grid .v2-control-button'));
    const button = buttons.find((b) => b.textContent?.trim() === 'CW');
    expect(button?.dataset.active).toBe('true');
  });

  it('calls onModeChange when a mode button is clicked', () => {
    const target = mountPanel();
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('.mode-grid .v2-control-button'));
    buttons.find((b) => b.textContent?.trim() === 'LSB')?.click();
    flushSync();
    expect(mockHandlers.onModeChange).toHaveBeenCalledWith('LSB');
  });

  it('renders DATA mode controls when supported', () => {
    const target = mountPanel();
    const dataButtons = Array.from(target.querySelectorAll<HTMLButtonElement>('.data-grid .v2-control-button')).map((button) => button.textContent?.trim());
    expect(dataButtons).toEqual(['OFF', 'D1', 'D2', 'D3']);
  });

  it('does not render DATA mode controls when unsupported', () => {
    const target = mountPanel({ hasDataMode: false });
    expect(target.querySelector('.data-grid')).toBeNull();
  });

  it('calls onDataModeChange with numeric modes', () => {
    const target = mountPanel();
    const dataButtons = Array.from(target.querySelectorAll<HTMLButtonElement>('.data-grid .v2-control-button'));
    dataButtons.find((b) => b.textContent?.trim() === 'D3')?.click();
    flushSync();
    expect(mockHandlers.onDataModeChange).toHaveBeenCalledWith(3);
  });
});
