export type BadgeColor = 'cyan' | 'orange' | 'red' | 'green' | 'muted';

export interface BadgeProps {
  active: boolean;
  color: BadgeColor;
  compact: boolean;
  clickable: boolean;
}

interface ColorTokens {
  bg: string;
  border: string;
  text: string;
  glow: string;
}

const COLOR_ACTIVE: Record<BadgeColor, ColorTokens> = {
  cyan:   { bg: 'var(--v2-badge-cyan-bg)', border: 'var(--v2-badge-cyan-border)', text: 'var(--v2-badge-cyan-text)', glow: 'var(--v2-badge-cyan-glow)' },
  orange: { bg: 'var(--v2-badge-orange-bg)', border: 'var(--v2-badge-orange-border)', text: 'var(--v2-badge-orange-text)', glow: 'var(--v2-badge-orange-glow)' },
  red:    { bg: 'var(--v2-badge-red-bg)', border: 'var(--v2-badge-red-border)', text: 'var(--v2-badge-red-text)', glow: 'var(--v2-badge-red-glow)' },
  green:  { bg: 'var(--v2-badge-green-bg)', border: 'var(--v2-badge-green-border)', text: 'var(--v2-badge-green-text)', glow: 'var(--v2-badge-green-glow)' },
  muted:  { bg: 'var(--v2-badge-muted-bg)', border: 'var(--v2-badge-muted-border)', text: 'var(--v2-badge-muted-text)', glow: 'var(--v2-badge-muted-glow)' },
};

export interface BadgeControlButtonVars {
  accent: string;
  text: string;
}

export function getBadgeControlButtonVars(color: BadgeColor): BadgeControlButtonVars {
  const tokens = COLOR_ACTIVE[color];
  return {
    accent: tokens.border,
    text: tokens.text,
  };
}

export interface BadgeStyle {
  background: string;
  border: string;
  color: string;
  boxShadow: string;
  height: string;
  padding: string;
  fontSize: string;
  cursor: string;
}

export function computeBadgeStyle({ active, color, compact, clickable }: BadgeProps): BadgeStyle {
  const c = COLOR_ACTIVE[color] || COLOR_ACTIVE['cyan']; // Fallback to cyan if invalid color

  return {
    background: active ? c.bg          : 'transparent',
    border:     active ? `1px solid ${c.border}` : '1px solid var(--v2-badge-inactive-border)',
    color:      active ? c.text        : 'var(--v2-badge-inactive-text)',
    boxShadow:  active ? `0 0 0 1px ${c.glow}` : 'none',
    height:     compact ? '16px'       : '22px',
    padding:    compact ? '0 5px'      : '0 8px',
    fontSize:   compact ? '7px'        : '9px',
    cursor:     clickable ? 'pointer'  : 'default',
  };
}

export function badgeStyleString(props: BadgeProps): string {
  const s = computeBadgeStyle(props);
  return [
    `background:${s.background}`,
    `border:${s.border}`,
    `color:${s.color}`,
    `box-shadow:${s.boxShadow}`,
    `height:${s.height}`,
    `padding:${s.padding}`,
    `font-size:${s.fontSize}`,
    `cursor:${s.cursor}`,
  ].join(';');
}
