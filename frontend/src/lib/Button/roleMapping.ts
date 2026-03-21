/**
 * Role → Family Mapping
 *
 * Maps semantic roles to visual families for a given theme or design preset.
 * This is the minimal first-pass model for #343.
 *
 * Semantic roles (what a control means):
 *   status-toggle  — interactive, sustained on/off state (VOX, NB, RIT, …)
 *   action-button  — momentary command, no sustained state (CLEAR, TUNE, RESET, …)
 *
 * Visual families (how a control is rendered):
 *   fill           — FillButton
 *   dot            — DotButton
 *   hardware-plain — HardwarePlainButton + warm glow
 *   hardware       — HardwareButton (with explicit indicator/color)
 *
 * A RoleMapping does NOT replace the component library.
 * It is a lookup table used by the demo/control-lab (and eventually by
 * theme-aware wrappers) to select the right visual family per role.
 */

export type VisualFamily = 'fill' | 'dot' | 'hardware-plain' | 'hardware';

export interface RoleMapping {
  /** Display name for the preset */
  readonly name: string;
  /** Visual family to use for status-toggle role */
  readonly statusToggle: VisualFamily;
  /** Visual family to use for action-button role */
  readonly actionButton: VisualFamily;
}

/**
 * Default: full fill color for both roles.
 * Current recommended mapping after StatusBadge migration.
 */
export const MAPPING_DEFAULT: RoleMapping = {
  name: 'default',
  statusToggle: 'fill',
  actionButton: 'fill',
};

/**
 * Hardware: warm-glow incandescent for both roles.
 * Vintage / skeuomorphic instrument-panel theme.
 */
export const MAPPING_HARDWARE: RoleMapping = {
  name: 'hardware',
  statusToggle: 'hardware-plain',
  actionButton: 'hardware-plain',
};

/**
 * Minimal: dot indicators for both roles.
 * Compact, low-visual-weight panel theme.
 */
export const MAPPING_MINIMAL: RoleMapping = {
  name: 'minimal',
  statusToggle: 'dot',
  actionButton: 'dot',
};

/**
 * Mixed: fills for sustained state, dots for momentary actions.
 * Most explicitly demonstrates the role split — the two roles
 * get visually distinct families so the semantic difference is legible.
 */
export const MAPPING_MIXED: RoleMapping = {
  name: 'mixed',
  statusToggle: 'fill',
  actionButton: 'dot',
};

export const PRESET_MAPPINGS: readonly RoleMapping[] = [
  MAPPING_DEFAULT,
  MAPPING_HARDWARE,
  MAPPING_MINIMAL,
  MAPPING_MIXED,
] as const;
