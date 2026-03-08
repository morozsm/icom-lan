import type { ServerState } from '../types/state';
import type { Capabilities } from '../types/capabilities';
import type { InfoResponse } from '../types/protocol';
import { setHttpConnected } from '../stores/connection.svelte';

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

/** Fetch server info (version, uptime). Used by StatusBar component (Sprint 2). */
export async function fetchInfo(): Promise<InfoResponse> {
  const res = await fetch(`${BASE}/info`);
  if (!res.ok) throw new Error(`fetchInfo: ${res.status}`);
  return res.json() as Promise<InfoResponse>;
}

/**
 * Poll `/api/v1/state` at the given interval, calling `callback` only when
 * the revision advances. Skips the poll if the previous one hasn't returned.
 *
 * @returns A stop function.
 */
const HTTP_ERROR_THRESHOLD = 3;

export function startPolling(
  callback: (state: ServerState) => void,
  intervalMs = 200,
): () => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let running = true;
  let inflight = false;
  let lastRevision = -1;
  let consecutiveErrors = 0;

  async function tick() {
    if (!running) return;
    if (!inflight) {
      inflight = true;
      try {
        const state = await fetchState();
        consecutiveErrors = 0;
        setHttpConnected(true);
        if (state.revision > lastRevision) {
          lastRevision = state.revision;
          callback(state);
        }
      } catch {
        consecutiveErrors++;
        if (consecutiveErrors >= HTTP_ERROR_THRESHOLD) {
          setHttpConnected(false);
        }
      } finally {
        inflight = false;
      }
    }
    if (running) {
      timer = setTimeout(tick, intervalMs);
    }
  }

  void tick();

  return () => {
    running = false;
    if (timer) clearTimeout(timer);
  };
}
