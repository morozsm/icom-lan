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

    it('both tiles are keyboard focusable (tabindex=0)', () => {
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN' });
      const tiles = t.querySelectorAll<HTMLElement>('.dual-vfo-tile');
      tiles.forEach((tile) => {
        expect(tile.getAttribute('tabindex')).toBe('0');
      });
    });

    it('both tiles have role=button', () => {
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN' });
      const tiles = t.querySelectorAll('.dual-vfo-tile');
      tiles.forEach((tile) => {
        expect(tile.getAttribute('role')).toBe('button');
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

    it('aria-pressed reflects active receiver (MAIN)', () => {
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN' });
      expect(t.querySelector('[data-receiver="main"]')?.getAttribute('aria-pressed')).toBe('true');
      expect(t.querySelector('[data-receiver="sub"]')?.getAttribute('aria-pressed')).toBe('false');
    });

    it('aria-pressed reflects active receiver (SUB)', () => {
      const t = mountDisplay({
        main: { ...mainVfo, isActive: false },
        sub: { ...subVfo, isActive: true },
        active: 'SUB',
      });
      expect(t.querySelector('[data-receiver="main"]')?.getAttribute('aria-pressed')).toBe('false');
      expect(t.querySelector('[data-receiver="sub"]')?.getAttribute('aria-pressed')).toBe('true');
    });
  });

  describe('onActivate callback', () => {
    it('clicking inactive tile fires onActivate with the receiver id (SUB)', () => {
      const onActivate = vi.fn();
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN', onActivate });
      t.querySelector<HTMLElement>('[data-receiver="sub"]')?.click();
      expect(onActivate).toHaveBeenCalledOnce();
      expect(onActivate).toHaveBeenCalledWith('SUB');
    });

    it('clicking inactive tile fires onActivate with the receiver id (MAIN)', () => {
      const onActivate = vi.fn();
      const t = mountDisplay({
        main: { ...mainVfo, isActive: false },
        sub: { ...subVfo, isActive: true },
        active: 'SUB',
        onActivate,
      });
      t.querySelector<HTMLElement>('[data-receiver="main"]')?.click();
      expect(onActivate).toHaveBeenCalledOnce();
      expect(onActivate).toHaveBeenCalledWith('MAIN');
    });

    it('clicking already-active tile does NOT fire onActivate', () => {
      const onActivate = vi.fn();
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN', onActivate });
      t.querySelector<HTMLElement>('[data-receiver="main"]')?.click();
      expect(onActivate).not.toHaveBeenCalled();
    });

    it('Enter key on inactive tile fires onActivate', () => {
      const onActivate = vi.fn();
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN', onActivate });
      const tile = t.querySelector<HTMLElement>('[data-receiver="sub"]');
      tile?.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      expect(onActivate).toHaveBeenCalledWith('SUB');
    });

    it('Space key on inactive tile fires onActivate', () => {
      const onActivate = vi.fn();
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN', onActivate });
      const tile = t.querySelector<HTMLElement>('[data-receiver="sub"]');
      tile?.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }));
      expect(onActivate).toHaveBeenCalledWith('SUB');
    });

    it('other keys do not fire onActivate', () => {
      const onActivate = vi.fn();
      const t = mountDisplay({ main: mainVfo, sub: subVfo, active: 'MAIN', onActivate });
      const tile = t.querySelector<HTMLElement>('[data-receiver="sub"]');
      tile?.dispatchEvent(new KeyboardEvent('keydown', { key: 'a', bubbles: true }));
      expect(onActivate).not.toHaveBeenCalled();
    });
  });
});
