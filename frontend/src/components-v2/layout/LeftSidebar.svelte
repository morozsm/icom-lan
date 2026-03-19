<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { formatStep, getTuningStep, isAutoStep } from '$lib/stores/tuning.svelte';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import RfFrontEnd from '../panels/RfFrontEnd.svelte';
  import ModePanel from '../panels/ModePanel.svelte';
  import FilterPanel from '../panels/FilterPanel.svelte';
  import AgcPanel from '../panels/AgcPanel.svelte';
  import RitXitPanel from '../panels/RitXitPanel.svelte';
  import BandSelector from '../controls/BandSelector.svelte';
  import CollapsiblePanel from '../controls/CollapsiblePanel.svelte';
  import { getShortcutHint } from './shortcut-hints';
  import {
    toRfFrontEndProps,
    toModeProps,
    toFilterProps,
    toAgcProps,
    toRitXitProps,
    toBandSelectorProps,
  } from '../wiring/state-adapter';
  import {
    makeRfFrontEndHandlers,
    makeModeHandlers,
    makeFilterHandlers,
    makeAgcHandlers,
    makeRitXitHandlers,
    makeBandHandlers,
  } from '../wiring/command-bus';

  // Reactive state + capabilities
  let radioState = $derived(radio.current);
  let caps = $derived(getCapabilities());

  // Derived props via state adapter
  let rfFrontEnd = $derived(toRfFrontEndProps(radioState, caps));
  let mode = $derived(toModeProps(radioState, caps));
  let filter = $derived(toFilterProps(radioState, caps));
  let agc = $derived(toAgcProps(radioState, caps));
  let ritXit = $derived(toRitXitProps(radioState, caps));
  let band = $derived(toBandSelectorProps(radioState));
  let tuningStep = $derived(getTuningStep());
  let tuningStepLabel = $derived(formatStep(tuningStep));
  let autoStep = $derived(isAutoStep());
  const stepUpHint = getShortcutHint('adjust_tuning_step', (binding) => binding.params?.direction === 'up');
  const stepDownHint = getShortcutHint('adjust_tuning_step', (binding) => binding.params?.direction === 'down');
  const tuneLeftHint = getShortcutHint('tune', (binding) => binding.sequence?.[0] === 'ArrowLeft');
  const tuneRightHint = getShortcutHint('tune', (binding) => binding.sequence?.[0] === 'ArrowRight');

  // Command handlers via command-bus
  const rfHandlers = makeRfFrontEndHandlers();
  const modeHandlers = makeModeHandlers();
  const filterHandlers = makeFilterHandlers();
  const agcHandlers = makeAgcHandlers();
  const ritXitHandlers = makeRitXitHandlers();
  const bandHandlers = makeBandHandlers();
</script>

<aside class="left-sidebar">
  <section class="step-panel">
    <div class="step-header-row">
      <span class="step-header">TUNING STEP</span>
      <span class="step-mode">{autoStep ? 'AUTO' : 'MANUAL'}</span>
    </div>
    <div class="step-value">{tuningStepLabel}</div>
    <div class="step-hints">
      <span class="step-chip" data-shortcut-hint={tuneLeftHint ?? undefined} title={tuneLeftHint ?? undefined}>LEFT</span>
      <span class="step-chip" data-shortcut-hint={tuneRightHint ?? undefined} title={tuneRightHint ?? undefined}>RIGHT</span>
      <span class="step-chip" data-shortcut-hint={stepDownHint ?? undefined} title={stepDownHint ?? undefined}>DOWN</span>
      <span class="step-chip" data-shortcut-hint={stepUpHint ?? undefined} title={stepUpHint ?? undefined}>UP</span>
    </div>
  </section>

  <CollapsiblePanel title="RF FRONT END" panelId="rf-front-end">
    <RfFrontEnd
      rfGain={rfFrontEnd.rfGain}
      att={rfFrontEnd.att}
      pre={rfFrontEnd.pre}
      onRfGainChange={rfHandlers.onRfGainChange}
      onAttChange={rfHandlers.onAttChange}
      onPreChange={rfHandlers.onPreChange}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="MODE" panelId="mode">
    <ModePanel
      currentMode={mode.currentMode}
      modes={mode.modes}
      dataMode={mode.dataMode}
      hasDataMode={mode.hasDataMode}
      dataModeCount={mode.dataModeCount}
      dataModeLabels={mode.dataModeLabels}
      onModeChange={modeHandlers.onModeChange}
      onDataModeChange={modeHandlers.onDataModeChange}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="FILTER" panelId="filter">
    <FilterPanel
      currentMode={filter.currentMode}
      currentFilter={filter.currentFilter}
      filterShape={filter.filterShape}
      filterLabels={filter.filterLabels}
      filterWidth={filter.filterWidth}
      filterWidthMin={filter.filterWidthMin}
      filterWidthMax={filter.filterWidthMax}
      filterConfig={filter.filterConfig}
      ifShift={filter.ifShift}
      hasPbt={filter.hasPbt}
      pbtInner={filter.pbtInner}
      pbtOuter={filter.pbtOuter}
      onFilterChange={filterHandlers.onFilterChange}
      onFilterWidthChange={filterHandlers.onFilterWidthChange}
      onFilterShapeChange={filterHandlers.onFilterShapeChange}
      onFilterPresetChange={filterHandlers.onFilterPresetChange}
      onFilterDefaults={filterHandlers.onFilterDefaults}
      onIfShiftChange={filterHandlers.onIfShiftChange}
      onPbtInnerChange={filterHandlers.onPbtInnerChange}
      onPbtOuterChange={filterHandlers.onPbtOuterChange}
      onPbtReset={filterHandlers.onPbtReset}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="AGC" panelId="agc">
    <AgcPanel
      agcMode={agc.agcMode}
      agcGain={agc.agcGain}
      onAgcModeChange={agcHandlers.onAgcModeChange}
      onAgcGainChange={agcHandlers.onAgcGainChange}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="RIT / XIT" panelId="rit-xit">
    <RitXitPanel
      ritActive={ritXit.ritActive}
      ritOffset={ritXit.ritOffset}
      xitActive={ritXit.xitActive}
      xitOffset={ritXit.xitOffset}
      hasRit={ritXit.hasRit}
      hasXit={ritXit.hasXit}
      onRitToggle={ritXitHandlers.onRitToggle}
      onXitToggle={ritXitHandlers.onXitToggle}
      onRitOffsetChange={ritXitHandlers.onRitOffsetChange}
      onXitOffsetChange={ritXitHandlers.onXitOffsetChange}
      onClear={ritXitHandlers.onClear}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="BAND" panelId="band">
    <BandSelector
      currentFreq={band.currentFreq}
      onBandSelect={bandHandlers.onBandSelect}
    />
  </CollapsiblePanel>
</aside>

<style>
  .left-sidebar {
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
    height: 100%;
    min-width: 0;
    padding: 6px;
    width: 100%;
    box-sizing: border-box;
  }

  .step-panel {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px 10px 10px;
    background: linear-gradient(180deg, var(--v2-sidebar-gradient-top), var(--v2-sidebar-gradient-bottom));
    border: 1px solid var(--v2-border-darker);
    border-radius: 4px;
    font-family: 'Roboto Mono', monospace;
  }

  .step-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .step-header,
  .step-mode {
    color: var(--v2-text-subdued);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
  }

  .step-mode {
    color: var(--v2-accent-cyan);
  }

  .step-value {
    color: var(--v2-text-primary);
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.03em;
  }

  .step-hints {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 4px;
  }

  .step-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 24px;
    border: 1px solid var(--v2-border);
    border-radius: 999px;
    background: var(--v2-sidebar-footer-bg);
    color: var(--v2-text-secondary);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }
</style>
