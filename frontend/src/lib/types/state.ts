// State types — mirrors backend /api/v1/state schema (camelCase)

export interface ReceiverState {
  freqHz: number;
  mode: string;
  filter: number;
  dataMode: number;
  sMeter: number;
  att: number;
  preamp: number;
  nb: boolean;
  nr: boolean;
  afLevel: number;
  rfGain: number;
  squelch: number;
  // Extended fields — optional (not all radio models expose these)
  digisel?: boolean;
  ipplus?: boolean;
  sMeterSqlOpen?: boolean;
  agc?: number;
  audioPeakFilter?: number;
  autoNotch?: boolean;
  manualNotch?: boolean;
  twinPeakFilter?: boolean;
  filterShape?: number;
  agcTimeConstant?: number;
  apfTypeLevel?: number;
  nrLevel?: number;
  pbtInner?: number;
  pbtOuter?: number;
  filterWidth?: number;
  nbLevel?: number;
  digiselShift?: number;
  afMute?: boolean;
}

export interface ScopeControls {
  receiver: number;
  dual: boolean;
  mode: number;
  span: number;
  edge: number;
  hold: boolean;
  refDb: number;
  speed: number;
  duringTx: boolean;
  centerType: number;
  vbwNarrow: boolean;
  rbw: number;
  fixedEdge: {
    rangeIndex: number;
    edge: number;
    startHz: number;
    endHz: number;
  };
}

export interface ServerState {
  revision: number;
  updatedAt: string;

  active: 'MAIN' | 'SUB';
  powerOn?: boolean;
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

  radioDetail?: {
    status: string;
    uptimeSeconds: number;
  };

  wsClients?: {
    scope: number;
    control: number;
    audio: number;
  };

  // Extended fields — optional (not all radio models expose these)
  powerLevel?: number;
  scanning?: boolean;
  tuningStep?: number;
  overflow?: boolean;
  txFreqMonitor?: boolean;
  ritFreq?: number;
  ritOn?: boolean;
  ritTx?: boolean;
  compMeter?: number;
  vdMeter?: number;
  idMeter?: number;
  cwPitch?: number;
  micGain?: number;
  keySpeed?: number;
  notchFilter?: number;
  mainSubTracking?: boolean;
  compressorOn?: boolean;
  compressorLevel?: number;
  monitorOn?: boolean;
  breakInDelay?: number;
  breakIn?: number;
  dialLock?: boolean;
  driveGain?: number;
  monitorGain?: number;
  voxOn?: boolean;
  voxGain?: number;
  antiVoxGain?: number;
  ssbTxBandwidth?: number;
  refAdjust?: number;
  dashRatio?: number;
  nbDepth?: number;
  nbWidth?: number;
  meterSource?: 'S' | 'SWR' | 'POWER';
  scopeControls?: ScopeControls;
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
  type: string;
  payload: unknown;
  createdAt: number;
  status: 'pending' | 'acked' | 'failed';
  timeoutMs: number;
}
