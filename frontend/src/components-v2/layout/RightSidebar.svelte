<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { getCapabilities, hasCapability } from '$lib/stores/capabilities.svelte';
  import RxAudioPanel from '../panels/RxAudioPanel.svelte';
  import DspPanel from '../panels/DspPanel.svelte';
  import TxPanel from '../panels/TxPanel.svelte';
  import CwPanel from '../panels/CwPanel.svelte';
  import MemoryPanel from '../panels/MemoryPanel.svelte';
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
    toDspProps,
    toTxProps,
    toCwProps,
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
    makeDspHandlers,
    makeTxHandlers,
    makeCwPanelHandlers,
    makeSystemHandlers,
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

  // Derived props via state adapter — native panels
  let dsp = $derived(toDspProps(radioState, caps));
  let tx = $derived(toTxProps(radioState, caps));
  let cw = $derived(toCwProps(radioState, caps));
  // Derived props — panels from left sidebar (for cross-sidebar rendering)
  let rfFrontEnd = $derived(toRfFrontEndProps(radioState, caps));
  let modeProps = $derived(toModeProps(radioState, caps));
  let filter = $derived(toFilterProps(radioState, caps));
  let agc = $derived(toAgcProps(radioState, caps));
  let ritXit = $derived(toRitXitProps(radioState, caps));
  let band = $derived(toBandSelectorProps(radioState));
  let antenna = $derived(toAntennaProps(radioState, caps));
  let scan = $derived(toScanProps(radioState));

  // Command handlers via command-bus
  const dspHandlers = makeDspHandlers();
  const txHandlers = makeTxHandlers();
  const cwHandlers = makeCwPanelHandlers();
  const systemHandlers = makeSystemHandlers();
  const rfHandlers = makeRfFrontEndHandlers();
  const modeHandlers = makeModeHandlers();
  const filterHandlers = makeFilterHandlers();
  const agcHandlers = makeAgcHandlers();
  const ritXitHandlers = makeRitXitHandlers();
  const bandHandlers = makeBandHandlers();
  const presetHandlers = makePresetHandlers();
  const antennaHandlers = makeAntennaHandlers();
  const scanHandlers = makeScanHandlers();

  type RightSidebarMode = 'all' | 'rx' | 'tx';

  interface Props {
    mode?: RightSidebarMode;
  }

  let { mode = 'all' }: Props = $props();

  let showRx = $derived(mode === 'all' || mode === 'rx');
  let showTx = $derived(mode === 'all' || mode === 'tx');

  // --- Panel reorder (shared logic) ---
  const drag = createDragReorder({
    storageKey: 'icom-lan:right-panel-order',
    defaults: ['rx-audio', 'dsp', 'tx', 'cw', 'memory'],
    containerSelector: '.right-sidebar',
  });
</script>

<aside class="right-sidebar" class:cross-drop-target={drag.isDropTarget}>
  {#if showRx && drag.order.includes('rx-audio')}
    <CollapsiblePanel title="RX AUDIO" panelId="rx-audio" draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('rx-audio')}>
      <RxAudioPanel />
    </CollapsiblePanel>
  {/if}

  {#if showRx && drag.order.includes('dsp')}
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

  {#if showTx && drag.order.includes('tx')}
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

  {#if showTx && drag.order.includes('cw') && hasCapability('cw')}
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

  {#if drag.order.includes('rf-front-end')}
    <CollapsiblePanel title="RF FRONT END" panelId="rf-front-end" dataPanel="rf-frontend"
      draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('rf-front-end')}>
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
      draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('mode')}>
      <ModePanel
        currentMode={modeProps.currentMode}
        modes={modeProps.modes}
        dataMode={modeProps.dataMode}
        hasDataMode={modeProps.hasDataMode}
        dataModeCount={modeProps.dataModeCount}
        dataModeLabels={modeProps.dataModeLabels}
        onModeChange={modeHandlers.onModeChange}
        onDataModeChange={modeHandlers.onDataModeChange}
      />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('filter')}
    <CollapsiblePanel title="FILTER" panelId="filter"
      draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('filter')}>
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
      draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('agc')}>
      <AgcPanel
        agcMode={agc.agcMode}
        onAgcModeChange={agcHandlers.onAgcModeChange}
      />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('rit-xit')}
    <CollapsiblePanel title="RIT / XIT" panelId="rit-xit"
      draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('rit-xit')}>
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
      draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('band')}>
      <BandSelector
        currentFreq={band.currentFreq}
        onBandSelect={bandHandlers.onBandSelect}
        onPresetSelect={presetHandlers.onPresetSelect}
      />
    </CollapsiblePanel>
  {/if}

  {#if drag.order.includes('antenna') && antenna.antennaCount > 1}
    <CollapsiblePanel title="ANTENNA" panelId="antenna" dataPanel="antenna"
      draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('antenna')}>
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

  {#if drag.order.includes('scan')}
    <CollapsiblePanel title="SCAN" panelId="scan"
      draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('scan')}>
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
</aside>

<style>
  .right-sidebar {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
    padding: 6px 6px 16px;
    width: 100%;
    box-sizing: border-box;
  }

  .right-sidebar.cross-drop-target {
    outline: 2px solid var(--v2-accent, #4af);
    outline-offset: -2px;
  }
</style>
