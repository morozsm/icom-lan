import { describe, it, expect, beforeEach } from 'vitest';
import { loadPanelOrder, reorderPanels } from '../drag-reorder.svelte';

const KEY = 'test:panel-order';
const DEFAULTS = ['rx-audio', 'audio-scope', 'dsp', 'tx', 'cw', 'memory'];

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => {
      store[k] = v;
    },
    removeItem: (k: string) => {
      delete store[k];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

beforeEach(() => {
  localStorageMock.clear();
});

describe('loadPanelOrder', () => {
  it('returns defaults when nothing stored', () => {
    expect(loadPanelOrder(KEY, DEFAULTS)).toEqual(DEFAULTS);
  });

  it('returns stored order when it fully matches defaults', () => {
    const custom = ['dsp', 'rx-audio', 'audio-scope', 'tx', 'cw', 'memory'];
    localStorage.setItem(KEY, JSON.stringify(custom));
    expect(loadPanelOrder(KEY, DEFAULTS)).toEqual(custom);
  });

  it('appends missing defaults so newly-introduced panels become visible (regression #821)', () => {
    // Simulates a user whose localStorage was written before `audio-scope`
    // was added to defaults. Without the merge, `audio-scope` never rendered.
    const pre821 = ['rx-audio', 'dsp', 'tx', 'cw', 'memory'];
    localStorage.setItem(KEY, JSON.stringify(pre821));
    const result = loadPanelOrder(KEY, DEFAULTS);
    expect(result).toContain('audio-scope');
    // Existing order is preserved; new id is appended.
    expect(result.slice(0, pre821.length)).toEqual(pre821);
    expect(result[result.length - 1]).toBe('audio-scope');
  });

  it('preserves unknown (peer-owned) ids in stored order', () => {
    const withForeign = ['rx-audio', 'audio-scope', 'dsp', 'tx', 'cw', 'memory', 'foreign-panel'];
    localStorage.setItem(KEY, JSON.stringify(withForeign));
    const result = loadPanelOrder(KEY, DEFAULTS);
    expect(result).toContain('foreign-panel');
  });

  it('deduplicates ids in stored order', () => {
    localStorage.setItem(KEY, JSON.stringify(['rx-audio', 'rx-audio', 'dsp']));
    const result = loadPanelOrder(KEY, DEFAULTS);
    expect(result.filter((id) => id === 'rx-audio')).toHaveLength(1);
  });

  it('falls back to defaults on invalid JSON', () => {
    localStorage.setItem(KEY, '{not-json');
    expect(loadPanelOrder(KEY, DEFAULTS)).toEqual(DEFAULTS);
  });

  it('falls back to defaults when stored value is not an array', () => {
    localStorage.setItem(KEY, JSON.stringify({ foo: 1 }));
    expect(loadPanelOrder(KEY, DEFAULTS)).toEqual(DEFAULTS);
  });
});

describe('reorderPanels', () => {
  it('moves a panel forward', () => {
    const r = reorderPanels(DEFAULTS, 'rx-audio', 3);
    expect(r[3]).toBe('rx-audio');
    expect(r).toHaveLength(DEFAULTS.length);
  });

  it('is a no-op when source equals target index', () => {
    const r = reorderPanels(DEFAULTS, 'dsp', 2);
    expect(r).toBe(DEFAULTS);
  });

  it('returns input unchanged when id is not in the order', () => {
    const r = reorderPanels(DEFAULTS, 'missing', 0);
    expect(r).toBe(DEFAULTS);
  });
});
