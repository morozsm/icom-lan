<script lang="ts">
  import { onMount } from 'svelte';
  import '../theme/index';
  import { setTheme, getTheme, setVfoTheme, getVfoTheme } from '../theme/theme-switcher';
  
  // Apply saved themes immediately (before any component renders)
  if (typeof window !== 'undefined') {
    setTheme(getTheme());
    const vfoTheme = getVfoTheme();
    if (vfoTheme) {
      setVfoTheme(vfoTheme);
    }
  }
  
  import { radio } from '$lib/stores/radio.svelte';
  import { applyModeDefault } from '$lib/stores/tuning.svelte';
  import { getCapabilities, getKeyboardConfig, hasDualReceiver, hasTx } from '$lib/stores/capabilities.svelte';
  import SpectrumPanel from '../../components/spectrum/SpectrumPanel.svelte';
  import LeftSidebar from './LeftSidebar.svelte';
  import RightSidebar from './RightSidebar.svelte';
  import VfoHeader from './VfoHeader.svelte';
  import KeyboardHandler from './KeyboardHandler.svelte';
  import StatusBar from './StatusBar.svelte';
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
  import { makeKeyboardHandlers, makeMeterHandlers, makeVfoHandlers } from '../wiring/command-bus';
  import MobileNav from './MobileNav.svelte';
  import { DEFAULT_TAB, type TabId } from './mobile-nav-utils';

  // Reactive state + capabilities
  let radioState = $derived(radio.current);
  let caps = $derived(getCapabilities());
  let keyboardConfig = $derived(getKeyboardConfig());
  let activeMode = $derived(radioState?.active === 'SUB' ? radioState?.sub?.mode : radioState?.main?.mode);

  // Derived props via state adapter
  let mainVfo = $derived(toVfoProps(radioState, 'main'));
  let subVfo = $derived(toVfoProps(radioState, 'sub'));
  let vfoOps = $derived(toVfoOpsProps(radioState, caps));
  let meter = $derived(toMeterProps(radioState));
  let txCapable = $derived(hasTx());
  let dualReceiver = $derived(hasDualReceiver());
  let windowWidth = $state(typeof window !== 'undefined' ? window.innerWidth : 1200);
  let isMobile = $derived(windowWidth < 640);
  let isLandscape = $state(false);
  let landscapeSpectrumDismissed = $state(false);
  let spectrumLandscape = $derived(isMobile && isLandscape && !landscapeSpectrumDismissed);
  let activeTab = $state<TabId>(DEFAULT_TAB);

  let activeReceiverLabel = $derived(radioState?.active === 'SUB' ? 'SUB' : 'MAIN');
  let activeModeLabel = $derived(radioState?.active === 'SUB' ? (radioState?.sub?.mode ?? '') : (radioState?.main?.mode ?? ''));
  let activeFilterLabel = $derived(radioState?.active === 'SUB' ? (radioState?.sub?.filter ?? '') : (radioState?.main?.filter ?? ''));
  let activeFreq = $derived(radioState?.active === 'SUB' ? (radioState?.sub?.freqHz ?? 0) : (radioState?.main?.freqHz ?? 0));
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
  const meterHandlers = makeMeterHandlers();
  const keyboardHandlers = makeKeyboardHandlers();

  $effect(() => {
    if (activeMode) {
      applyModeDefault(activeMode);
    }
  });

  $effect(() => {
    if (!isLandscape) {
      landscapeSpectrumDismissed = false;
    }
  });

  onMount(() => {
    // Theme already applied at module load
    manualVfoScaleOverrides = parseVfoLayoutScaleOverrides(window.location.search);

    const handleResize = () => {
      windowWidth = window.innerWidth;
    };
    window.addEventListener('resize', handleResize);

    const mql = window.matchMedia?.('(orientation: landscape)');
    const handleOrientationChange = (e: MediaQueryListEvent) => {
      isLandscape = e.matches;
    };

    if (mql) {
      isLandscape = mql.matches;
      mql.addEventListener('change', handleOrientationChange);
    }

    if (!receiverDeckElement) {
      return () => {
        window.removeEventListener('resize', handleResize);
        mql?.removeEventListener('change', handleOrientationChange);
      };
    }

    receiverDeckWidth = receiverDeckElement.getBoundingClientRect().width || receiverDeckElement.clientWidth || null;

    if (typeof ResizeObserver === 'undefined') {
      return () => {
        window.removeEventListener('resize', handleResize);
        mql?.removeEventListener('change', handleOrientationChange);
      };
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }

      receiverDeckWidth = entry.contentRect.width;
    });

    observer.observe(receiverDeckElement);
    return () => {
      window.removeEventListener('resize', handleResize);
      mql?.removeEventListener('change', handleOrientationChange);
      observer.disconnect();
    };
  });
</script>

{#if spectrumLandscape}
  <div class="spectrum-landscape" aria-label="Spectrum landscape">
    <div class="spectrum-hud" aria-label="Spectrum HUD">
      <button
        type="button"
        class="hud-btn"
        onclick={() => { landscapeSpectrumDismissed = true; }}
        aria-label="Exit fullscreen spectrum"
      >
        Back
      </button>

      <div class="hud-center">
        <div class="hud-freq">
          <FrequencyDisplay freq={activeFreq} compact active />
        </div>
        <div class="hud-meta">
          <span class="hud-rx">{activeReceiverLabel}</span>
          <span class="hud-sep">·</span>
          <span class="hud-mode">{activeModeLabel}</span>
          <span class="hud-sep">·</span>
          <span class="hud-filter">{activeFilterLabel}</span>
        </div>
      </div>

      <div class="hud-spacer"></div>
    </div>

    <div class="spectrum-landscape-frame">
      <SpectrumPanel />
    </div>
  </div>
{:else if isMobile}
  <div class="radio-layout radio-layout--mobile">
    <StatusBar />
    <KeyboardHandler config={keyboardConfig} onAction={keyboardHandlers.dispatch} />

    <section
      class="receiver-deck receiver-deck--mobile"
      class:receiver-deck--mobile-focus={activeTab === 'vfo'}
      bind:this={receiverDeckElement}
      style={receiverDeckStyle}
    >
      <VfoHeader
        {mainVfo}
        {subVfo}
        layoutProfile={vfoLayoutProfile}
        splitActive={vfoOps.splitActive}
        dualWatchActive={vfoOps.dualWatch}
        txVfo={vfoOps.txVfo}
        onSwap={vfoHandlers.onSwap}
        onCopy={vfoHandlers.onCopy}
        onEqual={vfoHandlers.onEqual}
        onSplitToggle={vfoHandlers.onSplitToggle}
        onDualWatchToggle={() => vfoHandlers.onDualWatchToggle(!vfoOps.dualWatch)}
        onTxVfoChange={vfoHandlers.onTxVfoChange}
        onMainVfoClick={vfoHandlers.onMainVfoClick}
        onSubVfoClick={vfoHandlers.onSubVfoClick}
        onMainModeClick={vfoHandlers.onMainModeClick}
        onMainFreqChange={vfoHandlers.onMainFreqChange}
        onSubFreqChange={vfoHandlers.onSubFreqChange}
        onSubModeClick={vfoHandlers.onSubModeClick}
      />
    </section>

    <main class="mobile-content">
      {#if activeTab === 'spectrum'}
        <div class="spectrum-slot">
          <div class="spectrum-frame">
            <SpectrumPanel />
          </div>
        </div>
      {:else if activeTab === 'vfo'}
        <div class="mobile-panels">
          <LeftSidebar />
        </div>
      {:else if activeTab === 'controls'}
        <div class="mobile-panels">
          <RightSidebar mode="rx" />
        </div>
      {:else if activeTab === 'tx'}
        <div class="mobile-panels">
          <RightSidebar mode="tx" />
        </div>
      {:else if activeTab === 'meters'}
        <div class="mobile-meters">
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
              sValue={meter.sValue}
              rfPower={meter.rfPower}
              swr={meter.swr}
              alc={meter.alc}
              txActive={meter.txActive}
              meterSource={meter.meterSource as 'S' | 'SWR' | 'POWER'}
              onMeterSourceChange={meterHandlers.onMeterSourceChange}
            />
          {/if}
        </div>
      {/if}
    </main>

    <MobileNav bind:activeTab={activeTab} />
  </div>
{:else}
<div class="radio-layout">
  <StatusBar />
  <KeyboardHandler config={keyboardConfig} onAction={keyboardHandlers.dispatch} />

  <section class="receiver-deck" bind:this={receiverDeckElement} style={receiverDeckStyle}>
    <VfoHeader
      {mainVfo}
      {subVfo}
      layoutProfile={vfoLayoutProfile}
      splitActive={vfoOps.splitActive}
      dualWatchActive={vfoOps.dualWatch}
      txVfo={vfoOps.txVfo}
      onSwap={vfoHandlers.onSwap}
      onCopy={vfoHandlers.onCopy}
      onEqual={vfoHandlers.onEqual}
      onSplitToggle={vfoHandlers.onSplitToggle}
      onDualWatchToggle={() => vfoHandlers.onDualWatchToggle(!vfoOps.dualWatch)}
      onTxVfoChange={vfoHandlers.onTxVfoChange}
      onMainVfoClick={vfoHandlers.onMainVfoClick}
      onSubVfoClick={vfoHandlers.onSubVfoClick}
      onMainModeClick={vfoHandlers.onMainModeClick}
      onMainFreqChange={vfoHandlers.onMainFreqChange}
      onSubFreqChange={vfoHandlers.onSubFreqChange}
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
        sValue={meter.sValue}
        rfPower={meter.rfPower}
        swr={meter.swr}
        alc={meter.alc}
        txActive={meter.txActive}
        meterSource={meter.meterSource as 'S' | 'SWR' | 'POWER'}
        onMeterSourceChange={meterHandlers.onMeterSourceChange}
      />
    {/if}
  </section>
</div>
{/if}

<style>
  .radio-layout {
    position: relative;
    display: grid;
    grid-template-rows: 28px 156px minmax(0, 1fr) auto;
    height: 100vh;
    background:
      linear-gradient(180deg, var(--v2-bg-gradient-start) 0%, var(--v2-bg-darkest) 100%),
      var(--v2-bg-app, var(--v2-bg-darker));
    gap: 5px;
    padding: 5px;
    box-sizing: border-box;
  }

  .receiver-deck,
  .content-left,
  .content-right,
  .spectrum-frame,
  .receiver-summary-card {
    border: 1px solid var(--v2-border-panel);
    border-radius: 4px;
    background:
      linear-gradient(180deg, var(--v2-panel-bg-gradient-top) 0%, var(--v2-panel-bg-gradient-bottom) 100%);
    box-shadow: var(--v2-shadow-sm);
  }

  .receiver-deck {
    position: relative;
    overflow: hidden;
    padding: 5px;
    min-height: 0;
    border-color: var(--v2-border-panel);
  }

  .receiver-deck :global(.vfo-header) {
    height: 100%;
  }

  .content-row {
    display: grid;
    grid-template-columns: 228px minmax(0, 1fr) 228px;
    grid-template-rows: minmax(0, 1fr);
    gap: 5px;
    min-height: 0;
    overflow: hidden;
  }

  .content-left,
  .content-right {
    min-height: 0;
    max-height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
    padding-bottom: 4px;
    /* Hide scrollbar but keep scroll functionality */
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* IE/Edge */
  }

  .content-left::-webkit-scrollbar,
  .content-right::-webkit-scrollbar {
    display: none; /* Chrome/Safari/Opera */
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
    background: var(--v2-bg-card);
    border-color: var(--v2-border-darker);
  }

  .spectrum-frame :global(.spectrum-panel) {
    height: 100%;
    border: none;
    border-radius: 0;
    box-shadow: none;
  }

  .content-left :global(.left-sidebar),
  .content-right :global(.right-sidebar) {
    min-height: 0;
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
    border-color: var(--v2-border-cyan);
    background: linear-gradient(180deg, var(--v2-bg-input) 0%, var(--v2-bg-card) 100%);
  }

  .receiver-summary-card-sub {
    border-color: var(--v2-border);
    background: linear-gradient(180deg, var(--v2-bg-input) 0%, var(--v2-bg-card) 100%);
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
    color: var(--v2-text-subdued);
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.14em;
  }

  .receiver-summary-mode {
    color: var(--v2-text-muted);
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
      grid-template-columns: 208px minmax(0, 1fr) 208px;
    }
  }

  @media (max-width: 1024px) {
    .radio-layout {
      grid-template-rows: 28px auto minmax(0, auto) auto auto;
    }

    .content-row {
      grid-template-columns: 1fr;
    }

    .bottom-dock {
      flex-direction: column;
    }
  }

  /* Mobile layout */
  .radio-layout--mobile {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: linear-gradient(180deg, var(--v2-bg-gradient-start) 0%, var(--v2-bg-darkest) 100%);
    padding: 4px;
    gap: 4px;
    box-sizing: border-box;
  }

  .receiver-deck--mobile {
    flex-shrink: 0;
    min-height: 80px;
    max-height: 100px;
    padding: 4px;
  }

  .receiver-deck--mobile.receiver-deck--mobile-focus {
    max-height: 156px;
  }

  .mobile-content {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding-bottom: 56px; /* MobileNav height */
    box-sizing: border-box;
  }

  .mobile-panels {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .mobile-meters {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 4px;
  }

  /* Mobile landscape fullscreen spectrum */
  .spectrum-landscape {
    position: fixed;
    inset: 0;
    z-index: 10000;
    background:
      linear-gradient(180deg, var(--v2-bg-gradient-start) 0%, var(--v2-bg-darkest) 100%),
      var(--v2-bg-app, var(--v2-bg-darker));
    padding:
      env(safe-area-inset-top, 0px)
      env(safe-area-inset-right, 0px)
      env(safe-area-inset-bottom, 0px)
      env(safe-area-inset-left, 0px);
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .spectrum-hud {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 8px;
    border: 1px solid var(--v2-border-panel);
    border-radius: 4px;
    background: linear-gradient(180deg, var(--v2-panel-bg-gradient-top) 0%, var(--v2-panel-bg-gradient-bottom) 100%);
    box-shadow: var(--v2-shadow-sm);
    min-height: 36px;
    box-sizing: border-box;
  }

  .hud-btn {
    height: 28px;
    padding: 0 10px;
    border-radius: 4px;
    border: 1px solid var(--v2-border-darker);
    background: var(--v2-bg-card);
    color: var(--v2-text-secondary);
    font-family: 'Roboto Mono', monospace;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    cursor: pointer;
  }

  .hud-btn:active {
    transform: translateY(1px);
  }

  .hud-center {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .hud-freq {
    line-height: 1;
  }

  .hud-meta {
    display: flex;
    align-items: center;
    gap: 4px;
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--v2-text-muted);
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .hud-rx {
    color: var(--v2-text-secondary);
  }

  .hud-sep {
    opacity: 0.6;
  }

  .hud-spacer {
    flex: 1;
  }

  .spectrum-landscape-frame {
    flex: 1;
    min-width: 0;
    min-height: 0;
    border: 1px solid var(--v2-border-panel);
    border-radius: 4px;
    overflow: hidden;
    background: var(--v2-bg-card);
    box-shadow: var(--v2-shadow-sm);
  }

  .spectrum-landscape-frame :global(.spectrum-panel) {
    height: 100%;
    border: none;
    border-radius: 0;
    box-shadow: none;
  }
</style>
