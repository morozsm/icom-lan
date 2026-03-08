// WebSocket protocol types

// Outgoing: client → server
export interface WsCommand {
  type: string;
  id: string;
  [key: string]: unknown;
}

// DX cluster spot
export interface DxSpot {
  spotter: string;
  freq: number;
  dx: string;
  comment: string;
  time: string;
}

// Incoming message union
export type WsIncoming =
  | { type: 'scope_data'; data: ArrayBuffer }
  | { type: 'dx_spot'; spot: DxSpot }
  | { type: 'dx_spots'; spots: DxSpot[] }
  | { type: 'notification'; level: string; message: string }
  | { type: 'ack'; id: string }
  | { type: 'error'; id: string; message: string };

// Incoming: server → client (loose form for existing callers)
export interface WsMessage {
  type: 'scope_data' | 'dx_spot' | 'dx_spots' | 'notification' | 'ack' | 'error';
  [key: string]: unknown;
}

export interface AckMessage extends WsMessage {
  type: 'ack';
  id: string;
}

export interface ErrorMessage extends WsMessage {
  type: 'error';
  id: string;
  message: string;
}

export interface NotificationMessage extends WsMessage {
  type: 'notification';
  level: 'info' | 'warning' | 'error';
  text: string;
}

// /api/v1/info response
export interface InfoResponse {
  version: string;
  revision: number;
  updatedAt: string;
  uptime: number;
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
