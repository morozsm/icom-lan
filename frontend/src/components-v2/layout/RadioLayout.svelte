<script lang="ts">
  import '../theme/index';
  import LeftSidebar from './LeftSidebar.svelte';
  import RightSidebar from './RightSidebar.svelte';
  import VfoHeader from './VfoHeader.svelte';
  import MeterPanel from '../panels/MeterPanel.svelte';
  import { hasTx } from '$lib/stores/capabilities.svelte';
  import { extractVfoState, extractMeterState } from './layout-utils';

  interface Props {
    radioState: any;
  }

  let { radioState }: Props = $props();

  let mainVfo = $derived(extractVfoState(radioState, 'main'));
  let subVfo = $derived(extractVfoState(radioState, 'sub'));
  let meter = $derived(extractMeterState(radioState));
</script>

<div class="radio-layout">
  <LeftSidebar {radioState} />

  <main class="center-column">
    <div class="vfo-section">
      <VfoHeader
        {mainVfo}
        {subVfo}
        splitActive={radioState?.splitActive ?? false}
        txVfo={radioState?.txVfo ?? 'main'}
      />
    </div>

    <div class="spectrum-slot"></div>

    {#if hasTx()}
      <div class="meter-section">
        <MeterPanel
          sValue={meter.sValue}
          rfPower={meter.rfPower}
          swr={meter.swr}
          alc={meter.alc}
          txActive={meter.txActive}
          meterSource={meter.meterSource}
          onMeterSourceChange={() => {}}
        />
      </div>
    {/if}
  </main>

  <RightSidebar {radioState} />
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
  }

  .meter-section {
    flex-shrink: 0;
  }
</style>
