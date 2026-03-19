/**
 * Core interaction logic for ValueControl components.
 * Pure functions, no Svelte dependency.
 */

/**
 * Clamp a value between min and max.
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Snap a value to the nearest step increment.
 */
export function snapToStep(value: number, step: number, min: number): number {
  if (step <= 0) return value;
  const offset = value - min;
  const snapped = Math.round(offset / step) * step;
  return min + snapped;
}

/**
 * Convert a normalized position (0-1) to a value within range.
 */
export function positionToValue(
  position: number,
  min: number,
  max: number,
  step: number
): number {
  const range = max - min;
  const rawValue = min + position * range;
  return snapToStep(clamp(rawValue, min, max), step, min);
}

/**
 * Convert a value to a normalized position (0-1).
 */
export function valueToPosition(value: number, min: number, max: number): number {
  const range = max - min;
  if (range === 0) return 0;
  return clamp((value - min) / range, 0, 1);
}

/**
 * Calculate fill percentage for unipolar (left-to-right) display.
 */
export function getFillPercent(value: number, min: number, max: number): number {
  return valueToPosition(value, min, max) * 100;
}

/**
 * Calculate center position for bipolar display (where zero is).
 */
export function getCenterPercent(min: number, max: number): number {
  return valueToPosition(0, min, max) * 100;
}

/**
 * Calculate fill start/end for bipolar display.
 */
export function getBipolarFill(
  value: number,
  min: number,
  max: number
): { fillStart: number; fillEnd: number } {
  const center = getCenterPercent(min, max);
  const position = valueToPosition(value, min, max) * 100;
  return {
    fillStart: Math.min(center, position),
    fillEnd: Math.max(center, position),
  };
}

/**
 * Calculate value change from pointer/drag delta.
 * Returns the new value.
 */
export function calculateDragValue(
  startValue: number,
  deltaX: number,
  deltaY: number,
  containerWidth: number,
  min: number,
  max: number,
  step: number,
  isKnob: boolean = false
): number {
  const range = max - min;
  let delta: number;

  if (isKnob) {
    // Knob: vertical drag (up = increase)
    delta = -deltaY / containerWidth * range;
  } else {
    // Bar: horizontal drag
    delta = deltaX / containerWidth * range;
  }

  const newValue = startValue + delta;
  return snapToStep(clamp(newValue, min, max), step, min);
}

/**
 * Calculate value from absolute position click.
 */
export function calculateClickValue(
  clickX: number,
  containerLeft: number,
  containerWidth: number,
  min: number,
  max: number,
  step: number
): number {
  const position = (clickX - containerLeft) / containerWidth;
  return positionToValue(clamp(position, 0, 1), min, max, step);
}

/**
 * Apply keyboard navigation.
 */
export function handleKeyboardStep(
  currentValue: number,
  key: string,
  step: number,
  fineStepDivisor: number,
  min: number,
  max: number,
  shiftKey: boolean
): number | null {
  const effectiveStep = shiftKey ? step / fineStepDivisor : step;

  switch (key) {
    case 'ArrowRight':
    case 'ArrowUp':
      return clamp(snapToStep(currentValue + effectiveStep, effectiveStep, min), min, max);
    case 'ArrowLeft':
    case 'ArrowDown':
      return clamp(snapToStep(currentValue - effectiveStep, effectiveStep, min), min, max);
    case 'Home':
      return min;
    case 'End':
      return max;
    default:
      return null;
  }
}

/**
 * Apply scroll wheel navigation.
 */
export function handleWheelStep(
  currentValue: number,
  deltaY: number,
  step: number,
  fineStepDivisor: number,
  min: number,
  max: number,
  shiftKey: boolean
): number {
  const effectiveStep = shiftKey ? step / fineStepDivisor : step;
  const direction = deltaY > 0 ? -1 : 1;
  const newValue = currentValue + direction * effectiveStep;
  return clamp(snapToStep(newValue, effectiveStep, min), min, max);
}

/**
 * Create a debounced function.
 */
export function debounce<T extends (...args: unknown[]) => void>(
  fn: T,
  delay: number
): T & { cancel: () => void; flush: () => void } {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let lastArgs: unknown[] | null = null;

  const debounced = ((...args: unknown[]) => {
    lastArgs = args;
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      timeoutId = null;
      const savedArgs = lastArgs;
      lastArgs = null;
      if (savedArgs !== null) {
        fn(...savedArgs);
      }
    }, delay);
  }) as T & { cancel: () => void; flush: () => void };

  debounced.cancel = () => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
      timeoutId = null;
      lastArgs = null;
    }
  };

  debounced.flush = () => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
      timeoutId = null;
      if (lastArgs !== null) {
        const savedArgs = lastArgs;
        lastArgs = null;
        fn(...savedArgs);
      }
    }
  };

  return debounced;
}

/**
 * Format a display value with sign for bipolar values.
 */
export function formatBipolarValue(value: number): string {
  if (value === 0) return '0';
  return value > 0 ? `+${value}` : `${value}`;
}

/**
 * Calculate SVG arc path for knob renderer.
 */
export function calculateArcPath(
  cx: number,
  cy: number,
  radius: number,
  startAngle: number,
  endAngle: number
): string {
  // Convert to radians
  const startRad = (startAngle - 90) * (Math.PI / 180);
  const endRad = (endAngle - 90) * (Math.PI / 180);

  const x1 = cx + radius * Math.cos(startRad);
  const y1 = cy + radius * Math.sin(startRad);
  const x2 = cx + radius * Math.cos(endRad);
  const y2 = cy + radius * Math.sin(endRad);

  // Determine if we need the large arc flag
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;

  return `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`;
}

/**
 * Calculate indicator position on knob arc.
 */
export function calculateIndicatorPosition(
  cx: number,
  cy: number,
  radius: number,
  value: number,
  min: number,
  max: number,
  arcAngle: number
): { x: number; y: number } {
  const position = valueToPosition(value, min, max);
  const startAngle = -arcAngle / 2;
  const angle = startAngle + position * arcAngle;
  const rad = (angle - 90) * (Math.PI / 180);

  return {
    x: cx + radius * Math.cos(rad),
    y: cy + radius * Math.sin(rad),
  };
}

/**
 * Generate tick positions for knob.
 */
export function generateTickPositions(
  cx: number,
  cy: number,
  innerRadius: number,
  outerRadius: number,
  tickCount: number,
  arcAngle: number
): Array<{ x1: number; y1: number; x2: number; y2: number }> {
  const ticks: Array<{ x1: number; y1: number; x2: number; y2: number }> = [];
  const startAngle = -arcAngle / 2;

  for (let i = 0; i <= tickCount; i++) {
    const position = i / tickCount;
    const angle = startAngle + position * arcAngle;
    const rad = (angle - 90) * (Math.PI / 180);

    ticks.push({
      x1: cx + innerRadius * Math.cos(rad),
      y1: cy + innerRadius * Math.sin(rad),
      x2: cx + outerRadius * Math.cos(rad),
      y2: cy + outerRadius * Math.sin(rad),
    });
  }

  return ticks;
}
