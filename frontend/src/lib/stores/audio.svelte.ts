// Audio state — volume, mute, RX/TX bridge
let audioState = $state({
  rxEnabled: false,
  txEnabled: false,
  volume: 50,
  muted: false,
  micEnabled: false,
  bridgeRunning: false,
});

export function getAudioState(): typeof audioState {
  return audioState;
}

export function setVolume(v: number): void {
  audioState.volume = Math.max(0, Math.min(100, Math.round(v)));
}

export function toggleMute(): void {
  audioState.muted = !audioState.muted;
}

export function setMuted(v: boolean): void {
  audioState.muted = v;
}

export function setRxEnabled(v: boolean): void {
  audioState.rxEnabled = v;
}

export function setTxEnabled(v: boolean): void {
  audioState.txEnabled = v;
}

export function setMicEnabled(v: boolean): void {
  audioState.micEnabled = v;
}

export function setBridgeRunning(v: boolean): void {
  audioState.bridgeRunning = v;
}
