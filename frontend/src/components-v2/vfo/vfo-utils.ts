export interface BadgeItem {
  label: string;
  active: boolean;
  color: string;
}

/**
 * Returns the badge color for a given badge key by reading from CSS custom properties.
 * Falls back to 'cyan' if token not defined.
 * 
 * Theme files can override per-badge colors, e.g.:
 *   --v2-badge-digi-sel-color: green;
 *   --v2-badge-nr-color: red;
 */
function _badgeColor(key: string): string {
  // Normalize key: "DIGI-SEL" → "digi-sel", "IP+" → "ip-plus"
  const normalizedKey = key.toLowerCase().replace(/\+/g, '-plus');
  const tokenName = `--v2-badge-${normalizedKey}-color`;
  
  // Read from CSS (browser resolves theme overrides)
  if (typeof window !== 'undefined' && document.documentElement) {
    const color = getComputedStyle(document.documentElement)
      .getPropertyValue(tokenName)
      .trim();
    if (color) {
      return color;
    }
  }
  
  // Fallback to default token if specific badge token missing
  const defaultColor = getComputedStyle(document.documentElement)
    .getPropertyValue('--v2-badge-default-color')
    .trim();
  
  return defaultColor || 'cyan';
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
