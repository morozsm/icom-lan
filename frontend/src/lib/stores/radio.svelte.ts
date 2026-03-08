import type { ServerState, ReceiverState } from '../types/state';

// $radioState — authoritative server state, updated by HTTP polling + WS push
let radioState = $state<ServerState | null>(null);
let lastRevision = $state(0);

// Derived values
let mainReceiver = $derived(radioState?.main ?? null);
let subReceiver = $derived(radioState?.sub ?? null);
let activeReceiver = $derived<ReceiverState | null>(
  radioState?.active === 'SUB' ? (radioState?.sub ?? null) : (radioState?.main ?? null),
);
let frequency = $derived(activeReceiver?.freqHz ?? 0);
let mode = $derived(activeReceiver?.mode ?? '');
let isTransmitting = $derived(radioState?.ptt ?? false);

export function getRadioState(): ServerState | null {
  return radioState;
}

export function setRadioState(state: ServerState): void {
  if (state.revision > lastRevision) {
    lastRevision = state.revision;
    radioState = state;
  }
}

export function getMainReceiver(): ReceiverState | null {
  return mainReceiver;
}

export function getSubReceiver(): ReceiverState | null {
  return subReceiver;
}

export function getActiveReceiver(): ReceiverState | null {
  return activeReceiver;
}

export function getFrequency(): number {
  return frequency;
}

export function getMode(): string {
  return mode;
}

export function getIsTransmitting(): boolean {
  return isTransmitting;
}

export function getLastRevision(): number {
  return lastRevision;
}
