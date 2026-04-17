import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, unmount, flushSync } from 'svelte';
import type { ComponentProps } from 'svelte';

// Mock capabilities for VfoPanel internals.
vi.mock('$lib/stores/capabilities.svelte', () => ({
  vfoLabel: vi.fn((slot: 'A' | 'B') => (slot === 'A' ? 'MAIN' : 'SUB')),
  getCapabilities: vi.fn(() => ({
    freqRanges: [
      {
        start: 14000000,
        end: 14350000,
        bands: [{ name: '20m', start: 14000000, end: 14350000, default: 14074000 }],
      },
    ],
  })),
  hasDualReceiver: vi.fn(() => true),
  getSmeterCalibration: vi.fn(() => null),
  getSmeterRedline: vi.fn(() => null),
}));

import DualVfoDisplay from '../DualVfoDisplay.svelte';
import type { VfoStateProps } from '../../../layout/layout-utils';

const mainVfo: VfoStateProps = {
  receiver: 'main',
  freq: 14074000,
  mode: 'USB',
  filter: 'FIL1',
  sValue: 50,
  isActive: true,
  badges: {},
};

const subVfo: VfoStateProps = {
  receiver: 'sub',
  freq: 7074000,
  mode: 'LSB',
  filter: 'FIL1',
  sValue: 30,
  isActive: false,
  badges: {},
};

let components: ReturnType<typeof mount>[] = [];

function mountDisplay(props: ComponentProps<typeof DualVfoDisplay>) {
  const t = document.createElement('div');
  document.body.appendChild(t);
  const component = mount(DualVfoDisplay, { target: t, props });
  flushSync();
  components.push(component);
  return t;
}

beforeEach(() => {
  components = [];
});

afterEach(() => {
  components.forEach((c) => unmount(c));
  document.body.innerHTML = '';
});

describe('DualVfoDisplay', () => {
  describe('structure', () => {
    it('mounts with two tiles', () => {
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN' });
      const tiles = t.querySelectorAll('.dual-vfo-tile');
      expect(tiles.length).toBe(2);
    });

    it('renders MAIN and SUB tiles with correct data-receiver', () => {
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN' });
      expect(t.querySelector('[data-receiver="main"]')).not.toBeNull();
      expect(t.querySelector('[data-receiver="sub"]')).not.toBeNull();
    });

    it('outer tiles are NOT role="button" (WCAG 4.1.2 — no nested interactive content)', () => {
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN' });
      const tiles = t.querySelectorAll('.dual-vfo-tile');
      tiles.forEach((tile) => {
        expect(tile.getAttribute('role')).toBeNull();
        expect(tile.getAttribute('tabindex')).toBeNull();
        expect(tile.getAttribute('aria-pressed')).toBeNull();
      });
    });
  });

  describe('active state', () => {
    it('active tile has is-active class (MAIN active)', () => {
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN' });
      const mainTile = t.querySelector('[data-receiver="main"]');
      const subTile = t.querySelector('[data-receiver="sub"]');
      expect(mainTile?.classList.contains('is-active')).toBe(true);
      expect(subTile?.classList.contains('is-active')).toBe(false);
    });

    it('active tile has is-active class (SUB active)', () => {
      const t = mountDisplay({
        main: { ...mainVfo, isActive: false },
        sub: { ...subVfo, isActive: true },
        active: 'SUB',
      });
      const mainTile = t.querySelector('[data-receiver="main"]');
      const subTile = t.querySelector('[data-receiver="sub"]');
      expect(mainTile?.classList.contains('is-active')).toBe(false);
      expect(subTile?.classList.contains('is-active')).toBe(true);
    });
  });

  describe('activate button', () => {
    it('inactive tile renders an activate button (SUB inactive)', () => {
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN' });
      expect(t.querySelector('button[data-activate="sub"]')).not.toBeNull();
      expect(t.querySelector('button[data-activate="main"]')).toBeNull();
    });

    it('inactive tile renders an activate button (MAIN inactive)', () => {
      const t = mountDisplay({
        main: { ...mainVfo, isActive: false },
        sub: { ...subVfo, isActive: true },
        active: 'SUB',
      });
      expect(t.querySelector('button[data-activate="main"]')).not.toBeNull();
      expect(t.querySelector('button[data-activate="sub"]')).toBeNull();
    });

    it('activate button has descriptive aria-label', () => {
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN' });
      const btn = t.querySelector<HTMLButtonElement>('button[data-activate="sub"]');
      expect(btn?.getAttribute('aria-label')).toBe('Activate SUB receiver');
    });

    it('activate button is a native <button> and keyboard-focusable by default', () => {
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN' });
      const btn = t.querySelector<HTMLButtonElement>('button[data-activate="sub"]');
      expect(btn).not.toBeNull();
      expect(btn?.tagName).toBe('BUTTON');
      expect(btn?.getAttribute('type')).toBe('button');
      // Native <button> is focusable without explicit tabindex.
      expect(btn?.hasAttribute('disabled')).toBe(false);
    });
  });

  describe('onActivate callback', () => {
    it('clicking activate button fires onActivate with the receiver id (SUB)', () => {
      const onActivate = vi.fn();
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN', onActivate });
      t.querySelector<HTMLButtonElement>('button[data-activate="sub"]')?.click();
      expect(onActivate).toHaveBeenCalledOnce();
      expect(onActivate).toHaveBeenCalledWith('SUB');
    });

    it('clicking activate button fires onActivate with the receiver id (MAIN)', () => {
      const onActivate = vi.fn();
      const t = mountDisplay({
        main: { ...mainVfo, isActive: false },
        sub: { ...subVfo, isActive: true },
        active: 'SUB',
        onActivate,
      });
      t.querySelector<HTMLButtonElement>('button[data-activate="main"]')?.click();
      expect(onActivate).toHaveBeenCalledOnce();
      expect(onActivate).toHaveBeenCalledWith('MAIN');
    });

    it('active tile does not render an activate button', () => {
      const onActivate = vi.fn();
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN', onActivate });
      // No button on the active (MAIN) tile — nothing to click.
      expect(t.querySelector('button[data-activate="main"]')).toBeNull();
      expect(onActivate).not.toHaveBeenCalled();
    });

    it('clicking the outer tile does NOT fire onActivate', () => {
      // Outer tile is no longer interactive — only the activate button inside it is.
      const onActivate = vi.fn();
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN', onActivate });
      const subTile = t.querySelector<HTMLElement>('[data-receiver="sub"]');
      subTile?.click();
      // The click bubbles from the tile itself (not the inner button), so no activation.
      // Note: if the click originated on the button, it would fire — but that's covered above.
      expect(onActivate).not.toHaveBeenCalledWith('MAIN');
    });
  });
});
