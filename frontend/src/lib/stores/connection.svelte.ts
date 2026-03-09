// Connection health state
let httpConnected = $state(false);
let wsConnected = $state(false);
let audioConnected = $state(false);
let lastResponseTime = $state<number | null>(null);

let lastStateUpdate = $state(0);
const STALE_THRESHOLD_MS = 3000;
let staleState = $state(false);

if (typeof window !== 'undefined') {
  setInterval(() => {
    const offline = (window as any).__RADIO_OFFLINE__ === true;
    const age = lastStateUpdate > 0 ? Date.now() - lastStateUpdate : 0;
    staleState = offline || (lastStateUpdate > 0 && age > STALE_THRESHOLD_MS);
  }, 1000);
}

let isFullyConnected = $derived(httpConnected && wsConnected);
let connectionStatus = $derived<'connected' | 'partial' | 'disconnected'>(
  isFullyConnected ? 'connected' : httpConnected || wsConnected ? 'partial' : 'disconnected',
);

export function setHttpConnected(v: boolean): void {
  httpConnected = v;
}

export function setWsConnected(v: boolean): void {
  wsConnected = v;
}

export function setLastResponseTime(ms: number): void {
  lastResponseTime = ms;
}

export function getConnectionStatus(): 'connected' | 'partial' | 'disconnected' {
  return connectionStatus;
}

export function isConnected(): boolean {
  return isFullyConnected;
}

export function getHttpConnected(): boolean {
  return httpConnected;
}

export function getWsConnected(): boolean {
  return wsConnected;
}

export function setAudioConnected(v: boolean): void {
  audioConnected = v;
}

export function isAudioConnected(): boolean {
  return audioConnected;
}

export function getLastResponseTime(): number | null {
  return lastResponseTime;
}

export function markStateUpdated(): void {
  lastStateUpdate = Date.now();
  staleState = false;
}

export function isStale(): boolean {
  return staleState;
}
