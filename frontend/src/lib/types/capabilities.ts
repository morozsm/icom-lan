// Capabilities — mirrors backend /api/v1/capabilities schema

export interface FreqRange {
  start: number;
  end: number;
  label: string;
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
}

