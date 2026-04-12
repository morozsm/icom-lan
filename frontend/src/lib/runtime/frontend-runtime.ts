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

import { radio, getRadioState, patchActiveReceiver, patchRadioState } from '$lib/stores/radio.svelte';
import { getCapabilities } from '$lib/stores/capabilities.svelte';
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
import { sendCommand } from '$lib/transport/ws-client';
import { audioManager } from '$lib/audio/audio-manager';

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

export interface AudioSnapshot {
  rxEnabled: boolean;
  txEnabled: boolean;
  volume: number;
  muted: boolean;
}

// ── Runtime class ──

class FrontendRuntime {
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

  /** Connection health snapshot. */
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

  /** Audio UI state (volume, mute, rx/tx enabled). */
  get audio(): AudioSnapshot {
    const s = getAudioState();
    return { rxEnabled: s.rxEnabled, txEnabled: s.txEnabled, volume: s.volume, muted: s.muted };
  }

  /** Whether the runtime has a radio connection. */
  get connected(): boolean {
    return isConnected();
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
