/**
 * Unit tests for ScopeController.
 *
 * Uses constructor injection (channelFactory) so no vi.mock is needed —
 * safe to run in the fast (non-isolated) vitest pool.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ScopeController } from '../scope-controller.svelte';
import type { ScopeFrame } from '../scope-controller.svelte';

// ── Helpers ──

function makeMockChannel() {
  const binaryHandlers = new Set<(buf: ArrayBuffer) => void>();
  return {
    connect: vi.fn(),
    disconnect: vi.fn(),
    onBinary: vi.fn((handler: (buf: ArrayBuffer) => void) => {
      binaryHandlers.add(handler);
      return () => { binaryHandlers.delete(handler); };
    }),
    /** Fire a binary message to all registered handlers. */
    _fire(buf: ArrayBuffer) {
      for (const h of binaryHandlers) h(buf);
    },
  };
}

/** Build a minimal valid scope frame ArrayBuffer (16-byte header + 4 pixels). */
function makeScopeFrameBuffer(pixelCount = 4): ArrayBuffer {
  const buf = new ArrayBuffer(16 + pixelCount);
  const view = new DataView(buf);
  view.setUint8(0, 0x01);          // magic
  view.setUint8(1, 0);             // receiver 0
  view.setUint32(3, 14_100_000, true); // startFreq
  view.setUint32(7, 14_200_000, true); // endFreq
  view.setUint16(14, pixelCount, true);
  return buf;
}

// ── Tests ──

describe('ScopeController', () => {
  let channel: ReturnType<typeof makeMockChannel>;
  let ctrl: ScopeController;

  beforeEach(() => {
    channel = makeMockChannel();
    ctrl = new ScopeController(() => channel as any);
  });

  it('subscribe() opens the WS channel on first subscriber', () => {
    expect(channel.connect).not.toHaveBeenCalled();

    ctrl.subscribe(vi.fn());

    expect(channel.connect).toHaveBeenCalledTimes(1);
    expect(channel.connect).toHaveBeenCalledWith('/api/v1/audio-scope');
  });

  it('second subscribe() reuses the existing channel without reconnecting', () => {
    ctrl.subscribe(vi.fn());
    ctrl.subscribe(vi.fn());

    expect(channel.connect).toHaveBeenCalledTimes(1);
    expect(channel.onBinary).toHaveBeenCalledTimes(1);
  });

  it('last unsubscribe() closes the channel', () => {
    const unsub1 = ctrl.subscribe(vi.fn());
    const unsub2 = ctrl.subscribe(vi.fn());

    unsub1();
    expect(channel.disconnect).not.toHaveBeenCalled();

    unsub2();
    expect(channel.disconnect).toHaveBeenCalledTimes(1);
  });

  it('both subscribers receive parsed frames', () => {
    const h1 = vi.fn<[ScopeFrame], void>();
    const h2 = vi.fn<[ScopeFrame], void>();

    ctrl.subscribe(h1);
    ctrl.subscribe(h2);

    channel._fire(makeScopeFrameBuffer());

    expect(h1).toHaveBeenCalledTimes(1);
    expect(h2).toHaveBeenCalledTimes(1);

    const frame = h1.mock.calls[0][0];
    expect(frame.startFreq).toBe(14_100_000);
    expect(frame.endFreq).toBe(14_200_000);
  });

  it('unsubscribed handler no longer receives frames', () => {
    const h1 = vi.fn();
    const h2 = vi.fn();

    const unsub1 = ctrl.subscribe(h1);
    ctrl.subscribe(h2);

    unsub1();
    channel._fire(makeScopeFrameBuffer());

    expect(h1).not.toHaveBeenCalled();
    expect(h2).toHaveBeenCalledTimes(1);
  });

  it('ignores malformed frames (wrong magic byte)', () => {
    const handler = vi.fn();
    ctrl.subscribe(handler);

    // Bad magic — parseScopeFrame returns null
    const bad = new ArrayBuffer(20);
    channel._fire(bad);

    expect(handler).not.toHaveBeenCalled();
  });

  it('reopens the channel after all subscribers leave and a new one joins', () => {
    const unsub = ctrl.subscribe(vi.fn());
    unsub();

    expect(channel.disconnect).toHaveBeenCalledTimes(1);

    ctrl.subscribe(vi.fn());
    expect(channel.connect).toHaveBeenCalledTimes(2);
  });
});
