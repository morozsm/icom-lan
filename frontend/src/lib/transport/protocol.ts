// Protocol types — message schemas for WebSocket communication

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

// Command type constants
export const CMD_SET_FREQ = 'set_freq';
export const CMD_SET_MODE = 'set_mode';
export const CMD_SET_FILTER = 'set_filter';
export const CMD_PTT_ON = 'ptt_on';
export const CMD_PTT_OFF = 'ptt_off';

// Generate a unique command ID
export function makeCommandId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
