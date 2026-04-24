/**
 * FrontendRuntime — shared singleton shell for all frontend behavior.
 *
 * Wraps existing stores, transport, and audio into a single entry point.
 * Components import `runtime` instead of reaching into individual modules.
 *
 * This is a thin delegation layer — it owns no state, only routes reads
 * and writes to the existing infrastructure. Svelte 5 reactivity is
 * preserved because getters return live $state references, not copies.
 *
 * @see docs/plans/2026-04-12-target-frontend-architecture.md
 */

import { radio, getRadioState, patchActiveReceiver, patchRadioState, setRadioState } from '$lib/stores/radio.svelte';
import { getCapabilities, setCapabilities } from '$lib/stores/capabilities.svelte';
import {
  getConnectionStatus,
  isConnected,
  getHttpConnected,
  getWsConnected,
  isAudioConnected,
  isStale,
  isReconnecting,
  getRadioStatus,
  getRadioPowerOn,
} from '$lib/stores/connection.svelte';
import { getAudioState, setVolume, setMuted, toggleMute } from '$lib/stores/audio.svelte';
import { sendCommand, connect, sendRaw } from '$lib/transport/ws-client';
import { fetchCapabilities, startPolling } from '$lib/transport/http-client';
import { audioManager } from '$lib/audio/audio-manager';
import { systemController } from './system-controller';
import { scopeController } from './scope-controller.svelte';
import type { ScopeController } from './scope-controller.svelte';

import type { ServerState, ReceiverState } from '$lib/types/state';
import type { Capabilities } from '$lib/types/capabilities';

// ── Types ──

export interface ConnectionSnapshot {
  status: 'connected' | 'partial' | 'disconnected';
  http: boolean;
  ws: boolean;
  audio: boolean;
  stale: boolean;
  reconnecting: boolean;
  radioStatus: string;
  radioPowerOn: boolean | null;
}


// ── Runtime class ──

class FrontendRuntime {
  private _bootstrapCleanup: (() => void) | null = null;

  // ── Reactive state reads ──
  // These return live $state references — Svelte 5 tracks them automatically.

  /** Current radio state (frequency, mode, meters, etc.) */
  get state(): ServerState | null {
    return radio.current;
  }

  /** Radio capabilities (modes, filters, features, etc.) */
  get caps(): Capabilities | null {
    return getCapabilities();
  }

  /** Connection health — individual reactive getters to avoid object allocation. */
  get connectionStatus(): 'connected' | 'partial' | 'disconnected' {
    return getConnectionStatus();
  }

  get connectionHttp(): boolean { return getHttpConnected(); }
  get connectionWs(): boolean { return getWsConnected(); }
  get connectionAudio(): boolean { return isAudioConnected(); }
  get connectionStale(): boolean { return isStale(); }
  get connectionReconnecting(): boolean { return isReconnecting(); }
  get radioStatus(): string { return getRadioStatus(); }
  get radioPowerOn(): boolean | null { return getRadioPowerOn(); }

  /**
   * Connection snapshot (for contexts that need all fields at once).
   * Prefer individual getters in $derived for better Svelte 5 reactivity.
   */
  get connection(): ConnectionSnapshot {
    return {
      status: getConnectionStatus(),
      http: getHttpConnected(),
      ws: getWsConnected(),
      audio: isAudioConnected(),
      stale: isStale(),
      reconnecting: isReconnecting(),
      radioStatus: getRadioStatus(),
      radioPowerOn: getRadioPowerOn(),
    };
  }

  /** Audio UI state — returns the live $state object directly. */
  get audio() {
    return getAudioState();
  }

  /** Whether the runtime has a radio connection. */
  get connected(): boolean {
    return isConnected();
  }

  // ── System controller ──

  /** System actions (power, connect/disconnect, frequency identification). */
  get system() {
    return systemController;
  }

  // ── Scope controller ──

  /** Single owner of the audio-scope WS channel. Subscribe to receive parsed frames. */
  get scope(): ScopeController {
    return scopeController;
  }

  // ── Bootstrap ──

  /**
   * Initialize the full transport stack: capabilities → polling → WebSocket → subscribe.
   *
   * Idempotent: if already started, returns the existing cleanup function without
   * re-running any transport calls. If the previous attempt threw, the flag is not
   * set and bootstrap can be retried.
   *
   * @returns A cleanup function that stops polling when called.
   */
  async bootstrap(): Promise<() => void> {
    if (this._bootstrapCleanup !== null) {
      return this._bootstrapCleanup;
    }

    // 1. Fetch capabilities and push into the store.
    const caps = await fetchCapabilities();
    setCapabilities(caps);

    // 2. Register polling lifecycle with SystemController so connect/disconnect works.
    systemController.registerPolling(() =>
      startPolling((state) => { setRadioState(state); }, 1000),
    );

    // 3. Start polling and hand the stop handle to SystemController.
    const stopPolling = startPolling((state) => { setRadioState(state); }, 1000);
    systemController.setStopPolling(stopPolling);

    // 4. Open the control WebSocket channel.
    connect('/api/v1/ws');

    // 5. Subscribe to the events stream (re-sent automatically on reconnect by WsChannel).
    sendRaw({ type: 'subscribe', streams: ['events'] });

    // Only latch as started after the entire chain succeeds.
    this._bootstrapCleanup = stopPolling;
    return stopPolling;
  }

  // ── Command dispatch ──

  /** Send a command to the radio backend. */
  send(name: string, params?: Record<string, unknown>): void {
    sendCommand(name, params ?? {});
  }

  // ── Optimistic state patches ──

  /** Apply an optimistic patch to the active receiver's state. */
  patchActiveReceiver(patch: Partial<ReceiverState>, lock?: boolean): void {
    patchActiveReceiver(patch, lock);
  }

  /** Apply an optimistic patch to the top-level radio state. */
  patchState(patch: Partial<ServerState>): void {
    patchRadioState(patch);
  }

  // ── Audio control ──

  startRx(): void {
    audioManager.startRx();
  }

  stopRx(): void {
    audioManager.stopRx();
  }

  setRxVolume(v: number): void {
    audioManager.setRxVolume(v);
  }

  async startTx(): Promise<string | null> {
    return audioManager.startTx();
  }

  stopTx(): void {
    audioManager.stopTx();
  }

  setVolume(v: number): void {
    setVolume(v);
  }

  setMuted(v: boolean): void {
    setMuted(v);
  }

  toggleMute(): void {
    toggleMute();
  }
}

/** Singleton runtime instance. */
export const runtime = new FrontendRuntime();
