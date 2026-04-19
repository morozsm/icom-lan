import { describe, expect, it } from 'vitest';

import { DEFAULT_KEYBOARD_CONFIG, resolveAction, shouldIgnoreEvent } from '../keyboard-map';

describe('resolveAction', () => {
  it('ArrowLeft tunes down by the current frontend step', () => {
    const action = resolveAction({ key: 'ArrowLeft' }, DEFAULT_KEYBOARD_CONFIG);

    expect(action).toEqual(
      expect.objectContaining({
        action: 'tune',
        params: { direction: 'down', fine: false },
      }),
    );
  });

  it('ArrowRight tunes up by the current frontend step', () => {
    const action = resolveAction({ key: 'ArrowRight' }, DEFAULT_KEYBOARD_CONFIG);

    expect(action).toEqual(
      expect.objectContaining({
        action: 'tune',
        params: { direction: 'up', fine: false },
      }),
    );
  });

  it('ArrowUp selects the next tuning step', () => {
    const action = resolveAction({ key: 'ArrowUp' }, DEFAULT_KEYBOARD_CONFIG);

    expect(action).toEqual(
      expect.objectContaining({
        action: 'adjust_tuning_step',
        params: { direction: 'up' },
      }),
    );
  });

  it('ArrowDown selects the previous tuning step', () => {
    const action = resolveAction({ key: 'ArrowDown' }, DEFAULT_KEYBOARD_CONFIG);

    expect(action).toEqual(
      expect.objectContaining({
        action: 'adjust_tuning_step',
        params: { direction: 'down' },
      }),
    );
  });

  it('returns null for an unbound key', () => {
    expect(resolveAction({ key: 'q' }, DEFAULT_KEYBOARD_CONFIG)).toBeNull();
  });

  it.each([
    ['[', 'scope_span_step', { direction: 'down' }],
    [']', 'scope_span_step', { direction: 'up' }],
    ['-', 'scope_ref_step', { direction: 'down' }],
    ['=', 'scope_ref_step', { direction: 'up' }],
    ['h', 'scope_toggle_hold', undefined],
    ['d', 'scope_toggle_dual', undefined],
    ['f', 'scope_toggle_fst', undefined],
  ])('binds %s to %s', (key, action, params) => {
    const resolved = resolveAction({ key }, DEFAULT_KEYBOARD_CONFIG);
    expect(resolved?.action).toBe(action);
    expect(resolved?.params).toEqual(params);
  });
});

describe('shouldIgnoreEvent', () => {
  function makeEl(tag: string): Element {
    return { tagName: tag } as Element;
  }

  it('suppresses shortcuts on editable elements', () => {
    expect(shouldIgnoreEvent(makeEl('INPUT'))).toBe(true);
    expect(shouldIgnoreEvent(makeEl('TEXTAREA'))).toBe(true);
    expect(shouldIgnoreEvent(makeEl('SELECT'))).toBe(true);
  });

  it('keeps shortcuts active on non-editable elements', () => {
    expect(shouldIgnoreEvent(makeEl('DIV'))).toBe(false);
    expect(shouldIgnoreEvent(makeEl('BUTTON'))).toBe(false);
    expect(shouldIgnoreEvent(null)).toBe(false);
  });
});
