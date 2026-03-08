// State types — mirrors backend /api/v1/state schema

export interface ReceiverState {
  freqHz: number;
  mode: string;
  filter: number;
  dataMode: boolean;
  sMeter: number;
  att: number;
  preamp: number;
  nb: boolean;
  nr: boolean;
  afLevel: number;
  rfGain: number;
  squelch: number;
}

export interface ServerState {
  revision: number;
  updatedAt: string;

  active: 'MAIN' | 'SUB';
  ptt: boolean;
  split: boolean;
  dualWatch: boolean;
  tunerStatus: number;

  main: ReceiverState;
  sub: ReceiverState;

  connection: {
    rigConnected: boolean;
    radioReady: boolean;
    controlConnected: boolean;
  };
}

export interface UiState {
  layout: 'desktop' | 'mobile';
  activePanel: 'main' | 'audio' | 'memories' | 'settings';
  spectrumFullscreen: boolean;
  freqEntryOpen: boolean;
  theme: 'dark' | 'light';
  gestures: {
    tuning: boolean;
    draggingSpectrum: boolean;
  };
}

export interface PendingCommand {
  id: string;
  type: 'set_freq' | 'set_mode' | 'set_filter' | 'ptt_on' | 'ptt_off';
  payload: unknown;
  createdAt: number;
  status: 'pending' | 'acked' | 'failed';
  timeoutMs: number;
}
