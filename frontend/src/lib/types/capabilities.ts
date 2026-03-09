// Capabilities — mirrors backend /api/v1/capabilities schema

export interface Band {
  name: string;
  start: number;
  end: number;
  default: number;
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
  freqRanges: FreqRange[];
  modes: string[];
  filters: string[];
  scopeConfig?: ScopeConfig;
  audioConfig?: AudioConfig;
}
