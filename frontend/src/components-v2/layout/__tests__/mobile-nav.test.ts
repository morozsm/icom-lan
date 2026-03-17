import { describe, it, expect } from 'vitest';
import {
  TABS,
  DEFAULT_TAB,
  isTabVisible,
  getVisibleTabs,
  type TabDef,
  type NavCapabilities,
} from '../mobile-nav-utils';

// ---------------------------------------------------------------------------
// TABS constant
// ---------------------------------------------------------------------------

describe('TABS constant', () => {
  it('contains exactly 5 tabs', () => {
    expect(TABS).toHaveLength(5);
  });

  it('has tabs in order: vfo, spectrum, controls, tx, meters', () => {
    const ids = TABS.map((t) => t.id);
    expect(ids).toEqual(['vfo', 'spectrum', 'controls', 'tx', 'meters']);
  });

  it('each tab has a non-empty id, label, and icon', () => {
    for (const tab of TABS) {
      expect(tab.id).toBeTruthy();
      expect(tab.label).toBeTruthy();
      expect(tab.icon).toBeTruthy();
    }
  });

  it('vfo tab has icon 📻', () => {
    const tab = TABS.find((t) => t.id === 'vfo');
    expect(tab?.icon).toBe('📻');
  });

  it('spectrum tab has icon 📊', () => {
    const tab = TABS.find((t) => t.id === 'spectrum');
    expect(tab?.icon).toBe('📊');
  });

  it('controls tab has icon 🎛', () => {
    const tab = TABS.find((t) => t.id === 'controls');
    expect(tab?.icon).toBe('🎛');
  });

  it('tx tab has icon 📡', () => {
    const tab = TABS.find((t) => t.id === 'tx');
    expect(tab?.icon).toBe('📡');
  });

  it('meters tab has icon 📈', () => {
    const tab = TABS.find((t) => t.id === 'meters');
    expect(tab?.icon).toBe('📈');
  });
});

// ---------------------------------------------------------------------------
// DEFAULT_TAB
// ---------------------------------------------------------------------------

describe('DEFAULT_TAB', () => {
  it('is "spectrum"', () => {
    expect(DEFAULT_TAB).toBe('spectrum');
  });

  it('refers to a tab that exists in TABS', () => {
    const ids = TABS.map((t) => t.id);
    expect(ids).toContain(DEFAULT_TAB);
  });
});

// ---------------------------------------------------------------------------
// isTabVisible
// ---------------------------------------------------------------------------

describe('isTabVisible', () => {
  it('returns true for vfo regardless of capabilities', () => {
    const tab = TABS.find((t) => t.id === 'vfo')!;
    expect(isTabVisible(tab, {})).toBe(true);
    expect(isTabVisible(tab, { hasTx: false })).toBe(true);
    expect(isTabVisible(tab, { hasTx: true })).toBe(true);
  });

  it('returns true for spectrum regardless of capabilities', () => {
    const tab = TABS.find((t) => t.id === 'spectrum')!;
    expect(isTabVisible(tab, {})).toBe(true);
    expect(isTabVisible(tab, { hasTx: false })).toBe(true);
  });

  it('returns true for controls regardless of capabilities', () => {
    const tab = TABS.find((t) => t.id === 'controls')!;
    expect(isTabVisible(tab, {})).toBe(true);
    expect(isTabVisible(tab, { hasTx: false })).toBe(true);
  });

  it('returns true for meters regardless of capabilities', () => {
    const tab = TABS.find((t) => t.id === 'meters')!;
    expect(isTabVisible(tab, {})).toBe(true);
    expect(isTabVisible(tab, { hasTx: false })).toBe(true);
  });

  it('returns false for tx when hasTx is false', () => {
    const tab = TABS.find((t) => t.id === 'tx')!;
    expect(isTabVisible(tab, { hasTx: false })).toBe(false);
  });

  it('returns false for tx when hasTx is undefined (empty capabilities)', () => {
    const tab = TABS.find((t) => t.id === 'tx')!;
    expect(isTabVisible(tab, {})).toBe(false);
  });

  it('returns true for tx when hasTx is true', () => {
    const tab = TABS.find((t) => t.id === 'tx')!;
    expect(isTabVisible(tab, { hasTx: true })).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// getVisibleTabs
// ---------------------------------------------------------------------------

describe('getVisibleTabs', () => {
  it('returns 4 tabs when hasTx is false', () => {
    expect(getVisibleTabs({ hasTx: false })).toHaveLength(4);
  });

  it('excludes tx tab when hasTx is false', () => {
    const tabs = getVisibleTabs({ hasTx: false });
    expect(tabs.find((t) => t.id === 'tx')).toBeUndefined();
  });

  it('returns 4 tabs when capabilities is empty (no hasTx)', () => {
    expect(getVisibleTabs({})).toHaveLength(4);
  });

  it('returns 5 tabs when hasTx is true', () => {
    expect(getVisibleTabs({ hasTx: true })).toHaveLength(5);
  });

  it('includes tx tab when hasTx is true', () => {
    const tabs = getVisibleTabs({ hasTx: true });
    expect(tabs.find((t) => t.id === 'tx')).toBeDefined();
  });

  it('preserves tab order when hasTx is true', () => {
    const ids = getVisibleTabs({ hasTx: true }).map((t) => t.id);
    expect(ids).toEqual(['vfo', 'spectrum', 'controls', 'tx', 'meters']);
  });

  it('preserves tab order when hasTx is false (tx omitted)', () => {
    const ids = getVisibleTabs({ hasTx: false }).map((t) => t.id);
    expect(ids).toEqual(['vfo', 'spectrum', 'controls', 'meters']);
  });

  it('always includes vfo, spectrum, controls, meters', () => {
    const caps: NavCapabilities[] = [
      {},
      { hasTx: false },
      { hasTx: true },
    ];
    for (const cap of caps) {
      const tabs = getVisibleTabs(cap);
      const ids = tabs.map((t) => t.id);
      expect(ids).toContain('vfo');
      expect(ids).toContain('spectrum');
      expect(ids).toContain('controls');
      expect(ids).toContain('meters');
    }
  });
});
