<script lang="ts">
  import '../controls/control-button.css';
  import { HardwareButton } from '$lib/Button';
  import { ValueControl, rawToPercentDisplay } from '../controls/value-control';
  import { hasCapability } from '$lib/stores/capabilities.svelte';

  import { deriveCwProps, getCwHandlers } from '$lib/runtime/adapters/panel-adapters';

  const handlers = getCwHandlers();
  let p = $derived(deriveCwProps());

  let cwPitch = $derived(p.cwPitch ?? 600);
  let keySpeed = $derived(p.keySpeed ?? 12);
  let breakIn = $derived(p.breakIn ?? 0);
  let breakInDelay = $derived(p.breakInDelay ?? 0);
  let apfMode = $derived(p.apfMode ?? 0);
  let twinPeak = $derived(p.twinPeak ?? false);
  let currentMode = $derived(p.currentMode ?? 'CW');
  const onCwPitchChange = handlers.onCwPitchChange;
  const onKeySpeedChange = handlers.onKeySpeedChange;
  const onBreakInToggle = handlers.onBreakInToggle;
  const onBreakInModeChange = handlers.onBreakInModeChange;
  const onBreakInDelayChange = handlers.onBreakInDelayChange;
  const onApfChange = handlers.onApfChange;
  const onTwinPeakToggle = handlers.onTwinPeakToggle;
  const onAutoTune = handlers.onAutoTune;

  let showBreakIn = $derived(hasCapability('break_in'));
  let showApf = $derived(hasCapability('apf'));
  let showTwinPeak = $derived(hasCapability('twin_peak'));
  let breakInActive = $derived(breakIn > 0);
  let apfActive = $derived(apfMode > 0);

  const BREAK_IN_LABELS: Record<number, string> = { 0: 'OFF', 1: 'SEMI', 2: 'FULL' };
  let breakInLabel = $derived(BREAK_IN_LABELS[breakIn] ?? 'OFF');
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
        <HardwareButton indicator="edge-left" active={breakIn === 1} color="cyan" onclick={() => onBreakInModeChange(breakIn === 1 ? 0 : 1)}>
          SEMI
        </HardwareButton>
        <HardwareButton indicator="edge-left" active={breakIn === 2} color="orange" onclick={() => onBreakInModeChange(breakIn === 2 ? 0 : 2)}>
          FULL
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

    {#if showBreakIn && breakIn === 1}
      <ValueControl
        label="Break-in Delay"
        value={breakInDelay}
        min={0}
        max={255}
        step={1}
        renderer="hbar"
        displayFn={rawToPercentDisplay}
        accentColor="var(--v2-accent-cyan)"
        onChange={onBreakInDelayChange}
        variant="hardware-illuminated"
      />
    {/if}

    {#if hasCapability('cw_auto_tune')}
    <div class="toggle-row">
      <button type="button" class="auto-tune-btn v2-control-button" onclick={onAutoTune}>
        AUTO TUNE
      </button>
    </div>
    {/if}
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
