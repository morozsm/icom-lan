// WebSocket protocol types

// Outgoing: client → server
export interface WsCommand {
  type: string;
  id: string;
  [key: string]: unknown;
}

// Incoming: server → client
export interface WsMessage {
  type: 'scope_data' | 'dx_spot' | 'notification' | 'ack' | 'error';
  [key: string]: unknown;
}

export interface AckMessage extends WsMessage {
  type: 'ack';
  commandId: string;
}

export interface ErrorMessage extends WsMessage {
  type: 'error';
  commandId?: string;
  message: string;
}

export interface NotificationMessage extends WsMessage {
  type: 'notification';
  level: 'info' | 'warning' | 'error';
  text: string;
}

// Command type constants
export const CMD_SET_FREQ = 'set_freq';
export const CMD_SET_MODE = 'set_mode';
export const CMD_SET_FILTER = 'set_filter';
export const CMD_PTT_ON = 'ptt_on';
export const CMD_PTT_OFF = 'ptt_off';

/** Generate a unique command ID using the Web Crypto API. */
export function makeCommandId(): string {
  return crypto.randomUUID();
}
