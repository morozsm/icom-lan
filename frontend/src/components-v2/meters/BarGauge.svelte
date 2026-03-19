<script lang="ts">
  import { onMount } from 'svelte';
  import { createSmoother } from '$lib/utils/smoothing.svelte';
  import { DEFAULT_ZONES, valueToSegments, getSegmentZone, dimColor } from './bar-gauge-utils';
  import type { Zone } from './bar-gauge-utils';

  interface Props {
    value: number;         // 0–1 normalized
    label: string;         // 'Po' | 'SWR' | 'ALC' | 'COMP'
    displayValue: string;  // '35W' | '1.2' | '-8'
    zones?: readonly Zone[];
    compact?: boolean;
  }

  let { value, label, displayValue, zones = DEFAULT_ZONES, compact = false }: Props = $props();

  // ── Segment geometry ────────────────────────────────────────────────────────
  const SEG_COUNT = 10;
  const BAR_X = 44;
  const BAR_WIDTH = 210;
  const SEG_GAP = 2;
  const SEG_W = (BAR_WIDTH - (SEG_COUNT - 1) * SEG_GAP) / SEG_COUNT; // 19.2

  const VALUE_X = BAR_X + BAR_WIDTH + 6; // 260

  function segX(i: number): number {
    return BAR_X + i * (SEG_W + SEG_GAP);
  }

  // ── Layout (switches between full / compact) ────────────────────────────────
  const TRACK_Y     = $derived(compact ? 6  : 8);
  const TRACK_H     = $derived(compact ? 10 : 14);
  const TOTAL_HEIGHT = $derived(compact ? 22 : 30);
  const LABEL_FS    = $derived(compact ? 7  : 8);
  const VALUE_FS    = $derived(compact ? 9  : 11);
  const TEXT_Y      = $derived(TRACK_Y + TRACK_H / 2);

  // ── Smoother ────────────────────────────────────────────────────────────────
  const smoother = createSmoother(0.08, 0.2);

  $effect(() => {
    smoother.update(valueToSegments(value, SEG_COUNT));
  });

  onMount(() => {
    smoother.start();
    return () => smoother.stop();
  });

  // ── Reactive display values ─────────────────────────────────────────────────
  let fullSegs = $derived(Math.floor(smoother.value));
  let fracSeg  = $derived(smoother.value - Math.floor(smoother.value));
</script>

<svg
  viewBox="0 0 300 {TOTAL_HEIGHT}"
  width="100%"
  height="auto"
  preserveAspectRatio="xMidYMid meet"
>
  <!-- Container background -->
  <rect
    x="0" y="0" width="300" height={TOTAL_HEIGHT}
    rx="6"
    fill="var(--v2-bg-darkest)"
    stroke="var(--v2-bg-panel)"
    stroke-width="1"
  />

  <!-- Label -->
  <text
    x="6"
    y={TEXT_Y}
    font-family="'Roboto Mono', monospace"
    font-size={LABEL_FS}
    font-weight="700"
    letter-spacing="0.8"
    fill="var(--v2-text-dim)"
    text-anchor="start"
    dominant-baseline="central"
  >{label}</text>

  <!-- Bar track background -->
  <rect
    x={BAR_X} y={TRACK_Y}
    width={BAR_WIDTH} height={TRACK_H}
    rx="1"
    fill="var(--v2-bg-darkest)"
    stroke="var(--v2-bg-panel)"
    stroke-width="1"
  />

  <!-- Segments -->
  {#each Array(SEG_COUNT) as _, i}
    {@const x = segX(i)}
    {@const zone = getSegmentZone(i, SEG_COUNT, zones)}

    <!-- Inactive (dim) -->
    <rect
      {x} y={TRACK_Y + 1}
      width={SEG_W} height={TRACK_H - 2}
      fill={dimColor(zone.color)}
    />

    <!-- Active -->
    {#if i < fullSegs}
      <rect
        {x} y={TRACK_Y + 1}
        width={SEG_W} height={TRACK_H - 2}
        fill={zone.color}
      />
    {:else if i === fullSegs && fracSeg > 0.01}
      <rect
        {x} y={TRACK_Y + 1}
        width={Math.max(1, SEG_W * fracSeg)} height={TRACK_H - 2}
        fill={zone.color}
      />
    {/if}
  {/each}

  <!-- Display value -->
  <text
    x={VALUE_X}
    y={TEXT_Y}
    font-family="'Roboto Mono', monospace"
    font-size={VALUE_FS}
    font-weight="700"
    fill="var(--v2-text-bright)"
    text-anchor="start"
    dominant-baseline="central"
  >{displayValue}</text>
</svg>

<style>
  svg {
    display: block;
  }
</style>
