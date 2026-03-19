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

  it('has dimmed border via token', () => {
    expect(computeBadgeStyle(inactive()).border).toBe('1px solid var(--v2-badge-inactive-border)');
  });

  it('has dimmed text color via token', () => {
    expect(computeBadgeStyle(inactive()).color).toBe('var(--v2-badge-inactive-text)');
  });

  it('has no box-shadow', () => {
    expect(computeBadgeStyle(inactive()).boxShadow).toBe('none');
  });
});

// ── Active state — cyan ────────────────────────────────────────────────────

describe('active cyan', () => {
  it('has background via token', () => {
    expect(computeBadgeStyle(active('cyan')).background).toBe('var(--v2-badge-cyan-bg)');
  });

  it('has border via token', () => {
    expect(computeBadgeStyle(active('cyan')).border).toBe('1px solid var(--v2-badge-cyan-border)');
  });

  it('has text via token', () => {
    expect(computeBadgeStyle(active('cyan')).color).toBe('var(--v2-badge-cyan-text)');
  });

  it('has cyan glow via token', () => {
    expect(computeBadgeStyle(active('cyan')).boxShadow).toContain('var(--v2-badge-cyan-glow)');
  });
});

// ── Active state — orange ──────────────────────────────────────────────────

describe('active orange', () => {
  it('has background via token', () => {
    expect(computeBadgeStyle(active('orange')).background).toBe('var(--v2-badge-orange-bg)');
  });

  it('has border via token', () => {
    expect(computeBadgeStyle(active('orange')).border).toBe('1px solid var(--v2-badge-orange-border)');
  });

  it('has orange glow via token', () => {
    expect(computeBadgeStyle(active('orange')).boxShadow).toContain('var(--v2-badge-orange-glow)');
  });
});

// ── Active state — red ─────────────────────────────────────────────────────

describe('active red', () => {
  it('has background via token', () => {
    expect(computeBadgeStyle(active('red')).background).toBe('var(--v2-badge-red-bg)');
  });

  it('has border via token', () => {
    expect(computeBadgeStyle(active('red')).border).toBe('1px solid var(--v2-badge-red-border)');
  });

  it('has red glow via token', () => {
    expect(computeBadgeStyle(active('red')).boxShadow).toContain('var(--v2-badge-red-glow)');
  });
});

// ── Active state — green ───────────────────────────────────────────────────

describe('active green', () => {
  it('has background via token', () => {
    expect(computeBadgeStyle(active('green')).background).toBe('var(--v2-badge-green-bg)');
  });

  it('has border via token', () => {
    expect(computeBadgeStyle(active('green')).border).toBe('1px solid var(--v2-badge-green-border)');
  });

  it('has green glow via token', () => {
    expect(computeBadgeStyle(active('green')).boxShadow).toContain('var(--v2-badge-green-glow)');
  });
});

// ── Active state — muted ───────────────────────────────────────────────────

describe('active muted', () => {
  it('has background via token', () => {
    expect(computeBadgeStyle(active('muted')).background).toBe('var(--v2-badge-muted-bg)');
  });

  it('has border via token', () => {
    expect(computeBadgeStyle(active('muted')).border).toBe('1px solid var(--v2-badge-muted-border)');
  });

  it('has muted text via token', () => {
    expect(computeBadgeStyle(active('muted')).color).toBe('var(--v2-badge-muted-text)');
  });

  it('has muted glow via token', () => {
    expect(computeBadgeStyle(active('muted')).boxShadow).toContain('var(--v2-badge-muted-glow)');
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

  it('active cyan produces correct border token in string', () => {
    const s = badgeStyleString(active('cyan'));
    expect(s).toContain('border:1px solid var(--v2-badge-cyan-border)');
  });

  it('compact produces 16px height in string', () => {
    const s = badgeStyleString({ ...active(), compact: true });
    expect(s).toContain('height:16px');
  });
});
