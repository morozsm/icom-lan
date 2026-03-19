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
      accentColor="var(--v2-accent-cyan)"
      onchange={onAgcGainChange}
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
