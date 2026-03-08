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
