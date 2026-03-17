<script lang="ts">
  import StatusBadge from '../controls/StatusBadge.svelte';
  import Slider from '../controls/Slider.svelte';
  import { hasTx } from '$lib/stores/capabilities.svelte';
  import { txStatusColor } from './tx-utils';

  interface Props {
    txActive: boolean;
    micGain: number;
    atuActive: boolean;
    atuTuning: boolean;
    voxActive: boolean;
    compActive: boolean;
    compLevel: number;
    monActive: boolean;
    monLevel: number;
    onMicGainChange: (v: number) => void;
    onAtuToggle: () => void;
    onAtuTune: () => void;
    onVoxToggle: () => void;
    onCompToggle: () => void;
    onCompLevelChange: (v: number) => void;
    onMonToggle: () => void;
    onMonLevelChange: (v: number) => void;
  }

  let {
    txActive,
    micGain,
    atuActive,
    atuTuning,
    voxActive,
    compActive,
    compLevel,
    monActive,
    monLevel,
    onMicGainChange,
    onAtuToggle,
    onAtuTune,
    onVoxToggle,
    onCompToggle,
    onCompLevelChange,
    onMonToggle,
    onMonLevelChange,
  }: Props = $props();

  let tuneButtonColor = $derived(txStatusColor(atuActive, atuTuning));
</script>

{#if hasTx()}
<div class="panel">
  <div class="panel-header">TX</div>
  <div class="panel-body">

    <div class="tx-indicator">
      <StatusBadge
        label={txActive ? 'TX ACTIVE' : 'TX IDLE'}
        active={txActive}
        color={txActive ? 'red' : 'muted'}
      />
    </div>

    <Slider
      label="Mic Gain"
      value={micGain}
      min={0}
      max={255}
      accentColor="#FF6A00"
      onchange={onMicGainChange}
    />

    <div class="atu-row">
      <StatusBadge
        label="ATU"
        active={atuActive}
        color="green"
        onclick={onAtuToggle}
      />
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <span
        class="tune-button"
        class:tuning={atuTuning}
        style="border-color: {tuneButtonColor}; color: {tuneButtonColor};"
        onclick={onAtuTune}
      >TUNE</span>
    </div>

    <div class="toggle-row">
      <StatusBadge label="VOX" active={voxActive} color="orange" onclick={onVoxToggle} />
    </div>

    <div class="toggle-row">
      <StatusBadge label="COMP" active={compActive} color="orange" onclick={onCompToggle} />
    </div>
    {#if compActive}
      <Slider
        label="Comp Level"
        value={compLevel}
        min={0}
        max={255}
        accentColor="#FF6A00"
        onchange={onCompLevelChange}
      />
    {/if}

    <div class="toggle-row">
      <StatusBadge label="MON" active={monActive} color="orange" onclick={onMonToggle} />
    </div>
    {#if monActive}
      <Slider
        label="Mon Level"
        value={monLevel}
        min={0}
        max={255}
        accentColor="#FF6A00"
        onchange={onMonLevelChange}
      />
    {/if}

  </div>
</div>
{/if}

<style>
  .panel {
    background: #060A10;
    border: 1px solid #18202A;
    border-radius: 4px;
    overflow: hidden;
    font-family: 'Roboto Mono', monospace;
  }

  .panel-header {
    padding: 5px 8px;
    color: #8CA0B8;
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

  .tx-indicator {
    display: flex;
    justify-content: center;
  }

  .atu-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .tune-button {
    font-family: 'Roboto Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 3px;
    border: 1px solid;
    background: transparent;
    cursor: pointer;
    user-select: none;
    transition: border-color 150ms ease, color 150ms ease, background 150ms ease;
  }

  .tune-button.tuning {
    background: rgba(255, 32, 32, 0.15);
  }

  .tune-button:hover {
    filter: brightness(1.2);
  }

  .toggle-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
</style>
