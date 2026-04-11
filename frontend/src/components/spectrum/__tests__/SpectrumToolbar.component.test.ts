/**
 * Component-level test for SpectrumToolbar.svelte.
 * Mounts the real component and verifies DOM output + interactions.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';

// ── Mocks (must be before imports) ──────────────────────────────────────────

vi.mock('$lib/stores/radio.svelte', () => ({
  radio: { current: { scopeControls: { mode: 0, span: 3, speed: 1, hold: false, dual: false, receiver: 0, refDb: 0, edge: 1 } } },
  getRadioState: vi.fn(() => null),
  patchActiveReceiver: vi.fn(),
  patchRadioState: vi.fn(),
}));

vi.mock('$lib/transport/ws-client', () => ({
  sendCommand: vi.fn(),
}));

vi.mock('$lib/stores/capabilities.svelte', () => ({
  hasCapability: vi.fn(() => true),
  hasDualReceiver: vi.fn(() => true),
}));

vi.mock('$lib/stores/tuning.svelte', () => ({
  getTuningStep: vi.fn(() => 1000),
  adjustTuningStep: vi.fn(),
  isAutoStep: vi.fn(() => false),
  formatStep: vi.fn(() => '1.0k'),
}));

vi.mock('../ScopeSettingsPopover.svelte', () => ({
  default: vi.fn(),
}));

// Stub fetch for band-plan API calls
globalThis.fetch = vi.fn(() =>
  Promise.resolve({ ok: false, json: () => Promise.resolve({}) } as Response),
);

import SpectrumToolbar from '../SpectrumToolbar.svelte';
import { sendCommand } from '$lib/transport/ws-client';

// ── Helpers ─────────────────────────────────────────────────────────────────

let components: ReturnType<typeof mount>[] = [];

function mountToolbar(props: Record<string, unknown> = {}) {
  const target = document.createElement('div');
  document.body.appendChild(target);
  const component = mount(SpectrumToolbar, {
    target,
    props: {
      enableAvg: true,
      enablePeakHold: true,
      brtLevel: 0,
      colorScheme: 'classic',
      fullscreen: false,
      showBandPlan: true,
      hiddenLayers: [],
      showEiBi: false,
      ...props,
    },
  });
  flushSync();
  components.push(component);
  return target;
}

beforeEach(() => {
  components = [];
  vi.clearAllMocks();
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

// ── Tests ───────────────────────────────────────────────────────────────────

describe('SpectrumToolbar component', () => {
  it('mounts without errors', () => {
    const target = mountToolbar();
    expect(target.querySelector('.spectrum-toolbar')).not.toBeNull();
  });

  it('renders scope mode buttons (CTR, FIX, S-C, S-F)', () => {
    const target = mountToolbar();
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('.toolbar-btn'));
    const labels = buttons.map((b) => b.textContent?.trim());
    expect(labels).toContain('CTR');
    expect(labels).toContain('FIX');
    expect(labels).toContain('S-C');
    expect(labels).toContain('S-F');
  });

  it('renders SPAN selector in center mode', () => {
    const target = mountToolbar();
    const labels = Array.from(target.querySelectorAll('.toolbar-label'));
    const spanLabel = labels.find((el) => el.textContent?.trim() === 'SPAN');
    expect(spanLabel).toBeDefined();
  });

  it('renders speed selector', () => {
    const target = mountToolbar();
    const labels = Array.from(target.querySelectorAll('.toolbar-label'));
    const spdLabel = labels.find((el) => el.textContent?.trim() === 'SPD');
    expect(spdLabel).toBeDefined();
  });

  it('renders STEP control', () => {
    const target = mountToolbar();
    const labels = Array.from(target.querySelectorAll('.toolbar-label'));
    const stepLabel = labels.find((el) => el.textContent?.trim() === 'STEP');
    expect(stepLabel).toBeDefined();
  });

  it('renders AVG and PEAK toggles', () => {
    const target = mountToolbar();
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('.toolbar-btn'));
    const labels = buttons.map((b) => b.textContent?.trim());
    expect(labels).toContain('AVG');
    expect(labels).toContain('PEAK');
  });

  it('renders brightness controls', () => {
    const target = mountToolbar();
    const labels = Array.from(target.querySelectorAll('.toolbar-label'));
    const brtLabel = labels.find((el) => el.textContent?.trim() === 'BRT');
    expect(brtLabel).toBeDefined();
  });

  it('renders HOLD button', () => {
    const target = mountToolbar();
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('.toolbar-btn'));
    const holdBtn = buttons.find((b) => b.textContent?.trim() === 'HOLD');
    expect(holdBtn).toBeDefined();
  });

  it('renders DUAL and receiver buttons when dual receiver available', () => {
    const target = mountToolbar();
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('.toolbar-btn'));
    const labels = buttons.map((b) => b.textContent?.trim());
    expect(labels).toContain('DUAL');
    expect(labels).toContain('MAIN');
  });

  it('renders color scheme selector', () => {
    const target = mountToolbar();
    const select = target.querySelector<HTMLSelectElement>('.toolbar-select');
    expect(select).not.toBeNull();
    const options = Array.from(select!.querySelectorAll('option')).map((o) => o.value);
    expect(options).toEqual(['classic', 'thermal', 'grayscale']);
  });

  it('renders BANDS button', () => {
    const target = mountToolbar();
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('.toolbar-btn'));
    const bandsBtn = buttons.find((b) => b.textContent?.trim() === 'BANDS');
    expect(bandsBtn).toBeDefined();
  });

  it('renders fullscreen toggle button', () => {
    const target = mountToolbar();
    const iconBtn = target.querySelector<HTMLButtonElement>('.icon-btn');
    expect(iconBtn).not.toBeNull();
  });

  it('mode button click dispatches sendCommand', () => {
    const target = mountToolbar();
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('.toolbar-btn'));
    const fixBtn = buttons.find((b) => b.textContent?.trim() === 'FIX');
    expect(fixBtn).toBeDefined();
    fixBtn!.click();
    flushSync();
    expect(sendCommand).toHaveBeenCalledWith('set_scope_mode', { mode: 1 });
  });

  it('HOLD button click dispatches sendCommand', () => {
    const target = mountToolbar();
    const buttons = Array.from(target.querySelectorAll<HTMLButtonElement>('.toolbar-btn'));
    const holdBtn = buttons.find((b) => b.textContent?.trim() === 'HOLD');
    expect(holdBtn).toBeDefined();
    holdBtn!.click();
    flushSync();
    expect(sendCommand).toHaveBeenCalledWith('set_scope_hold', { on: true });
  });

  it('unmounts cleanly', () => {
    const target = mountToolbar();
    expect(target.querySelector('.spectrum-toolbar')).not.toBeNull();
    const comp = components.pop()!;
    unmount(comp);
    expect(target.querySelector('.spectrum-toolbar')).toBeNull();
  });
});
