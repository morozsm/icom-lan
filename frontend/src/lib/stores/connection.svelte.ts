// Connection health state
let connected = $state(false);
let wsConnected = $state(false);
let lastUpdated = $state<Date | null>(null);

export function getConnected() {
  return connected;
}

export function getWsConnected() {
  return wsConnected;
}

export function getLastUpdated() {
  return lastUpdated;
}

export function setConnected(value: boolean) {
  connected = value;
}

export function setWsConnected(value: boolean) {
  wsConnected = value;
}

export function markUpdated() {
  lastUpdated = new Date();
}
