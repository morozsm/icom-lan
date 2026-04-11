import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TxMic } from '../tx-mic';
import { SAMPLE_RATE, CHANNELS, TX_BITRATE } from '../constants';

let mockTrack: any, mockEncoder: any, mockReader: any;
beforeEach(() => {
  mockTrack = { stop: vi.fn(), kind: 'audio' };
  mockReader = { read: vi.fn(() => Promise.resolve({ done: true })), cancel: vi.fn().mockResolvedValue(undefined) };
  mockEncoder = { configure: vi.fn(), encode: vi.fn(), close: vi.fn(), state: 'configured' };
  (globalThis as any).AudioEncoder = function (this: any) { Object.assign(this, mockEncoder); return mockEncoder; };
  (globalThis as any).MediaStreamTrackProcessor = function () {
    return { readable: { getReader: () => mockReader } };
  };
  const stream = { getTracks: () => [mockTrack], getAudioTracks: () => [mockTrack] };
  Object.defineProperty(globalThis, 'navigator', {
    value: { mediaDevices: { getUserMedia: vi.fn().mockResolvedValue(stream) } },
    writable: true, configurable: true,
  });
});
afterEach(() => { delete (globalThis as any).AudioEncoder; delete (globalThis as any).MediaStreamTrackProcessor; });

describe('TxMic', () => {
  it('detects support based on WebCodecs', () => {
    expect(TxMic.supported()).toBe(true);
    delete (globalThis as any).AudioEncoder;
    expect(TxMic.supported()).toBe(false);
  });
  it('errors when WebCodecs missing', async () => {
    delete (globalThis as any).AudioEncoder;
    const m = new TxMic(vi.fn());
    expect(await m.start()).toContain('WebCodecs not supported');
  });
  it('requests mic with correct constraints', async () => {
    const m = new TxMic(vi.fn()); await m.start();
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
      audio: { channelCount: CHANNELS, sampleRate: SAMPLE_RATE, echoCancellation: true, noiseSuppression: true },
    });
    expect(m.active).toBe(true); m.stop();
  });
  it('handles permission denied', async () => {
    (navigator.mediaDevices.getUserMedia as any).mockRejectedValueOnce(new Error('denied'));
    expect(await new TxMic(vi.fn()).start()).toContain('permission denied');
  });
  it('configures encoder correctly', async () => {
    const m = new TxMic(vi.fn()); await m.start();
    expect(mockEncoder.configure).toHaveBeenCalledWith({
      codec: 'opus', sampleRate: SAMPLE_RATE, numberOfChannels: CHANNELS, bitrate: TX_BITRATE,
    });
    m.stop();
  });
  it('cleans up all resources on stop', async () => {
    const m = new TxMic(vi.fn()); await m.start(); m.stop();
    expect(mockTrack.stop).toHaveBeenCalled();
    expect(mockReader.cancel).toHaveBeenCalled();
    expect(mockEncoder.close).toHaveBeenCalled();
    expect(m.active).toBe(false);
  });
  it('is idempotent on double start', async () => {
    const m = new TxMic(vi.fn()); await m.start();
    expect(await m.start()).toBeNull();
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(1); m.stop();
  });
});
