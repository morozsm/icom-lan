<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { getAudioState } from '$lib/stores/audio.svelte';
  import { getCapabilities, hasCapability } from '$lib/stores/capabilities.svelte';
  import RxAudioPanel from '../panels/RxAudioPanel.svelte';
  import DspPanel from '../panels/DspPanel.svelte';
  import TxPanel from '../panels/TxPanel.svelte';
  import CwPanel from '../panels/CwPanel.svelte';
  import MemoryPanel from '../panels/MemoryPanel.svelte';
  import CollapsiblePanel from '../controls/CollapsiblePanel.svelte';
  import { createDragReorder } from '$lib/drag-reorder.svelte';
  import {
    toRxAudioProps,
    toDspProps,
    toTxProps,
    toCwProps,
  } from '../wiring/state-adapter';
  import {
    makeRxAudioHandlers,
    makeDspHandlers,
    makeTxHandlers,
    makeCwPanelHandlers,
    makeSystemHandlers,
  } from '../wiring/command-bus';

  // Reactive state + capabilities
  let radioState = $derived(radio.current);
  let audioState = $derived(getAudioState());
  let caps = $derived(getCapabilities());

  // Derived props via state adapter
  let rxAudio = $derived(toRxAudioProps(radioState, caps, audioState));
  let dsp = $derived(toDspProps(radioState, caps));
  let tx = $derived(toTxProps(radioState, caps));
  let cw = $derived(toCwProps(radioState, caps));

  // Command handlers via command-bus
  const rxAudioHandlers = makeRxAudioHandlers();
  const dspHandlers = makeDspHandlers();
  const txHandlers = makeTxHandlers();
  const cwHandlers = makeCwPanelHandlers();
  const systemHandlers = makeSystemHandlers();

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
  {#if showRx}
    <CollapsiblePanel title="RX AUDIO" panelId="rx-audio" draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('rx-audio')}>
      <RxAudioPanel
        monitorMode={rxAudio.monitorMode}
        afLevel={rxAudio.afLevel}
        hasLiveAudio={rxAudio.hasLiveAudio}
        onMonitorModeChange={rxAudioHandlers.onMonitorModeChange}
        onAfLevelChange={rxAudioHandlers.onAfLevelChange}
      />
    </CollapsiblePanel>

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

  {#if showTx}
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

    {#if hasCapability('cw')}
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
  {/if}

  <CollapsiblePanel title="MEMORY" panelId="memory" draggable onDragStart={drag.handleDragStart} style={drag.dragStyle('memory')}>
    <MemoryPanel />
  </CollapsiblePanel>
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
