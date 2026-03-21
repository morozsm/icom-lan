/**
 * Control Button Types
 */

export type IndicatorColor = 'cyan' | 'green' | 'amber' | 'red' | 'orange' | 'white';

export type IndicatorStyle = 'ring' | 'dot' | 'edge-bottom' | 'edge-left' | 'edge-sides' | 'fill';

export type GlowVariant = 'color' | 'white' | 'warm';

export type ButtonSurface = 'flat' | 'hardware';

export interface BaseButtonProps {
  /** Button label */
  label?: string;
  /** Active state */
  active?: boolean;
  /** Disabled state */
  disabled?: boolean;
  /** Compact size variant */
  compact?: boolean;
  /** Tooltip / accessible title */
  title?: string | null;
  /** Shortcut hint rendered as data-shortcut-hint attribute */
  shortcutHint?: string | null;
  /** Click handler */
  onclick?: (event: MouseEvent) => void;
}

export interface DotButtonProps extends BaseButtonProps {
  /** Indicator color */
  color?: IndicatorColor;
  /** Glow variant (defaults to 'color') */
  glow?: GlowVariant;
}

export interface FillButtonProps extends BaseButtonProps {
  /** Fill color */
  color?: IndicatorColor;
}

export interface HardwareButtonProps extends BaseButtonProps {
  /** Indicator style (dot, edge-left, edge-bottom) */
  indicator?: 'dot' | 'edge-left' | 'edge-bottom';
  /** Indicator color */
  color?: IndicatorColor;
}

export interface HardwarePlainButtonProps extends BaseButtonProps {
  /** Glow variant (defaults to 'warm') */
  glow?: 'white' | 'warm';
}
