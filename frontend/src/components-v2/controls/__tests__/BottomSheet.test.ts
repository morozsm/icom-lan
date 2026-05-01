import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync, type Snippet } from 'svelte';
import BottomSheet from '../BottomSheet.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountSheet(props: {
  open: boolean;
  title: string;
  compact?: boolean;
  contentStyle?: string;
  onclose?: () => void;
}) {
  const target = document.createElement('div');
  document.body.appendChild(target);
  const component = mount(BottomSheet, {
    target,
    props: {
      ...props,
      children: ((anchor: any) => {
        const div = document.createElement('div');
        div.className = 'test-child';
        div.textContent = 'Sheet content';
        anchor.before(div);
        return {
          update: () => {},
          destroy: () => div.remove(),
        };
      }) as unknown as Snippet,
    },
  });
  flushSync();
  components.push(component);
  return target;
}

beforeEach(() => {
  components = [];
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

describe('BottomSheet', () => {
  it('renders when open=true', () => {
    const target = mountSheet({ open: true, title: 'TEST' });
    const backdrop = target.querySelector('[role="dialog"]');
    expect(backdrop).toBeTruthy();
    const title = target.querySelector('.m-sheet-title');
    expect(title?.textContent).toBe('TEST');
  });

  it('does not render when open=false', () => {
    const target = mountSheet({ open: false, title: 'TEST' });
    const backdrop = target.querySelector('[role="dialog"]');
    expect(backdrop).toBeNull();
  });

  it('renders children content', () => {
    const target = mountSheet({ open: true, title: 'TEST' });
    const child = target.querySelector('.test-child');
    expect(child?.textContent).toBe('Sheet content');
  });

  it('has aria-modal attribute', () => {
    const target = mountSheet({ open: true, title: 'TEST' });
    const dialog = target.querySelector('[role="dialog"]');
    expect(dialog?.getAttribute('aria-modal')).toBe('true');
  });

  it('has aria-label matching title', () => {
    const target = mountSheet({ open: true, title: 'SETTINGS' });
    const dialog = target.querySelector('[role="dialog"]');
    expect(dialog?.getAttribute('aria-label')).toBe('SETTINGS');
  });

  it('applies compact class when compact=true', () => {
    const target = mountSheet({ open: true, title: 'TEST', compact: true });
    const sheet = target.querySelector('.m-sheet');
    expect(sheet?.classList.contains('m-sheet--compact')).toBe(true);
  });

  it('does not apply compact class when compact=false', () => {
    const target = mountSheet({ open: true, title: 'TEST', compact: false });
    const sheet = target.querySelector('.m-sheet');
    expect(sheet?.classList.contains('m-sheet--compact')).toBe(false);
  });

  it('applies contentStyle to content div', () => {
    const target = mountSheet({
      open: true,
      title: 'TEST',
      contentStyle: 'padding: 12px;',
    });
    const content = target.querySelector('.m-sheet-content') as HTMLElement;
    expect(content?.style.padding).toBe('12px');
  });

  it('renders the handle element', () => {
    const target = mountSheet({ open: true, title: 'TEST' });
    const handle = target.querySelector('.m-sheet-handle');
    expect(handle).toBeTruthy();
  });
});

describe('swipe-to-dismiss threshold logic', () => {
  // Unit test the math used in the component's dismiss decision
  const DISMISS_THRESHOLD = 0.3;
  const VELOCITY_THRESHOLD = 0.5; // px/ms

  function shouldDismiss(
    dragDistance: number,
    sheetHeight: number,
    elapsedMs: number,
  ): boolean {
    const ratio = dragDistance / sheetHeight;
    const velocity = elapsedMs > 0 ? dragDistance / elapsedMs : 0;
    return ratio > DISMISS_THRESHOLD || velocity > VELOCITY_THRESHOLD;
  }

  it('dismisses when dragged past 30% of sheet height', () => {
    expect(shouldDismiss(160, 500, 1000)).toBe(true); // 32%
  });

  it('does not dismiss when dragged less than 30%', () => {
    expect(shouldDismiss(100, 500, 1000)).toBe(false); // 20%
  });

  it('dismisses on fast swipe even with small distance', () => {
    // 50px in 80ms = 0.625 px/ms > 0.5
    expect(shouldDismiss(50, 500, 80)).toBe(true);
  });

  it('does not dismiss on slow small drag', () => {
    // 50px in 500ms = 0.1 px/ms, ratio = 10%
    expect(shouldDismiss(50, 500, 500)).toBe(false);
  });

  it('dismisses at exact threshold boundary (ratio)', () => {
    // 151/500 = 0.302 > 0.3
    expect(shouldDismiss(151, 500, 2000)).toBe(true);
  });

  it('does not dismiss at just below threshold', () => {
    // 149/500 = 0.298, velocity = 0.0745
    expect(shouldDismiss(149, 500, 2000)).toBe(false);
  });

  it('dismisses at exact velocity boundary', () => {
    // 51px in 100ms = 0.51 px/ms > 0.5
    expect(shouldDismiss(51, 1000, 100)).toBe(true);
  });
});
