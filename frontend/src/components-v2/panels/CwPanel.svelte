<script lang="ts">
  import '../controls/control-button.css';
  import { FillButton } from '$lib/Button';
  import { ValueControl } from '../controls/value-control';
  import { hasCapability } from '$lib/stores/capabilities.svelte';

  interface Props {
    cwPitch: number;
    keySpeed: number;
    breakIn: number;
    apfMode: number;
    twinPeak: boolean;
    currentMode: string;
    onCwPitchChange: (v: number) => void;
    onKeySpeedChange: (v: number) => void;
    onBreakInToggle: () => void;
    onApfChange: (mode: number) => void;
    onTwinPeakToggle: () => void;
    onAutoTune: () => void;
  }

  let {
    cwPitch,
    keySpeed,
    breakIn,
    apfMode,
    twinPeak,
    currentMode,
    onCwPitchChange,
    onKeySpeedChange,
    onBreakInToggle,
    onApfChange,
    onTwinPeakToggle,
    onAutoTune,
  }: Props = $props();

  let showBreakIn = $derived(hasCapability('break_in'));
  let showApf = $derived(hasCapability('apf'));
  let showTwinPeak = $derived(hasCapability('twin_peak'));
  let breakInActive = $derived(breakIn > 0);
  let apfActive = $derived(apfMode > 0);
</script>

{#if hasCapability('cw')}
  <div class="panel-body">
    <div class="cw-mode-line">
      <span class="cw-mode-label">RX mode</span>
      <span class="cw-mode-value">{currentMode}</span>
    </div>

    <ValueControl
      label="CW Pitch"
      value={cwPitch}
      min={300}
      max={900}
      step={5}
      unit="Hz"
      renderer="hbar"
      accentColor="var(--v2-accent-cyan)"
      onChange={onCwPitchChange}
      variant="hardware-illuminated"
    />

    <ValueControl
      label="Key Speed"
      value={keySpeed}
      min={6}
      max={48}
      step={1}
      unit="WPM"
      renderer="discrete"
      tickStyle="notch"
      accentColor="var(--v2-accent-orange)"
      onChange={onKeySpeedChange}
      variant="hardware-illuminated"
    />

    <div class="toggle-row">
      {#if showBreakIn}
        <FillButton active={breakInActive} color="cyan" onclick={() => onBreakInToggle()}>
          BK-IN
        </FillButton>
      {/if}
      {#if showApf}
        <FillButton active={apfActive} color="cyan" onclick={() => onApfChange(apfActive ? 0 : 2)}>
          APF
        </FillButton>
      {/if}
      {#if showTwinPeak}
        <FillButton active={twinPeak} color="cyan" onclick={() => onTwinPeakToggle()}>
          TPF
        </FillButton>
      {/if}
    </div>

    <div class="toggle-row">
      <button type="button" class="auto-tune-btn v2-control-button" onclick={onAutoTune}>
        AUTO TUNE
      </button>
    </div>
  </div>
{/if}

<style>
  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px 8px;
  }

  .cw-mode-line {
    display: flex;
    flex-direction: row;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
  }

  .cw-mode-label {
    color: var(--v2-text-subdued);
    font-family: 'Roboto Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .cw-mode-value {
    color: var(--v2-text-header);
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    font-weight: 700;
  }

  .toggle-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .auto-tune-btn {
    flex: 1;
    background: transparent;
  }
</style>
