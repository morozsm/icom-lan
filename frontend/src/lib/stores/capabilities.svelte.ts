import type { Capabilities, ControlRange } from '../types/capabilities';

// Capabilities fetched once from GET /api/v1/capabilities
let capabilities = $state<Capabilities | null>(null);

export function getCapabilities(): Capabilities | null {
  return capabilities;
}

export function setCapabilities(caps: Capabilities): void {
  capabilities = caps;
}

export function hasSpectrum(): boolean {
  return capabilities?.scope ?? false;
}

export function hasAnyScope(): boolean {
  // True if hardware scope OR audio FFT scope available
  return (capabilities?.scope ?? false) || getScopeSource() === 'audio_fft';
}

export function getScopeSource(): string | null {
  return capabilities?.scopeSource ?? null;
}

export function isAudioFftScope(): boolean {
  return getScopeSource() === 'audio_fft';
}

export function hasAudio(): boolean {
  return capabilities?.audio ?? false;
}

export function hasDualReceiver(): boolean {
  return capabilities?.capabilities.includes('dual_rx') ?? false;
}

export function hasTx(): boolean {
  return capabilities?.tx ?? false;
}

export function getSupportedModes(): string[] {
  return capabilities?.modes ?? [];
}

export function getSupportedFilters(): string[] {
  return capabilities?.filters ?? [];
}

export function getKeyboardConfig() {
  return capabilities?.keyboard ?? null;
}

export function getAttValues(): number[] {
  return capabilities?.attValues ?? [0, 6, 12, 18];
}

export function getPreValues(): number[] {
  return capabilities?.preValues ?? [0, 1];
}

export function getAgcModes(): number[] {
  return capabilities?.agcModes ?? [1, 2, 3];
}

export function getAgcLabels(): Record<string, string> {
  return capabilities?.agcLabels ?? { "1": "FAST", "2": "MID", "3": "SLOW" };
}

export function getAntennaCount(): number {
  return capabilities?.antennas ?? 1;
}

export function getVfoScheme(): string {
  return capabilities?.vfoScheme ?? 'main_sub';
}

export function hasCapability(name: string): boolean {
  return capabilities?.capabilities.includes(name) ?? false;
}

export function vfoLabel(slot: 'A' | 'B'): string {
  const scheme = capabilities?.vfoScheme ?? 'main_sub';
  if (scheme === 'ab') return slot === 'A' ? 'VFO A' : 'VFO B';
  return slot === 'A' ? 'MAIN' : 'SUB';
}

export function getControlRange(name: string): ControlRange | null {
  return capabilities?.controls?.[name] ?? null;
}

export function getSmeterCalibration(): { raw: number; actual: number; label: string }[] | null {
  return capabilities?.meterCalibrations?.s_meter ?? null;
}

export function getSmeterRedline(): number | null {
  return capabilities?.meterRedlines?.s_meter ?? null;
}
