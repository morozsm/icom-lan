import type { Capabilities } from '../types/capabilities';

// Capabilities fetched once from GET /api/v1/capabilities
let capabilities = $state<Capabilities | null>(null);

export function getCapabilities() {
  return capabilities;
}

export function setCapabilities(caps: Capabilities) {
  capabilities = caps;
}
