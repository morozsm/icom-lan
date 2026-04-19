<script lang="ts">
  // ESSENTIALS panel — default mobile chip content.
  // Compact: VFO ops (SPLIT / A<->B / A=B), MODE quick, FILTER quick,
  // AUDIO (monitor mode + AF), DSP toggles (NB / NR / NOTCH).
  import { HardwareButton } from '$lib/Button';
  import { ValueControl, rawToPercentDisplay } from '../controls/value-control';

  interface Props {
    vfoOps: { splitActive: boolean };
    mode: { currentMode: string };
    quickModes: string[];
    filter: { currentFilter: number; filterLabels?: string[] };
    rxAudio: { monitorMode: string; afLevel: number };
    dsp: { nbActive: boolean; nrMode: number; notchMode: string };
    onSplitToggle: () => void;
    onSwap: () => void;
    onEqual: () => void;
    onModeChange: (m: string) => void;
    onMoreModes: () => void;
    onFilterChange: (idx: number) => void;
    onMoreFilters: () => void;
    onMonitorModeChange: (m: string) => void;
    onAfLevelChange: (v: number) => void;
    onNbToggle: (v: boolean) => void;
    onNrModeChange: (m: number) => void;
    onNotchModeChange: (m: string) => void;
  }

  let {
    vfoOps, mode, quickModes, filter, rxAudio, dsp,
    onSplitToggle, onSwap, onEqual,
    onModeChange, onMoreModes,
    onFilterChange, onMoreFilters,
    onMonitorModeChange, onAfLevelChange,
    onNbToggle, onNrModeChange, onNotchModeChange,
  }: Props = $props();
</script>

<div class="ess">
  <div class="ess-group">
    <div class="ess-label">VFO</div>
    <div class="ess-row">
      <HardwareButton active={vfoOps.splitActive} indicator="edge-left" color={vfoOps.splitActive ? 'yellow' : 'muted'} onclick={onSplitToggle}>SPLIT</HardwareButton>
      <HardwareButton indicator="edge-left" color="cyan" onclick={onSwap}>A↔B</HardwareButton>
      <HardwareButton indicator="edge-left" color="cyan" onclick={onEqual}>A=B</HardwareButton>
    </div>
  </div>

  <div class="ess-group">
    <div class="ess-label">MODE</div>
    <div class="ess-row">
      {#each quickModes as m}
        <HardwareButton active={mode.currentMode === m} indicator="edge-left" color="cyan" onclick={() => onModeChange(m)}>{m}</HardwareButton>
      {/each}
      <HardwareButton indicator="edge-left" color="muted" onclick={onMoreModes}>More…</HardwareButton>
    </div>
  </div>

  <div class="ess-group">
    <div class="ess-label">FILTER</div>
    <div class="ess-row">
      {#each (filter.filterLabels ?? ['FIL1', 'FIL2', 'FIL3']) as label, idx}
        <HardwareButton active={filter.currentFilter === idx + 1} indicator="edge-left" color="cyan" onclick={() => onFilterChange(idx + 1)}>{label}</HardwareButton>
      {/each}
      <HardwareButton indicator="edge-left" color="muted" onclick={onMoreFilters}>More…</HardwareButton>
    </div>
  </div>

  <div class="ess-group">
    <div class="ess-label">AUDIO</div>
    <div class="ess-row">
      {#each ['local', 'live', 'mute'] as opt}
        <HardwareButton active={rxAudio.monitorMode === opt} indicator="edge-left" color={opt === 'mute' ? 'red' : 'cyan'} onclick={() => onMonitorModeChange(opt)}>
          {opt === 'local' ? 'LOCAL' : opt === 'live' ? 'LIVE' : 'MUTE'}
        </HardwareButton>
      {/each}
    </div>
    <ValueControl
      label="AF Level"
      value={rxAudio.afLevel}
      min={0}
      max={255}
      step={1}
      renderer="hbar"
      displayFn={rawToPercentDisplay}
      accentColor="var(--v2-accent-cyan-alt)"
      onChange={onAfLevelChange}
      variant="hardware-illuminated"
    />
  </div>

  <div class="ess-group">
    <div class="ess-label">DSP</div>
    <div class="ess-row">
      <HardwareButton active={dsp.nbActive} indicator="edge-left" color={dsp.nbActive ? 'green' : 'muted'} onclick={() => onNbToggle(!dsp.nbActive)}>NB</HardwareButton>
      <HardwareButton active={dsp.nrMode > 0} indicator="edge-left" color={dsp.nrMode > 0 ? 'green' : 'muted'} onclick={() => onNrModeChange(dsp.nrMode > 0 ? 0 : 1)}>NR</HardwareButton>
      <HardwareButton active={dsp.notchMode !== 'off'} indicator="edge-left" color={dsp.notchMode !== 'off' ? 'green' : 'muted'} onclick={() => onNotchModeChange(dsp.notchMode !== 'off' ? 'off' : 'auto')}>NOTCH</HardwareButton>
    </div>
  </div>
</div>

<style>
  .ess {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 10px 8px;
  }

  .ess-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .ess-label {
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--v2-text-dim, #555);
    text-transform: uppercase;
  }

  .ess-row {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }

  .ess-row > :global(button) {
    flex: 1 1 0;
    min-width: 52px;
    min-height: 40px;
  }
</style>
