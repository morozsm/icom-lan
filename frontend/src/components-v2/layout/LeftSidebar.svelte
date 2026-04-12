<script lang="ts">
  import { runtime } from '$lib/runtime';
  import { hasCapability } from '$lib/stores/capabilities.svelte';
  import RfFrontEnd from '../panels/RfFrontEnd.svelte';
  import ModePanel from '../panels/ModePanel.svelte';
  import FilterPanel from '../panels/FilterPanel.svelte';
  import AgcPanel from '../panels/AgcPanel.svelte';
  import RitXitPanel from '../panels/RitXitPanel.svelte';
  import AntennaPanel from '../panels/AntennaPanel.svelte';
  import ScanPanel from '../panels/ScanPanel.svelte';
  import BandSelector from '../controls/BandSelector.svelte';
  import RxAudioPanel from '../panels/RxAudioPanel.svelte';
  import DspPanel from '../panels/DspPanel.svelte';
  import TxPanel from '../panels/TxPanel.svelte';
  import CwPanel from '../panels/CwPanel.svelte';
  import MemoryPanel from '../panels/MemoryPanel.svelte';
  import CollapsiblePanel from '../controls/CollapsiblePanel.svelte';
  import { createDragReorder } from '$lib/drag-reorder.svelte';
  import {
    toRfFrontEndProps,
    toFilterProps,
    toRitXitProps,
    toBandSelectorProps,
    toScanProps,
    toDspProps,
    toTxProps,
    toCwProps,
  } from '../wiring/state-adapter';
  import {
    makeRfFrontEndHandlers,
    makeFilterHandlers,
    makeRitXitHandlers,
    makeBandHandlers,
    makePresetHandlers,
    makeScanHandlers,
    makeDspHandlers,
    makeTxHandlers,
    makeCwPanelHandlers,
    makeSystemHandlers,
  } from '../wiring/command-bus';

  // Reactive state + capabilities — via runtime
  let radioState = $derived(runtime.state);
  let caps = $derived(runtime.caps);

  // --- Panel reorder (shared logic) ---
  const drag = createDragReorder({
    storageKey: 'icom-lan:panel-order',
    defaults: ['rf-front-end', 'mode', 'filter', 'agc', 'rit-xit', 'band', 'antenna', 'scan'],
    containerSelector: '.left-sidebar',
  });

  // Derived props via state adapter — panels not yet self-wiring
  let rfFrontEnd = $derived(toRfFrontEndProps(radioState, caps));
  let filter = $derived(toFilterProps(radioState, caps));
  let ritXit = $derived(toRitXitProps(radioState, caps));
  let band = $derived(toBandSelectorProps(radioState));
  let scan = $derived(toScanProps(radioState));
  let dsp = $derived(toDspProps(radioState, caps));
  let tx = $derived(toTxProps(radioState, caps));
  let cw = $derived(toCwProps(radioState, caps));
  // Command handlers
  const rfHandlers = makeRfFrontEndHandlers();
  const filterHandlers = makeFilterHandlers();
  const ritXitHandlers = makeRitXitHandlers();
  const bandHandlers = makeBandHandlers();
  const presetHandlers = makePresetHandlers();
  const scanHandlers = makeScanHandlers();
  const dspHandlers = makeDspHandlers();
  const txHandlers = makeTxHandlers();
  const cwHandlers = makeCwPanelHandlers();
  const systemHandlers = makeSystemHandlers();
</script>

<aside class="left-sidebar" class:cross-drop-target={drag.isDropTarget}>
  {#if drag.order.includes('rf-front-end')}
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
  {/if}

  {#if drag.order.includes('mode')}
    <CollapsiblePanel title="MODE" panelId="mode"
      draggable={true} onDragStart={drag.handleDragStart}
      style={drag.dragStyle('mode')}>
      <ModePanel />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('filter')}
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
  {/if}

  {#if drag.order.includes('agc')}
    <CollapsiblePanel title="AGC" panelId="agc"
      draggable={true} onDragStart={drag.handleDragStart}
      style={drag.dragStyle('agc')}>
      <AgcPanel />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('rit-xit')}
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
  {/if}

  {#if drag.order.includes('band')}
    <CollapsiblePanel title="BAND" panelId="band"
      draggable={true} onDragStart={drag.handleDragStart}
      style={drag.dragStyle('band')}>
      <BandSelector
        currentFreq={band.currentFreq}
        onBandSelect={bandHandlers.onBandSelect}
        onPresetSelect={presetHandlers.onPresetSelect}
      />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('antenna') && (caps?.antennas ?? 1) > 1}
    <CollapsiblePanel title="ANTENNA" panelId="antenna" dataPanel="antenna"
      draggable={true} onDragStart={drag.handleDragStart}
      style={drag.dragStyle('antenna')}>
      <AntennaPanel />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('scan')}
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
  {/if}

  {#if drag.order.includes('rx-audio')}
    <CollapsiblePanel title="RX AUDIO" panelId="rx-audio" draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('rx-audio')}>
      <RxAudioPanel />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('dsp')}
    <CollapsiblePanel title="DSP" panelId="dsp" draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('dsp')}>
      <DspPanel
        nrMode={dsp.nrMode}
        nrLevel={dsp.nrLevel}
        nbActive={dsp.nbActive}
        nbLevel={dsp.nbLevel}
        nbDepth={dsp.nbDepth}
        nbWidth={dsp.nbWidth}
        notchMode={dsp.notchMode}
        notchFreq={dsp.notchFreq}
        manualNotchWidth={dsp.manualNotchWidth}
        agcTimeConstant={dsp.agcTimeConstant}
        onNrModeChange={dspHandlers.onNrModeChange}
        onNrLevelChange={dspHandlers.onNrLevelChange}
        onNbToggle={dspHandlers.onNbToggle}
        onNbLevelChange={dspHandlers.onNbLevelChange}
        onNbDepthChange={dspHandlers.onNbDepthChange}
        onNbWidthChange={dspHandlers.onNbWidthChange}
        onNotchModeChange={dspHandlers.onNotchModeChange}
        onNotchFreqChange={dspHandlers.onNotchFreqChange}
        onManualNotchWidthChange={dspHandlers.onManualNotchWidthChange}
        onAgcTimeChange={dspHandlers.onAgcTimeChange}
      />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('tx')}
    <CollapsiblePanel title="TX" panelId="tx" draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('tx')}>
      <TxPanel
        txActive={tx.txActive}
        rfPower={tx.rfPower}
        micGain={tx.micGain}
        atuActive={tx.atuActive}
        atuTuning={tx.atuTuning}
        voxActive={tx.voxActive}
        compActive={tx.compActive}
        compLevel={tx.compLevel}
        monActive={tx.monActive}
        monLevel={tx.monLevel}
        driveGain={tx.driveGain}
        onRfPowerChange={txHandlers.onRfPowerChange}
        onMicGainChange={txHandlers.onMicGainChange}
        onAtuToggle={txHandlers.onAtuToggle}
        onAtuTune={txHandlers.onAtuTune}
        onVoxToggle={txHandlers.onVoxToggle}
        onCompToggle={txHandlers.onCompToggle}
        onCompLevelChange={txHandlers.onCompLevelChange}
        onMonToggle={txHandlers.onMonToggle}
        onMonLevelChange={txHandlers.onMonLevelChange}
        onDriveGainChange={txHandlers.onDriveGainChange}
        onPttOn={systemHandlers.onPttOn}
        onPttOff={systemHandlers.onPttOff}
      />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('cw') && hasCapability('cw')}
    <CollapsiblePanel title="CW" panelId="cw" draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('cw')}>
      <CwPanel
        cwPitch={cw.cwPitch}
        keySpeed={cw.keySpeed}
        breakIn={cw.breakIn}
        breakInDelay={cw.breakInDelay}
        apfMode={cw.apfMode}
        twinPeak={cw.twinPeak}
        currentMode={cw.currentMode}
        onCwPitchChange={cwHandlers.onCwPitchChange}
        onKeySpeedChange={cwHandlers.onKeySpeedChange}
        onBreakInToggle={cwHandlers.onBreakInToggle}
        onBreakInModeChange={cwHandlers.onBreakInModeChange}
        onBreakInDelayChange={cwHandlers.onBreakInDelayChange}
        onApfChange={cwHandlers.onApfChange}
        onTwinPeakToggle={cwHandlers.onTwinPeakToggle}
        onAutoTune={cwHandlers.onAutoTune}
      />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('memory')}
    <CollapsiblePanel title="MEMORY" panelId="memory" draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('memory')}>
      <MemoryPanel />
    </CollapsiblePanel>
  {/if}

  <div class="sidebar-footer" style="order:99">
    <button type="button" class="reset-order-btn" onclick={drag.resetAll}>
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
