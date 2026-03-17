import { describe, it, expect, beforeEach, vi } from 'vitest';

// Minimal localStorage mock — jsdom's implementation lacks .clear()
let localStore: Record<string, string> = {};
const localStorageMock = {
  getItem: (key: string) => localStore[key] ?? null,
  setItem: (key: string, value: string) => { localStore[key] = value; },
  removeItem: (key: string) => { delete localStore[key]; },
  clear: () => { localStore = {}; },
};

describe('ui-version store', () => {
  let store: typeof import('../ui-version.svelte');

  beforeEach(async () => {
    localStore = {};
    vi.stubGlobal('localStorage', localStorageMock);
    window.history.replaceState({}, '', '/');
    vi.resetModules();
    store = await import('../ui-version.svelte');
  });

  describe('getUiVersion', () => {
    it('returns v1 by default', () => {
      expect(store.getUiVersion()).toBe('v1');
    });
  });

  describe('setUiVersion', () => {
    it('sets version to v2', () => {
      store.setUiVersion('v2');
      expect(store.getUiVersion()).toBe('v2');
    });

    it('sets version back to v1', () => {
      store.setUiVersion('v2');
      store.setUiVersion('v1');
      expect(store.getUiVersion()).toBe('v1');
    });

    it('persists to localStorage', () => {
      store.setUiVersion('v2');
      expect(localStorageMock.getItem('icom-lan-ui-version')).toBe('v2');
    });

    it('overwrites previous localStorage value', () => {
      store.setUiVersion('v2');
      store.setUiVersion('v1');
      expect(localStorageMock.getItem('icom-lan-ui-version')).toBe('v1');
    });
  });

  describe('toggleUiVersion', () => {
    it('toggles from v1 to v2', () => {
      expect(store.getUiVersion()).toBe('v1');
      store.toggleUiVersion();
      expect(store.getUiVersion()).toBe('v2');
    });

    it('toggles from v2 back to v1', () => {
      store.setUiVersion('v2');
      store.toggleUiVersion();
      expect(store.getUiVersion()).toBe('v1');
    });

    it('persists toggled value to localStorage', () => {
      store.toggleUiVersion();
      expect(localStorageMock.getItem('icom-lan-ui-version')).toBe('v2');
    });
  });

  describe('initUiVersion', () => {
    it('uses default v1 when nothing set', () => {
      store.initUiVersion();
      expect(store.getUiVersion()).toBe('v1');
    });

    it('reads v2 from localStorage', () => {
      localStorageMock.setItem('icom-lan-ui-version', 'v2');
      store.initUiVersion();
      expect(store.getUiVersion()).toBe('v2');
    });

    it('reads v1 from localStorage', () => {
      localStorageMock.setItem('icom-lan-ui-version', 'v1');
      store.initUiVersion();
      expect(store.getUiVersion()).toBe('v1');
    });

    it('ignores invalid localStorage value and falls back to v1', () => {
      localStorageMock.setItem('icom-lan-ui-version', 'v3');
      store.initUiVersion();
      expect(store.getUiVersion()).toBe('v1');
    });

    it('URL param ?ui=v2 overrides localStorage', () => {
      localStorageMock.setItem('icom-lan-ui-version', 'v1');
      window.history.replaceState({}, '', '/?ui=v2');
      store.initUiVersion();
      expect(store.getUiVersion()).toBe('v2');
    });

    it('URL param ?ui=v1 overrides localStorage', () => {
      localStorageMock.setItem('icom-lan-ui-version', 'v2');
      window.history.replaceState({}, '', '/?ui=v1');
      store.initUiVersion();
      expect(store.getUiVersion()).toBe('v1');
    });

    it('URL param persists to localStorage', () => {
      window.history.replaceState({}, '', '/?ui=v2');
      store.initUiVersion();
      expect(localStorageMock.getItem('icom-lan-ui-version')).toBe('v2');
    });

    it('invalid URL param falls through to localStorage', () => {
      localStorageMock.setItem('icom-lan-ui-version', 'v2');
      window.history.replaceState({}, '', '/?ui=v99');
      store.initUiVersion();
      expect(store.getUiVersion()).toBe('v2');
    });

    it('invalid URL param and no localStorage falls back to v1', () => {
      window.history.replaceState({}, '', '/?ui=bad');
      store.initUiVersion();
      expect(store.getUiVersion()).toBe('v1');
    });
  });
});
