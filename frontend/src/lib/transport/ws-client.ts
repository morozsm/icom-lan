import type { WsCommand, WsIncoming } from '../types/protocol';
import { setWsConnected } from '../stores/connection.svelte';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';
type MessageHandler = (msg: WsIncoming) => void;
type BinaryHandler = (data: ArrayBuffer) => void;
type StateHandler = (state: ConnectionState) => void;

const BACKOFF_BASE_MS = 1_000;
const BACKOFF_MAX_MS = 30_000;
const HEARTBEAT_TIMEOUT_MS = 10_000;
const MAX_QUEUE_SIZE = 20;

// Command types where only the latest value matters (last write wins)
const IDEMPOTENT_TYPES = new Set(['set_freq', 'set_mode', 'set_filter']);

function calcBackoff(attempt: number): number {
  const base = Math.min(BACKOFF_BASE_MS * 2 ** attempt, BACKOFF_MAX_MS);
  return base * (0.8 + Math.random() * 0.4);
}

export class WsChannel {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null;
  private attempt = 0;
  private intentionalClose = false;
  private sendQueue: WsCommand[] = [];
  private messageHandlers = new Set<MessageHandler>();
  private binaryHandlers = new Set<BinaryHandler>();
  private stateHandlers = new Set<StateHandler>();
  private _state: ConnectionState = 'disconnected';
  private url = '';

  get state(): ConnectionState {
    return this._state;
  }

  private setState(s: ConnectionState) {
    this._state = s;
    this.stateHandlers.forEach((h) => h(s));
  }

  connect(url: string) {
    const rs = this.ws?.readyState;
    if (rs === WebSocket.OPEN || rs === WebSocket.CONNECTING) return;
    this.url = url;
    this.intentionalClose = false;
    this._open();
  }

  private _open() {
    this.setState(this.attempt === 0 ? 'connecting' : 'reconnecting');
    const ws = new WebSocket(this.url);
    ws.binaryType = 'arraybuffer';
    this.ws = ws;

    ws.onopen = () => {
      this.attempt = 0;
      this.setState('connected');
      this._resetHeartbeat();
      // drain send queue
      const queued = this.sendQueue.splice(0);
      for (const cmd of queued) ws.send(JSON.stringify(cmd));
    };

    ws.onmessage = (event: MessageEvent) => {
      this._resetHeartbeat();
      if (event.data instanceof ArrayBuffer) {
        this.binaryHandlers.forEach((h) => h(event.data as ArrayBuffer));
      } else {
        try {
          const msg = JSON.parse(event.data as string) as WsIncoming;
          this.messageHandlers.forEach((h) => h(msg));
        } catch {
          // ignore malformed frames
        }
      }
    };

    ws.onclose = () => {
      this._clearHeartbeat();
      this.ws = null;
      this.setState('disconnected');
      if (!this.intentionalClose) {
        const delay = calcBackoff(this.attempt++);
        this.reconnectTimer = setTimeout(() => this._open(), delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  disconnect() {
    this.intentionalClose = true;
    this._clearTimers();
    const ws = this.ws;
    this.ws = null;
    ws?.close(); // onclose fires, sees intentionalClose=true, calls setState('disconnected')
    this.attempt = 0;
  }

  send(cmd: WsCommand): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(cmd));
      return true;
    }
    // Deduplicate idempotent commands — keep only the latest value
    if (IDEMPOTENT_TYPES.has(cmd.type)) {
      this.sendQueue = this.sendQueue.filter((c) => c.type !== cmd.type);
    }
    this.sendQueue.push(cmd);
    // Drop oldest if over limit
    if (this.sendQueue.length > MAX_QUEUE_SIZE) {
      this.sendQueue.shift();
    }
    return false;
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onBinary(handler: BinaryHandler): () => void {
    this.binaryHandlers.add(handler);
    return () => this.binaryHandlers.delete(handler);
  }

  onStateChange(handler: StateHandler): () => void {
    this.stateHandlers.add(handler);
    return () => this.stateHandlers.delete(handler);
  }

  private _resetHeartbeat() {
    this._clearHeartbeat();
    this.heartbeatTimer = setTimeout(() => {
      this.ws?.close();
    }, HEARTBEAT_TIMEOUT_MS);
  }

  private _clearHeartbeat() {
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private _clearTimers() {
    this._clearHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

// ─── Control channel singleton (backward-compat API) ───────────────────────

const _ctrl = new WsChannel();
_ctrl.onStateChange((s) => setWsConnected(s === 'connected'));

export function connect(url: string = '/api/v1/ws') {
  _ctrl.connect(url);
}

export function disconnect() {
  _ctrl.disconnect();
}

export function sendCommand(cmd: WsCommand): boolean {
  return _ctrl.send(cmd);
}

export function onMessage(handler: MessageHandler): () => void {
  return _ctrl.onMessage(handler);
}

/** @deprecated Use onMessage */
export const addMessageHandler = onMessage;

export function isConnected(): boolean {
  return _ctrl.isConnected();
}

// ─── Named channel registry (scope / audio) ────────────────────────────────

const _channels = new Map<string, WsChannel>();

export function getChannel(name: string): WsChannel {
  let ch = _channels.get(name);
  if (!ch) {
    ch = new WsChannel();
    _channels.set(name, ch);
  }
  return ch;
}
