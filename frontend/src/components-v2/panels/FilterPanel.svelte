<script lang="ts">
  import '../controls/control-button.css';
  import BipolarSlider from '../controls/BipolarSlider.svelte';
  import Slider from '../controls/Slider.svelte';

  interface Props {
    filterWidth: number;
    ifShift: number;
    pbtInner?: number;
    pbtOuter?: number;
    hasPbt?: boolean;
    onFilterWidthChange: (v: number) => void;
    onIfShiftChange: (v: number) => void;
    onPbtInnerChange?: (v: number) => void;
    onPbtOuterChange?: (v: number) => void;
    onPbtReset?: () => void;
  }

  let {
    filterWidth,
    ifShift,
    pbtInner = 0,
    pbtOuter = 0,
    hasPbt = false,
    onFilterWidthChange,
    onIfShiftChange,
    onPbtInnerChange,
    onPbtOuterChange,
    onPbtReset,
  }: Props = $props();
</script>

<div class="filter-panel">
  <div class="panel-header">FILTER</div>
  <div class="panel-body">
    <Slider
      label="Width"
      value={filterWidth}
      min={50}
      max={3600}
      step={50}
      unit="Hz"
      accentColor="#00D4FF"
      onchange={onFilterWidthChange}
    />
    <BipolarSlider
      label="IF Shift"
      value={ifShift}
      min={-1200}
      max={1200}
      step={25}
      unit="Hz"
      accentColor="#00D4FF"
      onchange={onIfShiftChange}
    />
    {#if hasPbt}
      <BipolarSlider
        label="PBT Inner"
        value={pbtInner}
        min={-1200}
        max={1200}
        step={25}
        unit="Hz"
        accentColor="#00D4FF"
        onchange={onPbtInnerChange ?? (() => {})}
      />
      <BipolarSlider
        label="PBT Outer"
        value={pbtOuter}
        min={-1200}
        max={1200}
        step={25}
        unit="Hz"
        accentColor="#4ED37B"
        onchange={onPbtOuterChange ?? (() => {})}
      />

      <div class="filter-actions">
        <button
          type="button"
          class="pbt-reset-button v2-control-button"
          style="--control-accent:#4D6074; --control-active-text:#F0F5FA"
          onclick={() => onPbtReset?.()}
        >
          Reset PBT
        </button>
      </div>
    {/if}
  </div>
</div>

<style>
  .filter-panel {
    background: #060A10;
    border: 1px solid #18202A;
    border-radius: 4px;
    overflow: hidden;
    font-family: 'Roboto Mono', monospace;
  }

  .panel-header {
    color: #8CA0B8;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 5px 8px 4px;
    border-bottom: 1px solid #18202A;
  }

  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 7px 8px;
  }

  .filter-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 2px;
  }

  .pbt-reset-button {
    min-width: 88px;
  }
</style>
