/**
 * CLDR plural-form resolution via the platform `Intl.PluralRules`.
 *
 * We avoid bundling a plural-rules library (CLDR tables ship with every
 * modern browser) so the i18n runtime stays small and `Intl` updates with
 * the platform.
 *
 * Convention: a plural message has the same base key with CLDR-suffix
 * variants, e.g.
 *   core.diagnostics.attachedFiles.one     -> "1 file attached"
 *   core.diagnostics.attachedFiles.other   -> "{count} files attached"
 *
 * Resolution order for count = N:
 *   1. `base.<plural-cat-for-N>` in the active locale.
 *   2. `base.other` in the active locale.
 *   3. `base.<plural-cat-for-N>` in en-US (via lookup fallback).
 *   4. `base.other` in en-US.
 *   5. Missing-key path.
 *
 * Note: Japanese (`ja-JP`) collapses to `.other` only; CLDR returns "other"
 * for every count. This is correct, not a bug.
 */

import type { LocaleCode, MessageParams } from './types';
import { resolve } from './runtime';

export type PluralCategory = 'zero' | 'one' | 'two' | 'few' | 'many' | 'other';

const ORDERED_FALLBACKS: PluralCategory[] = [
  'zero',
  'one',
  'two',
  'few',
  'many',
  'other',
];

function selectCategory(locale: LocaleCode, count: number): PluralCategory {
  try {
    const rules = new Intl.PluralRules(locale);
    return rules.select(count) as PluralCategory;
  } catch {
    // Locale unknown to the platform. Treat as `other`.
    return 'other';
  }
}

/**
 * Resolve a plural-form message. Returns the rendered string with
 * interpolation applied (`{count}` is injected automatically unless the
 * caller already passed a `count` param).
 */
export function resolvePlural(
  baseKey: string,
  count: number,
  locale: LocaleCode,
  params?: MessageParams,
): string {
  const category = selectCategory(locale, count);
  const mergedParams: MessageParams = { count, ...(params ?? {}) };

  // 1) Try the CLDR-selected variant.
  const primaryKey = `${baseKey}.${category}`;
  // Resolver gives `[missing:...]` in dev when neither locale nor en-US has
  // the key; for plurals we explicitly want to fall through to `.other`.
  const primary = resolve(primaryKey, locale, mergedParams);
  if (!isMissingMarker(primary, primaryKey)) return primary;

  // 2) Fall back to `.other` in the active locale (en-US fallback handled
  //    by resolve()).
  if (category !== 'other') {
    const otherKey = `${baseKey}.other`;
    return resolve(otherKey, locale, mergedParams);
  }
  // If `.other` itself missing, resolve() already returned the missing
  // marker / key — propagate.
  return primary;
}

function isMissingMarker(rendered: string, key: string): boolean {
  return rendered === `[missing:${key}]` || rendered === key;
}

/** Exposed for tests. */
export { selectCategory };

/**
 * Walk the CLDR fallback chain. Currently unused by the resolver (the chain
 * is `category -> other`), but exported for downstream tooling and tests.
 */
export function pluralFallbackChain(category: PluralCategory): PluralCategory[] {
  const idx = ORDERED_FALLBACKS.indexOf(category);
  if (idx < 0) return ['other'];
  // Always end with 'other' as the safety net.
  return [...ORDERED_FALLBACKS.slice(idx).filter((c) => c !== 'other'), 'other'];
}
