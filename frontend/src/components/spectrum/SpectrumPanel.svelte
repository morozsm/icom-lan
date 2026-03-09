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
  let enableAvg = $state(true);
  let enablePeakHold = $state(true);
  let refLevel = $state(0);
  let colorScheme = $state<ColorSchemeName>('classic');
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
  <div class="spectrum-with-scales">
    <div class="db-scale">
      {#each DB_TICKS as tick}
        <div class="tick" style="top: {tick.position}%">{tick.label}</div>
      {/each}
    </div>
    <div class="spectrum-area">
      <SpectrumCanvas data={scopePixels} options={spectrumOptions} {spanHz} {enableAvg} {enablePeakHold} onRegisterPush={(fn) => spectrumPush = fn} />
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
  <div class="spectrum-controls">
    <label class="spectrum-option">
      <input type="checkbox" bind:checked={enableAvg} />
      Avg
    </label>
    <label class="spectrum-option">
      <input type="checkbox" bind:checked={enablePeakHold} />
      Peak
    </label>
    <label class="ref-level-control">
      Ref
      <input
        type="range"
        min="-30"
        max="30"
        step="5"
        value={refLevel}
        oninput={(e) => (refLevel = +(e.target as HTMLInputElement).value)}
      />
      <span class="value">{refLevel > 0 ? '+' : ''}{refLevel}</span>
    </label>
    <label class="color-scheme-selector">
      Colors
      <select bind:value={colorScheme}>
        <option value="classic">Classic</option>
        <option value="thermal">Thermal</option>
        <option value="grayscale">Gray</option>
      </select>
    </label>
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
  }

  .spectrum-controls {
    position: absolute;
    top: var(--space-2);
    right: 36px;
    z-index: 10;
    display: flex;
    gap: var(--space-2);
  }

  .spectrum-option {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.75rem;
    color: var(--text-muted);
    cursor: pointer;
    background: rgba(0, 0, 0, 0.5);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    padding: 2px 6px;
    user-select: none;
  }

  .spectrum-option:hover {
    color: var(--text);
  }

  .spectrum-option input[type='checkbox'] {
    margin: 0;
    cursor: pointer;
  }

  .ref-level-control {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.75rem;
    color: var(--text-muted);
    background: rgba(0, 0, 0, 0.5);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    padding: 2px 6px;
  }

  .ref-level-control input[type='range'] {
    width: 60px;
    cursor: pointer;
    accent-color: var(--accent);
  }

  .ref-level-control .value {
    min-width: 28px;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .color-scheme-selector {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.75rem;
    color: var(--text-muted);
    background: rgba(0, 0, 0, 0.5);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    padding: 2px 6px;
  }

  .color-scheme-selector select {
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0;
  }

  .color-scheme-selector select:focus {
    outline: none;
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
