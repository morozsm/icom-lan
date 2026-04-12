/**
 * SystemController — owns all HTTP system actions (power, connect, identify).
 *
 * Replaces direct fetch('/api/v1/...') calls in presentation components.
 * All backend HTTP side effects go through this controller.
 */

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

  async connect(): Promise<void> {
    const resp = await fetch('/api/v1/radio/connect', { method: 'POST' });
    if (!resp.ok) throw new Error(await resp.text());
  }

  async disconnect(): Promise<void> {
    const resp = await fetch('/api/v1/radio/disconnect', { method: 'POST' });
    if (!resp.ok) throw new Error(await resp.text());
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
