import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import type { ComponentProps } from 'svelte';
import FilterPanel from '../FilterPanel.svelte';
import { formatFilterWidth } from '../filter-utils';
import { deriveIfShift } from '../filter-controls';

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

function mountPanel(props: ComponentProps<typeof FilterPanel>) {
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

const baseProps: ComponentProps<typeof FilterPanel> = {
  currentMode: 'USB',
  currentFilter: 2,
  filterShape: 0,
  filterLabels: ['FIL1', 'FIL2', 'FIL3'],
  filterWidth: 2400,
  filterConfig: {
    defaults: [3000, 2400, 1800],
    fixed: false,
    minHz: 50,
    maxHz: 3600,
    stepHz: 50,
  },
  ifShift: 0,
  onFilterChange: vi.fn(),
  onFilterWidthChange: vi.fn(),
  onFilterShapeChange: vi.fn(),
  onFilterPresetChange: vi.fn(),
  onFilterDefaults: vi.fn(),
  onIfShiftChange: vi.fn(),
};

describe('panel structure', () => {
  it('renders the FILTER header label', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.panel-header')?.textContent).toBe('FILTER');
  });

  it('renders filter selector buttons', () => {
    const t = mountPanel(baseProps);
    const buttons = Array.from(t.querySelectorAll('button')).map((button) => button.textContent?.trim());
    expect(buttons).toContain('FIL1');
    expect(buttons).toContain('FIL2');
    expect(buttons).toContain('FIL3');
  });

  it('renders a read-only BW display instead of a Width slider', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.bw-label')?.textContent).toBe('BW');
    expect(t.querySelector('.bw-value')?.textContent).toBe('2.4kHz');
    const labels = Array.from(t.querySelectorAll('.slider-label')).map((el) => el.textContent);
    expect(labels).not.toContain('Width');
  });

  it('renders the IF Shift slider', () => {
    const t = mountPanel(baseProps);
    const labels = Array.from(t.querySelectorAll('.slider-label'));
    expect(labels.some(el => el.textContent === 'IF Shift')).toBe(true);
  });

  it('renders the settings gear button', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelector('.settings-button')?.textContent?.trim()).toBe('⚙');
  });

  it('IF Shift slider has min=-1200, max=1200, step=25', () => {
    const t = mountPanel(baseProps);
    const inputs = t.querySelectorAll<HTMLInputElement>('input[type="range"]');
    const ifShiftInput = inputs[0];
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

  it('renders Reset PBT button when hasPbt=true', () => {
    const t = mountPanel({ ...baseProps, hasPbt: true, pbtInner: 100, pbtOuter: -50, onPbtReset: vi.fn() });
    const buttons = Array.from(t.querySelectorAll('button')).map(el => el.textContent?.trim());
    expect(buttons).toContain('Reset');
  });

  it('renders 3 sliders total when hasPbt=true', () => {
    const t = mountPanel({ ...baseProps, hasPbt: true, pbtInner: 0, pbtOuter: 0 });
    expect(t.querySelectorAll('input[type="range"]').length).toBe(3);
  });

  it('renders 1 slider total when hasPbt=false', () => {
    const t = mountPanel(baseProps);
    expect(t.querySelectorAll('input[type="range"]').length).toBe(1);
  });
});

describe('callbacks', () => {
  it('calls onFilterChange when a filter button is clicked', () => {
    const onFilterChange = vi.fn();
    const t = mountPanel({ ...baseProps, onFilterChange });
    const button = Array.from(t.querySelectorAll('button')).find(el => el.textContent?.trim() === 'FIL3') as HTMLButtonElement;
    button.click();
    expect(onFilterChange).toHaveBeenCalledWith(3);
  });

  it('calls onIfShiftChange when IF Shift slider changes', () => {
    const onIfShiftChange = vi.fn();
    const t = mountPanel({ ...baseProps, onIfShiftChange });
    const input = t.querySelectorAll<HTMLInputElement>('input[type="range"]')[0];
    input.value = '-300';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    expect(onIfShiftChange).toHaveBeenCalledWith(-300);
  });

  it('calls onPbtInnerChange when PBT Inner slider changes', () => {
    const onPbtInnerChange = vi.fn();
    const t = mountPanel({ ...baseProps, hasPbt: true, pbtInner: 0, pbtOuter: 0, onPbtInnerChange });
    const inputs = t.querySelectorAll<HTMLInputElement>('input[type="range"]');
    inputs[1].value = '200';
    inputs[1].dispatchEvent(new Event('input', { bubbles: true }));
    expect(onPbtInnerChange).toHaveBeenCalledWith(200);
  });

  it('calls onPbtOuterChange when PBT Outer slider changes', () => {
    const onPbtOuterChange = vi.fn();
    const t = mountPanel({ ...baseProps, hasPbt: true, pbtInner: 0, pbtOuter: 0, onPbtOuterChange });
    const inputs = t.querySelectorAll<HTMLInputElement>('input[type="range"]');
    inputs[2].value = '-100';
    inputs[2].dispatchEvent(new Event('input', { bubbles: true }));
    expect(onPbtOuterChange).toHaveBeenCalledWith(-100);
  });

  it('calls onPbtReset when the reset button is clicked', () => {
    const onPbtReset = vi.fn();
    const t = mountPanel({ ...baseProps, hasPbt: true, pbtInner: 100, pbtOuter: -100, onPbtReset });
    const button = Array.from(t.querySelectorAll('button')).find(el => el.textContent?.trim() === 'Reset') as HTMLButtonElement;
    button.click();
    expect(onPbtReset).toHaveBeenCalledOnce();
  });

  it('opens the settings modal and calls onFilterPresetChange from a modal slider', () => {
    const onFilterPresetChange = vi.fn();
    const t = mountPanel({ ...baseProps, onFilterPresetChange });
    const gear = t.querySelector('.settings-button') as HTMLButtonElement;
    gear.click();
    flushSync();

    const modal = document.querySelector('.filter-modal');
    expect(modal).not.toBeNull();

    const inputs = modal?.querySelectorAll<HTMLInputElement>('input[type="range"]') ?? [];
    inputs[0].value = '3200';
    inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
    expect(onFilterPresetChange).toHaveBeenCalledWith(1, 3200);
  });

  it('calls onFilterDefaults when restore defaults is clicked in the modal', () => {
    const onFilterDefaults = vi.fn();
    const t = mountPanel({ ...baseProps, onFilterDefaults });
    const gear = t.querySelector('.settings-button') as HTMLButtonElement;
    gear.click();
    flushSync();

    const button = Array.from(document.querySelectorAll('button')).find(el => el.textContent?.trim() === 'Restore Defaults') as HTMLButtonElement;
    button.click();
    expect(onFilterDefaults).toHaveBeenCalledWith([3000, 2400, 1800]);
  });

  it('shows SHARP and SOFT shape buttons in the modal', () => {
    const t = mountPanel(baseProps);
    const gear = t.querySelector('.settings-button') as HTMLButtonElement;
    gear.click();
    flushSync();

    const buttons = Array.from(document.querySelectorAll('button')).map((el) => el.textContent?.trim());
    expect(buttons).toContain('SHARP');
    expect(buttons).toContain('SOFT');
  });

  it('calls onFilterShapeChange when the SOFT button is clicked in the modal', () => {
    const onFilterShapeChange = vi.fn();
    const t = mountPanel({ ...baseProps, onFilterShapeChange });
    const gear = t.querySelector('.settings-button') as HTMLButtonElement;
    gear.click();
    flushSync();

    const button = Array.from(document.querySelectorAll('button')).find((el) => el.textContent?.trim() === 'SOFT') as HTMLButtonElement;
    button.click();
    expect(onFilterShapeChange).toHaveBeenCalledWith(1);
  });
});

describe('IF Shift semantics', () => {
  it('can be derived from current PBT offsets', () => {
    expect(deriveIfShift(-150, 50)).toBe(-50);
  });
});
