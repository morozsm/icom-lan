<script lang="ts">
  import SegmentedButton from '../controls/SegmentedButton.svelte';
  import { ValueControl } from '../controls/value-control';
  import StatusBadge from '../controls/StatusBadge.svelte';
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

<div class="panel">
  <div class="panel-header">DSP</div>
  <div class="panel-body">

    {#if showNr}
      <div class="section">
        <div class="section-label">NR</div>
        <SegmentedButton
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
          accentColor="#00D4FF"
          onChange={onNrLevelChange}
        />
      </div>
    {/if}

    {#if showNb}
      <div class="section">
        <div class="section-label">NB</div>
        <div class="single-control">
          <StatusBadge
            label={nbActive ? 'ON' : 'OFF'}
            active={nbActive}
            color="orange"
            onclick={() => onNbToggle(!nbActive)}
          />
        </div>
        <ValueControl
          label="NB Level"
          value={nbLevel}
          min={0}
          max={255}
          step={1}
          renderer="hbar"
          accentColor="#FFB800"
          onChange={onNbLevelChange}
        />
      </div>
    {/if}

    <div class="section">
      <div class="section-label">Notch</div>
      <SegmentedButton
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
          accentColor="#00D4FF"
          onChange={onNotchFreqChange}
        />
      {/if}
    </div>

    {#if showCw}
      <div class="section">
        <div class="section-row">
          <div class="section-label">CW</div>
          <StatusBadge
            label="Auto Tune"
            active={cwAutoTune}
            onclick={() => onCwAutoTuneToggle(!cwAutoTune)}
          />
        </div>
        <ValueControl
          label="CW Pitch"
          value={cwPitch}
          min={300}
          max={900}
          step={1}
          unit="Hz"
          renderer="hbar"
          accentColor="#00D4FF"
          onChange={onCwPitchChange}
        />
      </div>
    {/if}

  </div>
</div>

<style>
  .panel {
    background: #060A10;
    border: 1px solid #18202A;
    border-radius: 4px;
    overflow: hidden;
  }

  .panel-header {
    padding: 5px 8px;
    color: var(--v2-text-header);
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    border-bottom: 1px solid #18202A;
  }

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
