export const FILTER_BIPOLAR_MIN = -1200;
export const FILTER_BIPOLAR_MAX = 1200;
export const FILTER_WIDTH_MIN = 50;
export const FILTER_WIDTH_MAX = 3600;
export const FILTER_WIDTH_STEP = 50;

// PBT raw <-> display conversion
// Reads range from capabilities if available, falls back to IC-7610 defaults
import { getControlRange } from '$lib/stores/capabilities.svelte';

function pbtRange() {
  const ctrl = getControlRange('pbt_inner');
  if (ctrl && ctrl.raw_center !== undefined && ctrl.display_min !== undefined && ctrl.display_max !== undefined) {
    return { rawCenter: ctrl.raw_center, displayMin: ctrl.display_min, displayMax: ctrl.display_max };
  }
  // Fallback: IC-7610 defaults
  return { rawCenter: 128, displayMin: -1200, displayMax: 1200 };
}

export function pbtRawToHz(raw: number): number {
  const { rawCenter, displayMax } = pbtRange();
  return Math.round((raw - rawCenter) * (displayMax / rawCenter));
}

export function pbtHzToRaw(hz: number): number {
  const { rawCenter, displayMax } = pbtRange();
  const raw = Math.round(hz * (rawCenter / displayMax) + rawCenter);
  return Math.max(0, Math.min(255, raw));
}

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