/**
 * LCD chrome adapter — façade over LCD skin-local UI state.
 *
 * Wraps `lib/stores/lcd-contrast.svelte` + `lib/stores/lcd-display-mode.svelte`
 * so panels under `components-v2/panels/lcd/` can consume LCD chrome state
 * through the runtime adapter layer instead of importing stores directly
 * (CLAUDE.md → "Frontend layering").
 *
 * LCD chrome state is browser-local, persisted in `localStorage`. It has no
 * radio-runtime equivalent — this adapter is mechanical pass-through.
 *
 * Long-term home (lib/stores vs skins/amber-lcd/state) is the audit's
 * Open Question #1; deferred. See
 * `docs/plans/2026-04-29-panel-adapter-migration.md` Cluster C.
 *
 * Tier 2 batch 4 of #1063. Issue #1247.
 */

import {
  LCD_CONTRAST_PRESETS,
  applyLcdContrast,
  getLcdContrastPreset,
  setLcdContrastPreset,
  stepLcdContrast,
  type LcdContrastPreset,
} from '$lib/stores/lcd-contrast.svelte';
import {
  LCD_DISPLAY_MODES,
  getLcdDisplayMode,
  setLcdDisplayMode,
  type LcdDisplayMode,
} from '$lib/stores/lcd-display-mode.svelte';

// ── Contrast facet ──

export {
  LCD_CONTRAST_PRESETS,
  applyLcdContrast,
  getLcdContrastPreset,
  setLcdContrastPreset,
  stepLcdContrast,
};
export type { LcdContrastPreset };

// ── Display-mode facet ──

export {
  LCD_DISPLAY_MODES,
  getLcdDisplayMode,
  setLcdDisplayMode,
};
export type { LcdDisplayMode };
