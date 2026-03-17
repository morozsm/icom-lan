<script lang="ts">
  import BarGauge from '../meters/BarGauge.svelte';
  import NeedleGauge from '../meters/NeedleGauge.svelte';
  import { hasTx } from '$lib/stores/capabilities.svelte';
  import {
    normalize,
    formatPowerWatts,
    formatSwr,
    formatAlc,
    formatSMeter,
    getNeedleMarks,
    type MeterSource,
  } from './meter-utils';

  interface Props {
    sValue: number;
    rfPower: number;
    swr: number;
    alc: number;
    txActive: boolean;
    meterSource: MeterSource;
    onMeterSourceChange: (v: string) => void;
  }

  let {
    sValue,
    rfPower,
    swr,
    alc,
    txActive,
    meterSource,
    onMeterSourceChange,
  }: Props = $props();

  let needleValue = $derived(
    meterSource === 'S'
      ? normalize(sValue)
      : meterSource === 'SWR'
        ? normalize(swr)
        : normalize(rfPower),
  );

  let needleDisplayValue = $derived(
    meterSource === 'S'
      ? formatSMeter(sValue)
      : meterSource === 'SWR'
        ? formatSwr(swr)
        : formatPowerWatts(rfPower),
  );

  let needleLabel = $derived(
    meterSource === 'S' ? 'S' : meterSource === 'SWR' ? 'SWR' : 'POWER',
  );

  let needleMarks = $derived(getNeedleMarks(meterSource));

  let needleDangerZone = $derived(meterSource === 'SWR' ? 0.6 : 0.8);
</script>

<div class="panel">
  <div class="panel-header">METERS</div>
  <div class="panel-body">

    <div class="needle-section">
      <NeedleGauge
        value={needleValue}
        label={needleLabel}
        displayValue={needleDisplayValue}
        marks={needleMarks}
        dangerZone={needleDangerZone}
      />
    </div>

    <div class="source-selector">
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <span
        class="source-btn"
        class:active={meterSource === 'S'}
        onclick={() => onMeterSourceChange('S')}
      >S</span>
      {#if hasTx()}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <span
          class="source-btn"
          class:active={meterSource === 'SWR'}
          onclick={() => onMeterSourceChange('SWR')}
        >SWR</span>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <span
          class="source-btn"
          class:active={meterSource === 'POWER'}
          onclick={() => onMeterSourceChange('POWER')}
        >Po</span>
      {/if}
    </div>

    {#if txActive}
      <div class="tx-meters">
        <BarGauge
          value={normalize(rfPower)}
          label="Po"
          displayValue={formatPowerWatts(rfPower)}
        />
        <BarGauge
          value={normalize(swr)}
          label="SWR"
          displayValue={formatSwr(swr)}
        />
        <BarGauge
          value={normalize(alc)}
          label="ALC"
          displayValue={formatAlc(alc)}
        />
      </div>
    {/if}

  </div>
</div>

<style>
  .panel {
    background: #060A10;
    border: 1px solid #18202A;
    border-radius: 10px;
    overflow: hidden;
    font-family: 'Roboto Mono', monospace;
  }

  .panel-header {
    padding: 6px 10px;
    color: #8CA0B8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    border-bottom: 1px solid #18202A;
  }

  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
  }

  .needle-section {
    width: 100%;
  }

  .source-selector {
    display: flex;
    justify-content: center;
    gap: 6px;
  }

  .source-btn {
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 10px;
    border-radius: 9999px;
    border: 1px solid #2A3A4A;
    background: transparent;
    color: #5A7090;
    cursor: pointer;
    user-select: none;
    transition: color 150ms ease, border-color 150ms ease, background 150ms ease;
  }

  .source-btn:hover {
    color: #8CA0B8;
    border-color: #4A6080;
  }

  .source-btn.active {
    color: #00D4FF;
    border-color: #00D4FF;
    background: rgba(0, 212, 255, 0.08);
  }

  .tx-meters {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
</style>
