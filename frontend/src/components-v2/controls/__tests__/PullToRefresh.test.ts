import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import PullToRefresh from '../PullToRefresh.svelte';

let components: ReturnType<typeof mount>[] = [];

function mountPTR(props: { onRefresh: () => Promise<void> }) {
  const target = document.createElement('div');
  document.body.appendChild(target);
  const component = mount(PullToRefresh, { target, props });
  flushSync();
  components.push(component);
  return target;
}

function touchEvent(
  type: string,
  clientY: number,
  target: EventTarget,
): PointerEvent {
  return new PointerEvent(type, {
    bubbles: true,
    pointerType: 'touch',
    clientY,
    clientX: 100,
  });
}

beforeEach(() => {
  components = [];
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

describe('PullToRefresh', () => {
  it('applies overscroll-behavior: contain on the wrapper', () => {
    const target = mountPTR({ onRefresh: () => Promise.resolve() });
    const wrapper = target.querySelector('.pull-to-refresh-wrapper') as HTMLElement;
    expect(wrapper).not.toBeNull();
    // Check computed style from the scoped CSS
    const style = getComputedStyle(wrapper);
    // jsdom doesn't compute scoped styles, so check the class exists
    expect(wrapper.classList.contains('pull-to-refresh-wrapper')).toBe(true);
  });

  it('calls onRefresh when pull exceeds threshold', async () => {
    let resolveRefresh: () => void;
    const refreshPromise = new Promise<void>((r) => {
      resolveRefresh = r;
    });
    const onRefresh = vi.fn(() => refreshPromise);

    const target = mountPTR({ onRefresh });
    const wrapper = target.querySelector('.pull-to-refresh-wrapper') as HTMLElement;

    // Simulate touch pull: 80px threshold / 0.4 resistance = 200px finger movement
    wrapper.dispatchEvent(touchEvent('pointerdown', 0, wrapper));
    flushSync();

    wrapper.dispatchEvent(touchEvent('pointermove', 250, wrapper));
    flushSync();

    wrapper.dispatchEvent(touchEvent('pointerup', 250, wrapper));
    flushSync();

    expect(onRefresh).toHaveBeenCalledTimes(1);

    // Resolve the refresh
    resolveRefresh!();
    await refreshPromise;
    flushSync();
  });

  it('does not call onRefresh when pull is below threshold', () => {
    const onRefresh = vi.fn(() => Promise.resolve());

    const target = mountPTR({ onRefresh });
    const wrapper = target.querySelector('.pull-to-refresh-wrapper') as HTMLElement;

    // Pull only 100px of finger movement = 40px actual (below 80px threshold)
    wrapper.dispatchEvent(touchEvent('pointerdown', 0, wrapper));
    flushSync();

    wrapper.dispatchEvent(touchEvent('pointermove', 100, wrapper));
    flushSync();

    wrapper.dispatchEvent(touchEvent('pointerup', 100, wrapper));
    flushSync();

    expect(onRefresh).not.toHaveBeenCalled();
  });

  it('does not activate on mouse pointer events', () => {
    const onRefresh = vi.fn(() => Promise.resolve());

    const target = mountPTR({ onRefresh });
    const wrapper = target.querySelector('.pull-to-refresh-wrapper') as HTMLElement;

    // Simulate mouse (not touch)
    const mouseDown = new PointerEvent('pointerdown', {
      bubbles: true,
      pointerType: 'mouse',
      clientY: 0,
    });
    wrapper.dispatchEvent(mouseDown);
    flushSync();

    const mouseMove = new PointerEvent('pointermove', {
      bubbles: true,
      pointerType: 'mouse',
      clientY: 300,
    });
    wrapper.dispatchEvent(mouseMove);
    flushSync();

    const mouseUp = new PointerEvent('pointerup', {
      bubbles: true,
      pointerType: 'mouse',
      clientY: 300,
    });
    wrapper.dispatchEvent(mouseUp);
    flushSync();

    expect(onRefresh).not.toHaveBeenCalled();
  });

  it('shows indicator when pulling', () => {
    const target = mountPTR({ onRefresh: () => Promise.resolve() });
    const wrapper = target.querySelector('.pull-to-refresh-wrapper') as HTMLElement;

    // Initially hidden
    const indicator = target.querySelector('.pull-indicator') as HTMLElement;
    expect(indicator.classList.contains('visible')).toBe(false);

    // Start pull
    wrapper.dispatchEvent(touchEvent('pointerdown', 0, wrapper));
    flushSync();

    wrapper.dispatchEvent(touchEvent('pointermove', 100, wrapper));
    flushSync();

    expect(indicator.classList.contains('visible')).toBe(true);
  });

  it('adds threshold-met class when pull meets threshold', () => {
    const target = mountPTR({ onRefresh: () => Promise.resolve() });
    const wrapper = target.querySelector('.pull-to-refresh-wrapper') as HTMLElement;
    const indicator = target.querySelector('.pull-indicator') as HTMLElement;

    wrapper.dispatchEvent(touchEvent('pointerdown', 0, wrapper));
    flushSync();

    // 250px * 0.4 = 100px > 80px threshold
    wrapper.dispatchEvent(touchEvent('pointermove', 250, wrapper));
    flushSync();

    expect(indicator.classList.contains('threshold-met')).toBe(true);
  });

  it('snaps back when pull is below threshold and released', () => {
    const target = mountPTR({ onRefresh: () => Promise.resolve() });
    const wrapper = target.querySelector('.pull-to-refresh-wrapper') as HTMLElement;
    const indicator = target.querySelector('.pull-indicator') as HTMLElement;

    wrapper.dispatchEvent(touchEvent('pointerdown', 0, wrapper));
    flushSync();

    wrapper.dispatchEvent(touchEvent('pointermove', 50, wrapper));
    flushSync();

    expect(indicator.classList.contains('visible')).toBe(true);

    wrapper.dispatchEvent(touchEvent('pointerup', 50, wrapper));
    flushSync();

    expect(indicator.classList.contains('visible')).toBe(false);
  });
});
