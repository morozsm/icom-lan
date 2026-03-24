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
    type ColorSchemeName,
  } from '../../lib/renderers/waterfall-renderer';
  import { getChannel, onMessage, sendCommand } from '../../lib/transport/ws-client';
  import { setScopeConnected, markScopeFrame } from '../../lib/stores/connection.svelte';
  import { type DxSpot } from '../../lib/types/protocol';
  import { patchActiveReceiver, radio } from '../../lib/stores/radio.svelte';
  import { getFilterWidthHz } from '../../lib/utils/filter-width';
  import { snapToStep } from '../../lib/stores/tuning.svelte';
  import SpectrumToolbar from './SpectrumToolbar.svelte';
  import BandPlanOverlay from './BandPlanOverlay.svelte';
  import { deriveIfShift } from '../../components-v2/panels/filter-controls';
  import { getCapabilities } from '../../lib/stores/capabilities.svelte';
  import { resolveFilterModeConfig } from '../../components-v2/wiring/state-adapter';
  import {
    canResizeFromRightEdge,
    getFilterWidthFromRightEdgePx,
    getPassbandGeometry,
  } from './passband-geometry';

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
  let enableAvg = $state(true);
  let enablePeakHold = $state(true);
  let refLevel = $state(0);
  let colorScheme = $state<ColorSchemeName>('classic');
  let spectrumPush: ((data: Uint8Array) => void) | null = null;
  let waterfallPush: ((data: Uint8Array) => void) | null = null;
  let startFreq = $state(0);
  let endFreq = $state(0);
  let fullscreen = $state(false);
  let showBandPlan = $state(true);
  let dxSpots = $state<DxSpot[]>([]);
  let spectrumArea: HTMLDivElement | null = null;
  let waterfallContent: HTMLDivElement | null = null;
  let resizingPassband = $state(false);
  let resizingPointerId = $state<number | null>(null);

  let centerHz = $derived(
    startFreq > 0 && endFreq > startFreq ? (startFreq + endFreq) / 2 : 0,
  );
  let spanHz = $derived(endFreq > startFreq ? endFreq - startFreq : 0);

  // Active receiver data for passband overlay
  let rx = $derived(radio.current?.active === 'SUB' ? radio.current?.sub : radio.current?.main);
  let tuneHz = $derived(rx?.freqHz ?? 0);
  let rxMode = $derived(rx?.mode ?? '');
  let passbandHz = $derived(rx?.filterWidth ?? getFilterWidthHz(rxMode, rx?.filter ?? 1));
  let passbandShiftHz = $derived(deriveIfShift(rx?.pbtInner ?? 0, rx?.pbtOuter ?? 0));
  let canResizePassband = $derived(canResizeFromRightEdge(rxMode));
  let filterConfig = $derived(resolveFilterModeConfig(getCapabilities(), rxMode, rx?.dataMode));
  let filterMaxHz = $derived(filterConfig?.maxHz ?? 10000);
  let filterStepHz = $derived(filterConfig?.stepHz ?? filterConfig?.segments?.[0]?.stepHz ?? 100);

  let spectrumOptions = $derived<SpectrumOptions>({
    ...defaultSpectrumOptions,
    spanHz,
    centerHz,
    tuneHz,
    passbandHz,
    passbandShiftHz,
    mode: rxMode,
  });

  let waterfallOptions = $derived<WaterfallOptions>({
    ...defaultWaterfallOptions,
    spanHz,
    centerHz,
    refLevel,
    colorScheme,
  });

  // --- Scale helpers ---
  function formatFreqOffset(hz: number): string {
    if (hz === 0) return '0';
    const absHz = Math.abs(hz);
    const sign = hz < 0 ? '-' : '+';
    if (absHz >= 1e6) return `${sign}${(absHz / 1e6).toFixed(1)}M`;
    if (absHz >= 1e3) return `${sign}${(absHz / 1e3).toFixed(0)}k`;
    return `${sign}${absHz}`;
  }

  const DB_TICKS = [
    { position: 0, label: '0' },
    { position: 33, label: '-20' },
    { position: 67, label: '-40' },
    { position: 100, label: '-60' },
  ];

  let freqTicks = $derived(
    spanHz > 0
      ? [-1, -0.5, 0, 0.5, 1].map((ratio) => ({
          position: (ratio + 1) * 50,
          label: formatFreqOffset((spanHz * ratio) / 2),
        }))
      : [],
  );

  // Passband overlay position derived from the same geometry as the spectrum renderer.
  let passbandOverlay = $derived(
    getPassbandGeometry(rxMode, passbandHz, passbandShiftHz, spanHz, 100),
  );
  let pbWidthPct = $derived(passbandOverlay?.widthPx ?? 0);
  let pbLeftPct = $derived(passbandOverlay?.leftPx ?? 0);
  let pbRightPct = $derived(passbandOverlay?.rightPx ?? 0);

  function applyFilterWidth(width: number): void {
    if (width === passbandHz) {
      return;
    }

    patchActiveReceiver({ filterWidth: width }, true);
    sendCommand('set_filter_width', { width });
  }

  function handlePassbandResizeStart(event: PointerEvent): void {
    if (!canResizePassband || !waterfallContent) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    resizingPassband = true;
    resizingPointerId = event.pointerId;
    (event.currentTarget as HTMLElement | null)?.setPointerCapture?.(event.pointerId);
  }

  function handleWindowPointerMove(event: PointerEvent): void {
    if (!resizingPassband || resizingPointerId !== event.pointerId || !waterfallContent) {
      return;
    }

    const rect = waterfallContent.getBoundingClientRect();
    const relativeX = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
    const nextWidth = getFilterWidthFromRightEdgePx(
      rxMode,
      passbandShiftHz,
      spanHz,
      rect.width,
      relativeX,
      filterMaxHz,
      filterStepHz,
    );

    if (nextWidth !== null) {
      applyFilterWidth(nextWidth);
    }
  }

  function stopPassbandResize(event?: PointerEvent): void {
    if (event && resizingPointerId !== null && event.pointerId !== resizingPointerId) {
      return;
    }

    resizingPassband = false;
    resizingPointerId = null;
  }

  // --- Click-to-tune ---
  function handleTune(hz: number): void {
    const freq = snapToStep(Math.round(hz));
    if (freq <= 0) return;
    const receiver = radio.current?.active === 'SUB' ? 1 : 0;
    sendCommand('set_freq', { freq, receiver });
  }

  // --- Lifecycle: connect scope WS + subscribe to DX spots ---
  onMount(() => {
    // Scope data arrives on its own WebSocket channel
    const scopeCh = getChannel('scope');
    scopeCh.connect('/api/v1/scope');
    const unsubState = scopeCh.onStateChange((s) => {
      setScopeConnected(s === 'connected');
    });
    const unsubBinary = scopeCh.onBinary((buf) => {
      markScopeFrame();
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
      unsubState();
      unsubBinary();
      unsubMsg();
      scopeCh.disconnect();
    };
  });
</script>

<svelte:window onpointermove={handleWindowPointerMove} onpointerup={stopPassbandResize} onpointercancel={stopPassbandResize} />

<div class="spectrum-panel" class:fullscreen>
  <SpectrumToolbar bind:enableAvg bind:enablePeakHold bind:refLevel bind:colorScheme bind:fullscreen bind:showBandPlan />
  <div class="spectrum-with-scales">
    <div class="db-scale">
      {#each DB_TICKS as tick}
        <div class="tick" style="top: {tick.position}%">{tick.label}</div>
      {/each}
    </div>
    <div class="spectrum-area" bind:this={spectrumArea}>
      <SpectrumCanvas data={scopePixels} options={spectrumOptions} {spanHz} {enableAvg} {enablePeakHold} onRegisterPush={(fn) => spectrumPush = fn} />
      {#if spanHz > 0 && pbWidthPct > 0 && canResizePassband}
        <button
          type="button"
          class="passband-resize-zone"
          class:active={resizingPassband}
          style="left:{pbRightPct}%"
          onpointerdown={handlePassbandResizeStart}
          aria-label="Resize filter width"
          title="Drag to resize filter width"
        ></button>
      {/if}
    </div>
  </div>
  {#if freqTicks.length > 0}
    <div class="freq-axis">
      {#each freqTicks as tick}
        <div class="tick" style="left: {tick.position}%">{tick.label}</div>
      {/each}
    </div>
  {/if}
  <div class="waterfall-area">
    <div class="waterfall-scale"></div>
    <div class="waterfall-content" bind:this={waterfallContent}>
      <WaterfallCanvas options={waterfallOptions} onFreqClick={handleTune} onRegisterPush={(fn) => waterfallPush = fn} />
      <BandPlanOverlay {startFreq} {endFreq} visible={showBandPlan} />
      <DxOverlay spots={dxSpots} {startFreq} {endFreq} onTune={handleTune} />
      <!-- Tuning + passband indicator overlays the waterfall -->
      {#if spanHz > 0}
        {#if pbWidthPct > 0}
          <div class="passband-overlay" style="left:{pbLeftPct}%;width:{pbWidthPct}%"></div>
          {#if canResizePassband}
            <button
              type="button"
              class="passband-resize-zone"
              class:active={resizingPassband}
              style="left:{pbRightPct}%"
              onpointerdown={handlePassbandResizeStart}
              aria-label="Resize filter width"
              title="Drag to resize filter width"
            ></button>
          {/if}
        {/if}
        <div class="tune-line" style="left:50%"></div>
      {/if}
    </div>
  </div>
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

  .spectrum-with-scales {
    flex: 0 0 30%;
    min-height: 0;
    display: flex;
    border-bottom: 1px solid var(--panel-border);
  }

  .db-scale {
    flex: 0 0 44px;
    position: relative;
    background: var(--panel);
    border-right: 1px solid var(--panel-border);
  }

  .db-scale .tick {
    position: absolute;
    right: 6px;
    transform: translateY(-50%);
    font-size: 10px;
    color: var(--text-muted);
    line-height: 1;
    white-space: nowrap;
  }

  .spectrum-area {
    flex: 1;
    min-width: 0;
    min-height: 0;
    position: relative;
  }

  .freq-axis {
    flex: 0 0 20px;
    position: relative;
    background: var(--panel);
    border-bottom: 1px solid var(--panel-border);
  }

  .freq-axis .tick {
    position: absolute;
    transform: translateX(-50%);
    font-size: 10px;
    color: var(--text-muted);
    line-height: 20px;
    white-space: nowrap;
    padding-left: 44px; /* offset for db-scale width */
  }

  .freq-axis .tick:first-child {
    transform: translateX(0);
  }

  .freq-axis .tick:last-child {
    transform: translateX(-100%);
  }

  .waterfall-area {
    flex: 1 1 70%;
    min-height: 0;
    position: relative;
    display: flex;
  }

  .waterfall-scale {
    flex: 0 0 44px;
    background: var(--panel);
    border-right: 1px solid var(--panel-border);
  }

  .waterfall-content {
    flex: 1 1 auto;
    min-width: 0;
    position: relative;
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

  .passband-resize-zone {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 14px;
    transform: translateX(-50%);
    cursor: ew-resize;
    z-index: 6;
    pointer-events: auto;
    padding: 0;
    margin: 0;
    border: 0;
    background: transparent;
  }

  .passband-resize-zone:focus-visible {
    outline: none;
  }
</style>
