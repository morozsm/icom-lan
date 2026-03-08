import type { ServerState } from '../types/state';
import type { Capabilities } from '../types/capabilities';

const BASE = '/api/v1';

export async function fetchState(): Promise<ServerState> {
  const res = await fetch(`${BASE}/state`);
  if (!res.ok) throw new Error(`fetchState: ${res.status}`);
  return res.json() as Promise<ServerState>;
}

export async function fetchCapabilities(): Promise<Capabilities> {
  const res = await fetch(`${BASE}/capabilities`);
  if (!res.ok) throw new Error(`fetchCapabilities: ${res.status}`);
  return res.json() as Promise<Capabilities>;
}

// Polling helper — calls callback every intervalMs
export function startPolling(
  callback: () => Promise<void>,
  intervalMs = 200,
): () => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let running = true;

  async function tick() {
    if (!running) return;
    try {
      await callback();
    } finally {
      if (running) {
        timer = setTimeout(tick, intervalMs);
      }
    }
  }

  void tick();

  return () => {
    running = false;
    if (timer) clearTimeout(timer);
  };
}
