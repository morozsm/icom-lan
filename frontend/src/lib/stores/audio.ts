// Audio state — volume, mute, PTT
let volume = $state(0.8);
let muted = $state(false);
let ptt = $state(false);
let pttPending = $state(false);

export function getVolume() {
  return volume;
}

export function getMuted() {
  return muted;
}

export function getPtt() {
  return ptt;
}

export function getPttPending() {
  return pttPending;
}

export function setVolume(value: number) {
  volume = Math.max(0, Math.min(1, value));
}

export function toggleMute() {
  muted = !muted;
}

export function setPttPending(value: boolean) {
  pttPending = value;
}

export function setPtt(value: boolean) {
  ptt = value;
  pttPending = false;
}
