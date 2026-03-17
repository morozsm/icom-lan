import { describe, it, expect } from 'vitest';
import {
  KEYBOARD_BINDINGS,
  IGNORED_TAGS,
  resolveAction,
  shouldIgnoreEvent,
} from '../keyboard-map';

// ---------------------------------------------------------------------------
// KEYBOARD_BINDINGS structure
// ---------------------------------------------------------------------------

describe('KEYBOARD_BINDINGS structure', () => {
  it('is a non-empty array', () => {
    expect(Array.isArray(KEYBOARD_BINDINGS)).toBe(true);
    expect(KEYBOARD_BINDINGS.length).toBeGreaterThan(0);
  });

  it('every entry has a string key and an action with a type', () => {
    for (const binding of KEYBOARD_BINDINGS) {
      expect(typeof binding.key).toBe('string');
      expect(typeof binding.action.type).toBe('string');
    }
  });

  it('contains bindings for all digits 1-9', () => {
    for (let i = 1; i <= 9; i++) {
      const found = KEYBOARD_BINDINGS.find(
        (b) => b.key === String(i) && b.action.type === 'bandSelect',
      );
      expect(found).toBeDefined();
    }
  });

  it('contains bindings for F1-F4', () => {
    for (let i = 1; i <= 4; i++) {
      const found = KEYBOARD_BINDINGS.find((b) => b.key === `F${i}`);
      expect(found).toBeDefined();
    }
  });

  it('band indices 1-9 map correctly in order', () => {
    const bandBindings = KEYBOARD_BINDINGS.filter((b) => b.action.type === 'bandSelect');
    const indices = bandBindings.map((b) => (b.action as { type: 'bandSelect'; index: number }).index);
    expect(indices.sort((a, z) => a - z)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);
  });
});

// ---------------------------------------------------------------------------
// resolveAction — tuning
// ---------------------------------------------------------------------------

describe('resolveAction — tuning', () => {
  it('ArrowUp without shift → tune up coarse', () => {
    const action = resolveAction({ key: 'ArrowUp', shiftKey: false });
    expect(action).toEqual({ type: 'tune', direction: 'up', fine: false });
  });

  it('ArrowUp with shift → tune up fine', () => {
    const action = resolveAction({ key: 'ArrowUp', shiftKey: true });
    expect(action).toEqual({ type: 'tune', direction: 'up', fine: true });
  });

  it('ArrowDown without shift → tune down coarse', () => {
    const action = resolveAction({ key: 'ArrowDown', shiftKey: false });
    expect(action).toEqual({ type: 'tune', direction: 'down', fine: false });
  });

  it('ArrowDown with shift → tune down fine', () => {
    const action = resolveAction({ key: 'ArrowDown', shiftKey: true });
    expect(action).toEqual({ type: 'tune', direction: 'down', fine: true });
  });

  it('ArrowLeft → tune down fine (VFO nudge)', () => {
    const action = resolveAction({ key: 'ArrowLeft', shiftKey: false });
    expect(action).toEqual({ type: 'tune', direction: 'down', fine: true });
  });

  it('ArrowRight → tune up fine (VFO nudge)', () => {
    const action = resolveAction({ key: 'ArrowRight', shiftKey: false });
    expect(action).toEqual({ type: 'tune', direction: 'up', fine: true });
  });

  it('ArrowLeft with shift still resolves (shift ignored for nudge)', () => {
    const action = resolveAction({ key: 'ArrowLeft', shiftKey: true });
    expect(action).toEqual({ type: 'tune', direction: 'down', fine: true });
  });
});

// ---------------------------------------------------------------------------
// resolveAction — band select
// ---------------------------------------------------------------------------

describe('resolveAction — band select', () => {
  it('digit 1 → bandSelect index 1 (160m)', () => {
    const action = resolveAction({ key: '1', shiftKey: false });
    expect(action).toEqual({ type: 'bandSelect', index: 1 });
  });

  it('digit 5 → bandSelect index 5 (30m)', () => {
    const action = resolveAction({ key: '5', shiftKey: false });
    expect(action).toEqual({ type: 'bandSelect', index: 5 });
  });

  it('digit 9 → bandSelect index 9 (6m)', () => {
    const action = resolveAction({ key: '9', shiftKey: false });
    expect(action).toEqual({ type: 'bandSelect', index: 9 });
  });
});

// ---------------------------------------------------------------------------
// resolveAction — mode select
// ---------------------------------------------------------------------------

describe('resolveAction — mode select', () => {
  it('F1 → modeSelect LSB', () => {
    const action = resolveAction({ key: 'F1', shiftKey: false });
    expect(action).toEqual({ type: 'modeSelect', mode: 'LSB' });
  });

  it('F2 → modeSelect USB', () => {
    const action = resolveAction({ key: 'F2', shiftKey: false });
    expect(action).toEqual({ type: 'modeSelect', mode: 'USB' });
  });

  it('F3 → modeSelect CW', () => {
    const action = resolveAction({ key: 'F3', shiftKey: false });
    expect(action).toEqual({ type: 'modeSelect', mode: 'CW' });
  });

  it('F4 → modeSelect AM', () => {
    const action = resolveAction({ key: 'F4', shiftKey: false });
    expect(action).toEqual({ type: 'modeSelect', mode: 'AM' });
  });
});

// ---------------------------------------------------------------------------
// resolveAction — controls and toggles
// ---------------------------------------------------------------------------

describe('resolveAction — controls and toggles', () => {
  it('Space → pttToggle', () => {
    const action = resolveAction({ key: ' ', shiftKey: false });
    expect(action).toEqual({ type: 'pttToggle' });
  });

  it('Tab → vfoSwap', () => {
    const action = resolveAction({ key: 'Tab', shiftKey: false });
    expect(action).toEqual({ type: 'vfoSwap' });
  });

  it('Escape → ritClear', () => {
    const action = resolveAction({ key: 'Escape', shiftKey: false });
    expect(action).toEqual({ type: 'ritClear' });
  });

  it('m → monitorToggle', () => {
    const action = resolveAction({ key: 'm', shiftKey: false });
    expect(action).toEqual({ type: 'monitorToggle' });
  });

  it('n → nrToggle', () => {
    const action = resolveAction({ key: 'n', shiftKey: false });
    expect(action).toEqual({ type: 'nrToggle' });
  });

  it('b → nbToggle', () => {
    const action = resolveAction({ key: 'b', shiftKey: false });
    expect(action).toEqual({ type: 'nbToggle' });
  });

  it('unknown key → null', () => {
    const action = resolveAction({ key: 'q', shiftKey: false });
    expect(action).toBeNull();
  });

  it('uppercase M → null (case-sensitive)', () => {
    const action = resolveAction({ key: 'M', shiftKey: false });
    expect(action).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// shouldIgnoreEvent — input focus filtering
// ---------------------------------------------------------------------------

describe('shouldIgnoreEvent', () => {
  function makeEl(tag: string): Element {
    return { tagName: tag } as Element;
  }

  it('returns false for null activeElement', () => {
    expect(shouldIgnoreEvent(null)).toBe(false);
  });

  it('returns true for INPUT element', () => {
    expect(shouldIgnoreEvent(makeEl('INPUT'))).toBe(true);
  });

  it('returns true for TEXTAREA element', () => {
    expect(shouldIgnoreEvent(makeEl('TEXTAREA'))).toBe(true);
  });

  it('returns true for SELECT element', () => {
    expect(shouldIgnoreEvent(makeEl('SELECT'))).toBe(true);
  });

  it('returns false for DIV element', () => {
    expect(shouldIgnoreEvent(makeEl('DIV'))).toBe(false);
  });

  it('returns false for BUTTON element', () => {
    expect(shouldIgnoreEvent(makeEl('BUTTON'))).toBe(false);
  });

  it('returns false for BODY element', () => {
    expect(shouldIgnoreEvent(makeEl('BODY'))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// IGNORED_TAGS set
// ---------------------------------------------------------------------------

describe('IGNORED_TAGS', () => {
  it('contains INPUT, TEXTAREA, SELECT', () => {
    expect(IGNORED_TAGS.has('INPUT')).toBe(true);
    expect(IGNORED_TAGS.has('TEXTAREA')).toBe(true);
    expect(IGNORED_TAGS.has('SELECT')).toBe(true);
  });

  it('does not contain DIV or BUTTON', () => {
    expect(IGNORED_TAGS.has('DIV')).toBe(false);
    expect(IGNORED_TAGS.has('BUTTON')).toBe(false);
  });
});
