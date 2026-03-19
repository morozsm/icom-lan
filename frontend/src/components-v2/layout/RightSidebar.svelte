<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { getAudioState } from '$lib/stores/audio.svelte';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import RxAudioPanel from '../panels/RxAudioPanel.svelte';
  import DspPanel from '../panels/DspPanel.svelte';
  import TxPanel from '../panels/TxPanel.svelte';
  import CollapsiblePanel from '../controls/CollapsiblePanel.svelte';
  import {
    toRxAudioProps,
    toDspProps,
    toTxProps,
  } from '../wiring/state-adapter';
  import {
    makeRxAudioHandlers,
    makeDspHandlers,
    makeTxHandlers,
  } from '../wiring/command-bus';

  // Reactive state + capabilities
  let radioState = $derived(radio.current);
  let audioState = $derived(getAudioState());
  let caps = $derived(getCapabilities());

  // Derived props via state adapter
  let rxAudio = $derived(toRxAudioProps(radioState, caps, audioState));
  let dsp = $derived(toDspProps(radioState, caps));
  let tx = $derived(toTxProps(radioState, caps));

  // Command handlers via command-bus
  const rxAudioHandlers = makeRxAudioHandlers();
  const dspHandlers = makeDspHandlers();
  const txHandlers = makeTxHandlers();
</script>

<aside class="right-sidebar">
  <CollapsiblePanel title="RX AUDIO" panelId="rx-audio">
    <RxAudioPanel
      monitorMode={rxAudio.monitorMode}
      afLevel={rxAudio.afLevel}
      hasLiveAudio={rxAudio.hasLiveAudio}
      onMonitorModeChange={rxAudioHandlers.onMonitorModeChange}
      onAfLevelChange={rxAudioHandlers.onAfLevelChange}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="DSP" panelId="dsp">
    <DspPanel
      nrMode={dsp.nrMode}
      nrLevel={dsp.nrLevel}
      nbActive={dsp.nbActive}
      nbLevel={dsp.nbLevel}
      notchMode={dsp.notchMode}
      notchFreq={dsp.notchFreq}
      cwAutoTune={dsp.cwAutoTune}
      cwPitch={dsp.cwPitch}
      currentMode={dsp.currentMode}
      onNrModeChange={dspHandlers.onNrModeChange}
      onNrLevelChange={dspHandlers.onNrLevelChange}
      onNbToggle={dspHandlers.onNbToggle}
      onNbLevelChange={dspHandlers.onNbLevelChange}
      onNotchModeChange={dspHandlers.onNotchModeChange}
      onNotchFreqChange={dspHandlers.onNotchFreqChange}
      onCwAutoTuneToggle={dspHandlers.onCwAutoTuneToggle}
      onCwPitchChange={dspHandlers.onCwPitchChange}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="TX" panelId="tx">
    <TxPanel
      txActive={tx.txActive}
      micGain={tx.micGain}
      atuActive={tx.atuActive}
      atuTuning={tx.atuTuning}
      voxActive={tx.voxActive}
      compActive={tx.compActive}
      compLevel={tx.compLevel}
      monActive={tx.monActive}
      monLevel={tx.monLevel}
      onMicGainChange={txHandlers.onMicGainChange}
      onAtuToggle={txHandlers.onAtuToggle}
      onAtuTune={txHandlers.onAtuTune}
      onVoxToggle={txHandlers.onVoxToggle}
      onCompToggle={txHandlers.onCompToggle}
      onCompLevelChange={txHandlers.onCompLevelChange}
      onMonToggle={txHandlers.onMonToggle}
      onMonLevelChange={txHandlers.onMonLevelChange}
    />
  </CollapsiblePanel>
</aside>

<style>
  .right-sidebar {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
    padding: 6px;
    width: 100%;
    box-sizing: border-box;
  }
</style>
