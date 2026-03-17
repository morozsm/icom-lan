import { describe, it, expect } from 'vitest';
import {
  GAUGE_START_DEG,
  GAUGE_END_DEG,
  GAUGE_SWEEP_DEG,
  valueToNeedleAngle,
  gaugeArcColor,
  yellowZoneStart,
} from '../needle-gauge-utils';

// ── Constants ─────────────────────────────────────────────────────────────

describe('gauge constants', () => {
  it('GAUGE_START_DEG is 210', () => {
    expect(GAUGE_START_DEG).toBe(210);
  });

  it('GAUGE_END_DEG is 330', () => {
    expect(GAUGE_END_DEG).toBe(330);
  });

  it('GAUGE_SWEEP_DEG is 120', () => {
    expect(GAUGE_SWEEP_DEG).toBe(120);
  });
});

// ── valueToNeedleAngle ───────────────────────────────────────────────────

describe('valueToNeedleAngle', () => {
  it('maps 0 to start angle (210°)', () => {
    expect(valueToNeedleAngle(0)).toBe(210);
  });

  it('maps 1 to end angle (330°)', () => {
    expect(valueToNeedleAngle(1)).toBe(330);
  });

  it('maps 0.5 to mid angle (270° — straight up in SVG)', () => {
    expect(valueToNeedleAngle(0.5)).toBe(270);
  });

  it('maps 0.25 to 240°', () => {
    expect(valueToNeedleAngle(0.25)).toBe(240);
  });

  it('maps 0.75 to 300°', () => {
    expect(valueToNeedleAngle(0.75)).toBe(300);
  });

  it('clamps negative values to start angle', () => {
    expect(valueToNeedleAngle(-0.5)).toBe(210);
  });

  it('clamps values above 1 to end angle', () => {
    expect(valueToNeedleAngle(1.5)).toBe(330);
  });

  it('always returns a value within [START, END]', () => {
    for (const v of [-1, 0, 0.1, 0.5, 0.9, 1, 2]) {
      const angle = valueToNeedleAngle(v);
      expect(angle).toBeGreaterThanOrEqual(GAUGE_START_DEG);
      expect(angle).toBeLessThanOrEqual(GAUGE_END_DEG);
    }
  });

  it('is linear across the sweep range', () => {
    // Each 0.1 step should increase angle by 12°
    for (let i = 0; i < 10; i++) {
      const diff = valueToNeedleAngle((i + 1) / 10) - valueToNeedleAngle(i / 10);
      expect(diff).toBeCloseTo(12, 10);
    }
  });
});

// ── gaugeArcColor ────────────────────────────────────────────────────────

describe('gaugeArcColor — default dangerZone (0.8)', () => {
  it('pos=0 is green', () => {
    expect(gaugeArcColor(0)).toBe('#14A665');
  });

  it('pos=0.5 is green (well below yellow threshold)', () => {
    expect(gaugeArcColor(0.5)).toBe('#14A665');
  });

  it('pos just below yellow threshold is green', () => {
    // yellow starts at 0.8 * 0.875 = 0.7
    expect(gaugeArcColor(0.6999)).toBe('#14A665');
  });

  it('pos at yellowZoneStart threshold is yellow', () => {
    // Use the actual computed threshold to avoid float precision surprises
    const threshold = yellowZoneStart(0.8);
    expect(gaugeArcColor(threshold)).toBe('#F2CF4A');
  });

  it('pos=0.75 is yellow', () => {
    expect(gaugeArcColor(0.75)).toBe('#F2CF4A');
  });

  it('pos just below dangerZone is yellow', () => {
    expect(gaugeArcColor(0.7999)).toBe('#F2CF4A');
  });

  it('pos=0.8 (= dangerZone) is red', () => {
    expect(gaugeArcColor(0.8)).toBe('#F14C42');
  });

  it('pos=1.0 is red', () => {
    expect(gaugeArcColor(1.0)).toBe('#F14C42');
  });
});

describe('gaugeArcColor — custom dangerZone', () => {
  it('pos below yellowZoneStart is green for dangerZone=0.6', () => {
    // yellowStart = 0.6 * 0.875 = 0.525
    expect(gaugeArcColor(0.5, 0.6)).toBe('#14A665');
  });

  it('pos above yellowZoneStart is yellow for dangerZone=0.6', () => {
    expect(gaugeArcColor(0.55, 0.6)).toBe('#F2CF4A');
  });

  it('pos at dangerZone is red for dangerZone=0.6', () => {
    expect(gaugeArcColor(0.6, 0.6)).toBe('#F14C42');
  });
});

// ── yellowZoneStart ──────────────────────────────────────────────────────

describe('yellowZoneStart', () => {
  it('returns 87.5% of dangerZone', () => {
    expect(yellowZoneStart(0.8)).toBeCloseTo(0.7, 10);
  });

  it('scales with dangerZone=0.5', () => {
    expect(yellowZoneStart(0.5)).toBeCloseTo(0.4375, 10);
  });

  it('returns 0 for dangerZone=0', () => {
    expect(yellowZoneStart(0)).toBe(0);
  });
});

// ── Mark positioning ─────────────────────────────────────────────────────

describe('mark positioning via valueToNeedleAngle', () => {
  it('mark at pos=0 sits at start angle', () => {
    expect(valueToNeedleAngle(0)).toBe(GAUGE_START_DEG);
  });

  it('mark at pos=1 sits at end angle', () => {
    expect(valueToNeedleAngle(1)).toBe(GAUGE_END_DEG);
  });

  it('five evenly-spaced marks span the full sweep range', () => {
    const positions = [0, 0.25, 0.5, 0.75, 1];
    const angles = positions.map(valueToNeedleAngle);
    // Each step should be SWEEP/4 = 30°
    for (let i = 1; i < angles.length; i++) {
      expect(angles[i] - angles[i - 1]).toBeCloseTo(30, 10);
    }
  });

  it('mark at pos=0.5 is exactly halfway along the sweep', () => {
    const mid = (GAUGE_START_DEG + GAUGE_END_DEG) / 2;
    expect(valueToNeedleAngle(0.5)).toBe(mid);
  });
});
