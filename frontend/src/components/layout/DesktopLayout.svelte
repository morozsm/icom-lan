<script lang="ts">
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
  import PttButton from '../audio/PttButton.svelte';
  import StatusBar from '../shared/StatusBar.svelte';

  import {
    getRadioState,
    getMainReceiver,
    getSubReceiver,
  } from '../../lib/stores/radio.svelte';
  import { hasDualReceiver, hasTx } from '../../lib/stores/capabilities.svelte';
  import { sendCommand } from '../../lib/transport/ws-client';

  let state = $derived(getRadioState());
  let main = $derived(getMainReceiver());
  let sub = $derived(getSubReceiver());
  let activeRx = $derived(state?.active ?? 'MAIN');
  let isDualRx = $derived(hasDualReceiver());
  let isTx = $derived(hasTx());

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
    sendCommand('set_dw', { on: !(state?.dualWatch ?? false) });
  }
</script>

<div class="desktop-layout">
  <StatusBar />

  <main class="main-grid">
    <!-- Left pane: VFO + Spectrum -->
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
    </section>

    <!-- Right pane: Meters + Controls -->
    <aside class="right-pane">
      <!-- S-Meter -->
      <div class="panel-card">
        {#if main}
          <SMeter value={main.sMeter} label="S" />
        {/if}
        {#if isTx}
          <div class="meter-spacer"></div>
          <PowerMeter power={state?.powerLevel ?? 0} swr={0} />
        {/if}
      </div>

      <!-- Band / Mode / Filter selectors -->
      <div class="panel-card">
        <div class="selectors-row">
          <BandSelector />
          <ModeSelector />
          <FilterSelector />
        </div>
        <div class="toggles-row">
          <FeatureToggles />
        </div>
      </div>

      <!-- Audio + PTT -->
      <div class="panel-card">
        <AudioControls />
        <PttButton />
      </div>
    </aside>
  </main>
</div>

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
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--panel-border);
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
  }

  .vfo-pair {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
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
    overflow: hidden;
    padding: var(--space-2) var(--space-4) var(--space-4);
  }

  /* ── Right pane ── */
  .right-pane {
    padding: var(--space-3);
    background-color: var(--panel);
    border-left: 1px solid var(--panel-border);
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
</style>
