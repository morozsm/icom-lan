/**
 * Cross-app locale preference contract — Core (reader) side.
 *
 * Strategy reference: glossary §5.4 (Cross-app locale precedence). The full
 * contract — envelope shape, transport surfaces, precedence semantics — is
 * documented in `docs/i18n/locale-contract.md`. Pro (RP-ML-012B) writes the
 * envelope; this module reads it.
 *
 * Design constraints (RP-ML-012A):
 *   - Layered on top of the existing i18n runtime/store. The resolver
 *     (`runtime.ts`, `plural.ts`, `pseudo.ts`) is NOT modified.
 *   - Standalone Core (no Pro hint) must behave exactly as before. This
 *     module is a no-op in that case.
 *   - No Tower dependency; no network. Local-first.
 *   - Boot-only signal: query/storage are read once at module init, not on
 *     every navigation, so a later in-UI locale change is not stomped.
 *   - External-source apply uses `_applyExternalLocale` and deliberately
 *     does NOT persist to the explicit Core key `rigplane.i18n.locale`.
 *     That key remains owned by the LanguageSelector and survives Pro
 *     reinstalls.
 */

import { _applyExternalLocale, isSupported, SUPPORTED_LOCALES } from './store.svelte';
import type { LocaleCode } from './types';

/** The five sources surfaceable from the precedence resolver. */
export type LocaleSourceKind =
  | 'pro-shell-query'
  | 'pro-shell-storage'
  | 'core-explicit'
  | 'browser'
  | 'fallback';

/** A locale paired with its provenance. */
export interface LocaleSource {
  locale: LocaleCode;
  source: LocaleSourceKind;
}

/**
 * `localStorage` key Pro writes the JSON envelope to. Versioned so that a
 * future shape change can coexist with old Pro installs.
 */
export const PRO_LOCALE_STORAGE_KEY = 'rigplane.i18n.proLocale.v1';

/** URL query parameter name Pro appends to launched Core URLs. */
export const PRO_LOCALE_QUERY_PARAM = 'locale';

/**
 * Envelope as written by Pro. The reader treats every field except
 * `locale` as informational — `locale` is validated against Core's own
 * bundled `SUPPORTED_LOCALES`.
 */
export interface LocalePreferenceEnvelope {
  locale: string;
  source?: 'pro-shell' | 'core-explicit' | 'browser' | 'fallback';
  updatedAt?: string;
  supportedLocales?: readonly string[];
}

/**
 * Parse `?locale=<bcp47>` from a URL (or `window.location` by default).
 * Returns null when the parameter is absent, malformed, or names a locale
 * Core does not bundle.
 */
export function readLocaleFromQuery(url?: string | URL): LocaleSource | null {
  let search: URLSearchParams;
  try {
    if (url !== undefined) {
      search = new URL(typeof url === 'string' ? url : url.toString()).searchParams;
    } else if (typeof window !== 'undefined' && window.location) {
      search = new URLSearchParams(window.location.search);
    } else {
      return null;
    }
  } catch {
    return null;
  }
  const raw = search.get(PRO_LOCALE_QUERY_PARAM);
  if (raw == null) return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  if (!isSupported(trimmed)) return null;
  return { locale: trimmed, source: 'pro-shell-query' };
}

/**
 * Parse the JSON envelope at `localStorage[PRO_LOCALE_STORAGE_KEY]`.
 * Silently returns null for missing/malformed envelopes or for a locale
 * that does not exist in Core's bundled `SUPPORTED_LOCALES`.
 */
export function readLocaleFromExternalStorage(): LocaleSource | null {
  if (typeof localStorage === 'undefined') return null;
  let raw: string | null;
  try {
    raw = localStorage.getItem(PRO_LOCALE_STORAGE_KEY);
  } catch {
    return null;
  }
  if (raw == null) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== 'object') return null;
  const envelope = parsed as Partial<LocalePreferenceEnvelope>;
  if (typeof envelope.locale !== 'string') return null;
  const candidate = envelope.locale.trim();
  if (!candidate || !isSupported(candidate)) return null;
  return { locale: candidate, source: 'pro-shell-storage' };
}

/**
 * Resolve the initial locale by applying the cross-app precedence rules.
 *
 *   1. URL `?locale=` (Pro launch hint).
 *   2. `localStorage[PRO_LOCALE_STORAGE_KEY]` envelope (Pro shared key).
 *   3. Explicit Core setting (existing `rigplane.i18n.locale`).
 *   4. Browser locale (narrowed to supported).
 *   5. en-US fallback.
 *
 * Rungs 3–5 are handled by the existing store; this function only reports
 * which Pro rung (if any) is active. Callers use the returned source to
 * decide whether to override the store via `_applyExternalLocale`.
 *
 * Pure: does not touch the store. Safe to call from tests.
 */
export function resolveInitialLocale(url?: string | URL): LocaleSource | null {
  return readLocaleFromQuery(url) ?? readLocaleFromExternalStorage();
}

/**
 * Apply the Pro-side hint to the i18n store, if any. Idempotent.
 *
 * Called once at module init from `index.ts`. Returns the resolved Pro
 * source for diagnostics; returns null when there is no Pro hint and the
 * store keeps its standalone-resolved value.
 *
 * Never persists to `rigplane.i18n.locale`. The user's stored Core
 * preference survives the Pro override.
 */
export function applyContractOnBoot(url?: string | URL): LocaleSource | null {
  const hint = resolveInitialLocale(url);
  if (hint) {
    _applyExternalLocale(hint.locale);
  }
  if (isDevMode()) {
    // Best-effort dev diagnostic so manual QA can see which rung resolved.
    // Silent in production builds.
    // eslint-disable-next-line no-console
    console.info(
      `[i18n] locale-contract: ${hint ? `applied ${hint.locale} from ${hint.source}` : 'no Pro hint; store retained'}`,
    );
  }
  return hint;
}

function isDevMode(): boolean {
  try {
    return !(import.meta as ImportMeta & { env?: { PROD?: boolean } }).env?.PROD;
  } catch {
    return false;
  }
}

export { SUPPORTED_LOCALES };
