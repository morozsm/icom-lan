// Capabilities — mirrors backend /api/v1/capabilities schema

export interface Band {
  name: string;
  start: number;
  end: number;
  default: number;
  bsrCode?: number;
}

export interface FreqRange {
  start: number;
  end: number;
  label: string;
  bands?: Band[];
}

export interface ScopeConfig {
  centerMode: boolean;
  amplitudeMax: number;
  defaultSpan: number;
}

export interface AudioConfig {
  sampleRate: number;
  channels: number;
  codecs: string[];
}

export interface Capabilities {
  model: string;
  scope: boolean;
  audio: boolean;
  tx: boolean;
  capabilities: string[];
  receivers?: number;      // 1 = single, 2 = dual receiver
  vfoScheme?: string;      // "ab" or "main_sub"
  hasLan?: boolean;        // Radio has LAN connectivity
  freqRanges: FreqRange[];
  modes: string[];
  filters: string[];
  attValues?: number[];   // Attenuator dB steps (e.g. [0,20] for IC-7300, [0,6,12,18] for IC-7610)
  preValues?: number[];   // Preamp levels: 0 = off, 1 = P1, 2 = P2, etc.
  agcModes?: number[];    // AGC mode values (e.g. [1,2,3] = FAST/MID/SLOW)
  agcLabels?: Record<string, string>;  // AGC mode labels (e.g. {"1":"FAST","2":"MID","3":"SLOW"})
  antennas?: number;      // Number of antenna ports
  scopeConfig?: ScopeConfig;
  audioConfig?: AudioConfig;
}
