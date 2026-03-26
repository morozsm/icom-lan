<script lang="ts">
  import '../controls/control-button.css';
  import { StatusIndicator, HardwareButton } from '$lib/Button';
  import { ValueControl, rawToPercentDisplay } from '../controls/value-control';
  import { hasTx, hasCapability } from '$lib/stores/capabilities.svelte';
  import { txStatusColor } from './tx-utils';

  interface Props {
    txActive: boolean;
    rfPower: number;
    micGain: number;
    atuActive: boolean;
    atuTuning: boolean;
    voxActive: boolean;
    compActive: boolean;
    compLevel: number;
    monActive: boolean;
    monLevel: number;
    driveGain: number;
    onRfPowerChange: (v: number) => void;
    onMicGainChange: (v: number) => void;
    onAtuToggle: () => void;
    onAtuTune: () => void;
    onVoxToggle: () => void;
    onCompToggle: () => void;
    onCompLevelChange: (v: number) => void;
    onMonToggle: () => void;
    onMonLevelChange: (v: number) => void;
    onDriveGainChange: (v: number) => void;
  }

  let {
    txActive,
    rfPower,
    micGain,
    atuActive,
    atuTuning,
    voxActive,
    compActive,
    compLevel,
    monActive,
    monLevel,
    driveGain,
    onRfPowerChange,
    onMicGainChange,
    onAtuToggle,
    onAtuTune,
    onVoxToggle,
    onCompToggle,
    onCompLevelChange,
    onMonToggle,
    onMonLevelChange,
    onDriveGainChange,
  }: Props = $props();

  let tuneButtonColor = $derived(txStatusColor(atuActive, atuTuning));
</script>

{#if hasTx()}
  <div class="panel-body">

    <div class="tx-indicator">
      <StatusIndicator
        label={txActive ? 'TX ACTIVE' : 'TX IDLE'}
        active={txActive}
        color={txActive ? 'red' : 'muted'}
      />
    </div>

    <ValueControl
      label="RF Power"
      value={rfPower}
      min={0}
      max={255}
      step={1}
      renderer="hbar"
      displayFn={rawToPercentDisplay}
      accentColor="var(--v2-accent-red)"
      onChange={onRfPowerChange}
      variant="hardware-illuminated"
    />

    <ValueControl
      label="Mic Gain"
      value={micGain}
      min={0}
      max={255}
      step={1}
      renderer="hbar"
      displayFn={rawToPercentDisplay}
      accentColor="var(--v2-accent-orange)"
      onChange={onMicGainChange}
    variant="hardware-illuminated"
    />

    {#if hasCapability('tuner')}
      <div class="atu-row">
        <!-- status-toggle: sustained on/off state, current visual candidate: fill -->
        <HardwareButton indicator="edge-left" active={atuActive} color="green" onclick={() => onAtuToggle()}>ATU</HardwareButton>
        <button
          type="button"
          class="tune-button v2-control-button"
          class:tuning={atuTuning}
          style="--control-accent: {tuneButtonColor}; --control-active-text: {tuneButtonColor}; border-color: {tuneButtonColor}; color: {tuneButtonColor};"
          onclick={onAtuTune}
        >TUNE</button>
      </div>
    {/if}

    <div class="toggle-row">
      <!-- status-toggle -->
      <HardwareButton indicator="edge-left" active={voxActive} color="orange" onclick={() => onVoxToggle()}>VOX</HardwareButton>
    </div>

    <div class="toggle-row">
      <!-- status-toggle -->
      <HardwareButton indicator="edge-left" active={compActive} color="orange" onclick={() => onCompToggle()}>COMP</HardwareButton>
    </div>
    {#if compActive}
      <ValueControl
        label="Comp Level"
        value={compLevel}
        min={0}
        max={255}
        step={1}
        renderer="hbar"
        displayFn={rawToPercentDisplay}
        accentColor="var(--v2-accent-orange)"
        onChange={onCompLevelChange}
      variant="hardware-illuminated"
      />
    {/if}

    <div class="toggle-row">
      <!-- status-toggle -->
      <HardwareButton indicator="edge-left" active={monActive} color="orange" onclick={() => onMonToggle()}>MON</HardwareButton>
    </div>
    {#if monActive}
      <ValueControl
        label="Mon Level"
        value={monLevel}
        min={0}
        max={255}
        step={1}
        renderer="hbar"
        displayFn={rawToPercentDisplay}
        accentColor="var(--v2-accent-orange)"
        onChange={onMonLevelChange}
      variant="hardware-illuminated"
      />
    {/if}

    <ValueControl
      label="Drive Gain"
      value={driveGain}
      min={0}
      max={255}
      step={1}
      renderer="hbar"
      displayFn={rawToPercentDisplay}
      accentColor="var(--v2-accent-orange)"
      onChange={onDriveGainChange}
      variant="hardware-illuminated"
    />

  </div>
{/if}

<style>
  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px 8px;
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
