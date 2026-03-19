<script lang="ts">
  import SegmentedButton from '../controls/SegmentedButton.svelte';
  import { ValueControl } from '../controls/value-control';
  import { hasAudio } from '$lib/stores/capabilities.svelte';
  import { buildMonitorOptions, formatMonitorStatus } from './audio-utils';
  import { getShortcutHint } from '../layout/shortcut-hints';

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
  const monitorShortcut = getShortcutHint('toggle_monitor');
  const afShortcut = getShortcutHint('adjust_af_level');
</script>

{#if hasAudio()}
  <div class="panel">
    <div class="panel-header">RX AUDIO</div>
    <div class="panel-body">
      <SegmentedButton
        {options}
        selected={monitorMode}
        accentColor="var(--v2-accent-cyan-alt)"
        title={monitorShortcut}
        onchange={(v) => onMonitorModeChange(v as string)}
      />
      <ValueControl
        label="AF Level"
        value={afLevel}
        min={0}
        max={255}
        step={1}
        renderer="hbar"
        accentColor="var(--v2-accent-cyan-alt)"
        shortcutHint={afShortcut}
        title={afShortcut}
        onChange={onAfLevelChange}
      />
      <div class="output-indicator">{statusText}</div>
    </div>
  </div>
{/if}

<style>
  .panel {
    background: var(--v2-bg-darker);
    border: 1px solid var(--v2-border-dark);
    border-radius: 4px;
    overflow: hidden;
  }

  .panel-header {
    padding: 5px 8px;
    color: var(--v2-text-subdued);
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    border-bottom: 1px solid var(--v2-border-dark);
  }

  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 7px 8px;
  }

  .output-indicator {
    color: var(--v2-text-muted);
    font-family: 'Roboto Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.04em;
    text-align: center;
  }
</style>
