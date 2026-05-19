/**
 * Pseudo-locale (`qps-ploc`) transform.
 *
 * Why runtime, not build-time:
 *   We chose a runtime transform layered on top of en-US (rather than
 *   shipping a precomputed `qps-ploc.json`) for three reasons:
 *
 *   1. The catalog is small and the transform is O(string length) — cost
 *      is negligible at render time.
 *   2. Build-time generation would have to track every new en-US key and
 *      keep a generated artifact in sync. A runtime transform cannot drift.
 *   3. Community contributors editing `en-US.json` automatically get
 *      pseudo-locale coverage for their additions, without learning a
 *      build step.
 *
 * Transformation rules (binding contract — strategy glossary §5.2):
 *   - Wrap every translated string in `⟦` and `⟧`. Missing wrappers in QA
 *     mean a string bypassed the catalog.
 *   - Substitute ASCII letters with diacritic forms.
 *   - Expand by >=35% with padding tokens to simulate European-language
 *     length.
 *   - Preserve `{placeholder}` runs verbatim — pseudo-locale does NOT
 *     interpolate placeholders into the transform.
 *   - Preserve the `'{'` literal-brace escape verbatim.
 *
 * Glossary tokens and protocol values are preserved by composing them at the
 * call site (the resolver pulls `glossary.callsign` etc. unchanged from
 * `en-US.json` once `qps-ploc` falls back, but pseudo-locale wraps the
 * returned string). For Phase 2, glossary preservation is delivered via
 * documented call-site composition (`t('glossary.callsign')` injected as a
 * params value, which the placeholder-skip rule below leaves untouched in
 * the transform).
 */

import type { Catalog, MessageParams } from './types';
import { interpolate, getCatalog } from './runtime';

const DIACRITIC_MAP: Record<string, string> = {
  a: 'á', b: 'ƀ', c: 'ç', d: 'đ', e: 'é', f: 'ƒ', g: 'ğ', h: 'ĥ',
  i: 'í', j: 'ĵ', k: 'ķ', l: 'ł', m: 'ɱ', n: 'ñ', o: 'ó', p: 'þ',
  q: 'ǫ', r: 'ŕ', s: 'š', t: 'ť', u: 'ú', v: 'ṽ', w: 'ŵ', x: 'ẋ',
  y: 'ý', z: 'ž',
  A: 'Á', B: 'Ɓ', C: 'Ç', D: 'Đ', E: 'É', F: 'Ƒ', G: 'Ğ', H: 'Ĥ',
  I: 'Í', J: 'Ĵ', K: 'Ķ', L: 'Ł', M: 'Ɱ', N: 'Ñ', O: 'Ó', P: 'Þ',
  Q: 'Ǫ', R: 'Ŕ', S: 'Š', T: 'Ť', U: 'Ú', V: 'Ṽ', W: 'Ŵ', X: 'Ẋ',
  Y: 'Ý', Z: 'Ž',
};

const EXPANSION_RATIO = 0.35;
const PAD_SEGMENT = '~';

/**
 * Apply the pseudo-locale transform to a single string drawn from en-US.
 * The string may contain `{placeholder}` runs and `'{'` literal-brace
 * escapes — both are preserved verbatim.
 */
export function pseudoize(source: string): string {
  if (source.length === 0) return '⟦⟧';

  // Tokenize: placeholders and literal-brace escapes are passthrough atoms;
  // everything else is letter-substitutable text.
  const PLACEHOLDER_OR_ESCAPE = /(\{[a-zA-Z][a-zA-Z0-9]*\}|'\{')/g;
  const parts = source.split(PLACEHOLDER_OR_ESCAPE);

  let baseLen = 0;
  const transformed = parts.map((part) => {
    if (!part) return '';
    if (PLACEHOLDER_OR_ESCAPE.test(part)) {
      // Reset lastIndex because we used the same regex above.
      PLACEHOLDER_OR_ESCAPE.lastIndex = 0;
      return part;
    }
    PLACEHOLDER_OR_ESCAPE.lastIndex = 0;
    baseLen += part.length;
    let buf = '';
    for (const ch of part) {
      buf += DIACRITIC_MAP[ch] ?? ch;
    }
    return buf;
  });

  // Compute padding required to hit >=35% expansion based on the
  // substitutable text length (the brackets already add 2 chars; we count
  // them toward the budget).
  const required = Math.ceil(baseLen * EXPANSION_RATIO);
  const padLength = Math.max(required, 1);
  const padding = ' ' + PAD_SEGMENT.repeat(padLength);

  return `⟦${transformed.join('')}${padding}⟧`;
}

/**
 * Resolve a key under `qps-ploc`. Reads the en-US catalog directly (not the
 * `qps-ploc` catalog — there is no such file) and transforms the result.
 * Missing keys return the same `[missing:key]` marker the resolver would.
 */
export function resolvePseudo(key: string, params?: MessageParams): string {
  const source = getCatalog('en-US');
  const value = source?.[key];
  if (typeof value !== 'string') {
    return `[missing:${key}]`;
  }
  // Interpolate AFTER pseudoizing the template, so placeholder atoms inside
  // the source survive (and so the interpolated values themselves are not
  // diacritic-substituted — they may be brand names, frequencies, etc.).
  const transformed = pseudoize(value);
  return interpolate(transformed, params);
}

/** Lightweight tap for tests that want to inspect the transformation. */
export function _stripPseudo(s: string): string {
  return s.replace(/^⟦/, '').replace(/[~ ]+⟧$/, '').replace(/⟧$/, '');
}

/** Exposed for tests / tooling. */
export function pseudoCatalog(): Catalog {
  const out: Catalog = {};
  const en = getCatalog('en-US');
  if (!en) return out;
  for (const k of Object.keys(en)) {
    out[k] = pseudoize(en[k]);
  }
  return out;
}
