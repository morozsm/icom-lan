/**
 * ScopeController — singleton owner of the audio-scope WebSocket channel.
 *
 * Opens `/api/v1/audio-scope` lazily when the first subscriber attaches and
 * closes it when the last subscriber detaches. Parses binary frames with
 * `parseScopeFrame()` from `scope-adapter.ts` and stores the latest frame as
 * a reactive `$state` property that Svelte components can read via `$derived`.
 *
 * Satisfies ADR INV-2 (single scope ownership) and INV-5 (mount/unmount of
 * presentation panels must not change transport state).
 *
 * @see docs/plans/2026-04-12-target-frontend-architecture.md §ScopeController
 */

import { getChannel } from '$lib/transport/ws-client';
import { markScopeFrame } from '$lib/stores/connection.svelte';
import { parseScopeFrame } from '$lib/runtime/adapters/scope-adapter';
import type { ScopeFrame } from '$lib/runtime/adapters/scope-adapter';
import type { WsChannel } from '$lib/transport/ws-client';

export type { ScopeFrame };

type FrameHandler = (frame: ScopeFrame) => void;
type ChannelFactory = (name: string) => WsChannel;

export class ScopeController {
  /** Latest parsed audio-scope frame (Svelte 5 reactive). */
  audioScopeFrame: ScopeFrame | null = $state(null);

  /** Hardware scope — not yet implemented; always false for now. */
  readonly hardwareScopeAvailable = false;
  readonly audioScopeAvailable = true;
  readonly activeScope: 'hardware' | 'audio-fft' | null = 'audio-fft';
  readonly scopeFrame: ScopeFrame | null = null;

  private _subscribers = new Map<number, FrameHandler>();
  private _nextId = 0;
  private _unsubBinary: (() => void) | null = null;
  private _channel: WsChannel | null = null;
  private _getChannel: ChannelFactory;

  constructor(channelFactory: ChannelFactory = getChannel) {
    this._getChannel = channelFactory;
  }

  /**
   * Subscribe to parsed scope frames.
   * Opens the WS channel on the first subscriber.
   * Returns an `unsubscribe` function — call it to stop receiving frames.
   * Each subscribe() call creates an independent subscription, even for the same handler reference.
   */
  subscribe(handler: FrameHandler): () => void {
    const id = this._nextId++;
    this._subscribers.set(id, handler);

    if (this._subscribers.size === 1) {
      this._connect();
    }

    return () => {
      this._subscribers.delete(id);
      if (this._subscribers.size === 0) {
        this._disconnect();
      }
    };
  }

  private _connect(): void {
    const ch = this._getChannel('audio-scope');
    this._channel = ch;
    ch.connect('/api/v1/audio-scope');
    this._unsubBinary = ch.onBinary((buf: ArrayBuffer) => {
      markScopeFrame();
      const frame = parseScopeFrame(buf);
      if (frame) {
        this.audioScopeFrame = frame;
        for (const h of this._subscribers.values()) {
          h(frame);
        }
      }
    });
  }

  private _disconnect(): void {
    this._unsubBinary?.();
    this._unsubBinary = null;
    this._channel?.disconnect();
    this._channel = null;
    this.audioScopeFrame = null;
  }
}

/** Singleton instance used by FrontendRuntime. */
export const scopeController = new ScopeController();
