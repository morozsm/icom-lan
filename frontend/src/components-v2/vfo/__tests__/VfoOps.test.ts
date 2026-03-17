import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import VfoOps from '../VfoOps.svelte';
import { vfoSwapLabel, vfoCopyLabel, vfoEqualLabel, vfoTxLabel } from '../vfo-ops-utils';

// ---------------------------------------------------------------------------
// Pure utility functions
// ---------------------------------------------------------------------------

describe('vfoSwapLabel', () => {
  it('returns A↔B for ab scheme', () => {
    expect(vfoSwapLabel('ab')).toBe('A↔B');
  });

  it('returns M↔S for main_sub scheme', () => {
    expect(vfoSwapLabel('main_sub')).toBe('M↔S');
  });

  it('defaults to A↔B for unknown scheme', () => {
    expect(vfoSwapLabel('unknown')).toBe('A↔B');
  });
});

describe('vfoCopyLabel', () => {
  it('returns A→B for ab scheme', () => {
    expect(vfoCopyLabel('ab')).toBe('A→B');
  });

  it('returns M→S for main_sub scheme', () => {
    expect(vfoCopyLabel('main_sub')).toBe('M→S');
  });
});

describe('vfoEqualLabel', () => {
  it('returns A=B for ab scheme', () => {
    expect(vfoEqualLabel('ab')).toBe('A=B');
  });

  it('returns M=S for main_sub scheme', () => {
    expect(vfoEqualLabel('main_sub')).toBe('M=S');
  });
});

describe('vfoTxLabel', () => {
  it('returns TX→A for main slot in ab scheme', () => {
    expect(vfoTxLabel('ab', 'main')).toBe('TX→A');
  });

  it('returns TX→B for sub slot in ab scheme', () => {
    expect(vfoTxLabel('ab', 'sub')).toBe('TX→B');
  });

  it('returns TX→M for main slot in main_sub scheme', () => {
    expect(vfoTxLabel('main_sub', 'main')).toBe('TX→M');
  });

  it('returns TX→S for sub slot in main_sub scheme', () => {
    expect(vfoTxLabel('main_sub', 'sub')).toBe('TX→S');
  });
});

// ---------------------------------------------------------------------------
// VfoOps component
// ---------------------------------------------------------------------------

vi.mock('$lib/stores/capabilities.svelte', () => ({
  hasDualReceiver: vi.fn(() => false),
  getVfoScheme: vi.fn(() => 'ab'),
  vfoLabel: vi.fn((slot: string) => (slot === 'A' ? 'VFO A' : 'VFO B')),
}));

import { hasDualReceiver, getVfoScheme } from '$lib/stores/capabilities.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountComponent(props: Record<string, unknown>) {
  const t = document.createElement('div');
  document.body.appendChild(t);
  const component = mount(VfoOps, { target: t, props });
  flushSync();
  components.push(component);
  return t;
}

const baseProps = {
  splitActive: false,
  txVfo: 'main',
  onSwap: vi.fn(),
  onCopy: vi.fn(),
  onEqual: vi.fn(),
  onSplitToggle: vi.fn(),
  onTxVfoChange: vi.fn(),
};

beforeEach(() => {
  components = [];
  vi.mocked(hasDualReceiver).mockReturnValue(false);
  vi.mocked(getVfoScheme).mockReturnValue('ab');
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

function getButtonLabels(t: HTMLElement): string[] {
  return Array.from(t.querySelectorAll('.bridge-button')).map((el) => el.textContent?.trim() ?? '');
}

describe('always-visible buttons (ab scheme)', () => {
  it('renders A↔B swap button', () => {
    const t = mountComponent(baseProps);
    expect(getButtonLabels(t)).toContain('A↔B');
  });

  it('renders A→B copy button', () => {
    const t = mountComponent(baseProps);
    expect(getButtonLabels(t)).toContain('A→B');
  });

  it('renders A=B equal button', () => {
    const t = mountComponent(baseProps);
    expect(getButtonLabels(t)).toContain('A=B');
  });

  it('renders SPLIT badge', () => {
    const t = mountComponent(baseProps);
    expect(getButtonLabels(t)).toContain('SPLIT');
  });
});

describe('always-visible buttons (main_sub scheme)', () => {
  beforeEach(() => {
    vi.mocked(getVfoScheme).mockReturnValue('main_sub');
  });

  it('renders M↔S swap button', () => {
    const t = mountComponent(baseProps);
    expect(getButtonLabels(t)).toContain('M↔S');
  });

  it('renders M→S copy button', () => {
    const t = mountComponent(baseProps);
    expect(getButtonLabels(t)).toContain('M→S');
  });

  it('renders M=S equal button', () => {
    const t = mountComponent(baseProps);
    expect(getButtonLabels(t)).toContain('M=S');
  });
});

describe('SPLIT button state', () => {
  it('SPLIT button is inactive when splitActive is false', () => {
    const t = mountComponent(baseProps);
    const split = Array.from(t.querySelectorAll('.bridge-button')).find(
      (el) => el.textContent?.trim() === 'SPLIT',
    );
    expect(split?.getAttribute('data-active')).toBe('false');
  });

  it('SPLIT button is active when splitActive is true', () => {
    const t = mountComponent({ ...baseProps, splitActive: true });
    const split = Array.from(t.querySelectorAll('.bridge-button')).find(
      (el) => el.textContent?.trim() === 'SPLIT',
    );
    expect(split?.getAttribute('data-active')).toBe('true');
  });
});

describe('TX routing (dual receiver)', () => {
  beforeEach(() => {
    vi.mocked(hasDualReceiver).mockReturnValue(true);
  });

  it('shows TX→A and TX→B when hasDualReceiver is true (ab scheme)', () => {
    const t = mountComponent(baseProps);
    const labels = getButtonLabels(t);
    expect(labels).toContain('TX→A');
    expect(labels).toContain('TX→B');
  });

  it('shows TX→M and TX→S when hasDualReceiver is true (main_sub scheme)', () => {
    vi.mocked(getVfoScheme).mockReturnValue('main_sub');
    const t = mountComponent(baseProps);
    const labels = getButtonLabels(t);
    expect(labels).toContain('TX→M');
    expect(labels).toContain('TX→S');
  });

  it('hides TX badges when hasDualReceiver is false', () => {
    vi.mocked(hasDualReceiver).mockReturnValue(false);
    const t = mountComponent(baseProps);
    const labels = getButtonLabels(t);
    expect(labels).not.toContain('TX→A');
    expect(labels).not.toContain('TX→B');
  });

  it('TX→A button is active when txVfo is main', () => {
    const t = mountComponent({ ...baseProps, txVfo: 'main' });
    const txA = Array.from(t.querySelectorAll('.bridge-button')).find(
      (el) => el.textContent?.trim() === 'TX→A',
    );
    expect(txA?.getAttribute('data-active')).toBe('true');
  });

  it('TX→B button is active when txVfo is sub', () => {
    const t = mountComponent({ ...baseProps, txVfo: 'sub' });
    const txB = Array.from(t.querySelectorAll('.bridge-button')).find(
      (el) => el.textContent?.trim() === 'TX→B',
    );
    expect(txB?.getAttribute('data-active')).toBe('true');
  });
});

describe('callbacks', () => {
  it('calls onSwap when swap button is clicked', () => {
    const onSwap = vi.fn();
    const t = mountComponent({ ...baseProps, onSwap });
    const badge = Array.from(t.querySelectorAll('.bridge-button')).find(
      (el) => el.textContent?.trim() === 'A↔B',
    ) as HTMLElement | undefined;
    badge?.click();
    expect(onSwap).toHaveBeenCalledOnce();
  });

  it('calls onCopy when copy button is clicked', () => {
    const onCopy = vi.fn();
    const t = mountComponent({ ...baseProps, onCopy });
    const badge = Array.from(t.querySelectorAll('.bridge-button')).find(
      (el) => el.textContent?.trim() === 'A→B',
    ) as HTMLElement | undefined;
    badge?.click();
    expect(onCopy).toHaveBeenCalledOnce();
  });

  it('calls onEqual when equal button is clicked', () => {
    const onEqual = vi.fn();
    const t = mountComponent({ ...baseProps, onEqual });
    const badge = Array.from(t.querySelectorAll('.bridge-button')).find(
      (el) => el.textContent?.trim() === 'A=B',
    ) as HTMLElement | undefined;
    badge?.click();
    expect(onEqual).toHaveBeenCalledOnce();
  });

  it('calls onSplitToggle when SPLIT button is clicked', () => {
    const onSplitToggle = vi.fn();
    const t = mountComponent({ ...baseProps, onSplitToggle });
    const badge = Array.from(t.querySelectorAll('.bridge-button')).find(
      (el) => el.textContent?.trim() === 'SPLIT',
    ) as HTMLElement | undefined;
    badge?.click();
    expect(onSplitToggle).toHaveBeenCalledOnce();
  });

  it('calls onTxVfoChange("sub") when TX→B is clicked', () => {
    vi.mocked(hasDualReceiver).mockReturnValue(true);
    const onTxVfoChange = vi.fn();
    const t = mountComponent({ ...baseProps, onTxVfoChange });
    const badge = Array.from(t.querySelectorAll('.bridge-button')).find(
      (el) => el.textContent?.trim() === 'TX→B',
    ) as HTMLElement | undefined;
    badge?.click();
    expect(onTxVfoChange).toHaveBeenCalledWith('sub');
  });

  it('calls onTxVfoChange("main") when TX→A is clicked', () => {
    vi.mocked(hasDualReceiver).mockReturnValue(true);
    const onTxVfoChange = vi.fn();
    const t = mountComponent({ ...baseProps, txVfo: 'sub', onTxVfoChange });
    const badge = Array.from(t.querySelectorAll('.bridge-button')).find(
      (el) => el.textContent?.trim() === 'TX→A',
    ) as HTMLElement | undefined;
    badge?.click();
    expect(onTxVfoChange).toHaveBeenCalledWith('main');
  });
});
