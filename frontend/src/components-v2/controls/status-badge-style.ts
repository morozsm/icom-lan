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
  cyan:   { bg: '#123247', border: '#00D4FF', text: '#EAF7FF', glow: 'rgba(0,212,255,0.14)' },
  orange: { bg: '#442506', border: '#FF8B2D', text: '#FFF0E4', glow: 'rgba(255,139,45,0.14)' },
  red:    { bg: '#571812', border: '#FF5D46', text: '#FFF0ED', glow: 'rgba(255,93,70,0.14)' },
  green:  { bg: '#143922', border: '#4ED37B', text: '#F0FFF6', glow: 'rgba(78,211,123,0.14)' },
  muted:  { bg: '#151d27', border: '#384a5d', text: '#A6B7C8', glow: 'rgba(77,96,116,0.10)' },
};

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
  const c = COLOR_ACTIVE[color];

  return {
    background: active ? c.bg          : 'transparent',
    border:     active ? `1px solid ${c.border}` : '1px solid #1A2028',
    color:      active ? c.text        : '#7C90A4',
    boxShadow:  active ? `0 0 0 1px ${c.glow}` : 'none',
    height:     compact ? '15px'       : '19px',
    padding:    compact ? '0 4px'      : '0 7px',
    fontSize:   compact ? '7px'        : '8px',
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
