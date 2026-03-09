<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import VfoDisplay from '../vfo/VfoDisplay.svelte';
  import ReceiverSwitch from '../controls/ReceiverSwitch.svelte';
  import SMeter from '../meters/SMeter.svelte';
  import SpectrumPanel from '../spectrum/SpectrumPanel.svelte';
  import BandSelector from '../controls/BandSelector.svelte';
  import ModeSelector from '../controls/ModeSelector.svelte';
  import FilterSelector from '../controls/FilterSelector.svelte';
  import FeatureToggles from '../controls/FeatureToggles.svelte';
  import BottomBar from '../shared/BottomBar.svelte';
  import Toast from '../shared/Toast.svelte';
  import TuningWheel from '../controls/TuningWheel.svelte';
  import StepSelector from '../controls/StepSelector.svelte';


  import { radio } from '../../lib/stores/radio.svelte';
  import { hasDualReceiver, getCapabilities } from '../../lib/stores/capabilities.svelte';
  import { getConnectionStatus } from '../../lib/stores/connection.svelte';
  import { sendCommand } from '../../lib/transport/ws-client';
  import { applyModeDefault } from '../../lib/stores/tuning.svelte';

  let state = $derived(radio.current);
  let main = $derived(radio.current?.main ?? null);
  let active = $derived(radio.current?.active === 'SUB' ? (radio.current?.sub ?? null) : (radio.current?.main ?? null));
  let activeRx = $derived(state?.active ?? 'MAIN');
  let isDualRx = $derived(hasDualReceiver());

  // Auto step based on mode
  let currentMode = $derived(active?.mode ?? '');
  $effect(() => {
    if (currentMode) applyModeDefault(currentMode);
  });
  let caps = $derived(getCapabilities());
  let connectionStatus = $derived(getConnectionStatus());
  let modelName = $derived(caps?.model ?? 'Radio');
  let isConnected = $derived(connectionStatus === 'connected');
  let isPartial = $derived(connectionStatus === 'partial');

  // Fullscreen spectrum — auto on landscape orientation
  let spectrumFullscreen = $state(false);
  let isLandscape = $state(false);

  onMount(() => {
    const mql = window.matchMedia('(orientation: landscape)');
    isLandscape = mql.matches;
    spectrumFullscreen = mql.matches;
    if (mql.matches) requestFullscreen();

    function onChange(e: MediaQueryListEvent) {
      isLandscape = e.matches;
      spectrumFullscreen = e.matches;
      if (e.matches) {
        requestFullscreen();
      } else {
        exitFullscreen();
      }
    }
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  });

  function requestFullscreen() {
    const el = document.documentElement;
    if (document.fullscreenElement) return;
    el.requestFullscreen?.().catch(() => {});
  }

  function exitFullscreen() {
    if (!document.fullscreenElement) return;
    document.exitFullscreen?.().catch(() => {});
  }

  // UTC clock — ticks every minute
  let utcTime = $state(nowUtc());

  function nowUtc(): string {
    return new Date().toISOString().slice(11, 16);
  }

  $effect(() => {
    utcTime = nowUtc();
    const id = setInterval(() => { utcTime = nowUtc(); }, 60_000);
    return () => clearInterval(id);
  });

  function handleTune(newFreq: number) {
    const rx = activeRx === 'MAIN' ? 0 : 1;
    sendCommand('set_freq', { freq: newFreq, receiver: rx });
  }

  function handleReceiverSwitch(receiver: 'MAIN' | 'SUB') {
    sendCommand('select_vfo', { vfo: receiver === 'MAIN' ? 'A' : 'B' });
  }

  function handleDwToggle() {
    sendCommand('set_dual_watch', { on: !(state?.dualWatch ?? false) });
  }

  function closeSpectrum() {
    spectrumFullscreen = false;
  }
</script>

<div class="mobile-layout">
  <!-- ── Status bar ── -->
  <header class="status-bar">
    <span
      class="status-dot"
      class:connected={isConnected}
      class:partial={isPartial}
      title={connectionStatus}
    ></span>
    <span class="radio-name">{modelName}</span>
    {#if state?.ptt}
      <span class="tx-badge">TX</span>
    {/if}
    <span class="spacer"></span>
    <span class="utc-clock">{utcTime} UTC</span>
  </header>

  <!-- ── Main scrollable stack ── -->
  <main class="stack">
    <!-- VFO section: active receiver only -->
    <section class="vfo-section">
      <div class="vfo-row">
        {#if active}
          <VfoDisplay
            label={activeRx === 'MAIN' ? 'VFO A' : 'VFO B'}
            freq={active.freqHz}
            mode={active.mode}
            filter={active.filter}
            active={true}
            dataMode={active.dataMode}
            ontune={handleTune}
          />
        {:else if main}
          <VfoDisplay
            label="VFO A"
            freq={main.freqHz}
            mode={main.mode}
            filter={main.filter}
            active={true}
            dataMode={main.dataMode}
            ontune={handleTune}
          />
        {:else if state}
          <div class="vfo-placeholder">Loading VFO…</div>
        {:else}
          <div class="vfo-placeholder">Connecting…</div>
        {/if}
      </div>

      {#if isDualRx}
        {@const inactiveRx = activeRx === 'MAIN' ? radio.current?.sub : radio.current?.main}
        <div class="receiver-row">
          <ReceiverSwitch
            active={activeRx}
            dualWatch={state?.dualWatch ?? false}
            hasDualReceiver={isDualRx}
            onswitch={handleReceiverSwitch}
            ondwtoggle={handleDwToggle}
          />
          {#if inactiveRx}
            <span class="inactive-vfo" onclick={() => handleReceiverSwitch(activeRx === 'MAIN' ? 'SUB' : 'MAIN')}>
              {activeRx === 'MAIN' ? 'B' : 'A'}: {(inactiveRx.freqHz / 1_000_000).toFixed(6)} {inactiveRx.mode}
            </span>
          {/if}
        </div>
      {/if}
    </section>

    <!-- Spectrum section — fullscreen on landscape -->
    {#if !spectrumFullscreen}
      <div class="spectrum-section">
        <SpectrumPanel />
      </div>
    {:else}
      <div class="spectrum-placeholder" aria-hidden="true"></div>
    {/if}

    <!-- S-meter + selectors + toggles -->
    <section class="controls-section">
      {#if main}
        <div class="smeter-row">
          <SMeter value={main.sMeter} label="S" />
        </div>
      {/if}

      <div class="selectors-row">
        <BandSelector />
        <ModeSelector />
        <FilterSelector />
      </div>

      <div class="toggles-row">
        <FeatureToggles />
      </div>
    </section>
  </main>

  <!-- ── Tuning wheel + Bottom bar ── -->
  <TuningWheel />
  <BottomBar />
</div>

<!-- ── Spectrum fullscreen overlay ── -->
<!-- Toast notifications — rendered in fixed position overlay -->
<Toast />

{#if spectrumFullscreen}
  <div
    class="spectrum-overlay"
    role="dialog"
    aria-label="Spectrum landscape"
    transition:fade={{ duration: 200 }}
  >
    <!-- Left sidebar: VFO info + controls -->
    <div class="overlay-sidebar">
      <div class="overlay-vfo">
        {#if active}
          <div class="overlay-freq">{(active.freqHz / 1_000_000).toFixed(6)}</div>
          <div class="overlay-info">{active.mode} · FIL{active.filter}</div>
        {/if}
      </div>

      <div class="overlay-controls">
        <ModeSelector />
        <FilterSelector />
        <FeatureToggles />
      </div>

      <div class="overlay-bottom">
        <BottomBar />
      </div>
    </div>

    <!-- Spectrum fills the rest -->
    <div class="overlay-spectrum">
      <SpectrumPanel />
    </div>
  </div>
{/if}

<style>
  /* ── Root layout ── */
  .mobile-layout {
    display: flex;
    flex-direction: column;
    height: 100dvh;
    background-color: var(--bg);
    color: var(--text);
    overflow: hidden;
  }

  /* ── Status bar ── */
  .status-bar {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 0 var(--space-4);
    height: 36px;
    background-color: var(--panel);
    border-bottom: 1px solid var(--panel-border);
    font-family: var(--font-mono);
    font-size: 0.8rem;
    flex-shrink: 0;
  }

  .radio-name {
    font-weight: 700;
    color: var(--text);
    letter-spacing: 0.05em;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--danger);
    flex-shrink: 0;
    transition: background 0.3s;
  }

  .status-dot.connected {
    background: var(--success);
  }

  .status-dot.partial {
    background: var(--warning);
  }

  .tx-badge {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #fff;
    background: var(--danger);
    padding: 1px 5px;
    border-radius: 3px;
    animation: tx-pulse 1s ease-in-out infinite;
  }

  .spacer {
    flex: 1;
  }

  .utc-clock {
    color: var(--text-muted);
    letter-spacing: 0.04em;
  }

  /* ── Scrollable main stack ── */
  .stack {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    padding: var(--space-1) var(--space-2);
  }

  /* ── VFO section ── */
  .vfo-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    flex-shrink: 0;
  }

  .vfo-row {
    flex: 1;
  }

  .vfo-placeholder {
    font-family: var(--font-mono);
    font-size: 0.875rem;
    color: var(--text-muted);
    padding: var(--space-3);
    border: 1px dashed var(--panel-border);
    border-radius: var(--radius);
    text-align: center;
  }

  .receiver-row {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--space-2);
  }

  .inactive-vfo {
    font-family: var(--font-mono);
    font-size: 0.625rem;
    color: var(--text-muted);
    cursor: pointer;
    opacity: 0.6;
    transition: opacity 0.15s;
    white-space: nowrap;
  }

  .inactive-vfo:hover {
    opacity: 1;
  }

  /* ── Spectrum section ── */
  .spectrum-section {
    flex: 1 1 0;
    min-height: 120px;
    max-height: 50vh;
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    overflow: hidden;
    position: relative;
    outline: none;
  }

  .spectrum-section:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  .spectrum-hint {
    position: absolute;
    bottom: var(--space-2);
    right: var(--space-2);
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.35);
    pointer-events: none;
    user-select: none;
  }

  .spectrum-placeholder {
    height: 180px;
    flex-shrink: 0;
  }

  /* ── Controls section ── */
  .controls-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    padding: var(--space-2);
    flex-shrink: 0;
  }

  .smeter-row {
    /* SMeter already has its own layout */
  }

  .selectors-row {
    display: flex;
    gap: var(--space-2);
    align-items: center;
    flex-wrap: wrap;
  }

  .toggles-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
  }

  /* ── Spectrum fullscreen overlay ── */
  /* ── Landscape overlay ── */
  .spectrum-overlay {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: var(--bg);
    display: flex;
    flex-direction: row;
  }

  .overlay-sidebar {
    width: 220px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    background: var(--panel);
    border-right: 1px solid var(--panel-border);
    overflow-y: auto;
  }

  .overlay-vfo {
    padding: var(--space-2) var(--space-3);
    border-bottom: 1px solid var(--panel-border);
  }

  .overlay-freq {
    font-family: var(--font-mono);
    font-size: 1.125rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: 0.04em;
  }

  .overlay-info {
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    color: var(--text-muted);
    margin-top: 2px;
  }

  .overlay-controls {
    flex: 1;
    padding: var(--space-2) var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    overflow-y: auto;
  }

  .overlay-bottom {
    border-top: 1px solid var(--panel-border);
  }

  .overlay-spectrum {
    flex: 1;
    overflow: hidden;
  }
</style>
