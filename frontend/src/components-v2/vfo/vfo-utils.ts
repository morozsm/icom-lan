export interface BadgeItem {
  label: string;
  active: boolean;
  color: string;
}

function _badgeColor(key: string): string {
  switch (key.toLowerCase()) {
    case 'atu':   return 'green';
    case 'pre':   return 'cyan';
    case 'nr':    return 'cyan';
    case 'nb':    return 'cyan';
    case 'notch': return 'orange';
    default:      return 'cyan';
  }
}

/**
 * Converts a badges record into a flat array of BadgeItem objects.
 *
 * Rules:
 * - Keys present in the record are always included (even if value is false).
 * - boolean true  → label = KEY (uppercased), active = true
 * - boolean false → label = KEY (uppercased), active = false
 * - string value  → label = value (used as-is, e.g. 'P1', 'AUTO'), active = true
 */
export function formatBadges(badges: Record<string, boolean | string>): BadgeItem[] {
  return Object.entries(badges).map(([key, value]) => {
    if (typeof value === 'string') {
      return { label: value, active: true, color: _badgeColor(key) };
    }
    return { label: key.toUpperCase(), active: value, color: _badgeColor(key) };
  });
}

/**
 * Formats a RIT/XIT offset in Hz as a compact signed string, e.g. '+120 Hz'.
 */
export function formatRitOffset(offsetHz: number): string {
  const sign = offsetHz >= 0 ? '+' : '−';
  return `${sign}${Math.abs(offsetHz)} Hz`;
}
