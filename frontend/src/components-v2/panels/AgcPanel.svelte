<script lang="ts">
  import { SegmentedControl } from '$lib/SegmentedControl';
  import ValueControl from '../controls/value-control/ValueControl.svelte';
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

<div class="panel-body">
    <SegmentedControl
      options={options}
      selected={agcMode}
      onchange={(v) => onAgcModeChange(v as number)}
    />
    <ValueControl
      label="Decay"
      value={agcGain}
      min={0}
      max={255}
      step={1}
      renderer="hbar"
      variant="hardware-illuminated"
      onChange={onAgcGainChange}
    />
  </div>

<style>
  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 7px 8px;
  }
</style>
