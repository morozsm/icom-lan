<script lang="ts">
  import '../theme/index';
  import { radio } from '$lib/stores/radio.svelte';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import LeftSidebar from './LeftSidebar.svelte';
  import RightSidebar from './RightSidebar.svelte';
  import VfoHeader from './VfoHeader.svelte';
  import MeterPanel from '../panels/MeterPanel.svelte';
  import { toVfoProps, toVfoOpsProps, toMeterProps } from '../wiring/state-adapter';
  import { makeVfoHandlers, makeMeterHandlers } from '../wiring/command-bus';

  // Reactive state + capabilities
  let radioState = $derived(radio.current);
  let caps = $derived(getCapabilities());

  // Derived props via state adapter
  let mainVfo = $derived(toVfoProps(radioState, 'main'));
  let subVfo = $derived(toVfoProps(radioState, 'sub'));
  let vfoOps = $derived(toVfoOpsProps(radioState, caps));
  let meter = $derived(toMeterProps(radioState));

  // Command handlers via command-bus
  const vfoHandlers = makeVfoHandlers();
  const meterHandlers = makeMeterHandlers();

  // Check if TX capability is present
  let hasTx = $derived(caps?.capabilities?.includes('tx') ?? false);
</script>

<div class="radio-layout">
  <LeftSidebar />

  <main class="center-column">
    <div class="vfo-section">
      <VfoHeader
        {mainVfo}
        {subVfo}
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
    </div>

    <div class="spectrum-slot">
      <!-- TODO: Mount existing Spectrum.svelte / Waterfall.svelte here (Phase 5) -->
      <div class="spectrum-placeholder">
        <span>Spectrum / Waterfall</span>
      </div>
    </div>

    {#if hasTx}
      <div class="meter-section">
        <MeterPanel
          sValue={meter.sValue}
          rfPower={meter.rfPower}
          swr={meter.swr}
          alc={meter.alc}
          txActive={meter.txActive}
          meterSource={meter.meterSource}
          onMeterSourceChange={meterHandlers.onMeterSourceChange}
        />
      </div>
    {/if}
  </main>

  <RightSidebar />
</div>

<style>
  .radio-layout {
    display: grid;
    grid-template-columns: 220px 1fr 220px;
    min-height: 100vh;
    background: var(--v2-bg-app, #060A10);
  }

  .center-column {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px;
    overflow-y: auto;
    min-height: 0;
  }

  .vfo-section {
    flex-shrink: 0;
  }

  .spectrum-slot {
    min-height: 300px;
    flex: 1;
    background: rgba(0, 212, 255, 0.02);
    border: 1px dashed rgba(0, 212, 255, 0.1);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .spectrum-placeholder {
    color: rgba(0, 212, 255, 0.3);
    font-family: var(--v2-font-mono, 'Roboto Mono', monospace);
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .meter-section {
    flex-shrink: 0;
  }
</style>
