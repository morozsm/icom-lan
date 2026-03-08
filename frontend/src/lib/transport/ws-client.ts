import type { WsCommand, WsMessage } from '../types/protocol';
import { setWsConnected } from '../stores/connection.svelte';

type MessageHandler = (msg: WsMessage) => void;

// WebSocket client with auto-reconnect
let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
const handlers = new Set<MessageHandler>();
const RECONNECT_DELAY_MS = 2000;

export function connect(url: string = '/api/v1/ws') {
  if (ws?.readyState === WebSocket.OPEN) return;

  ws = new WebSocket(url);

  ws.onopen = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    setWsConnected(true);
  };

  ws.onmessage = (event: MessageEvent) => {
    try {
      const msg: WsMessage = JSON.parse(event.data as string);
      handlers.forEach((h) => h(msg));
    } catch {
      // ignore non-JSON frames (e.g. binary scope data)
    }
  };

  ws.onclose = () => {
    ws = null;
    setWsConnected(false);
    reconnectTimer = setTimeout(() => connect(url), RECONNECT_DELAY_MS);
  };

  ws.onerror = () => {
    ws?.close();
  };
}

export function disconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  ws?.close();
  ws = null;
}

/**
 * Send a command over the WebSocket connection.
 * Returns `false` if the socket is not currently connected (caller should
 * check `isConnected()` or rely on the commands store to track pending state).
 */
export function sendCommand(cmd: WsCommand): boolean {
  if (ws?.readyState !== WebSocket.OPEN) {
    return false;
  }
  ws.send(JSON.stringify(cmd));
  return true;
}

export function addMessageHandler(handler: MessageHandler) {
  handlers.add(handler);
  return () => handlers.delete(handler);
}

export function isConnected(): boolean {
  return ws?.readyState === WebSocket.OPEN;
}
