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
import { setAudioConnected } from '../stores/connection.svelte';
import { getRadioState } from '../stores/radio.svelte';
import { setRxEnabled, setTxEnabled } from '../stores/audio.svelte';
import { CODEC_OPUS, CODEC_PCM16, parseRxHeader } from './constants';

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
  private rxHeaderLogCount = 0;

  // Reactive state (read externally)
  get rxEnabled(): boolean { return this._rxEnabled; }
  get txEnabled(): boolean { return this._txEnabled; }
  get wsConnected(): boolean { return this.ws?.readyState === WebSocket.OPEN; }
  get txSupported(): boolean { return TxMic.supported(); }

  constructor() {
    let txFrames = 0;
    let droppedFrames = 0;
    this.txMic = new TxMic((data) => {
      // CRITICAL: Only send TX frames when PTT is active
      // IC-7610 LAN audio cannot do full duplex (RX + TX simultaneously)
      const ptt = getRadioState()?.ptt ?? false;
      if (!ptt) {
        droppedFrames++;
        if (droppedFrames <= 3 || droppedFrames % 100 === 0) {
          console.log(`[audio-ws] TX frame dropped (PTT OFF), total=${droppedFrames}`);
        }
        return;
      }
      
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(data);
        txFrames++;
        if (txFrames <= 3 || txFrames % 50 === 0) {
          console.log(`[audio-ws] TX frame #${txFrames} sent, size=${data.byteLength}`);
        }
      } else {
        // Dropped! WS not ready
        droppedFrames++;
        if (droppedFrames <= 5) {
          console.warn(`[audio-ws] TX frame dropped, WS state=${this.ws?.readyState}`);
        }
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
    setRxEnabled(true);
    this.rxPlayer.start();
    this.connect();
    this.notify();
  }

  stopRx(): void {
    if (!this._rxEnabled) return;
    this._rxEnabled = false;
    setRxEnabled(false);
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
    setTxEnabled(true);
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
    setTxEnabled(false);
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
      this.rxHeaderLogCount = 0;
      setAudioConnected(true);
      console.log('[audio-ws] connected');
      if (this._rxEnabled) {
        ws.send(JSON.stringify({ type: 'audio_start', direction: 'rx' }));
      }
      if (this._txEnabled) {
        ws.send(JSON.stringify({ type: 'audio_start', direction: 'tx' }));
      }
      this.rxPlayer.flush();
      this.notify();
    };

    let frameCount = 0;
    ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        frameCount++;
        if (this.rxHeaderLogCount < 5) {
          const hdr = parseRxHeader(ev.data);
          if (!hdr) {
            console.warn(`[audio-ws] RX frame #${frameCount} has invalid header bytes=${ev.data.byteLength}`);
          } else {
            const codecName = hdr.codec === CODEC_PCM16
              ? 'PCM16'
              : hdr.codec === CODEC_OPUS
                ? 'OPUS'
                : `0x${hdr.codec.toString(16).padStart(2, '0')}`;
            console.info(
              `[audio-ws] RX frame #${frameCount} codec=${codecName} sr=${hdr.sampleRate} ch=${hdr.channels} payload=${hdr.payload.byteLength}`,
            );
          }
          this.rxHeaderLogCount++;
        }
        try {
          this.rxPlayer.feed(ev.data);
        } catch (e) {
          if (frameCount <= 3) console.error(`[audio-ws] feed error on frame #${frameCount}:`, e);
        }
      }
    };

    ws.onerror = (e) => {
      console.error('[audio-ws] error', e);
      ws.close();
    };

    ws.onclose = (ev) => {
      console.warn(`[audio-ws] closed code=${ev.code} reason=${ev.reason} frames=${frameCount} rxEnabled=${this._rxEnabled}`);
      this.ws = null;
      setAudioConnected(false);
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
      setAudioConnected(false);
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
