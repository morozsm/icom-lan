// Tuning step store — controls frequency step for all tuning methods

import { radio } from './radio.svelte';

/** Available tuning steps in Hz */
export const TUNING_STEPS = [10, 50, 100, 500, 1_000, 5_000, 10_000, 25_000, 100_000] as const;

/** Mode-based default steps */
const MODE_DEFAULTS: Record<string, number> = {
  'CW':     10,
  'CW-R':   10,
  'RTTY':   100,
  'RTTY-R': 100,
  'AM':     1_000,
  'FM':     25_000,
  // SSB and everything else → 1kHz
};

const DEFAULT_STEP = 1_000;

let _step = $state(DEFAULT_STEP);
let _autoStep = $state(true); // auto-select step based on mode

export function getTuningStep(): number {
  return _step;
}

export function setTuningStep(hz: number): void {
  _step = hz;
  _autoStep = false; // manual override disables auto
}

export function setAutoStep(on: boolean): void {
  _autoStep = on;
}

export function isAutoStep(): boolean {
  return _autoStep;
}

/** Apply mode-based default step (called when mode changes) */
export function applyModeDefault(mode: string): void {
  if (!_autoStep) return;
  _step = MODE_DEFAULTS[mode?.toUpperCase()] ?? DEFAULT_STEP;
}

/** Snap frequency to nearest step boundary 
 * NOTE: Only used for display/tuning UI. Server always returns precise Hz.
 */
export function snapToStep(freqHz: number): number {
  if (_step <= 0) return freqHz;
  return Math.round(freqHz / _step) * _step;
}

/** Tune up/down by N steps (positive = up, negative = down) */
export function tuneBy(steps: number): number {
  const rx = radio.current?.active === 'SUB' ? radio.current?.sub : radio.current?.main;
  const freq = rx?.freqHz ?? 0;
  if (freq <= 0) return 0;
  return snapToStep(freq + steps * _step);
}

/** Format step for display */
export function formatStep(hz: number): string {
  if (hz >= 1_000_000) return `${hz / 1_000_000}MHz`;
  if (hz >= 1_000) return `${hz / 1_000}kHz`;
  return `${hz}Hz`;
}
