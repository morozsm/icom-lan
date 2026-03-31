<script lang="ts">
  import '../controls/control-button.css';
  import { HardwareButton } from '$lib/Button';
  import { ValueControl } from '../controls/value-control';
  import { hasCapability } from '$lib/stores/capabilities.svelte';

  interface Props {
    cwPitch?: number;
    keySpeed?: number;
    breakIn?: number;
    apfMode?: number;
    twinPeak?: boolean;
    currentMode?: string;
    // Mobile CW panel props
    wpm?: number;
    breakInActive?: boolean;
    breakInDelay?: number;
    sidetonePitch?: number;
    sidetoneLevel?: number;
    reversePaddle?: boolean;
    keyerType?: number;
    hasCw?: boolean;
    onCwPitchChange?: (v: number) => void;
    onKeySpeedChange?: (v: number) => void;
    onBreakInToggle?: () => void;
    onApfChange?: (mode: number) => void;
    onTwinPeakToggle?: () => void;
    onAutoTune?: () => void;
    // Mobile CW handlers
    onWpmChange?: (v: number) => void;
    onBreakInDelayChange?: (v: number) => void;
    onSidetonePitchChange?: (v: number) => void;
    onSidetoneLevelChange?: (v: number) => void;
    onReversePaddleToggle?: () => void;
    onKeyerTypeChange?: (v: number) => void;
  }

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  const noop = () => {};
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  const noopN = (_v: number) => {};

  let {
    cwPitch = 600,
    keySpeed = 12,
    breakIn = 0,
    apfMode = 0,
    twinPeak = false,
    currentMode = 'CW',
    onCwPitchChange = noopN,
    onKeySpeedChange = noopN,
    onBreakInToggle = noop,
    onApfChange = noopN,
    onTwinPeakToggle = noop,
    onAutoTune = noop,
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
        <HardwareButton indicator="edge-left" active={breakInActive} color="cyan" onclick={() => onBreakInToggle()}>
          BK-IN
        </HardwareButton>
      {/if}
      {#if showApf}
        <HardwareButton indicator="edge-left" active={apfActive} color="cyan" onclick={() => onApfChange(apfActive ? 0 : 2)}>
          APF
        </HardwareButton>
      {/if}
      {#if showTwinPeak}
        <HardwareButton indicator="edge-left" active={twinPeak} color="cyan" onclick={() => onTwinPeakToggle()}>
          TPF
        </HardwareButton>
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
