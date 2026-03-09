import type { ServerState, ReceiverState } from '../types/state';

/**
 * Shared radio state — class-based $state pattern for cross-module reactivity.
 * Svelte 5 recommends class instances with $state properties for sharing
 * reactive state across modules and components.
 */
class RadioStore {
  current = $state<ServerState | null>(null);
}

export const radio = new RadioStore();

let lastRevision = 0;

// Optimistic patches: field → { value, expires, serverValueAtPatch }
// Kept until server confirms (value matches) OR hard timeout (5s)
const optimisticMain = new Map<string, { value: unknown; expires: number; serverValueAtPatch?: unknown }>();
const optimisticSub = new Map<string, { value: unknown; expires: number; serverValueAtPatch?: unknown }>();

function applyOptimistic(state: ServerState): ServerState {
  const now = Date.now();
  let result = state;

  for (const [map, key] of [[optimisticMain, 'main'], [optimisticSub, 'sub']] as const) {
    if (map.size === 0) continue;
    const serverRx = result[key];
    const rx = { ...serverRx };
    let changed = false;
    for (const [field, entry] of map) {
      const serverVal = (serverRx as any)[field];

      // Clear condition: hard timeout OR server confirmed
      let confirmed = now >= entry.expires;

      if (!confirmed) {
        if (field === 'freqHz' && typeof serverVal === 'number' && typeof entry.value === 'number') {
          // Frequency: tolerance-based (radio may snap to nearest step)
          confirmed = Math.abs(serverVal - entry.value) < 500; // 500 Hz tolerance
        } else {
          // All other fields: strict equality
          confirmed = serverVal === entry.value;
        }
      }

      if (!confirmed && entry.serverValueAtPatch !== undefined) {
        // Server value changed from what it was when we patched = radio processed our command
        confirmed = serverVal !== entry.serverValueAtPatch;
      }

      if (confirmed) {
        map.delete(field);
        continue;
      }
      // Server still has old value — keep optimistic override
      (rx as any)[field] = entry.value;
      changed = true;
    }
    if (changed) result = { ...result, [key]: rx };
  }
  return result;
}

export function setRadioState(state: ServerState): void {
  const isReset = lastRevision > 10 && state.revision < lastRevision / 2;
  if (isReset) {
    console.warn(
      `Detected server restart: revision reset from ${lastRevision} to ${state.revision}`,
    );
  }
  if (state.revision > lastRevision || isReset) {
    lastRevision = state.revision;
    radio.current = applyOptimistic(state);
  }
}

const OPTIMISTIC_TTL = 5000; // hard timeout — normally cleared by server confirmation

/**
 * Optimistic update — instantly patch the active receiver's state
 * AND register patches so incoming polls don't revert them.
 */
export function patchActiveReceiver(patch: Partial<ReceiverState>): void {
  const s = radio.current;
  if (!s) return;
  const key = s.active === 'SUB' ? 'sub' : 'main';
  const map = key === 'sub' ? optimisticSub : optimisticMain;
  const expires = Date.now() + OPTIMISTIC_TTL;
  const currentRx = s[key];
  for (const [field, value] of Object.entries(patch)) {
    map.set(field, { value, expires, serverValueAtPatch: (currentRx as any)[field] });
  }
  radio.current = {
    ...s,
    [key]: { ...s[key], ...patch },
  };
}

/**
 * Optimistic update for top-level state fields (ptt, split, etc.)
 */
export function patchRadioState(patch: Partial<ServerState>): void {
  const s = radio.current;
  if (!s) return;
  radio.current = { ...s, ...patch };
}

// Convenience getters (still work in non-reactive contexts like callbacks)
export function getRadioState(): ServerState | null {
  return radio.current;
}

export function getMainReceiver(): ReceiverState | null {
  return radio.current?.main ?? null;
}

export function getSubReceiver(): ReceiverState | null {
  return radio.current?.sub ?? null;
}

export function getActiveReceiver(): ReceiverState | null {
  const s = radio.current;
  return s?.active === 'SUB' ? (s?.sub ?? null) : (s?.main ?? null);
}

export function getFrequency(): number {
  const s = radio.current;
  const active = s?.active === 'SUB' ? s?.sub : s?.main;
  return active?.freqHz ?? 0;
}

export function getMode(): string {
  const s = radio.current;
  const active = s?.active === 'SUB' ? s?.sub : s?.main;
  return active?.mode ?? '';
}

export function getIsTransmitting(): boolean {
  return radio.current?.ptt ?? false;
}

export function getLastRevision(): number {
  return lastRevision;
}
