<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import RfFrontEnd from '../panels/RfFrontEnd.svelte';
  import FilterPanel from '../panels/FilterPanel.svelte';
  import AgcPanel from '../panels/AgcPanel.svelte';
  import RitXitPanel from '../panels/RitXitPanel.svelte';
  import BandSelector from '../controls/BandSelector.svelte';
  import {
    toRfFrontEndProps,
    toFilterProps,
    toAgcProps,
    toRitXitProps,
    toBandSelectorProps,
  } from '../wiring/state-adapter';
  import {
    makeRfFrontEndHandlers,
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
  let filter = $derived(toFilterProps(radioState, caps));
  let agc = $derived(toAgcProps(radioState, caps));
  let ritXit = $derived(toRitXitProps(radioState, caps));
  let band = $derived(toBandSelectorProps(radioState));

  // Command handlers via command-bus
  const rfHandlers = makeRfFrontEndHandlers();
  const filterHandlers = makeFilterHandlers();
  const agcHandlers = makeAgcHandlers();
  const ritXitHandlers = makeRitXitHandlers();
  const bandHandlers = makeBandHandlers();
</script>

<aside class="left-sidebar">
  <RfFrontEnd
    rfGain={rfFrontEnd.rfGain}
    att={rfFrontEnd.att}
    pre={rfFrontEnd.pre}
    onRfGainChange={rfHandlers.onRfGainChange}
    onAttChange={rfHandlers.onAttChange}
    onPreChange={rfHandlers.onPreChange}
  />

  <FilterPanel
    filterWidth={filter.filterWidth}
    ifShift={filter.ifShift}
    hasPbt={filter.hasPbt}
    pbtInner={filter.pbtInner}
    pbtOuter={filter.pbtOuter}
    onFilterWidthChange={filterHandlers.onFilterWidthChange}
    onIfShiftChange={filterHandlers.onIfShiftChange}
    onPbtInnerChange={filterHandlers.onPbtInnerChange}
    onPbtOuterChange={filterHandlers.onPbtOuterChange}
    onPbtReset={filterHandlers.onPbtReset}
  />

  <AgcPanel
    agcMode={agc.agcMode}
    agcGain={agc.agcGain}
    onAgcModeChange={agcHandlers.onAgcModeChange}
    onAgcGainChange={agcHandlers.onAgcGainChange}
  />

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

  <BandSelector
    currentFreq={band.currentFreq}
    onBandSelect={bandHandlers.onBandSelect}
  />
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
</style>
