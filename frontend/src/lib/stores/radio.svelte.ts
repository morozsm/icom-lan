import type { ServerState, ReceiverState } from '../types/state';
import { setRadioPowerOn } from './connection.svelte';

/**
 * Shared radio state — class-based $state pattern for cross-module reactivity.
 * Svelte 5 recommends class instances with $state properties for sharing
 * reactive state across modules and components.
 */
class RadioStore {
  current = $state<ServerState | null>(null);
}

export const radio = new RadioStore();

let lastRevision = -1;

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
    if (!serverRx) continue;
    const rx = { ...serverRx };
    let changed = false;
    for (const [field, entry] of map) {
      // Check if field is locked (rapid input protection)
      const lockKey = `${key}.${field}`;
      const lockExpires = lockedFields.get(lockKey);
      if (lockExpires && now < lockExpires) {
        // Field is locked - keep optimistic value, don't check server
        (rx as any)[field] = entry.value;
        changed = true;
        continue;
      } else if (lockExpires) {
        // Lock expired - clear it
        lockedFields.delete(lockKey);
      }
      
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

      // NOTE: Do NOT treat "server value changed from patch-time value" as confirmation.
      // With rapid discrete input (wheel/keyboard), a stale intermediate poll can differ from the
      // previous optimistic value while still not matching the latest target, which causes a false
      // confirmation and visible snap-back. We only clear on exact confirmation/tolerance or timeout.

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

/** Clear all radio state on disconnect. */
export function resetRadioState(): void {
  radio.current = null;
  lastRevision = -1;
  optimisticMain.clear();
  optimisticSub.clear();
  lockedFields.clear();
}

export function setRadioState(state: ServerState): void {
  const isReset = lastRevision > 10 && state.revision < lastRevision / 2;
  const isInitial = radio.current === null;
  if (isReset) {
    console.warn(
      `Detected server restart: revision reset from ${lastRevision} to ${state.revision}`,
    );
  }
  if (isInitial || state.revision > lastRevision || isReset) {
    lastRevision = state.revision;
    radio.current = applyOptimistic(state);
    // Sync power status to connection store
    if (state.powerOn !== undefined) {
      setRadioPowerOn(state.powerOn);
    }
  }
}

const OPTIMISTIC_TTL = 5000; // hard timeout — normally cleared by server confirmation
const INPUT_LOCK_TTL = 1500; // cover command latency / polling lag for discrete inputs like wheel

/**
 * Optimistic update — instantly patch the active receiver's state
 * AND register patches so incoming polls don't revert them.
 */
// Field lock: prevent server updates from overwriting local changes during rapid input
const lockedFields = new Map<string, number>(); // `${receiver}.${field}` → expires timestamp

export function patchActiveReceiver(patch: Partial<ReceiverState>, lock = false): void {
  const s = radio.current;
  if (!s) return;
  const key = s.active === 'SUB' ? 'sub' : 'main';
  const map = key === 'sub' ? optimisticSub : optimisticMain;
  const expires = Date.now() + OPTIMISTIC_TTL;
  const currentRx = s[key];
  
  for (const [field, value] of Object.entries(patch)) {
    // Skip updating locked fields from WS echo (preserve user input lock)
    const lockKey = `${key}.${field}`;
    const lockExpires = lockedFields.get(lockKey);
    if (lockExpires && Date.now() < lockExpires && !lock) {
      // Field is locked by user input, don't overwrite with WS echo
      continue;
    }
    
    if (lock) {
      // Lock this field long enough to survive normal command latency + poll lag.
      // Drag keeps refreshing the lock continuously; wheel/keyboard are discrete and need longer.
      lockedFields.set(lockKey, Date.now() + INPUT_LOCK_TTL);
    }
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
