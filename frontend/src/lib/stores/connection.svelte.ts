// Connection health state
let httpConnected = $state(false);
let wsConnected = $state(false);
let lastResponseTime = $state<number | null>(null);

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

export function getLastResponseTime(): number | null {
  return lastResponseTime;
}
