import type { Capabilities } from '../types/capabilities';

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

export function getAttValues(): number[] {
  return capabilities?.attValues ?? [0, 6, 12, 18];
}

export function getPreValues(): number[] {
  return capabilities?.preValues ?? [0, 1];
}

export function getAntennaCount(): number {
  return capabilities?.antennas ?? 1;
}
