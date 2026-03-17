<script lang="ts">
  import Slider from '../controls/Slider.svelte';
  import SegmentedButton from '../controls/SegmentedButton.svelte';
  import { hasCapability, getAttValues, getPreValues } from '$lib/stores/capabilities.svelte';
  import { buildAttOptions, buildPreOptions, shouldShowPanel } from './rf-frontend-utils';

  interface Props {
    rfGain: number;
    att: number;
    pre: number;
    onRfGainChange: (v: number) => void;
    onAttChange: (v: number) => void;
    onPreChange: (v: number) => void;
  }

  let { rfGain, att, pre, onRfGainChange, onAttChange, onPreChange }: Props = $props();

  let showRfGain = $derived(hasCapability('rf_gain'));
  let showAtt = $derived(hasCapability('attenuator'));
  let showPre = $derived(hasCapability('preamp'));
  let visible = $derived(shouldShowPanel(showRfGain, showAtt, showPre));

  let attOptions = $derived(buildAttOptions(getAttValues()));
  let preOptions = $derived(buildPreOptions(getPreValues()));
</script>

{#if visible}
  <div class="panel">
    <span class="panel-header">RF FRONT END</span>

    <div class="controls">
      {#if showRfGain}
        <Slider
          value={rfGain}
          min={0}
          max={255}
          label="RF Gain"
          accentColor="#22C55E"
          onchange={onRfGainChange}
        />
      {/if}

      {#if showAtt}
        <div class="control-row">
          <span class="control-label">ATT</span>
          <SegmentedButton
            options={attOptions}
            selected={att}
            onchange={(v) => onAttChange(v as number)}
          />
        </div>
      {/if}

      {#if showPre}
        <div class="control-row">
          <span class="control-label">PRE</span>
          <SegmentedButton
            options={preOptions}
            selected={pre}
            onchange={(v) => onPreChange(v as number)}
          />
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .panel {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px 12px;
    background-color: #060A10;
    border: 1px solid #18202A;
    border-radius: 10px;
    font-family: 'Roboto Mono', monospace;
    width: 100%;
    box-sizing: border-box;
  }

  .panel-header {
    color: #8CA0B8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    line-height: 1;
  }

  .controls {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .control-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .control-label {
    color: #6F8196;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    flex-shrink: 0;
    min-width: 28px;
  }
</style>
