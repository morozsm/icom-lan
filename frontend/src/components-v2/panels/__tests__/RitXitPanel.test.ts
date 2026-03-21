import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import type { ComponentProps } from 'svelte';
import RitXitPanel from '../RitXitPanel.svelte';
import { formatOffset, shouldShowPanel } from '../rit-utils';

let components: ReturnType<typeof mount>[] = [];

function mountPanel(props: ComponentProps<typeof RitXitPanel>) {
  const target = document.createElement('div');
  document.body.appendChild(target);
  const component = mount(RitXitPanel, { target, props });
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

const baseProps: ComponentProps<typeof RitXitPanel> = {
  ritActive: false,
  ritOffset: 0,
  xitActive: false,
  xitOffset: 0,
  hasRit: true,
  hasXit: true,
  onRitToggle: vi.fn(),
  onXitToggle: vi.fn(),
  onRitOffsetChange: vi.fn(),
  onXitOffsetChange: vi.fn(),
  onClear: vi.fn(),
};

// ---------------------------------------------------------------------------
// formatOffset
// ---------------------------------------------------------------------------

describe('formatOffset', () => {
  
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

it('returns "±0 Hz" for zero', () => {
    expect(formatOffset(0)).toBe('±0 Hz');
  });

  it('returns "+120 Hz" for positive 120', () => {
    expect(formatOffset(120)).toBe('+120 Hz');
  });

  it('returns "+1 Hz" for positive 1', () => {
    expect(formatOffset(1)).toBe('+1 Hz');
  });

  it('returns Unicode minus for negative values', () => {
    expect(formatOffset(-50)).toBe('\u221250 Hz');
  });

  it('returns "−50 Hz" for -50 (Unicode minus sign)', () => {
    expect(formatOffset(-50)).toBe('−50 Hz');
  });

  it('returns "−1 Hz" for -1', () => {
    expect(formatOffset(-1)).toBe('−1 Hz');
  });

  it('handles large positive offset', () => {
    expect(formatOffset(9999)).toBe('+9999 Hz');
  });

  it('handles large negative offset', () => {
    expect(formatOffset(-9999)).toBe('−9999 Hz');
  });

  it('positive sign is ASCII + not Unicode', () => {
    expect(formatOffset(100)[0]).toBe('+');
  });

  it('negative sign is Unicode minus U+2212 not ASCII hyphen', () => {
    expect(formatOffset(-100).charCodeAt(0)).toBe(0x2212);
  });
});

// ---------------------------------------------------------------------------
// shouldShowPanel
// ---------------------------------------------------------------------------

describe('shouldShowPanel', () => {
  it('returns true when both hasRit and hasXit are true', () => {
    expect(shouldShowPanel(true, true)).toBe(true);
  });

  it('returns true when only hasRit is true', () => {
    expect(shouldShowPanel(true, false)).toBe(true);
  });

  it('returns true when only hasXit is true', () => {
    expect(shouldShowPanel(false, true)).toBe(true);
  });

  it('returns false when both hasRit and hasXit are false', () => {
    expect(shouldShowPanel(false, false)).toBe(false);
  });
});

describe('CLEAR button', () => {
  it('renders a CLEAR action button', () => {
    const target = mountPanel(baseProps);
    const btn = target.querySelector<HTMLButtonElement>('.clear-button');
    expect(btn).not.toBeNull();
    expect(btn?.textContent?.trim()).toBe('CLEAR');
  });

  it('CLEAR button is never data-active (action-button, not a toggle)', () => {
    const target = mountPanel(baseProps);
    const btn = target.querySelector<HTMLButtonElement>('.clear-button');
    expect(btn?.dataset.active).toBeUndefined();
  });

  it('calls onClear when CLEAR button is clicked', () => {
    const onClear = vi.fn();
    const target = mountPanel({ ...baseProps, onClear });
    const btn = target.querySelector<HTMLButtonElement>('.clear-button');
    btn?.click();
    flushSync();
    expect(onClear).toHaveBeenCalledOnce();
  });
});

describe('RitXitPanel component', () => {

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the Offset slider when visible', () => {
    const target = mountPanel(baseProps);
    const labels = Array.from(target.querySelectorAll('.vc-label')).map((el) => el.textContent);
    expect(labels).toContain('Offset');
  });

  it('uses the shared offset constraints', () => {
    const target = mountPanel(baseProps);
    const slider = target.querySelector<HTMLElement>('[role="slider"]');
    expect(slider?.getAttribute('aria-valuemin')).toBe('-9999');
    expect(slider?.getAttribute('aria-valuemax')).toBe('9999');
  });

  it('calls onRitOffsetChange when the offset slider changes by default', () => {
    const onRitOffsetChange = vi.fn();
    const target = mountPanel({ ...baseProps, onRitOffsetChange });
    const slider = target.querySelector<HTMLElement>('[role="slider"]');
    slider!.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    vi.advanceTimersByTime(60);

    expect(onRitOffsetChange).toHaveBeenCalled();
  });

  it('calls onXitOffsetChange when only XIT is active', () => {
    const onXitOffsetChange = vi.fn();
    const target = mountPanel({
      ...baseProps,
      xitActive: true,
      onXitOffsetChange,
    });
    const slider = target.querySelector<HTMLElement>('[role="slider"]');
    slider!.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    vi.advanceTimersByTime(60);

    expect(onXitOffsetChange).toHaveBeenCalled();
  });
});
