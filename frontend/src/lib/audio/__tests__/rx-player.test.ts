import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { RxPlayer } from '../rx-player';
import { AUDIO_HEADER_SIZE, MSG_TYPE_RX, CODEC_PCM16, SAMPLE_RATE, FRAME_DURATION_MS } from '../constants';

let ctx: any;
beforeEach(() => {
  const gain = { gain: { value: 1 }, connect: vi.fn() };
  ctx = {
    state: 'running', currentTime: 0, destination: {},
    resume: vi.fn().mockResolvedValue(undefined), close: vi.fn().mockResolvedValue(undefined),
    createGain: vi.fn(() => gain),
    createBuffer: vi.fn((ch: number, n: number, sr: number) => ({
      duration: n / sr, getChannelData: () => new Float32Array(n),
    })),
    _lastSrc: null as any,
    createBufferSource: vi.fn(function (this: any) {
      const src = { buffer: null, connect: vi.fn(), start: vi.fn() };
      ctx._lastSrc = src;
      return src;
    }),
    _gain: gain,
  };
  (globalThis as any).AudioContext = function () { return ctx; } as any;
});
afterEach(() => { delete (globalThis as any).AudioContext; });

function pcm16(n: number): ArrayBuffer {
  const buf = new ArrayBuffer(AUDIO_HEADER_SIZE + n * 2);
  const v = new DataView(buf);
  v.setUint8(0, MSG_TYPE_RX); v.setUint8(1, CODEC_PCM16);
  v.setUint16(4, SAMPLE_RATE / 100, true); v.setUint8(6, 1); v.setUint8(7, FRAME_DURATION_MS);
  return buf;
}

describe('RxPlayer', () => {
  it('creates AudioContext and GainNode on start', () => {
    const p = new RxPlayer(); p.start();
    expect(ctx.createGain).toHaveBeenCalled();
    expect(ctx._gain.connect).toHaveBeenCalledWith(ctx.destination);
    expect(p.active).toBe(true); p.stop();
  });
  it('is inactive before start and after stop', () => {
    const p = new RxPlayer();
    expect(p.active).toBe(false); p.start(); p.stop(); expect(p.active).toBe(false);
  });
  it('resumes suspended context', () => {
    ctx.state = 'suspended'; const p = new RxPlayer(); p.start(); p.start();
    expect(ctx.resume).toHaveBeenCalled(); p.stop();
  });
  it('handles missing AudioContext', () => {
    delete (globalThis as any).AudioContext;
    const p = new RxPlayer(); p.start(); expect(p.active).toBe(false);
  });
  it('clamps volume and applies to gain', () => {
    const p = new RxPlayer(); p.start();
    p.volume = -1; expect(p.volume).toBe(0);
    p.volume = 5; expect(p.volume).toBe(1);
    p.volume = 0.3; expect(ctx._gain.gain.value).toBeCloseTo(0.3); p.stop();
  });
  it('processes PCM16 frame and schedules playback', () => {
    const p = new RxPlayer(); p.start(); p.feed(pcm16(480));
    expect(ctx.createBuffer).toHaveBeenCalledWith(1, 480, SAMPLE_RATE);
    expect(ctx.createBufferSource).toHaveBeenCalled();
    expect(ctx._lastSrc.start).toHaveBeenCalled();
    p.stop();
  });
  it('ignores feed when stopped', () => {
    new RxPlayer().feed(pcm16(480));
    expect(ctx.createBuffer).not.toHaveBeenCalled();
  });
  it('cleans up on stop', () => {
    const p = new RxPlayer(); p.start(); p.stop();
    expect(ctx.close).toHaveBeenCalled();
  });
});
