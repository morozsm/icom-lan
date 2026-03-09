/**
 * Global keyboard shortcut handler for desktop radio control.
 *
 * F1–F11 = band switch (160m … 6m)
 * M       = cycle mode
 * ↑ / ↓  = tune ±1 kHz
 * Space   = toggle PTT
 * Escape  = close FreqEntry modal
 */

import { sendCommand } from '../transport/ws-client';
import { getRadioState, getMode } from '../stores/radio.svelte';
import { getSupportedModes } from '../stores/capabilities.svelte';
import { getUiState, toggleFreqEntry } from '../stores/ui.svelte';

// Default frequencies for each band (IC-7610 HF + 6m)
const BAND_FREQS_HZ: number[] = [
  1_825_000,   // F1  160m
  3_700_000,   // F2  80m
  5_357_000,   // F3  60m
  7_100_000,   // F4  40m
  10_130_000,  // F5  30m
  14_200_000,  // F6  20m
  18_120_000,  // F7  17m
  21_200_000,  // F8  15m
  24_940_000,  // F9  12m
  28_500_000,  // F10 10m
  50_200_000,  // F11 6m
];

// Fallback mode cycle if capabilities not yet loaded
const FALLBACK_MODES = ['USB', 'LSB', 'CW', 'AM', 'FM'];

// Tuning step for ↑/↓ keys
// TUNE_STEP_HZ removed - tuning step now handled by tuning.svelte.ts store

function isInputFocused(): boolean {
  const el = document.activeElement;
  return (
    el instanceof HTMLInputElement ||
    el instanceof HTMLTextAreaElement ||
    el instanceof HTMLSelectElement ||
    (el instanceof HTMLElement && el.isContentEditable)
  );
}

function handleKeydown(e: KeyboardEvent): void {
  // Never steal keys from text inputs
  if (isInputFocused()) return;

  const state = getRadioState();
  const receiverIdx = state?.active === 'SUB' ? 1 : 0;

  // F1–F11: band switching
  const fKey = /^F(\d+)$/.exec(e.key);
  if (fKey) {
    const n = parseInt(fKey[1], 10);
    if (n >= 1 && n <= 11) {
      e.preventDefault();
      sendCommand('set_freq', { freq: BAND_FREQS_HZ[n - 1], receiver: receiverIdx });
      return;
    }
  }

  switch (e.key) {
    case 'm':
    case 'M': {
      e.preventDefault();
      const currentMode = getMode();
      const available = getSupportedModes();
      const modes = available.length > 0 ? available : FALLBACK_MODES;
      const idx = modes.indexOf(currentMode);
      const next = modes[(idx + 1) % modes.length];
      sendCommand('set_mode', { mode: next, receiver: receiverIdx });
      break;
    }

    // Arrow keys handled in DesktopLayout with debounce + stable base freq

    case ' ': {
      e.preventDefault();
      const ptt = state?.ptt ?? false;
      sendCommand('ptt', { state: !ptt });
      break;
    }

    case 'Escape': {
      if (getUiState().freqEntryOpen) {
        e.preventDefault();
        toggleFreqEntry();
      }
      break;
    }
  }
}

/** Register global keyboard shortcuts. Returns an unregister function. */
export function setupKeyboard(): () => void {
  window.addEventListener('keydown', handleKeydown);
  return () => window.removeEventListener('keydown', handleKeydown);
}
