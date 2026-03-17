import { describe, it, expect } from 'vitest';
import { computeBadgeStyle, badgeStyleString } from '../status-badge-style';
import type { BadgeProps } from '../status-badge-style';

// ── Helpers ────────────────────────────────────────────────────────────────

function active(color: BadgeProps['color'] = 'cyan', compact = false): BadgeProps {
  return { active: true, color, compact, clickable: false };
}

function inactive(color: BadgeProps['color'] = 'cyan', compact = false): BadgeProps {
  return { active: false, color, compact, clickable: false };
}

// ── Inactive state (universal) ─────────────────────────────────────────────

describe('inactive state', () => {
  it('has transparent background regardless of color', () => {
    for (const color of ['cyan', 'orange', 'red', 'green', 'muted'] as const) {
      expect(computeBadgeStyle(inactive(color)).background).toBe('transparent');
    }
  });

  it('has dimmed border #1A2028', () => {
    expect(computeBadgeStyle(inactive()).border).toBe('1px solid #1A2028');
  });

  it('has dimmed text color #4D6074', () => {
    expect(computeBadgeStyle(inactive()).color).toBe('#4D6074');
  });

  it('has no box-shadow', () => {
    expect(computeBadgeStyle(inactive()).boxShadow).toBe('none');
  });
});

// ── Active state — cyan ────────────────────────────────────────────────────

describe('active cyan', () => {
  it('has background #0D3B66', () => {
    expect(computeBadgeStyle(active('cyan')).background).toBe('#0D3B66');
  });

  it('has border #00D4FF', () => {
    expect(computeBadgeStyle(active('cyan')).border).toBe('1px solid #00D4FF');
  });

  it('has white text', () => {
    expect(computeBadgeStyle(active('cyan')).color).toBe('#FFFFFF');
  });

  it('has cyan glow', () => {
    expect(computeBadgeStyle(active('cyan')).boxShadow).toContain('rgba(0,212,255');
  });
});

// ── Active state — orange ──────────────────────────────────────────────────

describe('active orange', () => {
  it('has background #3D2200', () => {
    expect(computeBadgeStyle(active('orange')).background).toBe('#3D2200');
  });

  it('has border #FF6A00', () => {
    expect(computeBadgeStyle(active('orange')).border).toBe('1px solid #FF6A00');
  });

  it('has orange glow', () => {
    expect(computeBadgeStyle(active('orange')).boxShadow).toContain('rgba(255,106,0');
  });
});

// ── Active state — red ─────────────────────────────────────────────────────

describe('active red', () => {
  it('has background #3D0A0A', () => {
    expect(computeBadgeStyle(active('red')).background).toBe('#3D0A0A');
  });

  it('has border #FF2020', () => {
    expect(computeBadgeStyle(active('red')).border).toBe('1px solid #FF2020');
  });

  it('has red glow', () => {
    expect(computeBadgeStyle(active('red')).boxShadow).toContain('rgba(255,32,32');
  });
});

// ── Active state — green ───────────────────────────────────────────────────

describe('active green', () => {
  it('has background #0A3D1A', () => {
    expect(computeBadgeStyle(active('green')).background).toBe('#0A3D1A');
  });

  it('has border #00CC66', () => {
    expect(computeBadgeStyle(active('green')).border).toBe('1px solid #00CC66');
  });

  it('has green glow', () => {
    expect(computeBadgeStyle(active('green')).boxShadow).toContain('rgba(0,204,102');
  });
});

// ── Active state — muted ───────────────────────────────────────────────────

describe('active muted', () => {
  it('has background #1A2028', () => {
    expect(computeBadgeStyle(active('muted')).background).toBe('#1A2028');
  });

  it('has border #4D6074', () => {
    expect(computeBadgeStyle(active('muted')).border).toBe('1px solid #4D6074');
  });

  it('has muted text color #8DA2B8', () => {
    expect(computeBadgeStyle(active('muted')).color).toBe('#8DA2B8');
  });

  it('has muted glow', () => {
    expect(computeBadgeStyle(active('muted')).boxShadow).toContain('rgba(77,96,116');
  });
});

// ── Compact mode ───────────────────────────────────────────────────────────

describe('compact mode', () => {
  it('compact height is 16px', () => {
    expect(computeBadgeStyle({ ...active(), compact: true }).height).toBe('16px');
  });

  it('compact font-size is 7px', () => {
    expect(computeBadgeStyle({ ...active(), compact: true }).fontSize).toBe('7px');
  });

  it('compact padding is 0 5px', () => {
    expect(computeBadgeStyle({ ...active(), compact: true }).padding).toBe('0 5px');
  });

  it('full height is 22px', () => {
    expect(computeBadgeStyle({ ...active(), compact: false }).height).toBe('22px');
  });

  it('full font-size is 9px', () => {
    expect(computeBadgeStyle({ ...active(), compact: false }).fontSize).toBe('9px');
  });

  it('full padding is 0 8px', () => {
    expect(computeBadgeStyle({ ...active(), compact: false }).padding).toBe('0 8px');
  });
});

// ── Cursor / clickable ─────────────────────────────────────────────────────

describe('cursor', () => {
  it('pointer when clickable', () => {
    expect(computeBadgeStyle({ ...active(), clickable: true }).cursor).toBe('pointer');
  });

  it('default when not clickable', () => {
    expect(computeBadgeStyle({ ...active(), clickable: false }).cursor).toBe('default');
  });
});

// ── badgeStyleString ───────────────────────────────────────────────────────

describe('badgeStyleString', () => {
  it('returns semicolon-separated CSS properties', () => {
    const s = badgeStyleString(active('cyan'));
    expect(s).toContain('background:');
    expect(s).toContain('border:');
    expect(s).toContain('color:');
    expect(s).toContain('box-shadow:');
    expect(s).toContain('height:');
    expect(s).toContain('padding:');
    expect(s).toContain('font-size:');
    expect(s).toContain('cursor:');
  });

  it('inactive produces transparent background in string', () => {
    const s = badgeStyleString(inactive('cyan'));
    expect(s).toContain('background:transparent');
  });

  it('active cyan produces correct border in string', () => {
    const s = badgeStyleString(active('cyan'));
    expect(s).toContain('border:1px solid #00D4FF');
  });

  it('compact produces 16px height in string', () => {
    const s = badgeStyleString({ ...active(), compact: true });
    expect(s).toContain('height:16px');
  });
});
