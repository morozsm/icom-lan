/**
 * RX Audio Player — decodes Opus/PCM16 frames and plays via AudioContext.
 *
 * Low-latency: schedules buffers ~20ms ahead, drops if >150ms behind.
 */

import {
  CODEC_OPUS,
  CODEC_PCM16,
  SAMPLE_RATE,
  parseRxHeader,
} from './constants';

export class RxPlayer {
  private ctx: AudioContext | null = null;
  private gain: GainNode | null = null;
  private decoder: AudioDecoder | null = null;
  private nextPlayTime = 0;
  private opusTs = 0;
  private _volume = 1.0;
  private loggedSuspendedPcm = false;
  private loggedSuspendedOpus = false;
  private loggedMissingDecoder = false;
  private loggedDecoderInit = false;

  get volume(): number {
    return this._volume;
  }

  set volume(v: number) {
    this._volume = Math.max(0, Math.min(1, v));
    if (this.gain) this.gain.gain.value = this._volume;
  }

  get active(): boolean {
    return this.ctx !== null && this.ctx.state !== 'closed';
  }

  start(): void {
    if (this.ctx) {
      if (this.ctx.state === 'suspended') {
        console.info('[rx-player] reusing suspended AudioContext; attempting resume');
        this.ctx.resume()
          .then(() => {
            console.info(`[rx-player] AudioContext resumed (state=${this.ctx?.state ?? 'none'})`);
          })
          .catch((err) => {
            console.warn('[rx-player] AudioContext resume failed', err);
          });
      }
      return;
    }
    const Ctx = globalThis.AudioContext ?? (globalThis as any).webkitAudioContext;
    if (!Ctx) return;
    this.ctx = new Ctx({ sampleRate: SAMPLE_RATE });
    this.ctx.onstatechange = () => {
      console.info(`[rx-player] AudioContext state=${this.ctx?.state ?? 'none'}`);
    };
    this.gain = this.ctx.createGain();
    this.gain.gain.value = this._volume;
    this.gain.connect(this.ctx.destination);
    this.nextPlayTime = 0;
    console.info(`[rx-player] AudioContext created sampleRate=${this.ctx.sampleRate} state=${this.ctx.state}`);
    // Resume suspended context. When it transitions to 'running',
    // playPcm16/decodeOpus will start scheduling buffers automatically.
    if (this.ctx.state === 'suspended') {
      console.info('[rx-player] initial AudioContext is suspended; attempting resume');
      this.ctx.resume()
        .then(() => {
          console.info(`[rx-player] initial resume resolved state=${this.ctx?.state ?? 'none'}`);
        })
        .catch((err) => {
          console.warn('[rx-player] initial AudioContext resume failed', err);
        });
    }
  }

  stop(): void {
    if (this.decoder) {
      try { this.decoder.close(); } catch { /* ok */ }
      this.decoder = null;
    }
    if (this.ctx) {
      this.ctx.close().catch(() => {});
      this.ctx = null;
      this.gain = null;
    }
    this.nextPlayTime = 0;
    this.opusTs = 0;
    this.loggedSuspendedPcm = false;
    this.loggedSuspendedOpus = false;
    this.loggedMissingDecoder = false;
    this.loggedDecoderInit = false;
  }

  /** Feed a raw binary frame from WS */
  feed(buffer: ArrayBuffer): void {
    const hdr = parseRxHeader(buffer);
    if (!hdr) return;

    if (hdr.codec === CODEC_PCM16) {
      this.playPcm16(hdr.payload, hdr.sampleRate, hdr.channels);
    } else if (hdr.codec === CODEC_OPUS) {
      this.decodeOpus(hdr.payload, hdr.sampleRate, hdr.channels);
    }
  }

  /** Flush pipeline (e.g. on reconnect) */
  flush(): void {
    this.nextPlayTime = 0;
  }

  // ── PCM16 playback ──

  private playPcm16(payload: Uint8Array, sr: number, ch: number): void {
    if (!this.ctx || !this.gain) return;
    if (this.ctx.state === 'suspended') {
      if (!this.loggedSuspendedPcm) {
        this.loggedSuspendedPcm = true;
        console.warn(
          `[rx-player] skipping PCM16 playback while AudioContext is suspended payload=${payload.byteLength} sr=${sr} ch=${ch}`,
        );
      }
      return; // wait for resume
    }
    const channels = ch === 2 ? 2 : 1;
    const frameCount = Math.floor(payload.byteLength / (2 * channels));
    if (frameCount <= 0) return;

    const int16 = new Int16Array(payload.buffer, payload.byteOffset, frameCount * channels);
    const buf = this.ctx.createBuffer(channels, frameCount, sr > 0 ? sr : SAMPLE_RATE);
    for (let c = 0; c < channels; c++) {
      const data = buf.getChannelData(c);
      for (let i = 0; i < frameCount; i++) {
        data[i] = int16[i * channels + c] / 32768.0;
      }
    }
    this.schedule(buf);
  }

  // ── Opus decode ──

  private decodeOpus(payload: Uint8Array, sr: number, ch: number): void {
    if (!this.ctx || !this.gain) return;
    if (this.ctx.state === 'suspended') {
      if (!this.loggedSuspendedOpus) {
        this.loggedSuspendedOpus = true;
        console.warn(
          `[rx-player] skipping Opus decode while AudioContext is suspended payload=${payload.byteLength} sr=${sr} ch=${ch}`,
        );
      }
      return;
    }
    if (typeof AudioDecoder === 'undefined') {
      if (!this.loggedMissingDecoder) {
        this.loggedMissingDecoder = true;
        console.warn(
          `[rx-player] AudioDecoder unavailable; cannot play Opus payload=${payload.byteLength} sr=${sr} ch=${ch}`,
        );
      }
      return;
    }

    if (!this.decoder) {
      const ctx = this.ctx;
      this.opusTs = 0;
      if (!this.loggedDecoderInit) {
        this.loggedDecoderInit = true;
        console.info(`[rx-player] creating AudioDecoder sr=${sr > 0 ? sr : SAMPLE_RATE} ch=${ch === 2 ? 2 : 1}`);
      }
      this.decoder = new AudioDecoder({
        output: (audioData: AudioData) => {
          const frames = audioData.numberOfFrames;
          const numCh = audioData.numberOfChannels;
          const buf = ctx.createBuffer(numCh, frames, audioData.sampleRate);
          for (let c = 0; c < numCh; c++) {
            const data = buf.getChannelData(c);
            audioData.copyTo(data, { planeIndex: c, format: 'f32-planar' });
          }
          this.schedule(buf);
          audioData.close();
        },
        error: (err: DOMException) => {
          console.warn('RxPlayer: AudioDecoder error', err);
          // Decoder auto-closes on error — null it so next frame recreates
          this.decoder = null;
        },
      });
      this.decoder.configure({
        codec: 'opus',
        sampleRate: sr > 0 ? sr : SAMPLE_RATE,
        numberOfChannels: ch === 2 ? 2 : 1,
      });
    }

    if (!this.decoder || this.decoder.state === 'closed') {
      this.decoder = null;
      return; // will be recreated on next call
    }

    const chunk = new EncodedAudioChunk({
      type: 'key',
      timestamp: this.opusTs,
      data: payload,
    });
    this.opusTs += 20_000; // 20ms in µs
    this.decoder.decode(chunk);
  }

  // ── Scheduler ──

  private schedule(buf: AudioBuffer): void {
    if (!this.ctx || !this.gain) return;
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.gain);

    const now = this.ctx.currentTime;
    if (this.nextPlayTime < now + 0.01) {
      this.nextPlayTime = now + 0.02;
    }
    // Drop if >150ms ahead → keep latency low
    if (this.nextPlayTime > now + 0.15) return;

    src.start(this.nextPlayTime);
    this.nextPlayTime += buf.duration;
  }
}
