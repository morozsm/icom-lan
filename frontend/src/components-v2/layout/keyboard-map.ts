import type {
  KeyboardBindingConfig as CapKeyboardBindingConfig,
  KeyboardConfig as CapKeyboardConfig,
} from '$lib/types/capabilities';

export type KeyboardBindingConfig = CapKeyboardBindingConfig;
export type KeyboardConfig = CapKeyboardConfig;

export interface KeyboardActionConfig {
  id: string;
  action: string;
  params?: Record<string, unknown>;
  section: string;
  label?: string;
  description?: string;
  sequence: string[];
  modifiers?: string[];
  repeatable?: boolean;
}

export const DEFAULT_KEYBOARD_CONFIG: KeyboardConfig = {
  leaderKey: 'g',
  leaderTimeoutMs: 1000,
  altHints: true,
  helpTitle: 'Keyboard Shortcuts',
  bindings: [
    {
      id: 'step-up',
      section: 'Tuning',
      label: 'Increase tuning step',
      sequence: ['ArrowUp'],
      action: 'adjust_tuning_step',
      params: { direction: 'up' },
    },
    {
      id: 'step-down',
      section: 'Tuning',
      label: 'Decrease tuning step',
      sequence: ['ArrowDown'],
      action: 'adjust_tuning_step',
      params: { direction: 'down' },
    },
    {
      id: 'tune-down',
      section: 'Tuning',
      label: 'Tune down',
      sequence: ['ArrowLeft'],
      action: 'tune',
      repeatable: true,
      params: { direction: 'down', fine: false },
    },
    {
      id: 'tune-up',
      section: 'Tuning',
      label: 'Tune up',
      sequence: ['ArrowRight'],
      action: 'tune',
      repeatable: true,
      params: { direction: 'up', fine: false },
    },
    {
      id: 'help',
      section: 'System',
      label: 'Keyboard help',
      sequence: ['?'],
      action: 'toggle_help',
    },
  ],
};

/** Tags whose focused presence should suppress keyboard shortcuts. */
export const IGNORED_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT']);

const MODIFIER_ORDER = ['CTRL', 'SHIFT', 'ALT', 'META'] as const;

function normalizeModifier(modifier: string): string {
  return modifier.trim().toUpperCase();
}

export function normalizeKeyboardConfig(config: KeyboardConfig | null | undefined): KeyboardConfig {
  const source = config ?? DEFAULT_KEYBOARD_CONFIG;
  return {
    leaderKey: source.leaderKey || DEFAULT_KEYBOARD_CONFIG.leaderKey,
    leaderTimeoutMs: source.leaderTimeoutMs || DEFAULT_KEYBOARD_CONFIG.leaderTimeoutMs,
    altHints: source.altHints ?? DEFAULT_KEYBOARD_CONFIG.altHints,
    helpTitle: source.helpTitle || DEFAULT_KEYBOARD_CONFIG.helpTitle,
    bindings: (source.bindings?.length ? source.bindings : DEFAULT_KEYBOARD_CONFIG.bindings).map((binding) => ({
      id: binding.id,
      action: binding.action,
      sequence: [...binding.sequence],
      section: binding.section || 'General',
      label: binding.label,
      description: binding.description,
      modifiers: binding.modifiers?.map(normalizeModifier),
      repeatable: binding.repeatable ?? false,
      params: binding.params,
    })),
  };
}

export function getEventModifiers(event: {
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  metaKey?: boolean;
}): string[] {
  const modifiers: string[] = [];
  if (event.ctrlKey) modifiers.push('CTRL');
  if (event.shiftKey) modifiers.push('SHIFT');
  if (event.altKey) modifiers.push('ALT');
  if (event.metaKey) modifiers.push('META');
  return modifiers;
}

function modifiersMatch(binding: KeyboardBindingConfig, event: { ctrlKey?: boolean; shiftKey?: boolean; altKey?: boolean; metaKey?: boolean }): boolean {
  const expected = [...(binding.modifiers ?? [])].map(normalizeModifier).sort();
  const actual = getEventModifiers(event).sort();
  if (expected.length !== actual.length) {
    return false;
  }
  return expected.every((modifier, index) => modifier === actual[index]);
}

export function resolveAction(
  event: { key: string; ctrlKey?: boolean; shiftKey?: boolean; altKey?: boolean; metaKey?: boolean },
  config: KeyboardConfig | null | undefined = DEFAULT_KEYBOARD_CONFIG,
): KeyboardActionConfig | null {
  const normalized = normalizeKeyboardConfig(config);
  const binding = normalized.bindings.find(
    (candidate) => candidate.sequence.length === 1 && candidate.sequence[0] === event.key && modifiersMatch(candidate, event),
  );
  if (!binding) {
    return null;
  }
  return {
    id: binding.id,
    action: binding.action,
    params: binding.params,
    section: binding.section,
    label: binding.label,
    description: binding.description,
    sequence: binding.sequence,
    modifiers: binding.modifiers,
    repeatable: binding.repeatable,
  };
}

export function resolveSequenceStart(
  event: { key: string; ctrlKey?: boolean; shiftKey?: boolean; altKey?: boolean; metaKey?: boolean },
  config: KeyboardConfig | null | undefined = DEFAULT_KEYBOARD_CONFIG,
): KeyboardBindingConfig | null {
  const normalized = normalizeKeyboardConfig(config);
  return normalized.bindings.find(
    (binding) => binding.sequence.length > 1 && binding.sequence[0] === event.key && modifiersMatch(binding, event),
  ) ?? null;
}

export function resolveSequenceContinuation(
  binding: KeyboardBindingConfig,
  event: { key: string },
): KeyboardActionConfig | null {
  if (binding.sequence.length < 2 || binding.sequence[1] !== event.key) {
    return null;
  }
  return {
    id: binding.id,
    action: binding.action,
    params: binding.params,
    section: binding.section,
    label: binding.label,
    description: binding.description,
    sequence: binding.sequence,
    modifiers: binding.modifiers,
    repeatable: binding.repeatable,
  };
}

export function formatShortcut(binding: KeyboardBindingConfig): string {
  const sequence = binding.sequence.map((step, index) => {
    const prefix = index === 0 && binding.modifiers?.length
      ? [...binding.modifiers].map(normalizeModifier).sort((left, right) => {
          return MODIFIER_ORDER.indexOf(left as (typeof MODIFIER_ORDER)[number]) - MODIFIER_ORDER.indexOf(right as (typeof MODIFIER_ORDER)[number]);
        }).join('+') + '+'
      : '';
    return `${prefix}${step}`;
  });
  return sequence.join(' then ');
}

export function findBindingByAction(
  config: KeyboardConfig | null | undefined,
  action: string,
  predicate?: (binding: KeyboardBindingConfig) => boolean,
): KeyboardBindingConfig | null {
  const normalized = normalizeKeyboardConfig(config);
  return normalized.bindings.find((binding) => binding.action === action && (predicate ? predicate(binding) : true)) ?? null;
}

/**
 * Returns true when the active element is an editable field and
 * keyboard shortcuts should be suppressed.
 */
export function shouldIgnoreEvent(activeElement: Element | null): boolean {
  if (!activeElement) return false;
  return IGNORED_TAGS.has(activeElement.tagName);
}
