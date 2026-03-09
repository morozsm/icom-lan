<script lang="ts">
  import { onMount } from 'svelte';
  import SpectrumCanvas from './SpectrumCanvas.svelte';
  import WaterfallCanvas from './WaterfallCanvas.svelte';
  import DxOverlay from './DxOverlay.svelte';
  import {
    defaultSpectrumOptions,
    type SpectrumOptions,
  } from '../../lib/renderers/spectrum-renderer';
  import {
    defaultWaterfallOptions,
    type WaterfallOptions,
  } from '../../lib/renderers/waterfall-renderer';
  import { getChannel, onMessage, sendCommand } from '../../lib/transport/ws-client';
  import { type DxSpot } from '../../lib/types/protocol';
  import { radio } from '../../lib/stores/radio.svelte';
  import { getFilterWidthHz } from '../../lib/utils/filter-width';
  import { snapToStep } from '../../lib/stores/tuning.svelte';

  // --- Scope frame binary protocol ---
  interface ScopeFrame {
    receiver: number;
    startFreq: number;
    endFreq: number;
    pixels: Uint8Array;
  }

  function parseScopeFrame(buf: ArrayBuffer): ScopeFrame | null {
    const view = new DataView(buf);
    // Magic byte 0x01, minimum 16-byte header
    if (view.byteLength < 16 || view.getUint8(0) !== 0x01) return null;
    const receiver = view.getUint8(1);
    const startFreq = view.getUint32(3, true);
    const endFreq = view.getUint32(7, true);
    const pixelCount = view.getUint16(14, true);
    if (16 + pixelCount > view.byteLength) return null;
    return {
      receiver,
      startFreq,
      endFreq,
      pixels: new Uint8Array(buf, 16, pixelCount),
    };
  }

  // --- Component state ---
  let scopePixels = $state<Uint8Array | null>(null);
  let spectrumPush: ((data: Uint8Array) => void) | null = null;
  let waterfallPush: ((data: Uint8Array) => void) | null = null;
  let startFreq = $state(0);
  let endFreq = $state(0);
  let fullscreen = $state(false);
  let dxSpots = $state<DxSpot[]>([]);

  let centerHz = $derived(
    startFreq > 0 && endFreq > startFreq ? (startFreq + endFreq) / 2 : 0,
  );
  let spanHz = $derived(endFreq > startFreq ? endFreq - startFreq : 0);

  // Active receiver data for passband overlay
  let rx = $derived(radio.current?.active === 'SUB' ? radio.current?.sub : radio.current?.main);
  let tuneHz = $derived(rx?.freqHz ?? 0);
  let rxMode = $derived(rx?.mode ?? '');
  let passbandHz = $derived(getFilterWidthHz(rxMode, rx?.filter ?? 1));

  let spectrumOptions = $derived<SpectrumOptions>({
    ...defaultSpectrumOptions,
    spanHz,
    centerHz,
    tuneHz,
    passbandHz,
    mode: rxMode,
  });

  let waterfallOptions = $derived<WaterfallOptions>({
    ...defaultWaterfallOptions,
    spanHz,
    centerHz,
  });

  // Passband overlay position — always centered in center scope mode
  let tunePct = $derived(50); // center mode: VFO freq is always at center
  let pbWidthPct = $derived(spanHz > 0 && passbandHz > 0 ? (passbandHz / spanHz) * 100 : 0);
  let pbLeftPct = $derived(() => {
    const m = rxMode?.toUpperCase() ?? '';
    if (m === 'LSB') return tunePct - pbWidthPct;
    if (m === 'CW' || m === 'CW-R' || m === 'RTTY' || m === 'RTTY-R' || m === 'AM')
      return tunePct - pbWidthPct / 2;
    return tunePct; // USB default
  });

  // --- Click-to-tune ---
  function handleTune(hz: number): void {
    const freq = snapToStep(Math.round(hz));
    if (freq <= 0) return;
    const receiver = radio.current?.active === 'SUB' ? 1 : 0;
    sendCommand('set_freq', { freq, receiver });
  }

  // --- Fullscreen toggle ---
  function toggleFullscreen(): void {
    fullscreen = !fullscreen;
  }

  // --- Lifecycle: connect scope WS + subscribe to DX spots ---
  onMount(() => {
    // Scope data arrives on its own WebSocket channel
    const scopeCh = getChannel('scope');
    scopeCh.connect('/api/v1/scope');
    const unsubBinary = scopeCh.onBinary((buf) => {
      const frame = parseScopeFrame(buf);
      if (!frame) return;
      if (frame.startFreq !== startFreq || frame.endFreq !== endFreq) {
        startFreq = frame.startFreq;
        endFreq = frame.endFreq;
      }
      scopePixels = frame.pixels;
      // Direct push to both children — bypasses Svelte reactivity
      // which can't track Uint8Array changes at 100+ fps
      spectrumPush?.(frame.pixels);
      waterfallPush?.(frame.pixels);
    });

    // DX spots come through the main control WebSocket as JSON messages
    const unsubMsg = onMessage((msg) => {
      if (msg.type === 'dx_spot') {
        const spot = (msg as unknown as { spot: DxSpot }).spot;
        if (spot) dxSpots = [...dxSpots.slice(-49), spot];
      } else if (msg.type === 'dx_spots') {
        const list = (msg as unknown as { spots: DxSpot[] }).spots;
        if (Array.isArray(list)) dxSpots = list;
      }
    });

    return () => {
      unsubBinary();
      unsubMsg();
      scopeCh.disconnect();
    };
  });
</script>

<div class="spectrum-panel" class:fullscreen>
  <div class="spectrum-area">
    <SpectrumCanvas data={scopePixels} options={spectrumOptions} onRegisterPush={(fn) => spectrumPush = fn} />
  </div>
  <div class="waterfall-area">
    <WaterfallCanvas data={scopePixels} options={waterfallOptions} onFreqClick={handleTune} onRegisterPush={(fn) => waterfallPush = fn} />
    <DxOverlay spots={dxSpots} {startFreq} {endFreq} onTune={handleTune} />
    <!-- Tuning + passband indicator overlays the waterfall -->
    {#if spanHz > 0}
      {#if pbWidthPct > 0}
        <div class="passband-overlay" style="left:{pbLeftPct()}%;width:{pbWidthPct}%"></div>
      {/if}
      <div class="tune-line" style="left:50%"></div>
    {/if}
  </div>
  <button class="fullscreen-btn" onclick={toggleFullscreen} title="Toggle fullscreen">
    {fullscreen ? '✕' : '⛶'}
  </button>
</div>

<style>
  .spectrum-panel {
    position: relative;
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    overflow: hidden;
  }

  .spectrum-panel.fullscreen {
    position: fixed;
    inset: 0;
    z-index: 100;
    border-radius: 0;
    border: none;
  }

  .spectrum-area {
    flex: 0 0 40%;
    min-height: 0;
    border-bottom: 1px solid var(--panel-border);
  }

  .waterfall-area {
    flex: 1 1 60%;
    min-height: 0;
    position: relative;
  }

  .fullscreen-btn {
    position: absolute;
    top: var(--space-2);
    right: var(--space-2);
    z-index: 10;
    background: rgba(0, 0, 0, 0.5);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 0.875rem;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    padding: 0;
  }

  .fullscreen-btn:hover {
    color: var(--text);
    border-color: var(--accent);
  }

  /* Tuning line + passband overlay on waterfall */
  .tune-line {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: rgba(239, 68, 68, 0.75);
    pointer-events: none;
    z-index: 5;
    transform: translateX(-0.5px);
  }

  .passband-overlay {
    position: absolute;
    top: 0;
    bottom: 0;
    background: rgba(59, 130, 246, 0.15);
    border-left: 1px dashed rgba(59, 130, 246, 0.4);
    border-right: 1px dashed rgba(59, 130, 246, 0.4);
    pointer-events: none;
    z-index: 4;
  }
</style>
