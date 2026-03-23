import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  clamp,
  snapToStep,
  positionToValue,
  valueToPosition,
  getFillPercent,
  getCenterPercent,
  getBipolarFill,
  calculateDragValue,
  calculateClickValue,
  handleKeyboardStep,
  handleWheelStep,
  debounce,
  formatBipolarValue,
  DUAL_PARAM_DEAD_LOW,
  DUAL_PARAM_DEAD_HIGH,
  dualParamZone,
  dualParamRfFromX,
  dualParamSqlFromX,
  dualParamRfThumbPercent,
  dualParamSqlThumbPercent,
  dualParamPickSide,
  calculateArcPath,
  calculateIndicatorPosition,
  generateTickPositions,
} from '../value-control-core';

describe('clamp', () => {
  it('returns value when within range', () => {
    expect(clamp(50, 0, 100)).toBe(50);
  });

  it('returns min when value is below range', () => {
    expect(clamp(-10, 0, 100)).toBe(0);
  });

  it('returns max when value is above range', () => {
    expect(clamp(150, 0, 100)).toBe(100);
  });

  it('handles equal min and max', () => {
    expect(clamp(50, 50, 50)).toBe(50);
  });
});

describe('snapToStep', () => {
  it('snaps to nearest step', () => {
    expect(snapToStep(23, 10, 0)).toBe(20);
    expect(snapToStep(27, 10, 0)).toBe(30);
  });

  it('respects min offset', () => {
    expect(snapToStep(25, 10, 5)).toBe(25);
    expect(snapToStep(28, 10, 5)).toBe(25);
  });

  it('handles step of 1', () => {
    expect(snapToStep(5.4, 1, 0)).toBe(5);
    expect(snapToStep(5.6, 1, 0)).toBe(6);
  });

  it('handles zero step', () => {
    expect(snapToStep(5.5, 0, 0)).toBe(5.5);
  });
});

describe('positionToValue', () => {
  it('converts 0 position to min', () => {
    expect(positionToValue(0, 0, 100, 1)).toBe(0);
  });

  it('converts 1 position to max', () => {
    expect(positionToValue(1, 0, 100, 1)).toBe(100);
  });

  it('converts 0.5 position to middle', () => {
    expect(positionToValue(0.5, 0, 100, 1)).toBe(50);
  });

  it('snaps to step', () => {
    expect(positionToValue(0.33, 0, 100, 10)).toBe(30);
  });

  it('works with negative ranges', () => {
    expect(positionToValue(0.5, -100, 100, 10)).toBe(0);
  });
});

describe('valueToPosition', () => {
  it('converts min to 0', () => {
    expect(valueToPosition(0, 0, 100)).toBe(0);
  });

  it('converts max to 1', () => {
    expect(valueToPosition(100, 0, 100)).toBe(1);
  });

  it('converts middle to 0.5', () => {
    expect(valueToPosition(50, 0, 100)).toBe(0.5);
  });

  it('handles zero range', () => {
    expect(valueToPosition(50, 50, 50)).toBe(0);
  });

  it('clamps to 0-1', () => {
    expect(valueToPosition(-10, 0, 100)).toBe(0);
    expect(valueToPosition(150, 0, 100)).toBe(1);
  });
});

describe('getFillPercent', () => {
  it('returns 0 at min', () => {
    expect(getFillPercent(0, 0, 100)).toBe(0);
  });

  it('returns 100 at max', () => {
    expect(getFillPercent(100, 0, 100)).toBe(100);
  });

  it('returns 50 at middle', () => {
    expect(getFillPercent(50, 0, 100)).toBe(50);
  });
});

describe('getCenterPercent', () => {
  it('returns 50% for symmetric range', () => {
    expect(getCenterPercent(-100, 100)).toBe(50);
  });

  it('returns 0% when range starts at zero', () => {
    expect(getCenterPercent(0, 100)).toBe(0);
  });

  it('returns correct percent for asymmetric range', () => {
    expect(getCenterPercent(-50, 100)).toBeCloseTo(33.33, 1);
  });
});

describe('getBipolarFill', () => {
  it('returns center to position for positive values', () => {
    const result = getBipolarFill(50, -100, 100);
    expect(result.fillStart).toBe(50);
    expect(result.fillEnd).toBe(75);
  });

  it('returns position to center for negative values', () => {
    const result = getBipolarFill(-50, -100, 100);
    expect(result.fillStart).toBe(25);
    expect(result.fillEnd).toBe(50);
  });

  it('returns center to center for zero', () => {
    const result = getBipolarFill(0, -100, 100);
    expect(result.fillStart).toBe(50);
    expect(result.fillEnd).toBe(50);
  });
});

describe('calculateClickValue', () => {
  it('calculates value from click position', () => {
    expect(calculateClickValue(50, 0, 100, 0, 100, 1)).toBe(50);
  });

  it('snaps to step', () => {
    expect(calculateClickValue(33, 0, 100, 0, 100, 10)).toBe(30);
  });

  it('clamps to range', () => {
    expect(calculateClickValue(-10, 0, 100, 0, 100, 1)).toBe(0);
    expect(calculateClickValue(150, 0, 100, 0, 100, 1)).toBe(100);
  });
});

describe('handleKeyboardStep', () => {
  it('increases value on ArrowRight', () => {
    expect(handleKeyboardStep(50, 'ArrowRight', 10, 10, 0, 100, false)).toBe(60);
  });

  it('decreases value on ArrowLeft', () => {
    expect(handleKeyboardStep(50, 'ArrowLeft', 10, 10, 0, 100, false)).toBe(40);
  });

  it('increases value on ArrowUp', () => {
    expect(handleKeyboardStep(50, 'ArrowUp', 10, 10, 0, 100, false)).toBe(60);
  });

  it('decreases value on ArrowDown', () => {
    expect(handleKeyboardStep(50, 'ArrowDown', 10, 10, 0, 100, false)).toBe(40);
  });

  it('uses fine step with shift key', () => {
    expect(handleKeyboardStep(50, 'ArrowRight', 10, 10, 0, 100, true)).toBe(51);
  });

  it('goes to min on Home', () => {
    expect(handleKeyboardStep(50, 'Home', 10, 10, 0, 100, false)).toBe(0);
  });

  it('goes to max on End', () => {
    expect(handleKeyboardStep(50, 'End', 10, 10, 0, 100, false)).toBe(100);
  });

  it('returns null for unhandled keys', () => {
    expect(handleKeyboardStep(50, 'a', 10, 10, 0, 100, false)).toBe(null);
  });

  it('clamps to range', () => {
    expect(handleKeyboardStep(95, 'ArrowRight', 10, 10, 0, 100, false)).toBe(100);
    expect(handleKeyboardStep(5, 'ArrowLeft', 10, 10, 0, 100, false)).toBe(0);
  });
});

describe('handleWheelStep', () => {
  it('increases value on scroll up (negative deltaY)', () => {
    expect(handleWheelStep(50, -100, 10, 10, 0, 100, false)).toBe(60);
  });

  it('decreases value on scroll down (positive deltaY)', () => {
    expect(handleWheelStep(50, 100, 10, 10, 0, 100, false)).toBe(40);
  });

  it('uses fine step with shift key', () => {
    expect(handleWheelStep(50, -100, 10, 10, 0, 100, true)).toBe(51);
  });

  it('clamps to range', () => {
    expect(handleWheelStep(95, -100, 10, 10, 0, 100, false)).toBe(100);
    expect(handleWheelStep(5, 100, 10, 10, 0, 100, false)).toBe(0);
  });
});

describe('debounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('delays function execution', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced();
    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledOnce();
  });

  it('resets timer on repeated calls', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced();
    vi.advanceTimersByTime(50);
    debounced();
    vi.advanceTimersByTime(50);
    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(50);
    expect(fn).toHaveBeenCalledOnce();
  });

  it('can be cancelled', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced();
    debounced.cancel();
    vi.advanceTimersByTime(100);
    expect(fn).not.toHaveBeenCalled();
  });

  it('can be flushed', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced('arg');
    debounced.flush();
    expect(fn).toHaveBeenCalledWith('arg');
  });
});

describe('dual RF/SQL bar mapping', () => {
  it('places dead zone between configured edges', () => {
    expect(dualParamZone(0.2)).toBe('rf');
    expect(dualParamZone(0.5)).toBe('dead');
    expect(dualParamZone(0.9)).toBe('sql');
  });

  it('maps RF with max at left (x=0 → max)', () => {
    expect(dualParamRfFromX(0, 0, 255, 1)).toBe(255);
    expect(dualParamRfFromX(DUAL_PARAM_DEAD_LOW, 0, 255, 1)).toBe(0);
  });

  it('maps SQL with max at right', () => {
    expect(dualParamSqlFromX(DUAL_PARAM_DEAD_HIGH, 0, 255, 1)).toBe(0);
    expect(dualParamSqlFromX(1, 0, 255, 1)).toBe(255);
  });

  it('thumb percents align with inner zone edges', () => {
    expect(dualParamRfThumbPercent(255, 0, 255)).toBeCloseTo(0, 5);
    expect(dualParamRfThumbPercent(0, 0, 255)).toBeCloseTo(DUAL_PARAM_DEAD_LOW * 100, 5);
    expect(dualParamSqlThumbPercent(0, 0, 255)).toBeCloseTo(DUAL_PARAM_DEAD_HIGH * 100, 5);
    expect(dualParamSqlThumbPercent(255, 0, 255)).toBe(100);
  });

  it('picks closer side in dead zone', () => {
    const midDead = (DUAL_PARAM_DEAD_LOW + DUAL_PARAM_DEAD_HIGH) / 2;
    expect(midDead).toBeGreaterThan(DUAL_PARAM_DEAD_LOW);
    expect(midDead).toBeLessThan(DUAL_PARAM_DEAD_HIGH);
    // Thumbs at inner edges (RF min, SQL min): equidistant from center → RF wins on tie.
    expect(dualParamPickSide(midDead, 0, 0, 0, 255)).toBe('rf');
    // Nudge toward the SQL leg: SQL thumb is closer.
    expect(dualParamPickSide(0.51, 255, 255, 0, 255)).toBe('sql');
    expect(dualParamPickSide(0.49, 255, 255, 0, 255)).toBe('rf');
  });
});

describe('formatBipolarValue', () => {
  it('formats positive values with plus sign', () => {
    expect(formatBipolarValue(50)).toBe('+50');
  });

  it('formats negative values with minus sign', () => {
    expect(formatBipolarValue(-50)).toBe('-50');
  });

  it('formats zero without sign', () => {
    expect(formatBipolarValue(0)).toBe('0');
  });
});

describe('calculateArcPath', () => {
  it('generates valid SVG path', () => {
    const path = calculateArcPath(50, 50, 40, -135, 135);
    expect(path).toMatch(/^M\s+[\d.]+\s+[\d.]+\s+A/);
  });
});

describe('calculateIndicatorPosition', () => {
  it('calculates position on arc', () => {
    const pos = calculateIndicatorPosition(50, 50, 30, 50, 0, 100, 270);
    expect(pos.x).toBeCloseTo(50, 0);
    expect(pos.y).toBeGreaterThan(0);
  });
});

describe('generateTickPositions', () => {
  it('generates correct number of ticks', () => {
    const ticks = generateTickPositions(50, 50, 35, 40, 5, 270);
    expect(ticks).toHaveLength(6); // tickCount + 1
  });

  it('generates tick lines with valid coordinates', () => {
    const ticks = generateTickPositions(50, 50, 35, 40, 2, 270);
    ticks.forEach(tick => {
      expect(tick.x1).toBeDefined();
      expect(tick.y1).toBeDefined();
      expect(tick.x2).toBeDefined();
      expect(tick.y2).toBeDefined();
    });
  });
});
