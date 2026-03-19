<script lang="ts">
  import '../controls/control-button.css';
  import StatusBadge from '../controls/StatusBadge.svelte';
  import { ValueControl } from '../controls/value-control';
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
  <div class="panel-body">

    <div class="tx-indicator">
      <StatusBadge
        label={txActive ? 'TX ACTIVE' : 'TX IDLE'}
        active={txActive}
        color={txActive ? 'red' : 'muted'}
      />
    </div>

    <ValueControl
      label="Mic Gain"
      value={micGain}
      min={0}
      max={255}
      step={1}
      renderer="hbar"
      accentColor="var(--v2-accent-orange)"
      onChange={onMicGainChange}
    />

    <div class="atu-row">
      <StatusBadge
        label="ATU"
        active={atuActive}
        color="green"
        onclick={onAtuToggle}
      />
      <button
        type="button"
        class="tune-button v2-control-button"
        class:tuning={atuTuning}
        style="--control-accent: {tuneButtonColor}; --control-active-text: {tuneButtonColor}; border-color: {tuneButtonColor}; color: {tuneButtonColor};"
        onclick={onAtuTune}
      >TUNE</button>
    </div>

    <div class="toggle-row">
      <StatusBadge label="VOX" active={voxActive} color="orange" onclick={onVoxToggle} />
    </div>

    <div class="toggle-row">
      <StatusBadge label="COMP" active={compActive} color="orange" onclick={onCompToggle} />
    </div>
    {#if compActive}
      <ValueControl
        label="Comp Level"
        value={compLevel}
        min={0}
        max={255}
        step={1}
        renderer="hbar"
        accentColor="var(--v2-accent-orange)"
        onChange={onCompLevelChange}
      />
    {/if}

    <div class="toggle-row">
      <StatusBadge label="MON" active={monActive} color="orange" onclick={onMonToggle} />
    </div>
    {#if monActive}
      <ValueControl
        label="Mon Level"
        value={monLevel}
        min={0}
        max={255}
        step={1}
        renderer="hbar"
        accentColor="var(--v2-accent-orange)"
        onChange={onMonLevelChange}
      />
    {/if}

  </div>
{/if}

<style>
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
    background: transparent;
  }

  .tune-button.tuning {
    background: var(--v2-tx-panel-glow);
  }

  .toggle-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
</style>
