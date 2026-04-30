import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';

const mockProps = {
  nrMode: 0,
  nrLevel: 5,
  nbActive: false,
  nbLevel: 128,
  notchMode: 'off' as string,
  notchFreq: 1000,
  nbDepth: 0,
  nbWidth: 0,
  manualNotchWidth: 0,
  agcTimeConstant: 0,
  hasNr: true,
  hasNb: true,
};

const mockHandlers = {
  onNrModeChange: vi.fn(),
  onNrLevelChange: vi.fn(),
  onNbToggle: vi.fn(),
  onNbLevelChange: vi.fn(),
  onNotchModeChange: vi.fn(),
  onNotchFreqChange: vi.fn(),
  onNbDepthChange: vi.fn(),
  onNbWidthChange: vi.fn(),
  onManualNotchWidthChange: vi.fn(),
  onAgcTimeChange: vi.fn(),
};

vi.mock('$lib/runtime/adapters/panel-adapters', () => ({
  deriveDspProps: () => mockProps,
  getDspHandlers: () => mockHandlers,
}));

import DspPanel from '../DspPanel.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountPanel(overrides?: Partial<typeof mockProps>) {
  if (overrides) Object.assign(mockProps, overrides);
  const t = document.createElement('div');
  document.body.appendChild(t);
  const component = mount(DspPanel, { target: t });
  flushSync();
  components.push(component);
  return t;
}

beforeEach(() => {
  components = [];
  Object.assign(mockProps, {
    nrMode: 0, nrLevel: 5, nbActive: false, nbLevel: 128,
    notchMode: 'off', notchFreq: 1000, nbDepth: 0, nbWidth: 0,
    manualNotchWidth: 0, agcTimeConstant: 0,
    hasNr: true, hasNb: true,
  });
  mockHandlers.onNrModeChange = vi.fn();
  mockHandlers.onNrLevelChange = vi.fn();
  mockHandlers.onNbToggle = vi.fn();
  mockHandlers.onNbLevelChange = vi.fn();
  mockHandlers.onNotchModeChange = vi.fn();
  mockHandlers.onNotchFreqChange = vi.fn();
  mockHandlers.onNbDepthChange = vi.fn();
  mockHandlers.onNbWidthChange = vi.fn();
  mockHandlers.onManualNotchWidthChange = vi.fn();
  mockHandlers.onAgcTimeChange = vi.fn();
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

describe('DspPanel component rendering', () => {
  it('mounts without errors', () => {
    const t = mountPanel();
    expect(t.querySelector('.dsp-panel')).not.toBeNull();
  });

  it('renders NB button', () => {
    const t = mountPanel();
    const buttons = Array.from(t.querySelectorAll('button'));
    expect(buttons.some((b) => b.textContent?.trim().startsWith('NB'))).toBe(true);
  });

  it('renders NR button', () => {
    const t = mountPanel();
    const buttons = Array.from(t.querySelectorAll('button'));
    expect(buttons.some((b) => b.textContent?.trim().startsWith('NR'))).toBe(true);
  });

  it('renders NOTCH button', () => {
    const t = mountPanel();
    const buttons = Array.from(t.querySelectorAll('button'));
    expect(buttons.some((b) => b.textContent?.trim() === 'NOTCH')).toBe(true);
  });

  it('renders A-NOTCH button', () => {
    const t = mountPanel();
    const buttons = Array.from(t.querySelectorAll('button'));
    expect(buttons.some((b) => b.textContent?.trim() === 'A-NOTCH')).toBe(true);
  });

  it('renders AGC-T button', () => {
    const t = mountPanel();
    const buttons = Array.from(t.querySelectorAll('button'));
    expect(buttons.some((b) => b.textContent?.trim().startsWith('AGC-T'))).toBe(true);
  });

  it('unmounts cleanly', () => {
    const t = mountPanel();
    const comp = components.pop()!;
    unmount(comp);
    expect(t.innerHTML).toBe('');
  });
});
