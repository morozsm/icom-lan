import { describe, it, expect, vi, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import ControlButton from '../ControlButton.svelte';
import FillButton from '../FillButton.svelte';
import DotButton from '../DotButton.svelte';
import HardwareButton from '../HardwareButton.svelte';
import HardwarePlainButton from '../HardwarePlainButton.svelte';
import ControlledHarness from './ControlledHarness.svelte';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mounted: ReturnType<typeof mount>[] = [];

function mountButton<T extends object>(
  Component: Parameters<typeof mount>[0],
  props: T,
): { target: HTMLElement; el: HTMLButtonElement; component: ReturnType<typeof mount> } {
  const target = document.createElement('div');
  document.body.appendChild(target);
  const component = mount(Component, { target, props });
  flushSync();
  // Get the last button (harness renders two: the parent-toggle + the tested button)
  const buttons = target.querySelectorAll('button');
  const el = buttons[buttons.length - 1] as HTMLButtonElement;
  mounted.push(component);
  return { target, el, component };
}

afterEach(() => {
  while (mounted.length) unmount(mounted.pop()!);
  document.body.innerHTML = '';
});

// Mount a controlled harness and return handles to the tested button and parent toggle
function mountHarness(family: string, initial: boolean) {
  const target = document.createElement('div');
  document.body.appendChild(target);
  const component = mount(ControlledHarness, { target, props: { family, initial } });
  flushSync();
  mounted.push(component);
  const parentToggle = target.querySelector('[data-testid="parent-toggle"]') as HTMLButtonElement;
  const buttons = target.querySelectorAll('button');
  const testedButton = buttons[buttons.length - 1] as HTMLButtonElement;
  return { parentToggle, testedButton };
}

// ---------------------------------------------------------------------------
// ControlButton — base primitive
// ---------------------------------------------------------------------------

describe('ControlButton', () => {
  it('reflects initial active=false', () => {
    const { el } = mountButton(ControlButton, { active: false });
    expect(el.dataset.active).toBe('false');
  });

  it('reflects initial active=true', () => {
    const { el } = mountButton(ControlButton, { active: true });
    expect(el.dataset.active).toBe('true');
  });

  it('self-toggles on click (uncontrolled)', () => {
    const { el } = mountButton(ControlButton, { active: false });
    el.click();
    flushSync();
    expect(el.dataset.active).toBe('true');
  });

  it('calls onclick handler on click', () => {
    const onclick = vi.fn();
    const { el } = mountButton(ControlButton, { active: false, onclick });
    el.click();
    expect(onclick).toHaveBeenCalledOnce();
  });

  it('does not toggle or call onclick when disabled', () => {
    const onclick = vi.fn();
    const { el } = mountButton(ControlButton, { active: false, disabled: true, onclick });
    el.click();
    flushSync();
    expect(el.dataset.active).toBe('false');
    expect(onclick).not.toHaveBeenCalled();
  });

  it('syncs active state when parent-owned state changes', () => {
    const { parentToggle, testedButton } = mountHarness('control', false);
    expect(testedButton.dataset.active).toBe('false');
    parentToggle.click();
    flushSync();
    expect(testedButton.dataset.active).toBe('true');
  });

  it('syncs back to false when parent toggles again', () => {
    const { parentToggle, testedButton } = mountHarness('control', true);
    expect(testedButton.dataset.active).toBe('true');
    parentToggle.click();
    flushSync();
    expect(testedButton.dataset.active).toBe('false');
  });
});

// ---------------------------------------------------------------------------
// Wrapper controlled-state tests
// ---------------------------------------------------------------------------

function makeControlledWrapperTests(
  name: string,
  family: string,
  Component: Parameters<typeof mount>[0],
) {
  describe(`${name} — controlled state`, () => {
    it('passes active=false through to button', () => {
      const { el } = mountButton(Component, { active: false });
      expect(el.dataset.active).toBe('false');
    });

    it('passes active=true through to button', () => {
      const { el } = mountButton(Component, { active: true });
      expect(el.dataset.active).toBe('true');
    });

    it('syncs when parent-owned state changes to true', () => {
      const { parentToggle, testedButton } = mountHarness(family, false);
      expect(testedButton.dataset.active).toBe('false');
      parentToggle.click();
      flushSync();
      expect(testedButton.dataset.active).toBe('true');
    });

    it('syncs when parent-owned state changes back to false', () => {
      const { parentToggle, testedButton } = mountHarness(family, true);
      expect(testedButton.dataset.active).toBe('true');
      parentToggle.click();
      flushSync();
      expect(testedButton.dataset.active).toBe('false');
    });

    it('calls onclick when clicked', () => {
      const onclick = vi.fn();
      const { el } = mountButton(Component, { active: false, onclick });
      el.click();
      expect(onclick).toHaveBeenCalledOnce();
    });
  });
}

makeControlledWrapperTests('FillButton', 'fill', FillButton);
makeControlledWrapperTests('DotButton', 'dot', DotButton);
makeControlledWrapperTests('HardwareButton', 'hardware', HardwareButton);
makeControlledWrapperTests('HardwarePlainButton', 'hardware-plain', HardwarePlainButton);
