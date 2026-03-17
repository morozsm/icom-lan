<script lang="ts">
  import RxAudioPanel from '../panels/RxAudioPanel.svelte';
  import DspPanel from '../panels/DspPanel.svelte';
  import TxPanel from '../panels/TxPanel.svelte';

  interface Props {
    radioState: any;
  }

  let { radioState }: Props = $props();

  const noop = () => {};
  const noopN = (_v: number) => {};
  const noopS = (_v: string) => {};
  const noopB = (_v: boolean) => {};
</script>

<aside class="right-sidebar">
  <RxAudioPanel
    monitorMode={radioState?.monitorMode ?? 'local'}
    afLevel={radioState?.afLevel ?? 128}
    hasLiveAudio={radioState?.capabilities?.audio ?? false}
    onMonitorModeChange={noopS}
    onAfLevelChange={noopN}
  />

  <DspPanel
    nrMode={radioState?.nrMode ?? 0}
    nrLevel={radioState?.nrLevel ?? 0}
    nbActive={radioState?.nbActive ?? false}
    nbLevel={radioState?.nbLevel ?? 0}
    notchMode={radioState?.notchMode ?? 'off'}
    notchFreq={radioState?.notchFreq ?? 0}
    cwAutoTune={radioState?.cwAutoTune ?? false}
    cwPitch={radioState?.cwPitch ?? 600}
    currentMode={radioState?.main?.mode ?? 'USB'}
    onNrModeChange={noopN}
    onNrLevelChange={noopN}
    onNbToggle={noopB}
    onNbLevelChange={noopN}
    onNotchModeChange={noopS}
    onNotchFreqChange={noopN}
    onCwAutoTuneToggle={noopB}
    onCwPitchChange={noopN}
  />

  <TxPanel
    txActive={radioState?.txActive ?? false}
    micGain={radioState?.micGain ?? 128}
    atuActive={radioState?.atuActive ?? false}
    atuTuning={radioState?.atuTuning ?? false}
    voxActive={radioState?.voxActive ?? false}
    compActive={radioState?.compActive ?? false}
    compLevel={radioState?.compLevel ?? 0}
    monActive={radioState?.monActive ?? false}
    monLevel={radioState?.monLevel ?? 0}
    onMicGainChange={noopN}
    onAtuToggle={noop}
    onAtuTune={noop}
    onVoxToggle={noop}
    onCompToggle={noop}
    onCompLevelChange={noopN}
    onMonToggle={noop}
    onMonLevelChange={noopN}
  />
</aside>

<style>
  .right-sidebar {
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
    max-height: 100vh;
    padding: 8px;
    width: 220px;
    box-sizing: border-box;
  }
</style>
