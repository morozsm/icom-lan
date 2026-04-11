<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import RfFrontEnd from '../panels/RfFrontEnd.svelte';
  import ModePanel from '../panels/ModePanel.svelte';
  import FilterPanel from '../panels/FilterPanel.svelte';
  import AgcPanel from '../panels/AgcPanel.svelte';
  import RitXitPanel from '../panels/RitXitPanel.svelte';
  import AntennaPanel from '../panels/AntennaPanel.svelte';
  import ScanPanel from '../panels/ScanPanel.svelte';
  import BandSelector from '../controls/BandSelector.svelte';
  import CollapsiblePanel from '../controls/CollapsiblePanel.svelte';
  import { createDragReorder } from '$lib/drag-reorder.svelte';
  import {
    toRfFrontEndProps,
    toModeProps,
    toFilterProps,
    toAgcProps,
    toRitXitProps,
    toBandSelectorProps,
    toAntennaProps,
    toScanProps,
  } from '../wiring/state-adapter';
  import {
    makeRfFrontEndHandlers,
    makeModeHandlers,
    makeFilterHandlers,
    makeAgcHandlers,
    makeRitXitHandlers,
    makeBandHandlers,
    makePresetHandlers,
    makeAntennaHandlers,
    makeScanHandlers,
  } from '../wiring/command-bus';

  // Reactive state + capabilities
  let radioState = $derived(radio.current);
  let caps = $derived(getCapabilities());

  // --- Panel reorder (shared logic) ---
  const drag = createDragReorder({
    storageKey: 'icom-lan:panel-order',
    defaults: ['rf-front-end', 'mode', 'filter', 'agc', 'rit-xit', 'band', 'antenna', 'scan'],
    containerSelector: '.left-sidebar',
  });

  // Derived props via state adapter
  let rfFrontEnd = $derived(toRfFrontEndProps(radioState, caps));
  let mode = $derived(toModeProps(radioState, caps));
  let filter = $derived(toFilterProps(radioState, caps));
  let agc = $derived(toAgcProps(radioState, caps));
  let ritXit = $derived(toRitXitProps(radioState, caps));
  let band = $derived(toBandSelectorProps(radioState));
  let antenna = $derived(toAntennaProps(radioState, caps));
  let scan = $derived(toScanProps(radioState));
  // Command handlers via command-bus
  const rfHandlers = makeRfFrontEndHandlers();
  const modeHandlers = makeModeHandlers();
  const filterHandlers = makeFilterHandlers();
  const agcHandlers = makeAgcHandlers();
  const ritXitHandlers = makeRitXitHandlers();
  const bandHandlers = makeBandHandlers();
  const presetHandlers = makePresetHandlers();
  const antennaHandlers = makeAntennaHandlers();
  const scanHandlers = makeScanHandlers();
</script>

<aside class="left-sidebar" class:cross-drop-target={drag.isDropTarget}>
  <CollapsiblePanel title="RF FRONT END" panelId="rf-front-end" dataPanel="rf-frontend"
    draggable={true} onDragStart={drag.handleDragStart}
    style={drag.dragStyle('rf-front-end')}>
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

  <CollapsiblePanel title="MODE" panelId="mode"
    draggable={true} onDragStart={drag.handleDragStart}
    style={drag.dragStyle('mode')}>
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

  <CollapsiblePanel title="FILTER" panelId="filter"
    draggable={true} onDragStart={drag.handleDragStart}
    style={drag.dragStyle('filter')}>
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

  <CollapsiblePanel title="AGC" panelId="agc"
    draggable={true} onDragStart={drag.handleDragStart}
    style={drag.dragStyle('agc')}>
    <AgcPanel
      agcMode={agc.agcMode}
      onAgcModeChange={agcHandlers.onAgcModeChange}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="RIT / XIT" panelId="rit-xit"
    draggable={true} onDragStart={drag.handleDragStart}
    style={drag.dragStyle('rit-xit')}>
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

  <CollapsiblePanel title="BAND" panelId="band"
    draggable={true} onDragStart={drag.handleDragStart}
    style={drag.dragStyle('band')}>
    <BandSelector
      currentFreq={band.currentFreq}
      onBandSelect={bandHandlers.onBandSelect}
      onPresetSelect={presetHandlers.onPresetSelect}
    />
  </CollapsiblePanel>

  {#if antenna.antennaCount > 1}
    <CollapsiblePanel title="ANTENNA" panelId="antenna" dataPanel="antenna"
      draggable={true} onDragStart={drag.handleDragStart}
      style={drag.dragStyle('antenna')}>
      <AntennaPanel
        txAntenna={antenna.txAntenna}
        rxAnt={antenna.rxAnt}
        antennaCount={antenna.antennaCount}
        hasRxAntenna={antenna.hasRxAntenna}
        onSelectAnt1={antennaHandlers.onSelectAnt1}
        onSelectAnt2={antennaHandlers.onSelectAnt2}
        onToggleRxAnt={antennaHandlers.onToggleRxAnt}
      />
    </CollapsiblePanel>
  {/if}

  <CollapsiblePanel title="SCAN" panelId="scan"
    draggable={true} onDragStart={drag.handleDragStart}
    style={drag.dragStyle('scan')}>
    <ScanPanel
      scanning={scan.scanning}
      scanType={scan.scanType}
      scanResumeMode={scan.scanResumeMode}
      onScanStart={scanHandlers.onScanStart}
      onScanStop={scanHandlers.onScanStop}
      onDfSpanChange={scanHandlers.onDfSpanChange}
      onResumeChange={scanHandlers.onResumeChange}
    />
  </CollapsiblePanel>

  <div class="sidebar-footer" style="order:99">
    <button type="button" class="reset-order-btn" onclick={drag.reset}>
      Reset panel order
    </button>
  </div>
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

  .left-sidebar.cross-drop-target {
    outline: 2px solid var(--v2-accent, #4af);
    outline-offset: -2px;
  }

  .sidebar-footer {
    display: flex;
    justify-content: center;
    padding-top: 4px;
  }

  .reset-order-btn {
    background: none;
    border: 1px solid var(--v2-collapsible-border, #444);
    color: var(--v2-collapsible-chevron, #888);
    font-family: 'Roboto Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 3px;
    cursor: pointer;
    transition: color 0.15s ease, border-color 0.15s ease;
  }

  .reset-order-btn:hover {
    color: var(--v2-collapsible-header-text, #ccc);
    border-color: var(--v2-collapsible-header-text, #ccc);
  }
</style>
