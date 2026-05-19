/**
 * Core i18n resolver: catalog lookup, en-US fallback, and `{name}`
 * interpolation with `'{'` literal-brace escape.
 *
 * This module is deliberately small and synchronous.  Catalogs are imported
 * statically by `index.ts` and registered via `registerCatalog`, so runtime
 * lookups never hit the network.  See `pseudo.ts` for the `qps-ploc`
 * transformation that wraps the resolver during dev/QA.
 *
 * Missing-key policy:
 *   - production builds (import.meta.env.PROD): return the en-US source
 *     value silently; if even en-US is missing, return the key itself.  A
 *     missing-key hook is still invoked so CI lint (RP-ML-013A) can report.
 *   - development builds: return `[missing:scope.key]` so contributors notice
 *     the gap immediately.
 */

import type {
  Catalog,
  LocaleCode,
  MessageParams,
  MissingKeyHandler,
} from './types';
import { SOURCE_LOCALE } from './types';

const catalogs: Map<LocaleCode, Catalog> = new Map();
let missingKeyHandler: MissingKeyHandler | null = null;

/**
 * Strip the `$schema` documentation wrapper from a raw catalog object before
 * it is used as a lookup table. Community contributors can copy the wrapper
 * verbatim from `en-US.json`; the runtime ignores it.
 */
function stripSchemaWrapper(raw: Record<string, unknown>): Catalog {
  const out: Catalog = {};
  for (const k of Object.keys(raw)) {
    if (k === '$schema') continue;
    const v = raw[k];
    if (typeof v === 'string') {
      out[k] = v;
    }
  }
  return out;
}

export function registerCatalog(
  locale: LocaleCode,
  raw: Record<string, unknown>,
): void {
  catalogs.set(locale, stripSchemaWrapper(raw));
}

export function getCatalog(locale: LocaleCode): Catalog | undefined {
  return catalogs.get(locale);
}

/** Test/development helper. Not part of the public API. */
export function _resetCatalogs(): void {
  catalogs.clear();
  missingKeyHandler = null;
}

export function setMissingKeyHandler(handler: MissingKeyHandler | null): void {
  missingKeyHandler = handler;
}

function isProd(): boolean {
  // Vite injects `import.meta.env.PROD`. Vitest/jsdom default to dev.
  try {
    return Boolean((import.meta as ImportMeta & { env?: { PROD?: boolean } }).env?.PROD);
  } catch {
    return false;
  }
}

/**
 * Replace `{name}` placeholders. A literal `{` is written as `'{'` (single
 * quote prefix; mirrors ICU MessageFormat escape and is unambiguous because
 * placeholder names never begin with a quote).
 *
 * Unknown placeholders are left intact so they show up in tests / QA.
 */
export function interpolate(template: string, params?: MessageParams): string {
  if (!params) return template.replace(/'\{'/g, '{');
  // Two-pass: first interpolate {name}, then unescape '{'. This ordering
  // means params named like '{' do not collide; placeholders are matched
  // strictly as `{<lowerCamelCase ASCII>}`.
  const interpolated = template.replace(
    /\{([a-zA-Z][a-zA-Z0-9]*)\}/g,
    (match, name: string) => {
      if (Object.prototype.hasOwnProperty.call(params, name)) {
        const val = params[name];
        return val == null ? match : String(val);
      }
      return match;
    },
  );
  return interpolated.replace(/'\{'/g, '{');
}

/**
 * Look up a key in `locale`, falling back to en-US, then to `[missing:key]`
 * (dev) or the key itself (prod). Calls the missing-key hook in either case.
 */
export function lookup(
  key: string,
  locale: LocaleCode,
  options?: { source?: string },
): string {
  const primary = catalogs.get(locale);
  const fromPrimary = primary?.[key];
  if (typeof fromPrimary === 'string') return fromPrimary;

  // Fallback path. Report once.
  const fallback = catalogs.get(SOURCE_LOCALE);
  const fromFallback = fallback?.[key];
  if (typeof fromFallback === 'string') {
    // Missing in the selected locale, but covered by en-US. CI cares only
    // when *en-US* is missing the key; we still emit a softer hook so QA
    // can spot incomplete locales.
    if (locale !== SOURCE_LOCALE) {
      missingKeyHandler?.({ key, locale, source: options?.source });
    }
    return fromFallback;
  }

  // Truly missing — even en-US lacks this key. This is a bug.
  missingKeyHandler?.({ key, locale, source: options?.source });
  return isProd() ? key : `[missing:${key}]`;
}

/**
 * Resolve and interpolate. The runtime entry point that `index.ts#t` calls.
 */
export function resolve(
  key: string,
  locale: LocaleCode,
  params?: MessageParams,
  options?: { source?: string },
): string {
  return interpolate(lookup(key, locale, options), params);
}
