<script lang="ts">
  import RfFrontEnd from '../panels/RfFrontEnd.svelte';
  import FilterPanel from '../panels/FilterPanel.svelte';
  import AgcPanel from '../panels/AgcPanel.svelte';
  import RitXitPanel from '../panels/RitXitPanel.svelte';
  import BandSelector from '../controls/BandSelector.svelte';

  interface Props {
    radioState: any;
  }

  let { radioState }: Props = $props();

  const noop = () => {};
  const noopN = (_v: number) => {};
  const noopS = (_v: string) => {};
</script>

<aside class="left-sidebar">
  <RfFrontEnd
    rfGain={radioState?.rfGain ?? 255}
    att={radioState?.att ?? 0}
    pre={radioState?.pre ?? 0}
    onRfGainChange={noopN}
    onAttChange={noopN}
    onPreChange={noopN}
  />

  <FilterPanel
    filterWidth={radioState?.filterWidth ?? 2400}
    ifShift={radioState?.ifShift ?? 0}
    hasPbt={radioState?.hasPbt ?? false}
    pbtInner={radioState?.pbtInner ?? 0}
    pbtOuter={radioState?.pbtOuter ?? 0}
    onFilterWidthChange={noopN}
    onIfShiftChange={noopN}
    onPbtInnerChange={noopN}
    onPbtOuterChange={noopN}
  />

  <AgcPanel
    agcMode={radioState?.agcMode ?? 0}
    agcGain={radioState?.agcGain ?? 128}
    onAgcModeChange={noopN}
    onAgcGainChange={noopN}
  />

  <RitXitPanel
    ritActive={radioState?.ritActive ?? false}
    ritOffset={radioState?.ritOffset ?? 0}
    xitActive={radioState?.xitActive ?? false}
    xitOffset={radioState?.xitOffset ?? 0}
    hasRit={radioState?.hasRit ?? true}
    hasXit={radioState?.hasXit ?? true}
    onRitToggle={noop}
    onXitToggle={noop}
    onRitOffsetChange={noopN}
    onXitOffsetChange={noopN}
    onClear={noop}
  />

  <BandSelector
    currentFreq={radioState?.main?.freq ?? 14074000}
    onBandSelect={(_name: string, _freq: number) => {}}
  />
</aside>

<style>
  .left-sidebar {
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
