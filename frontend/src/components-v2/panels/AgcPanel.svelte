<script lang="ts">
  import SegmentedButton from '../controls/SegmentedButton.svelte';
  import Slider from '../controls/Slider.svelte';
  import { getAgcModes, getAgcLabels } from '$lib/stores/capabilities.svelte';
  import { buildAgcOptions } from './agc-utils';

  interface Props {
    agcMode: number;
    agcGain: number;
    onAgcModeChange: (v: number) => void;
    onAgcGainChange: (v: number) => void;
  }

  let { agcMode, agcGain, onAgcModeChange, onAgcGainChange }: Props = $props();

  let options = $derived(buildAgcOptions(getAgcModes(), getAgcLabels()));
</script>

<div class="panel">
  <div class="panel-header">AGC</div>
  <div class="panel-body">
    <SegmentedButton
      options={options}
      selected={agcMode}
      onchange={(v) => onAgcModeChange(v as number)}
    />
    <Slider
      label="Decay"
      value={agcGain}
      min={0}
      max={255}
      accentColor="#00D4FF"
      onchange={onAgcGainChange}
    />
  </div>
</div>

<style>
  .panel {
    background: #060A10;
    border: 1px solid #18202A;
    border-radius: 4px;
    overflow: hidden;
  }

  .panel-header {
    padding: 5px 8px;
    color: #8CA0B8;
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    border-bottom: 1px solid #18202A;
  }

  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 7px 8px;
  }
</style>
