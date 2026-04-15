/**
 * SystemController — owns system-level actions: power, client connect/disconnect,
 * frequency identification.
 *
 * connect()/disconnect() control the entire frontend connection lifecycle:
 * all WebSocket channels, HTTP polling, audio, and MediaSession.
 */

import { connect as wsConnect, disconnectAll as wsDisconnectAll } from '$lib/transport/ws-client';
import { audioManager } from '$lib/audio/audio-manager';
import { destroyMediaSession, initMediaSession } from '$lib/media/media-session';
import { clearEtag } from '$lib/transport/http-client';
import { setHttpConnected, setRadioStatus } from '$lib/stores/connection.svelte';
import { resetRadioState } from '$lib/stores/radio.svelte';

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
  private _stopPolling: (() => void) | null = null;
  private _startPolling: (() => (() => void)) | null = null;
  private _clientConnected = true;

  get clientConnected(): boolean {
    return this._clientConnected;
  }

  /** Register the polling start function (called once from App.svelte). */
  registerPolling(startFn: () => (() => void)): void {
    this._startPolling = startFn;
  }

  /** Register an active polling stop handle (called from App.svelte after startPolling). */
  setStopPolling(stopFn: (() => void) | null): void {
    this._stopPolling = stopFn;
  }

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

  /** Disconnect all frontend channels: WS, audio, polling, MediaSession. */
  disconnect(): void {
    if (!this._clientConnected) return;
    this._clientConnected = false;

    // 1. Stop audio (RX/TX playback + audio WS)
    audioManager.destroy();

    // 2. Close all WebSocket channels (control + scope + any named)
    wsDisconnectAll();

    // 3. Stop HTTP polling
    this._stopPolling?.();
    this._stopPolling = null;
    setHttpConnected(false);

    // 4. Stop MediaSession silent audio loop
    destroyMediaSession();

    // 5. Clear stale state
    setRadioStatus('disconnected');
    resetRadioState();
  }

  /** Reconnect all frontend channels. */
  connect(): void {
    if (this._clientConnected) return;
    this._clientConnected = true;

    // 1. Restart MediaSession
    initMediaSession();

    // 2. Restart HTTP polling
    clearEtag();
    if (this._startPolling) {
      this._stopPolling = this._startPolling();
    }

    // 3. Reconnect control WebSocket
    wsConnect();
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
