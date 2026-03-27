<script lang="ts">
  import { ValueControl, rawToPercentDisplay } from '../controls/value-control';
  import DualParamRenderer from '../controls/value-control/DualParamRenderer.svelte';
  import AttenuatorControl from '../controls/AttenuatorControl.svelte';
  import { HardwareButton } from '$lib/Button';
  import { hasCapability, getAttValues, getAttLabels, getPreValues, getPreLabels } from '$lib/stores/capabilities.svelte';
  import { buildPreOptions, shouldShowPanel } from './rf-frontend-utils';
  import { getShortcutHint } from '../layout/shortcut-hints';

  interface Props {
    rfGain: number;
    squelch: number;
    att: number;
    pre: number;
    digiSel: boolean;
    ipPlus: boolean;
    onRfGainChange: (v: number) => void;
    onSquelchChange: (v: number) => void;
    onAttChange: (v: number) => void;
    onPreChange: (v: number) => void;
    onDigiSelToggle: (v: boolean) => void;
    onIpPlusToggle: (v: boolean) => void;
  }

  let {
    rfGain,
    squelch,
    att,
    pre,
    digiSel,
    ipPlus,
    onRfGainChange,
    onSquelchChange,
    onAttChange,
    onPreChange,
    onDigiSelToggle,
    onIpPlusToggle,
  }: Props = $props();

  let showRfGain = $derived(hasCapability('rf_gain'));
  let showSquelch = $derived(hasCapability('squelch'));
  let showAtt = $derived(hasCapability('attenuator'));
  let showPre = $derived(hasCapability('preamp'));
  let showDigiSel = $derived(hasCapability('digisel'));
  let showIpPlus = $derived(hasCapability('ip_plus'));
  let showRfSqlDual = $derived(showRfGain && showSquelch);
  let visible = $derived(shouldShowPanel(showRfGain, showAtt, showPre, showSquelch));

  let attValues = $derived(getAttValues());
  let attLabels = $derived(getAttLabels());
  let preOptions = $derived(buildPreOptions(getPreValues(), getPreLabels()));
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
      {#if attValues.length <= 2}
        <HardwareButton
          active={att > 0}
          indicator="edge-left"
          color="amber"
          title={attShortcut}
          shortcutHint={attShortcut}
          onclick={() => onAttChange(att > 0 ? 0 : 1)}
        >
          ATT
        </HardwareButton>
      {:else}
        <div class="control-row" data-shortcut-hint={attShortcut ?? undefined} title={attShortcut ?? undefined}>
          <span class="control-label">ATT</span>
          <AttenuatorControl values={attValues} selected={att} onchange={onAttChange} labels={attLabels} shortcutHint={attShortcut} title={attShortcut} />
        </div>
      {/if}
    {/if}

    {#if showPre}
      <div class="control-row" data-shortcut-hint={preShortcut ?? undefined} title={preShortcut ?? undefined}>
        <span class="control-label">PRE</span>
        <div class="button-group">
          {#each preOptions as option}
            <HardwareButton
              active={pre === option.value}
              indicator="edge-left"
              color="cyan"
              title={preShortcut}
              shortcutHint={preShortcut}
              onclick={() => onPreChange(option.value)}
            >
              {option.label}
            </HardwareButton>
          {/each}
        </div>
      </div>
    {/if}

    {#if showDigiSel || showIpPlus}
      <div class="button-row">
        {#if showDigiSel}
          <HardwareButton
            active={digiSel}
            indicator="edge-left"
            color="green"
            onclick={() => onDigiSelToggle(!digiSel)}
          >
            DIGI-SEL
          </HardwareButton>
        {/if}
        {#if showIpPlus}
          <HardwareButton
            active={ipPlus}
            indicator="edge-left"
            color="cyan"
            onclick={() => onIpPlusToggle(!ipPlus)}
          >
            IP+
          </HardwareButton>
        {/if}
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
  .control-row > :global(.att-control),
  .control-row > .button-group {
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

  .button-row {
    display: flex;
    gap: 6px;
  }

  .button-row > :global(button) {
    flex: 1 1 0;
    min-width: 0;
  }

  .button-group {
    display: flex;
    gap: 4px;
    flex: 1 1 auto;
    min-width: 0;
  }

  .button-group > :global(button) {
    flex: 1 1 0;
    min-width: 0;
  }
</style>
