import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import FilterPanel from '../FilterPanel.svelte';
import { formatFilterWidth } from '../filter-utils';

// ---------------------------------------------------------------------------
// formatFilterWidth
// ---------------------------------------------------------------------------

describe('formatFilterWidth', () => {
  it('returns raw number string for values below 1000', () => {
    expect(formatFilterWidth(500)).toBe('500');
  });

  it('returns raw number string for minimum value 50', () => {
    expect(formatFilterWidth(50)).toBe('50');
  });

  it('returns raw number string for 999', () => {
    expect(formatFilterWidth(999)).toBe('999');
  });

  it('returns "1k" for exactly 1000 Hz', () => {
    expect(formatFilterWidth(1000)).toBe('1k');
  });

  it('returns "1.2k" for 1200 Hz', () => {
    expect(formatFilterWidth(1200)).toBe('1.2k');
  });

  it('returns "2.4k" for 2400 Hz', () => {
    expect(formatFilterWidth(2400)).toBe('2.4k');
  });

  it('returns "3k" for 3000 Hz', () => {
    expect(formatFilterWidth(3000)).toBe('3k');
  });

  it('returns "3.6k" for 3600 Hz', () => {
    expect(formatFilterWidth(3600)).toBe('3.6k');
  });
});

// ---------------------------------------------------------------------------
// FilterPanel component
// ---------------------------------------------------------------------------

let components: ReturnType<typeof mount>[] = [];

function mountPanel(props: Record<string, unknown>) {
  const t = document.createElement('div');
  document.body.appendChild(t);
  const component = mount(FilterPanel, { target: t, props });
  flushSync();
  components.push(component);
  return t;
}

beforeEach(() => {
  components = [];
});

afterEach(() => {
  components.forEach(c => unmount(c));
  document.body.innerHTML = '';
});

const baseProps = {
  filterWidth: 2400,
  ifShift: 0,
  onFilterWidthChange: vi.fn(),
  onIfShiftChange: vi.fn(),
};

describe('panel structure', () => {
  it('renders the FILTER header label', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.panel-header')?.textContent).toBe('FILTER');
  });

  it('renders the Width slider', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.slider-label'));
    expect(labels.some(el => el.textContent === 'Width')).toBe(true);
  });

  it('renders the IF Shift slider', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.slider-label'));
    expect(labels.some(el => el.textContent === 'IF Shift')).toBe(true);
  });

  it('Width slider has min=50, max=3600, step=50', () => {
    const t = mountPanel(baseProps);
    const inputs = t.querySelectorAll<HTMLInputElement>('input[type="range"]');
    const widthInput = inputs[0];
    expect(widthInput.min).toBe('50');
    expect(widthInput.max).toBe('3600');
    expect(widthInput.step).toBe('50');
  });

  it('IF Shift slider has min=-1200, max=1200, step=25', () => {
    const t = mountPanel(baseProps);
    const inputs = t.querySelectorAll<HTMLInputElement>('input[type="range"]');
    const ifShiftInput = inputs[1];
    expect(ifShiftInput.min).toBe('-1200');
    expect(ifShiftInput.max).toBe('1200');
    expect(ifShiftInput.step).toBe('25');
  });
});

describe('PBT sliders visibility', () => {
  it('does not render PBT sliders when hasPbt is false (default)', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.slider-label')).map(el => el.textContent);
    expect(labels).not.toContain('PBT Inner');
    expect(labels).not.toContain('PBT Outer');
  });

  it('does not render PBT sliders when hasPbt=false explicitly', () => {
    const t = mountPanel({ ...baseProps, hasPbt: false });
    const labels = Array.from(t.querySelectorAll('.slider-label')).map(el => el.textContent);
    expect(labels).not.toContain('PBT Inner');
    expect(labels).not.toContain('PBT Outer');
  });

  it('renders PBT Inner slider when hasPbt=true', () => {
    const t = mountPanel({ ...baseProps, hasPbt: true, pbtInner: 100, pbtOuter: -50 });
    const labels = Array.from(t.querySelectorAll('.slider-label')).map(el => el.textContent);
    expect(labels).toContain('PBT Inner');
  });

  it('renders PBT Outer slider when hasPbt=true', () => {
    const t = mountPanel({ ...baseProps, hasPbt: true, pbtInner: 100, pbtOuter: -50 });
    const labels = Array.from(t.querySelectorAll('.slider-label')).map(el => el.textContent);
    expect(labels).toContain('PBT Outer');
  });

  it('renders 4 sliders total when hasPbt=true', () => {
    const t = mountPanel({ ...baseProps, hasPbt: true, pbtInner: 0, pbtOuter: 0 });
    expect(t.querySelectorAll('input[type="range"]').length).toBe(4);
  });

  it('renders 2 sliders total when hasPbt=false', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelectorAll('input[type="range"]').length).toBe(2);
  });
});

describe('callbacks', () => {
  it('calls onFilterWidthChange when Width slider changes', () => {
    const onFilterWidthChange = vi.fn();
    const t = mountPanel({ ...baseProps, onFilterWidthChange });
    const input = t.querySelectorAll<HTMLInputElement>('input[type="range"]')[0];
    input.value = '1800';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    expect(onFilterWidthChange).toHaveBeenCalledWith(1800);
  });

  it('calls onIfShiftChange when IF Shift slider changes', () => {
    const onIfShiftChange = vi.fn();
    const t = mountPanel({ ...baseProps, onIfShiftChange });
    const input = t.querySelectorAll<HTMLInputElement>('input[type="range"]')[1];
    input.value = '-300';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    expect(onIfShiftChange).toHaveBeenCalledWith(-300);
  });

  it('calls onPbtInnerChange when PBT Inner slider changes', () => {
    const onPbtInnerChange = vi.fn();
    const t = mountPanel({ ...baseProps, hasPbt: true, pbtInner: 0, pbtOuter: 0, onPbtInnerChange });
    const inputs = t.querySelectorAll<HTMLInputElement>('input[type="range"]');
    inputs[2].value = '200';
    inputs[2].dispatchEvent(new Event('input', { bubbles: true }));
    expect(onPbtInnerChange).toHaveBeenCalledWith(200);
  });

  it('calls onPbtOuterChange when PBT Outer slider changes', () => {
    const onPbtOuterChange = vi.fn();
    const t = mountPanel({ ...baseProps, hasPbt: true, pbtInner: 0, pbtOuter: 0, onPbtOuterChange });
    const inputs = t.querySelectorAll<HTMLInputElement>('input[type="range"]');
    inputs[3].value = '-100';
    inputs[3].dispatchEvent(new Event('input', { bubbles: true }));
    expect(onPbtOuterChange).toHaveBeenCalledWith(-100);
  });
});
