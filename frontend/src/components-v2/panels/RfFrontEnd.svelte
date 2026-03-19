<script lang="ts">
  import Slider from '../controls/Slider.svelte';
  import AttenuatorControl from '../controls/AttenuatorControl.svelte';
  import SegmentedButton from '../controls/SegmentedButton.svelte';
  import { hasCapability, getAttValues, getPreValues } from '$lib/stores/capabilities.svelte';
  import { buildPreOptions, shouldShowPanel } from './rf-frontend-utils';
  import { getShortcutHint } from '../layout/shortcut-hints';

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

  let attValues = $derived(getAttValues());
  let preOptions = $derived(buildPreOptions(getPreValues()));
  const rfGainShortcut = getShortcutHint('adjust_rf_gain');
  const attShortcut = getShortcutHint('cycle_att');
  const preShortcut = getShortcutHint('cycle_preamp');
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
          shortcutHint={rfGainShortcut}
          title={rfGainShortcut}
          onchange={onRfGainChange}
        />
      {/if}

      {#if showAtt}
        <div class="control-row" data-shortcut-hint={attShortcut ?? undefined} title={attShortcut ?? undefined}>
          <span class="control-label">ATT</span>
          <AttenuatorControl values={attValues} selected={att} onchange={onAttChange} shortcutHint={attShortcut} title={attShortcut} />
        </div>
      {/if}

      {#if showPre}
        <div class="control-row" data-shortcut-hint={preShortcut ?? undefined} title={preShortcut ?? undefined}>
          <span class="control-label">PRE</span>
          <SegmentedButton
            options={preOptions}
            selected={pre}
            title={preShortcut}
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
    padding: 8px 10px 10px;
    background-color: #060A10;
    border: 1px solid #18202A;
    border-radius: 4px;
    font-family: 'Roboto Mono', monospace;
    width: 100%;
    box-sizing: border-box;
  }

  .panel-header {
    color: #8CA0B8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.14em;
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
    gap: 10px;
    min-width: 0;
  }

  .control-label {
    color: #6F8196;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    flex-shrink: 0;
    min-width: 34px;
  }

  .control-row > :global(.segmented-button),
  .control-row > :global(.att-control) {
    flex: 1 1 auto;
    min-width: 0;
  }

  .control-row :global(.segment),
  .control-row :global(.more-button) {
    min-height: 28px;
    padding: 4px 8px;
    font-size: 10px;
  }

  .control-row :global(.segmented-button) {
    width: 100%;
  }

  .control-row :global(.segment) {
    flex: 1 1 0;
    min-width: 0;
  }
</style>
