<script lang="ts">
  import { onMount } from 'svelte';
  import VfoDisplay from '../vfo/VfoDisplay.svelte';
  import ReceiverSwitch from '../controls/ReceiverSwitch.svelte';
  import SMeter from '../meters/SMeter.svelte';
  import PowerMeter from '../meters/PowerMeter.svelte';
  import SpectrumPanel from '../spectrum/SpectrumPanel.svelte';
  import BandSelector from '../controls/BandSelector.svelte';
  import ModeSelector from '../controls/ModeSelector.svelte';
  import FilterSelector from '../controls/FilterSelector.svelte';
  import FeatureToggles from '../controls/FeatureToggles.svelte';
  import AudioControls from '../audio/AudioControls.svelte';
  import AudioPanel from '../audio/AudioPanel.svelte';
  import PttButton from '../audio/PttButton.svelte';
  import StatusBar from '../shared/StatusBar.svelte';
  import Toast from '../shared/Toast.svelte';
  import DxClusterPanel from '../dx/DxClusterPanel.svelte';
  import StepSelector from '../controls/StepSelector.svelte';

  import { radio } from '../../lib/stores/radio.svelte';
  import { hasDualReceiver, hasTx } from '../../lib/stores/capabilities.svelte';
  import { getConnectionStatus } from '../../lib/stores/connection.svelte';
  import { sendCommand } from '../../lib/transport/ws-client';
  import { setupKeyboard } from '../../lib/actions/keyboard';
  import { applyModeDefault, tuneBy } from '../../lib/stores/tuning.svelte';

  let state = $derived(radio.current);
  let main = $derived(radio.current?.main ?? null);
  let sub = $derived(radio.current?.sub ?? null);
  let activeRx = $derived(radio.current?.active ?? 'MAIN');

  let isDualRx = $derived(hasDualReceiver());
  let isTx = $derived(hasTx());
  let connectionStatus = $derived(getConnectionStatus());
  let isDisconnected = $derived(connectionStatus === 'disconnected');
  let isReconnecting = $derived(connectionStatus === 'partial');

  // Auto-select tuning step when mode changes
  let currentMode = $derived(main?.mode ?? '');
  $effect(() => {
    if (currentMode) applyModeDefault(currentMode);
  });

  onMount(() => {
    const cleanupKb = setupKeyboard();

    // Arrow key tuning — debounced to prevent race conditions from rapid keypresses.
    // Keypresses accumulate delta; a single command is sent after 100ms of inactivity.
    let tuningDebounce: ReturnType<typeof setTimeout> | null = null;
    let accumulatedDelta = 0;

    function onKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === 'ArrowUp' || e.key === 'ArrowRight') {
        accumulatedDelta += 1;
      } else if (e.key === 'ArrowDown' || e.key === 'ArrowLeft') {
        accumulatedDelta -= 1;
      } else {
        return;
      }
      e.preventDefault();

      if (tuningDebounce) clearTimeout(tuningDebounce);
      tuningDebounce = setTimeout(() => {
        const delta = accumulatedDelta;
        accumulatedDelta = 0;
        tuningDebounce = null;
        const freq = tuneBy(delta);
        if (freq > 0) sendCommand('set_freq', { freq, receiver: activeRx === 'SUB' ? 1 : 0 });
      }, 100);
    }

    window.addEventListener('keydown', onKeyDown);
    return () => {
      cleanupKb();
      window.removeEventListener('keydown', onKeyDown);
      if (tuningDebounce) clearTimeout(tuningDebounce);
    };
  });

  function handleTune(receiver: 'MAIN' | 'SUB', newFreq: number) {
    const rx = receiver === 'MAIN' ? 0 : 1;
    sendCommand('set_freq', { freq: newFreq, receiver: rx });
  }

  function handleModeChange(receiver: 'MAIN' | 'SUB', mode: string) {
    const rx = receiver === 'MAIN' ? 0 : 1;
    sendCommand('set_mode', { mode, receiver: rx });
  }

  function handleReceiverSwitch(receiver: 'MAIN' | 'SUB') {
    sendCommand('select_vfo', { vfo: receiver === 'MAIN' ? 'A' : 'B' });
  }

  function handleDwToggle() {
    sendCommand('set_dual_watch', { on: !(state?.dualWatch ?? false) });
  }
</script>

<div class="desktop-layout">
  <StatusBar />

  <main class="main-grid">
    <!-- Left pane: VFO + Spectrum + Band bar -->
    <section class="left-pane">
      <!-- Dual VFO display -->
      <div class="vfo-section">
        <div class="vfo-pair">
          {#if main}
            <VfoDisplay
              label="VFO A"
              freq={main.freqHz}
              mode={main.mode}
              filter={main.filter}
              active={activeRx === 'MAIN'}
              dataMode={main.dataMode}
              ontune={(f) => handleTune('MAIN', f)}
            />
          {:else}
            <div class="vfo-placeholder">VFO A — connecting…</div>
          {/if}

          {#if isDualRx && sub}
            <VfoDisplay
              label="VFO B"
              freq={sub.freqHz}
              mode={sub.mode}
              filter={sub.filter}
              active={activeRx === 'SUB'}
              dataMode={sub.dataMode}
              ontune={(f) => handleTune('SUB', f)}
            />
          {/if}
        </div>

        <div class="vfo-controls">
          {#if isDualRx}
            <ReceiverSwitch
              active={activeRx}
              dualWatch={state?.dualWatch ?? false}
              hasDualReceiver={isDualRx}
              onswitch={handleReceiverSwitch}
              ondwtoggle={handleDwToggle}
            />
          {/if}
        </div>
      </div>

      <!-- Spectrum + Waterfall -->
      <div class="spectrum-section">
        <SpectrumPanel />
      </div>

      <!-- Band bar -->
      <div class="band-bar">
        <BandSelector />
      </div>
    </section>

    <!-- Right pane: Meters + Controls + DX -->
    <aside class="right-pane">
      <!-- S-Meter / Power meter -->
      <div class="panel-card">
        {#if main}
          <SMeter value={main.sMeter} label="S" />
        {/if}
        {#if isTx}
          <div class="meter-spacer"></div>
          <PowerMeter power={state?.powerLevel ?? 0} swr={0} />
        {/if}
      </div>

      <!-- Mode / Filter / Step selectors -->
      <div class="panel-card">
        <div class="selectors-row">
          <ModeSelector />
          <FilterSelector />
        </div>
        <StepSelector />
        <div class="toggles-row">
          <FeatureToggles />
        </div>
      </div>

      <!-- Audio + PTT -->
      <div class="panel-card">
        <AudioControls />
        <PttButton />
      </div>

      <!-- Audio RX/TX streaming -->
      <div class="panel-card">
        <AudioPanel />
      </div>

      <!-- DX Cluster -->
      <div class="panel-card dx-card">
        <DxClusterPanel />
      </div>
    </aside>
  </main>
</div>

<!-- Toast notifications — rendered in fixed position overlay -->
<Toast />

<!-- Disconnection overlay: dims UI when not connected -->
{#if isDisconnected || isReconnecting}
  <div
    class="connection-overlay"
    class:reconnecting={isReconnecting}
    aria-hidden="true"
  ></div>
{/if}

<style>
  .desktop-layout {
    display: flex;
    flex-direction: column;
    height: 100dvh;
    background-color: var(--bg);
    color: var(--text);
    overflow: hidden;
  }

  .main-grid {
    display: grid;
    grid-template-columns: 1fr var(--right-pane-width);
    flex: 1;
    overflow: hidden;
  }

  /* ── Left pane ── */
  .left-pane {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .vfo-section {
    padding: var(--space-2) var(--space-3);
    border-bottom: 1px solid var(--panel-border);
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    flex-shrink: 0;
  }

  .vfo-pair {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    flex: 1;
  }

  .vfo-controls {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: var(--space-2);
    padding-top: var(--space-1);
  }

  .vfo-placeholder {
    font-family: var(--font-mono);
    font-size: 0.875rem;
    color: var(--text-muted);
    padding: var(--space-3);
    border: 1px dashed var(--panel-border);
    border-radius: var(--radius);
  }

  .spectrum-section {
    flex: 1;
    min-height: 200px;
    overflow: hidden;
    padding: var(--space-2) var(--space-3) 0;
  }

  .band-bar {
    flex-shrink: 0;
    padding: var(--space-2) var(--space-4);
    border-top: 1px solid var(--panel-border);
    overflow-x: auto;
  }

  /* ── Right pane ── */
  .right-pane {
    padding: var(--space-3);
    background: var(--panel-gradient);
    border-left: 1px solid var(--panel-border-strong);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .panel-card {
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
  }

  .dx-card {
    flex: 1;
    min-height: 120px;
    overflow: hidden;
  }

  .meter-spacer {
    height: 1px;
    background: var(--panel-border);
    margin: var(--space-1) 0;
  }

  .selectors-row {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .toggles-row {
    display: flex;
    gap: var(--space-1);
    flex-wrap: wrap;
  }

  /* ── Connection overlay ── */
  .connection-overlay {
    position: fixed;
    inset: 0;
    z-index: 50;
    background: rgba(0, 0, 0, 0.5);
    pointer-events: none;
  }

  .connection-overlay.reconnecting {
    background: rgba(0, 0, 0, 0.3);
    animation: reconnect-pulse 1.5s ease-in-out infinite;
  }
</style>
