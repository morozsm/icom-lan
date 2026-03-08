import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { Capabilities } from '../../types/capabilities';

function makeCaps(overrides: Partial<Capabilities> = {}): Capabilities {
  return {
    model: 'IC-7610',
    scope: true,
    audio: true,
    tx: true,
    capabilities: ['scope', 'dual_rx', 'tx', 'tuner', 'cw'],
    freqRanges: [{ start: 1800000, end: 30000000, label: 'HF' }],
    modes: ['USB', 'LSB', 'CW', 'AM', 'FM'],
    filters: ['FIL1', 'FIL2', 'FIL3'],
    ...overrides,
  };
}

describe('capabilities store', () => {
  let store: typeof import('../capabilities.svelte');

  beforeEach(async () => {
    vi.resetModules();
    store = await import('../capabilities.svelte');
  });

  it('starts with null capabilities', () => {
    expect(store.getCapabilities()).toBeNull();
  });

  it('getters return false/[] before setCapabilities is called', () => {
    expect(store.hasSpectrum()).toBe(false);
    expect(store.hasAudio()).toBe(false);
    expect(store.hasDualReceiver()).toBe(false);
    expect(store.hasTx()).toBe(false);
    expect(store.getSupportedModes()).toEqual([]);
    expect(store.getSupportedFilters()).toEqual([]);
  });

  describe('setCapabilities + getCapabilities', () => {
    it('stores and returns capabilities', () => {
      const caps = makeCaps();
      store.setCapabilities(caps);
      expect(store.getCapabilities()).toStrictEqual(caps);
    });

    it('can be updated with new capabilities', () => {
      store.setCapabilities(makeCaps({ model: 'IC-7300' }));
      store.setCapabilities(makeCaps({ model: 'IC-9700' }));
      expect(store.getCapabilities()?.model).toBe('IC-9700');
    });
  });

  describe('hasSpectrum', () => {
    it('returns true when scope is true', () => {
      store.setCapabilities(makeCaps({ scope: true }));
      expect(store.hasSpectrum()).toBe(true);
    });

    it('returns false when scope is false', () => {
      store.setCapabilities(makeCaps({ scope: false }));
      expect(store.hasSpectrum()).toBe(false);
    });
  });

  describe('hasAudio', () => {
    it('returns true when audio is true', () => {
      store.setCapabilities(makeCaps({ audio: true }));
      expect(store.hasAudio()).toBe(true);
    });

    it('returns false when audio is false', () => {
      store.setCapabilities(makeCaps({ audio: false }));
      expect(store.hasAudio()).toBe(false);
    });
  });

  describe('hasDualReceiver', () => {
    it('returns true when capabilities includes dual_rx', () => {
      store.setCapabilities(makeCaps({ capabilities: ['dual_rx'] }));
      expect(store.hasDualReceiver()).toBe(true);
    });

    it('returns false when dual_rx is absent', () => {
      store.setCapabilities(makeCaps({ capabilities: ['scope', 'tx'] }));
      expect(store.hasDualReceiver()).toBe(false);
    });

    it('returns false for empty capabilities array', () => {
      store.setCapabilities(makeCaps({ capabilities: [] }));
      expect(store.hasDualReceiver()).toBe(false);
    });
  });

  describe('hasTx', () => {
    it('returns true when tx is true', () => {
      store.setCapabilities(makeCaps({ tx: true }));
      expect(store.hasTx()).toBe(true);
    });

    it('returns false when tx is false', () => {
      store.setCapabilities(makeCaps({ tx: false }));
      expect(store.hasTx()).toBe(false);
    });
  });

  describe('getSupportedModes', () => {
    it('returns modes array after setCapabilities', () => {
      store.setCapabilities(makeCaps({ modes: ['USB', 'LSB', 'CW'] }));
      expect(store.getSupportedModes()).toEqual(['USB', 'LSB', 'CW']);
    });

    it('returns empty array before setCapabilities', () => {
      expect(store.getSupportedModes()).toEqual([]);
    });
  });

  describe('getSupportedFilters', () => {
    it('returns filters array after setCapabilities', () => {
      store.setCapabilities(makeCaps({ filters: ['FIL1', 'FIL2'] }));
      expect(store.getSupportedFilters()).toEqual(['FIL1', 'FIL2']);
    });

    it('returns empty array before setCapabilities', () => {
      expect(store.getSupportedFilters()).toEqual([]);
    });
  });
});
