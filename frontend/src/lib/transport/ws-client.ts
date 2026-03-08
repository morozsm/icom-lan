import type { WsCommand, WsMessage } from '../types/protocol';

type MessageHandler = (msg: WsMessage) => void;

// WebSocket client with auto-reconnect
let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
const handlers = new Set<MessageHandler>();
const RECONNECT_DELAY_MS = 2000;

export function connect(url: string = '/ws') {
  if (ws?.readyState === WebSocket.OPEN) return;

  ws = new WebSocket(url);

  ws.onopen = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
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

export function sendCommand(cmd: WsCommand) {
  if (ws?.readyState !== WebSocket.OPEN) {
    throw new Error('WebSocket not connected');
  }
  ws.send(JSON.stringify(cmd));
}

export function addMessageHandler(handler: MessageHandler) {
  handlers.add(handler);
  return () => handlers.delete(handler);
}

export function isConnected(): boolean {
  return ws?.readyState === WebSocket.OPEN;
}
