import type { ServerState } from '../types/state';

// $radioState — authoritative server state, updated by HTTP polling + WS push
let radioState = $state<ServerState | null>(null);

export function getRadioState() {
  return radioState;
}

export function setRadioState(state: ServerState) {
  if (radioState === null || state.revision > radioState.revision) {
    radioState = state;
  }
}
