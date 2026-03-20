export const FILTER_BIPOLAR_MIN = -1200;
export const FILTER_BIPOLAR_MAX = 1200;
export const FILTER_WIDTH_MIN = 50;
export const FILTER_WIDTH_MAX = 3600;
export const FILTER_WIDTH_STEP = 50;

function clampToBipolarRange(value: number): number {
  return Math.max(FILTER_BIPOLAR_MIN, Math.min(FILTER_BIPOLAR_MAX, Math.round(value)));
}

export function clampFilterWidth(
  value: number,
  maxHz: number = FILTER_WIDTH_MAX,
  stepHz: number = FILTER_WIDTH_STEP
): number {
  const clamped = Math.max(FILTER_WIDTH_MIN, Math.min(maxHz, value));
  return Math.round(clamped / stepHz) * stepHz;
}

export function deriveIfShift(pbtInner: number, pbtOuter: number): number {
  return clampToBipolarRange((pbtInner + pbtOuter) / 2);
}

export function mapIfShiftToPbt(
  targetIfShift: number,
  currentPbtInner: number,
  currentPbtOuter: number,
): { pbtInner: number; pbtOuter: number } {
  const currentIfShift = deriveIfShift(currentPbtInner, currentPbtOuter);
  const delta = clampToBipolarRange(targetIfShift) - currentIfShift;

  return {
    pbtInner: clampToBipolarRange(currentPbtInner + delta),
    pbtOuter: clampToBipolarRange(currentPbtOuter + delta),
  };
}