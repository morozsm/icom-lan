<script lang="ts">
  import SegmentedButton from '../controls/SegmentedButton.svelte';
  import Slider from '../controls/Slider.svelte';
  import { hasAudio } from '$lib/stores/capabilities.svelte';
  import { buildMonitorOptions, formatMonitorStatus } from './audio-utils';

  interface Props {
    monitorMode: 'local' | 'live' | 'mute';
    afLevel: number;
    hasLiveAudio: boolean;
    onMonitorModeChange: (v: string) => void;
    onAfLevelChange: (v: number) => void;
  }

  let { monitorMode, afLevel, hasLiveAudio, onMonitorModeChange, onAfLevelChange }: Props =
    $props();

  let options = $derived(buildMonitorOptions(hasLiveAudio));
  let statusText = $derived(formatMonitorStatus(monitorMode));
</script>

{#if hasAudio()}
  <div class="panel">
    <div class="panel-header">RX AUDIO</div>
    <div class="panel-body">
      <SegmentedButton
        {options}
        selected={monitorMode}
        accentColor="#00FFFF"
        onchange={(v) => onMonitorModeChange(v as string)}
      />
      <Slider
        label="AF Level"
        value={afLevel}
        min={0}
        max={255}
        accentColor="#00FFFF"
        onchange={onAfLevelChange}
      />
      <div class="output-indicator">{statusText}</div>
    </div>
  </div>
{/if}

<style>
  .panel {
    background: #060a10;
    border: 1px solid #18202a;
    border-radius: 4px;
    overflow: hidden;
  }

  .panel-header {
    padding: 5px 8px;
    color: #8ca0b8;
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    border-bottom: 1px solid #18202a;
  }

  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 7px 8px;
  }

  .output-indicator {
    color: #4a6080;
    font-family: 'Roboto Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.04em;
    text-align: center;
  }
</style>
