/**
 * SystemController — owns all HTTP system actions (power, connect, identify).
 *
 * Replaces direct fetch('/api/v1/...') calls in presentation components.
 * All backend HTTP side effects go through this controller.
 */

import { connect as wsConnect, disconnect as wsDisconnect } from '$lib/transport/ws-client';

export interface EibiStation {
  name?: string;
  freq?: number;
  language?: string;
  target?: string;
  [key: string]: unknown;
}

export interface EibiResult {
  stations: EibiStation[];
}

class SystemController {
  async powerOn(): Promise<void> {
    const resp = await fetch('/api/v1/radio/power', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state: 'on' }),
    });
    if (!resp.ok) throw new Error(await resp.text());
  }

  async powerOff(): Promise<void> {
    const resp = await fetch('/api/v1/radio/power', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state: 'off' }),
    });
    if (!resp.ok) throw new Error(await resp.text());
  }

  connect(): void {
    wsConnect();
  }

  disconnect(): void {
    wsDisconnect();
  }

  async identifyFrequency(freqHz: number): Promise<EibiResult | null> {
    try {
      const resp = await fetch(`/api/v1/eibi/identify?freq=${freqHz}`);
      if (!resp.ok) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }
}

export const systemController = new SystemController();
