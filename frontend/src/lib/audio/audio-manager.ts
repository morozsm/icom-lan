/**
 * Audio Manager — manages the /api/v1/audio WebSocket, RX playback, TX mic.
 *
 * Usage:
 *   audioManager.startRx()  → opens WS, starts playback
 *   audioManager.stopRx()   → stops playback
 *   audioManager.startTx()  → captures mic, starts encoding
 *   audioManager.stopTx()   → stops mic
 */

import { RxPlayer } from './rx-player';
import { TxMic } from './tx-mic';

const BACKOFF_MIN = 500;
const BACKOFF_MAX = 10000;

class AudioManager {
  private ws: WebSocket | null = null;
  private rxPlayer = new RxPlayer();
  private txMic: TxMic;
  private _rxEnabled = false;
  private _txEnabled = false;
  private backoff = BACKOFF_MIN;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _listeners: Set<() => void> = new Set();

  // Reactive state (read externally)
  get rxEnabled(): boolean { return this._rxEnabled; }
  get txEnabled(): boolean { return this._txEnabled; }
  get wsConnected(): boolean { return this.ws?.readyState === WebSocket.OPEN; }
  get txSupported(): boolean { return TxMic.supported(); }

  constructor() {
    this.txMic = new TxMic((data) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(data);
      }
    });
  }

  /** Register a change callback for reactive UI updates. Returns unsubscribe fn. */
  onChange(fn: () => void): () => void {
    this._listeners.add(fn);
    return () => { this._listeners.delete(fn); };
  }

  private notify(): void {
    for (const fn of this._listeners) fn();
  }

  // ── RX ──

  startRx(): void {
    if (this._rxEnabled) return;
    this._rxEnabled = true;
    this.rxPlayer.start();
    this.connect();
    this.notify();
  }

  stopRx(): void {
    if (!this._rxEnabled) return;
    this._rxEnabled = false;
    this.rxPlayer.stop();
    this.maybeDisconnect();
    this.notify();
  }

  setRxVolume(v: number): void {
    this.rxPlayer.volume = v;
  }

  // ── TX ──

  async startTx(): Promise<string | null> {
    if (this._txEnabled) return null;
    const err = await this.txMic.start();
    if (err) return err;
    this._txEnabled = true;
    this.connect();
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'audio_start', direction: 'tx' }));
    }
    this.notify();
    return null;
  }

  stopTx(): void {
    if (!this._txEnabled) return;
    this._txEnabled = false;
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'audio_stop', direction: 'tx' }));
    }
    this.txMic.stop();
    this.maybeDisconnect();
    this.notify();
  }

  // ── WS lifecycle ──

  private connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }
    this.close();

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${location.host}/api/v1/audio`;
    const ws = new WebSocket(url);
    ws.binaryType = 'arraybuffer';
    this.ws = ws;

    ws.onopen = () => {
      this.backoff = BACKOFF_MIN;
      if (this._rxEnabled) {
        ws.send(JSON.stringify({ type: 'audio_start', direction: 'rx' }));
      }
      if (this._txEnabled) {
        ws.send(JSON.stringify({ type: 'audio_start', direction: 'tx' }));
      }
      this.rxPlayer.flush();
      this.notify();
    };

    ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        this.rxPlayer.feed(ev.data);
      }
    };

    ws.onerror = () => ws.close();

    ws.onclose = () => {
      this.ws = null;
      this.notify();
      if (!this._rxEnabled && !this._txEnabled) return;
      // Reconnect with backoff
      const delay = this.backoff;
      this.backoff = Math.min(Math.floor(this.backoff * 1.7), BACKOFF_MAX);
      this.reconnectTimer = setTimeout(() => this.connect(), delay);
    };
  }

  private close(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
  }

  private maybeDisconnect(): void {
    if (!this._rxEnabled && !this._txEnabled) {
      this.close();
      this.notify();
    }
  }

  /** Full cleanup */
  destroy(): void {
    this.stopRx();
    this.stopTx();
    this.close();
  }
}

export const audioManager = new AudioManager();
