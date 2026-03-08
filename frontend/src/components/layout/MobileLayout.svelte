<script lang="ts">
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

  import {
    getRadioState,
    getMainReceiver,
    getActiveReceiver,
  } from '../../lib/stores/radio.svelte';
  import { hasDualReceiver, getCapabilities } from '../../lib/stores/capabilities.svelte';
  import { getConnectionStatus } from '../../lib/stores/connection.svelte';
  import { sendCommand } from '../../lib/transport/ws-client';

  let state = $derived(getRadioState());
  let main = $derived(getMainReceiver());
  let active = $derived(getActiveReceiver());
  let activeRx = $derived(state?.active ?? 'MAIN');
  let isDualRx = $derived(hasDualReceiver());
  let caps = $derived(getCapabilities());
  let connectionStatus = $derived(getConnectionStatus());
  let modelName = $derived(caps?.model ?? 'Radio');
  let isConnected = $derived(connectionStatus === 'connected');
  let isPartial = $derived(connectionStatus === 'partial');

  // Fullscreen spectrum overlay
  let spectrumFullscreen = $state(false);

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

  function openSpectrum() {
    spectrumFullscreen = true;
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
        {:else}
          <div class="vfo-placeholder">Connecting…</div>
        {/if}
      </div>

      {#if isDualRx}
        <div class="receiver-row">
          <ReceiverSwitch
            active={activeRx}
            dualWatch={state?.dualWatch ?? false}
            hasDualReceiver={isDualRx}
            onswitch={handleReceiverSwitch}
            ondwtoggle={handleDwToggle}
          />
        </div>
      {/if}
    </section>

    <!-- Spectrum section — tap to expand -->
    {#if !spectrumFullscreen}
      <div
        class="spectrum-section"
        onclick={openSpectrum}
        onkeydown={(e) => e.key === 'Enter' && openSpectrum()}
        role="button"
        tabindex="0"
        aria-label="Spectrum — tap to expand"
      >
        <SpectrumPanel />
        <div class="spectrum-hint">tap to expand</div>
      </div>
    {:else}
      <!-- Placeholder height so layout doesn't collapse -->
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

  <!-- ── Fixed bottom bar ── -->
  <BottomBar />
</div>

<!-- ── Spectrum fullscreen overlay ── -->
<!-- Toast notifications — rendered in fixed position overlay -->
<Toast />

{#if spectrumFullscreen}
  <div
    class="spectrum-overlay"
    role="dialog"
    aria-label="Spectrum fullscreen"
    transition:fade={{ duration: 200 }}
  >
    <!-- Thin VFO info strip at top of overlay -->
    <div class="overlay-header">
      {#if active}
        <span class="overlay-freq">
          {(active.freqHz / 1_000_000).toFixed(6)} MHz
        </span>
        <span class="overlay-mode">{active.mode} · FIL{active.filter}</span>
      {/if}
      <button
        class="overlay-close"
        onclick={closeSpectrum}
        aria-label="Close fullscreen spectrum"
      >✕</button>
    </div>

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
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-2);
    /* Leave room for fixed bottom bar */
    padding-bottom: var(--space-2);
  }

  /* ── VFO section ── */
  .vfo-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
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
    justify-content: flex-end;
  }

  /* ── Spectrum section ── */
  .spectrum-section {
    height: 180px;
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    overflow: hidden;
    cursor: pointer;
    position: relative;
    flex-shrink: 0;
    /* Remove default button outline, add focus ring */
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
    gap: var(--space-2);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    padding: var(--space-3);
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
  .spectrum-overlay {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: var(--bg);
    display: flex;
    flex-direction: column;
    transform-origin: center;
  }

  .overlay-header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: 0 var(--space-4);
    height: 44px;
    background: var(--panel);
    border-bottom: 1px solid var(--panel-border);
    font-family: var(--font-mono);
    flex-shrink: 0;
  }

  .overlay-freq {
    font-size: 1rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: 0.04em;
  }

  .overlay-mode {
    font-size: 0.8rem;
    color: var(--text-muted);
    flex: 1;
  }

  .overlay-close {
    min-width: 44px;
    min-height: 44px;
    background: none;
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 1rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s, border-color 0.15s;
  }

  .overlay-close:hover {
    color: var(--text);
    border-color: var(--text-muted);
  }

  .overlay-spectrum {
    flex: 1;
    overflow: hidden;
  }
</style>
