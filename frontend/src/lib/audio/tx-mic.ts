/**
 * TX Microphone — captures mic, encodes Opus, sends via WS.
 *
 * Requires WebCodecs (AudioEncoder + MediaStreamTrackProcessor).
 * Only works on HTTPS or localhost.
 */

import { buildTxHeader, TX_BITRATE, SAMPLE_RATE, CHANNELS } from './constants';

export type TxSendFn = (data: ArrayBuffer) => void;

export class TxMic {
  private stream: MediaStream | null = null;
  private encoder: AudioEncoder | null = null;
  private reader: ReadableStreamDefaultReader<AudioData> | null = null;
  private seq = 0;
  private _active = false;
  private sendFn: TxSendFn;

  constructor(sendFn: TxSendFn) {
    this.sendFn = sendFn;
  }

  get active(): boolean {
    return this._active;
  }

  /** Check if browser supports TX mic */
  static supported(): boolean {
    return (
      typeof AudioEncoder !== 'undefined' &&
      typeof MediaStreamTrackProcessor !== 'undefined'
    );
  }

  async start(): Promise<string | null> {
    if (this._active) return null;

    if (!TxMic.supported()) {
      return 'TX MIC: WebCodecs not supported (need HTTPS)';
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: CHANNELS,
          sampleRate: SAMPLE_RATE,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
    } catch {
      return 'TX MIC: permission denied';
    }

    this._active = true;
    this.seq = 0;

    const track = this.stream.getAudioTracks()[0];
    const processor = new MediaStreamTrackProcessor({ track });
    this.reader = processor.readable.getReader();

    let sentFrames = 0;
    this.encoder = new AudioEncoder({
      output: (chunk: EncodedAudioChunk) => {
        const payload = new Uint8Array(chunk.byteLength);
        chunk.copyTo(payload);
        const header = buildTxHeader(this.seq++);
        const frame = new Uint8Array(header.length + payload.length);
        frame.set(header);
        frame.set(payload, header.length);
        this.sendFn(frame.buffer);
        sentFrames++;
        if (sentFrames <= 3 || sentFrames % 50 === 0) {
          console.log(`[TxMic] sent frame #${sentFrames}, size=${frame.length} bytes`);
        }
      },
      error: (err: DOMException) => {
        console.warn('TxMic: encoder error', err);
      },
    });

    this.encoder.configure({
      codec: 'opus',
      sampleRate: SAMPLE_RATE,
      numberOfChannels: CHANNELS,
      bitrate: TX_BITRATE,
    });

    // Read loop
    this.readLoop();
    return null;
  }

  stop(): void {
    this._active = false;
    if (this.reader) {
      this.reader.cancel().catch(() => {});
      this.reader = null;
    }
    if (this.encoder) {
      try { this.encoder.close(); } catch { /* ok */ }
      this.encoder = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
  }

  private async readLoop(): Promise<void> {
    let samplesRead = 0;
    console.log('[TxMic] read loop started');
    while (this._active && this.reader) {
      let result: ReadableStreamReadResult<AudioData>;
      try {
        result = await this.reader.read();
      } catch (err) {
        console.error('[TxMic] read error:', err);
        break;
      }
      if (!result || result.done) {
        console.log('[TxMic] read loop done');
        break;
      }
      if (this.encoder && this._active) {
        this.encoder.encode(result.value);
        samplesRead++;
        if (samplesRead <= 3 || samplesRead % 100 === 0) {
          console.log(`[TxMic] encoded sample #${samplesRead}`);
        }
      }
      result.value.close();
    }
    console.log('[TxMic] read loop exited, samples=' + samplesRead);
  }
}
