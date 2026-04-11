/**
 * Skin abstraction for ValueControl renderers.
 *
 * A Skin provides Svelte component overrides for each renderer type.
 * When a skin is set on ValueControl, it delegates rendering to the
 * skin's component instead of the built-in renderer.
 */
import type { Component } from 'svelte';

/** Props that every skin renderer receives (same as built-in renderers). */
export interface SkinRendererProps {
  value: number;
  min: number;
  max: number;
  step: number;
  defaultValue?: number;
  fineStepDivisor?: number;
  label: string;
  displayFn?: (v: number) => string;
  accentColor?: string;
  fillColor?: string;
  fillGradient?: string[];
  trackColor?: string;
  showValue?: boolean;
  showLabel?: boolean;
  compact?: boolean;
  variant?: 'modern' | 'hardware' | 'hardware-illuminated';
  onChange: (value: number) => void;
  debounceMs?: number;
  disabled?: boolean;
  unit?: string;
  shortcutHint?: string | null;
  title?: string | null;
}

/** Extra props for knob skin renderers. */
export interface KnobSkinRendererProps extends SkinRendererProps {
  arcAngle?: number;
  tickCount?: number;
  tickLabels?: string[];
}

/** A skin provides component overrides per renderer type. */
export interface Skin {
  name: string;
  knob?: Component<KnobSkinRendererProps>;
  hbar?: Component<SkinRendererProps>;
  bipolar?: Component<SkinRendererProps>;
}
