<script lang="ts">
  import { ValueControl, rawToPercentDisplay } from '../controls/value-control';
  import DualParamRenderer from '../controls/value-control/DualParamRenderer.svelte';
  import AttenuatorControl from '../controls/AttenuatorControl.svelte';
  import { SegmentedControl } from '$lib/SegmentedControl';
  import { hasCapability, getAttValues, getPreValues } from '$lib/stores/capabilities.svelte';
  import { buildPreOptions, shouldShowPanel } from './rf-frontend-utils';
  import { getShortcutHint } from '../layout/shortcut-hints';

  interface Props {
    rfGain: number;
    squelch: number;
    att: number;
    pre: number;
    onRfGainChange: (v: number) => void;
    onSquelchChange: (v: number) => void;
    onAttChange: (v: number) => void;
    onPreChange: (v: number) => void;
  }

  let {
    rfGain,
    squelch,
    att,
    pre,
    onRfGainChange,
    onSquelchChange,
    onAttChange,
    onPreChange,
  }: Props = $props();

  let showRfGain = $derived(hasCapability('rf_gain'));
  let showSquelch = $derived(hasCapability('squelch'));
  let showAtt = $derived(hasCapability('attenuator'));
  let showPre = $derived(hasCapability('preamp'));
  let showRfSqlDual = $derived(showRfGain && showSquelch);
  let visible = $derived(shouldShowPanel(showRfGain, showAtt, showPre, showSquelch));

  let attValues = $derived(getAttValues());
  let preOptions = $derived(buildPreOptions(getPreValues()));
  const rfGainShortcut = getShortcutHint('adjust_rf_gain');
  const attShortcut = getShortcutHint('cycle_att');
  const preShortcut = getShortcutHint('cycle_preamp');
</script>

{#if visible}
  <div class="controls">
    {#if showRfSqlDual}
      <DualParamRenderer
        rfValue={rfGain}
        sqlValue={squelch}
        min={0}
        max={255}
        step={1}
        rfAccentColor="#22C55E"
        sqlAccentColor="#F59E0B"
        shortcutHint={rfGainShortcut}
        title={rfGainShortcut}
        onRfChange={onRfGainChange}
        onSqlChange={onSquelchChange}
        variant="hardware-illuminated"
      />
    {:else if showRfGain}
      <div data-control="rf-gain">
        <ValueControl
          value={rfGain}
          min={0}
          max={255}
          step={1}
          label="RF Gain"
          renderer="hbar"
          displayFn={rawToPercentDisplay}
          accentColor="#22C55E"
          shortcutHint={rfGainShortcut}
          title={rfGainShortcut}
          onChange={onRfGainChange}
          variant="hardware-illuminated"
        />
      </div>
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
        <SegmentedControl
          options={preOptions}
          selected={pre}
          title={preShortcut}
          onchange={(v) => onPreChange(v as number)}
        />
      </div>
    {/if}
  </div>
{/if}

<style>
  .controls {
    padding: 8px 10px 10px;
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
    color: var(--v2-text-dim);
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
