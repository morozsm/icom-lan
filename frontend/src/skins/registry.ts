/**
 * Skin registry — resolves which skin to load based on capabilities and user preference.
 *
 * Each skin is a top-level Svelte component that composes semantic components
 * into a layout. Skins are lazy-loaded to keep the initial bundle small.
 *
 * @see docs/plans/2026-04-12-target-frontend-architecture.md
 */

import type { Component } from 'svelte';
import type { Capabilities } from '$lib/types/capabilities';
import type { LayoutMode } from '$lib/stores/layout.svelte';

export type SkinId = 'desktop-v2' | 'lcd-cockpit' | 'lcd-scope' | 'mobile';

/**
 * Persisted skin IDs include the legacy `amber-lcd` alias, which routes to
 * `lcd-cockpit`. Kept indefinitely for backwards compatibility with stored
 * user preferences (see docs/plans/2026-04-19-lcd-twin-skins.md §2).
 */
export type PersistedSkinId = SkinId | 'amber-lcd';

export interface SkinResolutionContext {
  capabilities: Capabilities | null;
  layoutPreference: LayoutMode;
  isMobile: boolean;
  hasAnyScope: boolean;
}

/**
 * Determine which skin to use based on context.
 *
 * Rules:
 * - Mobile viewport → mobile skin
 * - User forced 'lcd' → lcd-cockpit (default LCD variant)
 * - User forced 'standard' → desktop-v2
 * - Auto: use desktop-v2 if any scope is available, lcd-cockpit otherwise
 */
export function resolveSkinId(ctx: SkinResolutionContext): SkinId {
  if (ctx.isMobile) return 'mobile';
  if (ctx.layoutPreference === 'lcd') return 'lcd-cockpit';
  if (ctx.layoutPreference === 'standard') return 'desktop-v2';
  // auto: scope available → desktop, otherwise LCD
  return ctx.hasAnyScope ? 'desktop-v2' : 'lcd-cockpit';
}

/**
 * Lazy-load a skin component by ID.
 *
 * Returns the default export of the skin's entry Svelte component.
 * Skins are code-split — only the active skin is loaded.
 *
 * Phase 0 of the twin-skin epic (#887): both `lcd-cockpit` and `lcd-scope`
 * point at the existing `LcdSkin.svelte` until dedicated wrappers land.
 * The legacy `amber-lcd` alias is accepted via `resolvePersistedSkinId()`.
 */
const SKIN_LOADERS: Record<SkinId, () => Promise<{ default: Component }>> = {
  'desktop-v2': () => import('./desktop-v2/DesktopSkin.svelte'),
  'lcd-cockpit': () => import('./amber-lcd/LcdSkin.svelte'),
  'lcd-scope': () => import('./amber-lcd/LcdSkin.svelte'),
  'mobile': () => import('./mobile/MobileSkin.svelte'),
};

/**
 * Normalize a persisted skin ID, mapping the legacy `amber-lcd` alias to
 * `lcd-cockpit`. Use this when reading from localStorage or other stored
 * preferences.
 */
export function resolvePersistedSkinId(id: PersistedSkinId): SkinId {
  if (id === 'amber-lcd') return 'lcd-cockpit';
  return id;
}

export async function loadSkin(id: SkinId): Promise<Component> {
  return (await SKIN_LOADERS[id]).default;
}
