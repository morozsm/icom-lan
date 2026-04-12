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

export type SkinId = 'desktop-v2' | 'amber-lcd' | 'mobile';

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
 * - User forced 'lcd' → amber-lcd
 * - User forced 'standard' → desktop-v2
 * - Auto: use desktop-v2 if any scope is available, amber-lcd otherwise
 */
export function resolveSkinId(ctx: SkinResolutionContext): SkinId {
  if (ctx.isMobile) return 'mobile';
  if (ctx.layoutPreference === 'lcd') return 'amber-lcd';
  if (ctx.layoutPreference === 'standard') return 'desktop-v2';
  // auto: scope available → desktop, otherwise LCD
  return ctx.hasAnyScope ? 'desktop-v2' : 'amber-lcd';
}

/**
 * Lazy-load a skin component by ID.
 *
 * Returns the default export of the skin's entry Svelte component.
 * Skins are code-split — only the active skin is loaded.
 */
const SKIN_LOADERS: Record<SkinId, () => Promise<{ default: Component }>> = {
  'desktop-v2': () => import('./desktop-v2/DesktopSkin.svelte'),
  'amber-lcd': () => import('./amber-lcd/LcdSkin.svelte'),
  'mobile': () => import('./mobile/MobileSkin.svelte'),
};

export async function loadSkin(id: SkinId): Promise<Component> {
  return (await SKIN_LOADERS[id]).default;
}
