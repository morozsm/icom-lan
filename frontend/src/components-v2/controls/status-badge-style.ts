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
  cyan:   { bg: '#0D3B66', border: '#00D4FF', text: '#FFFFFF', glow: 'rgba(0,212,255,0.14)' },
  orange: { bg: '#3D2200', border: '#FF6A00', text: '#FFF0E4', glow: 'rgba(255,106,0,0.14)' },
  red:    { bg: '#3D0A0A', border: '#FF2020', text: '#FFF0ED', glow: 'rgba(255,32,32,0.14)' },
  green:  { bg: '#0A3D1A', border: '#00CC66', text: '#F0FFF6', glow: 'rgba(0,204,102,0.14)' },
  muted:  { bg: '#1A2028', border: '#4D6074', text: '#8DA2B8', glow: 'rgba(77,96,116,0.10)' },
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
  const c = COLOR_ACTIVE[color];

  return {
    background: active ? c.bg          : 'transparent',
    border:     active ? `1px solid ${c.border}` : '1px solid #1A2028',
    color:      active ? c.text        : '#4D6074',
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
