export type KeyAction =
  | { type: 'tune'; direction: 'up' | 'down'; fine: boolean }
  | { type: 'bandSelect'; index: number }
  | { type: 'modeSelect'; mode: string }
  | { type: 'pttToggle' }
  | { type: 'vfoSwap' }
  | { type: 'ritClear' }
  | { type: 'monitorToggle' }
  | { type: 'nrToggle' }
  | { type: 'nbToggle' };

interface KeyBinding {
  key: string;
  /** If defined, shift state must match exactly. If undefined, shift is ignored. */
  shift?: boolean;
  action: KeyAction;
}

export const KEYBOARD_BINDINGS: KeyBinding[] = [
  // Tuning: Arrow Up/Down — coarse (no shift) or fine (shift)
  { key: 'ArrowUp', shift: false, action: { type: 'tune', direction: 'up', fine: false } },
  { key: 'ArrowUp', shift: true, action: { type: 'tune', direction: 'up', fine: true } },
  { key: 'ArrowDown', shift: false, action: { type: 'tune', direction: 'down', fine: false } },
  { key: 'ArrowDown', shift: true, action: { type: 'tune', direction: 'down', fine: true } },
  // VFO nudge: Arrow Left/Right always fine
  { key: 'ArrowLeft', action: { type: 'tune', direction: 'down', fine: true } },
  { key: 'ArrowRight', action: { type: 'tune', direction: 'up', fine: true } },
  // Band select: 1=160m, 2=80m, 3=60m, 4=40m, 5=30m, 6=20m, 7=15m, 8=10m, 9=6m
  { key: '1', action: { type: 'bandSelect', index: 1 } },
  { key: '2', action: { type: 'bandSelect', index: 2 } },
  { key: '3', action: { type: 'bandSelect', index: 3 } },
  { key: '4', action: { type: 'bandSelect', index: 4 } },
  { key: '5', action: { type: 'bandSelect', index: 5 } },
  { key: '6', action: { type: 'bandSelect', index: 6 } },
  { key: '7', action: { type: 'bandSelect', index: 7 } },
  { key: '8', action: { type: 'bandSelect', index: 8 } },
  { key: '9', action: { type: 'bandSelect', index: 9 } },
  // Mode select via F-keys
  { key: 'F1', action: { type: 'modeSelect', mode: 'LSB' } },
  { key: 'F2', action: { type: 'modeSelect', mode: 'USB' } },
  { key: 'F3', action: { type: 'modeSelect', mode: 'CW' } },
  { key: 'F4', action: { type: 'modeSelect', mode: 'AM' } },
  // Controls
  { key: ' ', action: { type: 'pttToggle' } },
  { key: 'Tab', action: { type: 'vfoSwap' } },
  { key: 'Escape', action: { type: 'ritClear' } },
  // Toggle features
  { key: 'm', action: { type: 'monitorToggle' } },
  { key: 'n', action: { type: 'nrToggle' } },
  { key: 'b', action: { type: 'nbToggle' } },
];

/** Tags whose focused presence should suppress keyboard shortcuts. */
export const IGNORED_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT']);

/**
 * Resolves a keyboard event to a KeyAction, or null if not mapped.
 * Handles shift-sensitive bindings (ArrowUp/Down) and shift-agnostic ones.
 */
export function resolveAction(event: { key: string; shiftKey: boolean }): KeyAction | null {
  for (const binding of KEYBOARD_BINDINGS) {
    if (binding.key !== event.key) continue;
    if (binding.shift !== undefined && binding.shift !== event.shiftKey) continue;
    return binding.action;
  }
  return null;
}

/**
 * Returns true when the active element is an editable field and
 * keyboard shortcuts should be suppressed.
 */
export function shouldIgnoreEvent(activeElement: Element | null): boolean {
  if (!activeElement) return false;
  return IGNORED_TAGS.has(activeElement.tagName);
}
