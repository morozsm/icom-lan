<script lang="ts">
  import { SegmentedControl } from '$lib/SegmentedControl';
  import { ValueControl } from '../controls/value-control';
  import { FillButton } from '$lib/Button';
  import { hasCapability } from '$lib/stores/capabilities.svelte';
  import { isCwMode, buildNrOptions, buildNotchOptions } from './dsp-utils';

  interface Props {
    nrMode: number;
    nrLevel: number;
    nbActive: boolean;
    nbLevel: number;
    notchMode: 'off' | 'auto' | 'manual';
    notchFreq: number;
    cwAutoTune: boolean;
    cwPitch: number;
    currentMode: string;
    onNrModeChange: (v: number) => void;
    onNrLevelChange: (v: number) => void;
    onNbToggle: (v: boolean) => void;
    onNbLevelChange: (v: number) => void;
    onNotchModeChange: (v: string) => void;
    onNotchFreqChange: (v: number) => void;
    onCwAutoTuneToggle: (v: boolean) => void;
    onCwPitchChange: (v: number) => void;
  }

  let {
    nrMode,
    nrLevel,
    nbActive,
    nbLevel,
    notchMode,
    notchFreq,
    cwAutoTune,
    cwPitch,
    currentMode,
    onNrModeChange,
    onNrLevelChange,
    onNbToggle,
    onNbLevelChange,
    onNotchModeChange,
    onNotchFreqChange,
    onCwAutoTuneToggle,
    onCwPitchChange,
  }: Props = $props();

  let showNr = $derived(hasCapability('nr'));
  let showNb = $derived(hasCapability('nb'));
  let showCw = $derived(isCwMode(currentMode));
  let nrOptions = $derived(buildNrOptions());
  let notchOptions = $derived(buildNotchOptions());
</script>

<div class="panel-body">

    {#if showNr}
      <div class="section">
        <div class="section-label">NR</div>
        <SegmentedControl
          options={nrOptions}
          selected={nrMode}
          onchange={(v) => onNrModeChange(v as number)}
        />
        <ValueControl
          label="NR Level"
          value={nrLevel}
          min={0}
          max={255}
          step={1}
          renderer="hbar"
          accentColor="var(--v2-accent-cyan)"
          onChange={onNrLevelChange}
        />
      </div>
    {/if}

    {#if showNb}
      <div class="section">
        <div class="section-label">NB</div>
        <!-- status-toggle: NB on/off -->
        <div class="single-control">
          <FillButton
            active={nbActive}
            color="orange"
            onclick={() => onNbToggle(!nbActive)}
          >{nbActive ? 'ON' : 'OFF'}</FillButton>
        </div>
        <ValueControl
          label="NB Level"
          value={nbLevel}
          min={0}
          max={255}
          step={1}
          renderer="hbar"
          accentColor="var(--v2-accent-yellow)"
          onChange={onNbLevelChange}
        />
      </div>
    {/if}

    <div class="section">
      <div class="section-label">Notch</div>
      <SegmentedControl
        options={notchOptions}
        selected={notchMode}
        onchange={(v) => onNotchModeChange(v as string)}
      />
      {#if notchMode === 'manual'}
        <ValueControl
          label="Notch Freq"
          value={notchFreq}
          min={0}
          max={3000}
          step={1}
          unit="Hz"
          renderer="hbar"
          accentColor="var(--v2-accent-cyan)"
          onChange={onNotchFreqChange}
        />
      {/if}
    </div>

    {#if showCw}
      <div class="section">
        <div class="section-row">
          <div class="section-label">CW</div>
          <!-- action-button: CW auto tune command (not sustained state; not yet implemented in command-bus/state) -->
          <button
            type="button"
            class="v2-control-button"
            onclick={() => onCwAutoTuneToggle(true)}
          >Auto Tune</button>
        </div>
        <ValueControl
          label="CW Pitch"
          value={cwPitch}
          min={300}
          max={900}
          step={1}
          unit="Hz"
          renderer="hbar"
          accentColor="var(--v2-accent-cyan)"
          onChange={onCwPitchChange}
        />
      </div>
    {/if}

  </div>

<style>
  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 7px 8px;
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .section-label {
    color: var(--v2-text-header);
    font-family: 'Roboto Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .section-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .single-control {
    display: flex;
    align-items: center;
    justify-content: flex-start;
  }
</style>
