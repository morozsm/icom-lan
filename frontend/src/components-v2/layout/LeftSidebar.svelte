<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import RfFrontEnd from '../panels/RfFrontEnd.svelte';
  import ModePanel from '../panels/ModePanel.svelte';
  import FilterPanel from '../panels/FilterPanel.svelte';
  import AgcPanel from '../panels/AgcPanel.svelte';
  import RitXitPanel from '../panels/RitXitPanel.svelte';
  import BandSelector from '../controls/BandSelector.svelte';
  import CollapsiblePanel from '../controls/CollapsiblePanel.svelte';
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
    makePresetHandlers,
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
  // Command handlers via command-bus
  const rfHandlers = makeRfFrontEndHandlers();
  const modeHandlers = makeModeHandlers();
  const filterHandlers = makeFilterHandlers();
  const agcHandlers = makeAgcHandlers();
  const ritXitHandlers = makeRitXitHandlers();
  const bandHandlers = makeBandHandlers();
  const presetHandlers = makePresetHandlers();
</script>

<aside class="left-sidebar">
  <CollapsiblePanel title="RF FRONT END" panelId="rf-front-end" dataPanel="rf-frontend">
    <RfFrontEnd
      rfGain={rfFrontEnd.rfGain}
      squelch={rfFrontEnd.squelch}
      att={rfFrontEnd.att}
      pre={rfFrontEnd.pre}
      digiSel={rfFrontEnd.digiSel}
      ipPlus={rfFrontEnd.ipPlus}
      onRfGainChange={rfHandlers.onRfGainChange}
      onSquelchChange={rfHandlers.onSquelchChange}
      onAttChange={rfHandlers.onAttChange}
      onPreChange={rfHandlers.onPreChange}
      onDigiSelToggle={rfHandlers.onDigiSelToggle}
      onIpPlusToggle={rfHandlers.onIpPlusToggle}
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
      onAgcModeChange={agcHandlers.onAgcModeChange}
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
      onPresetSelect={presetHandlers.onPresetSelect}
    />
  </CollapsiblePanel>
</aside>

<style>
  .left-sidebar {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
    padding: 6px 6px 16px;
    width: 100%;
    box-sizing: border-box;
  }


</style>
