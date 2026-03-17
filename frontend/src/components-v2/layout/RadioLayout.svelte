<script lang="ts">
  import { onMount } from 'svelte';
  import '../theme/index';
  import { radio } from '$lib/stores/radio.svelte';
  import { getCapabilities, hasDualReceiver, hasTx } from '$lib/stores/capabilities.svelte';
  import SpectrumPanel from '../../components/spectrum/SpectrumPanel.svelte';
  import LeftSidebar from './LeftSidebar.svelte';
  import RightSidebar from './RightSidebar.svelte';
  import VfoHeader from './VfoHeader.svelte';
  import DockMeterPanel from '../panels/DockMeterPanel.svelte';
  import FrequencyDisplay from '../display/FrequencyDisplay.svelte';
  import LinearSMeter from '../meters/LinearSMeter.svelte';
  import {
    parseVfoLayoutScaleOverrides,
    resolveVfoLayoutProfile,
    vfoLayoutStyleVars,
    type VfoLayoutScaleOverrides,
  } from './vfo-layout-tokens';
  import { toVfoProps, toVfoOpsProps, toMeterProps } from '../wiring/state-adapter';
  import { makeVfoHandlers } from '../wiring/command-bus';

  // Reactive state + capabilities
  let radioState = $derived(radio.current);
  let caps = $derived(getCapabilities());

  // Derived props via state adapter
  let mainVfo = $derived(toVfoProps(radioState, 'main'));
  let subVfo = $derived(toVfoProps(radioState, 'sub'));
  let vfoOps = $derived(toVfoOpsProps(radioState, caps));
  let meter = $derived(toMeterProps(radioState));
  let txCapable = $derived(hasTx());
  let dualReceiver = $derived(hasDualReceiver());
  let receiverDeckElement = $state<HTMLElement | null>(null);
  let receiverDeckWidth = $state<number | null>(null);
  let manualVfoScaleOverrides = $state<VfoLayoutScaleOverrides>({});
  let vfoLayoutProfile = $derived(resolveVfoLayoutProfile(receiverDeckWidth));
  let receiverDeckStyle = $derived(vfoLayoutStyleVars(vfoLayoutProfile, {
    width: receiverDeckWidth,
    overrides: manualVfoScaleOverrides,
  }));

  // Command handlers via command-bus
  const vfoHandlers = makeVfoHandlers();

  onMount(() => {
    manualVfoScaleOverrides = parseVfoLayoutScaleOverrides(window.location.search);

    if (!receiverDeckElement) {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }

      receiverDeckWidth = entry.contentRect.width;
    });

    observer.observe(receiverDeckElement);
    return () => observer.disconnect();
  });
</script>

<div class="radio-layout">
  <section class="receiver-deck" bind:this={receiverDeckElement} style={receiverDeckStyle}>
    <VfoHeader
      {mainVfo}
      {subVfo}
      layoutProfile={vfoLayoutProfile}
      splitActive={vfoOps.splitActive}
      txVfo={vfoOps.txVfo}
      onSwap={vfoHandlers.onSwap}
      onCopy={vfoHandlers.onCopy}
      onEqual={vfoHandlers.onEqual}
      onSplitToggle={vfoHandlers.onSplitToggle}
      onTxVfoChange={vfoHandlers.onTxVfoChange}
      onMainVfoClick={vfoHandlers.onMainVfoClick}
      onSubVfoClick={vfoHandlers.onSubVfoClick}
      onMainModeClick={vfoHandlers.onMainModeClick}
      onSubModeClick={vfoHandlers.onSubModeClick}
    />
  </section>

  <section class="content-row">
    <div class="content-left">
      <LeftSidebar />
    </div>

    <main class="content-center center-column">
      <div class="spectrum-slot">
        <div class="spectrum-frame">
          <SpectrumPanel />
        </div>
      </div>
    </main>

    <div class="content-right">
      <RightSidebar />
    </div>
  </section>

  <section class="bottom-dock">
    <article class="receiver-summary-card receiver-summary-card-main">
      <div class="receiver-summary-header">
        <span class="receiver-summary-label">RX 1</span>
        <span class="receiver-summary-mode">{mainVfo.mode} / {mainVfo.filter}</span>
      </div>
      <div class="receiver-summary-frequency">
        <FrequencyDisplay freq={mainVfo.freq} compact active={mainVfo.isActive} />
      </div>
      <div class="receiver-summary-meter">
        <LinearSMeter value={mainVfo.sValue} compact label="MAIN" />
      </div>
    </article>

    {#if dualReceiver}
      <article class="receiver-summary-card receiver-summary-card-sub">
        <div class="receiver-summary-header">
          <span class="receiver-summary-label">RX 2</span>
          <span class="receiver-summary-mode">{subVfo.mode} / {subVfo.filter}</span>
        </div>
        <div class="receiver-summary-frequency">
          <FrequencyDisplay freq={subVfo.freq} compact active={subVfo.isActive} />
        </div>
        <div class="receiver-summary-meter">
          <LinearSMeter value={subVfo.sValue} compact label="SUB" />
        </div>
      </article>
    {/if}

    {#if txCapable}
      <DockMeterPanel
        rfPower={meter.rfPower}
        swr={meter.swr}
        alc={meter.alc}
        txActive={meter.txActive}
      />
    {/if}
  </section>
</div>

<style>
  .radio-layout {
    display: grid;
    grid-template-rows: 156px minmax(0, 1fr) auto;
    min-height: 100vh;
    background:
      linear-gradient(180deg, #0d0d14 0%, #090911 100%),
      var(--v2-bg-app, #060a10);
    gap: 5px;
    padding: 5px;
    box-sizing: border-box;
  }

  .receiver-deck,
  .content-left,
  .content-right,
  .spectrum-frame,
  .receiver-summary-card {
    border: 1px solid #1e2530;
    border-radius: 4px;
    background:
      linear-gradient(180deg, rgba(13, 17, 23, 0.98) 0%, rgba(9, 13, 18, 0.98) 100%);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28);
  }

  .receiver-deck {
    overflow: hidden;
    padding: 5px;
    min-height: 0;
    border-color: #18222d;
  }

  .receiver-deck :global(.vfo-header) {
    height: 100%;
  }

  .content-row {
    display: grid;
    grid-template-columns: 198px minmax(0, 1fr) 198px;
    gap: 5px;
    min-height: 0;
  }

  .content-left,
  .content-right {
    min-height: 0;
    overflow: hidden;
  }

  .content-center {
    min-height: 0;
    min-width: 0;
    display: flex;
  }

  .spectrum-slot {
    flex: 1;
    min-height: 0;
    min-width: 0;
    display: flex;
  }

  .spectrum-frame {
    flex: 1;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
    background: #05090f;
    border-color: #111922;
  }

  .spectrum-frame :global(.spectrum-panel) {
    height: 100%;
    border: none;
    border-radius: 0;
    box-shadow: none;
  }

  .content-left :global(.left-sidebar),
  .content-right :global(.right-sidebar) {
    height: 100%;
  }

  .bottom-dock {
    display: flex;
    align-items: stretch;
    gap: 6px;
    min-height: 112px;
    padding: 6px 8px;
    box-sizing: border-box;
  }

  .receiver-summary-card {
    flex: 1 1 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
    padding: 6px 8px;
    overflow: hidden;
  }

  .receiver-summary-card-main {
    border-color: #0a627c;
    background: linear-gradient(180deg, #0a1620 0%, #071019 100%);
  }

  .receiver-summary-card-sub {
    border-color: #253341;
    background: linear-gradient(180deg, #091118 0%, #071018 100%);
  }

  .receiver-summary-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    min-width: 0;
  }

  .receiver-summary-label,
  .receiver-summary-mode {
    font-family: 'Roboto Mono', monospace;
  }

  .receiver-summary-label {
    color: #8ca0b8;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.14em;
  }

  .receiver-summary-mode {
    color: #5e7489;
    font-size: 8px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .receiver-summary-frequency {
    min-width: 0;
  }

  .receiver-summary-frequency :global(.freq) {
    max-width: 100%;
  }

  .receiver-summary-meter {
    min-height: 0;
  }

  .receiver-summary-meter :global(svg) {
    display: block;
  }

  @media (max-width: 1200px) {
    .content-row {
      grid-template-columns: 186px minmax(0, 1fr) 186px;
    }
  }

  @media (max-width: 1024px) {
    .radio-layout {
      grid-template-rows: auto minmax(0, auto) auto auto;
    }

    .content-row {
      grid-template-columns: 1fr;
    }

    .bottom-dock {
      flex-direction: column;
    }
  }
</style>
