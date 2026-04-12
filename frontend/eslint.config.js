/**
 * ESLint flat config — frontend architecture guardrails.
 *
 * Enforces import boundaries defined in ADR 2026-04-12:
 *   - Presentational components (panels, layout, skins, semantic, primitives)
 *     must NOT import runtime/transport modules directly.
 *   - Only wiring/ (adapter layer) and lib/ internals may import these.
 *
 * @see docs/plans/2026-04-12-target-frontend-architecture.md
 */

import tsParser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import sveltePlugin from 'eslint-plugin-svelte';
import svelteParser from 'svelte-eslint-parser';

/** Modules that only the runtime/wiring layer may import. */
const FORBIDDEN_RUNTIME_IMPORTS = {
  paths: [
    {
      name: '$lib/audio/audio-manager',
      message:
        'Presentation components must not import audioManager directly. ' +
        'Use callback props from the adapter/wiring layer instead. ' +
        'See ADR 2026-04-12.',
    },
  ],
  patterns: [
    {
      group: ['$lib/transport/*'],
      message:
        'Presentation components must not import transport modules (sendCommand, getChannel). ' +
        'Use callback props from the adapter/wiring layer instead. ' +
        'See ADR 2026-04-12.',
    },
  ],
};

export default [
  // ── Global ignores ──
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      '.svelte-kit/**',
      '**/*.config.js',
      '**/*.config.ts',
    ],
  },

  // ── TypeScript files ──
  {
    files: ['src/**/*.ts'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    linterOptions: {
      reportUnusedDisableDirectives: 'off',
    },
    rules: {},
  },

  // ── Svelte files ──
  {
    files: ['src/**/*.svelte'],
    languageOptions: {
      parser: svelteParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
    plugins: {
      svelte: sveltePlugin,
    },
    linterOptions: {
      reportUnusedDisableDirectives: 'off',
    },
    rules: {},
  },

  // ── Import boundary: presentation components ──
  // Panels, layouts, LCD, skins — must NOT import runtime/transport directly.
  {
    files: [
      'src/components-v2/panels/**/*.svelte',
      'src/components-v2/panels/**/*.ts',
      'src/components-v2/layout/**/*.svelte',
      'src/components-v2/layout/**/*.ts',
      'src/components-v2/display/**/*.svelte',
      'src/components-v2/meters/**/*.svelte',
      'src/components-v2/vfo/**/*.svelte',
      'src/components-v2/controls/**/*.svelte',
      // Future layers:
      'src/semantic/**/*.svelte',
      'src/skins/**/*.svelte',
      'src/primitives/**/*.svelte',
    ],
    rules: {
      'no-restricted-imports': ['error', FORBIDDEN_RUNTIME_IMPORTS],
    },
  },

  // ── Legacy V1 components — same restrictions ──
  {
    files: [
      'src/components/**/*.svelte',
      'src/components/**/*.ts',
    ],
    rules: {
      'no-restricted-imports': ['warn', FORBIDDEN_RUNTIME_IMPORTS],
    },
  },

  // ── Tests may import anything (mocking is legitimate) ──
  {
    files: ['src/**/__tests__/**', 'src/**/*.test.ts'],
    rules: {
      'no-restricted-imports': 'off',
    },
  },
];
