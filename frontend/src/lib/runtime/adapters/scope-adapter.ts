/**
 * Scope adapter — encapsulates audio-scope WS channel lifecycle.
 *
 * Replaces direct getChannel('audio-scope') usage in AudioSpectrumPanel
 * and AmberLcdDisplay. Parses binary scope frames in one place.
 *
 * Usage in a Svelte $effect:
 *   const scope = createAudioScopeConnection(frame => { ... });
 *   return () => scope.disconnect();
 */

import { getChannel } from '$lib/transport/ws-client';
import { markScopeFrame } from '$lib/stores/connection.svelte';

let _scopeInstanceId = 0;

export interface ScopeFrame {
  receiver: number;
  startFreq: number;
  endFreq: number;
  pixels: Uint8Array;
}

export function parseScopeFrame(buf: ArrayBuffer): ScopeFrame | null {
  const view = new DataView(buf);
  if (view.byteLength < 16 || view.getUint8(0) !== 0x01) return null;
  const receiver = view.getUint8(1);
  const startFreq = view.getUint32(3, true);
  const endFreq = view.getUint32(7, true);
  const pixelCount = view.getUint16(14, true);
  if (16 + pixelCount > view.byteLength) return null;
  return { receiver, startFreq, endFreq, pixels: new Uint8Array(buf, 16, pixelCount) };
}

export interface AudioScopeHandle {
  disconnect: () => void;
}

/**
 * Open audio-scope WS channel and deliver parsed frames to the callback.
 * Returns a handle with disconnect() for cleanup.
 */
export function createAudioScopeConnection(
  onFrame: (frame: ScopeFrame) => void,
): AudioScopeHandle {
  // Each caller gets its own channel to avoid lifecycle conflicts
  // when multiple components mount/unmount independently.
  const ch = getChannel(`audio-scope-${++_scopeInstanceId}`);
  ch.connect('/api/v1/audio-scope');
  const unsubBinary = ch.onBinary((buf) => {
    markScopeFrame();
    const frame = parseScopeFrame(buf);
    if (frame) onFrame(frame);
  });

  return {
    disconnect: () => {
      unsubBinary();
      ch.disconnect();
    },
  };
}
