/**
 * ESLint flat config — frontend architecture guardrails (v2 layering only).
 *
 * Enforces import boundaries defined in ADR 2026-04-12:
 *   - Presentational components (panels, layout, skins, semantic, primitives)
 *     must NOT import runtime/transport modules directly (alias or relative).
 *   - Only wiring/ (adapter layer) and lib/ internals may import these.
 *   - lib/runtime/** must NOT import from components-v2/ (no circular deps).
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
      group: ['$lib/transport/*', '**/lib/transport/*'],
      message:
        'Presentation components must not import transport modules (sendCommand, getChannel). ' +
        'Use callback props from the adapter/wiring layer instead. ' +
        'See ADR 2026-04-12.',
    },
    {
      group: ['**/lib/audio/audio-manager'],
      message:
        'Presentation components must not import audioManager directly (relative paths included). ' +
        'Use callback props from the adapter/wiring layer instead. ' +
        'See ADR 2026-04-12.',
    },
  ],
};

/**
 * Panel-specific lockdown (Tier 2 — issue #1241).
 *
 * After all 18 panels migrated to adapters across batches 1-5
 * (#1244, #1245, #1246, #1247, #1248), the boundary is enforced at lint time.
 * Panels must route store reads through `lib/runtime/adapters/*` (state + commands).
 *
 * Note: this is panel-only on purpose. Other presentation layers (layout, display,
 * meters, vfo, controls, skins) have their own Tier-N migrations tracked under #1063.
 */
const FORBIDDEN_PANEL_IMPORTS = {
  patterns: [
    {
      group: ['$lib/stores/*', '$lib/stores', '**/lib/stores/*', '**/lib/stores'],
      message:
        'Panels must not import from $lib/stores/* — route via lib/runtime/adapters/* instead. ' +
        'See docs/plans/2026-04-29-panel-adapter-migration.md and ADR 2026-04-12.',
    },
    {
      group: ['$lib/transport/*', '**/lib/transport/*'],
      message:
        'Presentation components must not import transport modules (sendCommand, getChannel). ' +
        'Use callback props from the adapter/wiring layer instead. ' +
        'See ADR 2026-04-12.',
    },
    {
      group: ['**/lib/audio/audio-manager'],
      message:
        'Presentation components must not import audioManager directly (relative paths included). ' +
        'Use callback props from the adapter/wiring layer instead. ' +
        'See ADR 2026-04-12.',
    },
  ],
  paths: [
    {
      name: '$lib/audio/audio-manager',
      message:
        'Presentation components must not import audioManager directly. ' +
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
  // Panels, layouts, LCD, skins, and app entry — must NOT import runtime/transport directly.
  {
    files: [
      'src/App.svelte',
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

  // ── Import boundary: panels (Tier 2 lockdown — issue #1241) ──
  // Adds `$lib/stores/*` to the panel-specific ban list. All 18 panels were migrated
  // to adapters across batches 1-5 (#1244, #1245, #1246, #1247, #1248); this block
  // freezes the boundary so it cannot regress. Other presentation layers retain the
  // looser FORBIDDEN_RUNTIME_IMPORTS rule until their own tier migrates (#1063).
  {
    files: [
      'src/components-v2/panels/**/*.svelte',
      'src/components-v2/panels/**/*.ts',
    ],
    rules: {
      'no-restricted-imports': ['error', FORBIDDEN_PANEL_IMPORTS],
    },
  },

  // ── Import boundary: lib/runtime isolation ──
  // lib/runtime must NOT import from components-v2 to prevent circular dependencies.
  // See ADR 2026-04-12 and issue #1005.
  {
    files: [
      'src/lib/runtime/**/*.ts',
      'src/lib/runtime/**/*.svelte',
      'src/lib/runtime/**/*.svelte.ts',
    ],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['**/components-v2/**'],
              message:
                'lib/runtime must not import from components-v2. ' +
                'Use lib/runtime/props/ or lib/runtime/commands/ instead. ' +
                'See ADR 2026-04-12.',
            },
          ],
        },
      ],
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
