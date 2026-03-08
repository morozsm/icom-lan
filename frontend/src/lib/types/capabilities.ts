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

// Derived feature flags — computed from flat capabilities[] array
export interface FeatureFlags {
  hasSpectrum: boolean;
  hasDualReceiver: boolean;
  hasTx: boolean;
  hasTuner: boolean;
  hasCw: boolean;
  maxReceivers: number;
}

export function deriveFeatureFlags(caps: Capabilities): FeatureFlags {
  const set = new Set(caps.capabilities);
  return {
    hasSpectrum: set.has('scope'),
    hasDualReceiver: set.has('dual_rx'),
    hasTx: set.has('tx'),
    hasTuner: set.has('tuner'),
    hasCw: set.has('cw'),
    maxReceivers: set.has('dual_rx') ? 2 : 1,
  };
}
