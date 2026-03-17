<script lang="ts">
  import { onMount } from 'svelte';
  import { createSmoother } from '$lib/utils/smoothing.svelte';
  import { polar, arcPath } from '$lib/utils/meter-utils';
  import {
    GAUGE_START_DEG,
    GAUGE_END_DEG,
    GAUGE_SWEEP_DEG,
    valueToNeedleAngle,
    yellowZoneStart,
  } from './needle-gauge-utils';

  interface Props {
    value: number;          // 0–1 normalized
    label: string;          // e.g. 'SWR', 'POWER', 'S'
    displayValue: string;   // e.g. '1.5', '35W', 'S7'
    marks: { pos: number; label: string; color?: string }[];
    dangerZone?: number;    // 0–1, above this the arc turns red (default 0.8)
    compact?: boolean;
  }

  let {
    value,
    label,
    displayValue,
    marks,
    dangerZone = 0.8,
    compact = false,
  }: Props = $props();

  // ── Layout (switches between full / compact) ─────────────────────────────
  const VW         = $derived(compact ? 170 : 220);
  const VH         = $derived(compact ? 108 : 140);
  const CX         = $derived(VW / 2);
  const CY         = $derived(compact ? 72  : 97);
  const R          = $derived(compact ? 50  : 66);    // arc radius
  const R_TICK_OUT = $derived(R + (compact ? 5 : 7)); // tick tip (outside arc)
  const R_LABEL    = $derived(R + (compact ? 14 : 19)); // label ring
  const NEEDLE_R   = $derived(R - (compact ? 4 : 5)); // needle reaches just inside arc
  const PIVOT_R    = $derived(compact ? 3 : 4);
  const ARC_W      = $derived(compact ? 4 : 5);
  const DISP_FS    = $derived(compact ? 16 : 22);
  const LBL_FS     = $derived(compact ? 8 : 9);
  const MARK_FS    = $derived(compact ? 7 : 8);

  // ── Zone thresholds ──────────────────────────────────────────────────────
  const YELLOW_POS        = $derived(yellowZoneStart(dangerZone));
  const yellowStartAngle  = $derived(GAUGE_START_DEG + YELLOW_POS * GAUGE_SWEEP_DEG);
  const redStartAngle     = $derived(GAUGE_START_DEG + dangerZone * GAUGE_SWEEP_DEG);

  // ── Smoother ─────────────────────────────────────────────────────────────
  const smoother = createSmoother(0.08, 0.2);

  $effect(() => { smoother.update(value); });

  onMount(() => {
    smoother.start();
    return () => smoother.stop();
  });

  // ── Derived geometry ─────────────────────────────────────────────────────
  let smoothedAngle  = $derived(valueToNeedleAngle(smoother.value));
  let needleTip      = $derived(polar(CX, CY, NEEDLE_R, smoothedAngle));

  // Active arc endpoints (each segment clamped to its zone range)
  let greenEndAngle  = $derived(
    GAUGE_START_DEG + Math.min(smoother.value, YELLOW_POS) * GAUGE_SWEEP_DEG,
  );
  let yellowEndAngle = $derived(
    GAUGE_START_DEG + Math.min(smoother.value, dangerZone) * GAUGE_SWEEP_DEG,
  );
  let redEndAngle    = $derived(GAUGE_START_DEG + smoother.value * GAUGE_SWEEP_DEG);
</script>

<svg
  viewBox="0 0 {VW} {VH}"
  width="100%"
  height="auto"
  preserveAspectRatio="xMidYMid meet"
>
  <!-- Background -->
  <rect
    x="0" y="0" width={VW} height={VH}
    rx="8"
    fill="#07090D"
    stroke="#1E252C"
    stroke-width="1"
  />

  <!-- Track arc — full range, dim -->
  <path
    d={arcPath(CX, CY, R, GAUGE_START_DEG, GAUGE_END_DEG)}
    fill="none"
    stroke="#1E252C"
    stroke-width={ARC_W + 2}
    stroke-linecap="round"
  />

  <!-- Active arc — green segment (0 → yellow zone start) -->
  {#if smoother.value > 0.005}
    <path
      d={arcPath(CX, CY, R, GAUGE_START_DEG, greenEndAngle)}
      fill="none"
      stroke="#14A665"
      stroke-width={ARC_W}
      stroke-linecap="round"
    />
  {/if}

  <!-- Active arc — yellow segment -->
  {#if smoother.value > YELLOW_POS}
    <path
      d={arcPath(CX, CY, R, yellowStartAngle, yellowEndAngle)}
      fill="none"
      stroke="#F2CF4A"
      stroke-width={ARC_W}
      stroke-linecap="round"
    />
  {/if}

  <!-- Active arc — red segment -->
  {#if smoother.value > dangerZone}
    <path
      d={arcPath(CX, CY, R, redStartAngle, redEndAngle)}
      fill="none"
      stroke="#F14C42"
      stroke-width={ARC_W}
      stroke-linecap="round"
    />
  {/if}

  <!-- Tick marks and labels -->
  {#each marks as mark}
    {@const angle    = valueToNeedleAngle(mark.pos)}
    {@const tickBase = polar(CX, CY, R, angle)}
    {@const tickTip  = polar(CX, CY, R_TICK_OUT, angle)}
    {@const labelPt  = polar(CX, CY, R_LABEL, angle)}
    {@const color    = mark.color ?? '#6F8196'}

    <line
      x1={tickBase.x} y1={tickBase.y}
      x2={tickTip.x}  y2={tickTip.y}
      stroke={color}
      stroke-width="1.2"
      stroke-linecap="round"
    />

    {#if !compact || mark.label}
      <text
        x={labelPt.x}
        y={labelPt.y}
        text-anchor="middle"
        dominant-baseline="central"
        font-family="'Roboto Mono', monospace"
        font-size={MARK_FS}
        fill={color}
      >{mark.label}</text>
    {/if}
  {/each}

  <!-- Needle -->
  <line
    x1={CX}         y1={CY}
    x2={needleTip.x} y2={needleTip.y}
    stroke="#F0F5FA"
    stroke-width={compact ? 1.5 : 2}
    stroke-linecap="round"
  />

  <!-- Pivot circle -->
  <circle cx={CX} cy={CY} r={PIVOT_R} fill="#6F8196" />

  <!-- Display value — large, centred inside the arc -->
  <text
    x={CX}
    y={CY - (compact ? 22 : 28)}
    text-anchor="middle"
    dominant-baseline="central"
    font-family="'Roboto Mono', monospace"
    font-size={DISP_FS}
    font-weight="700"
    fill="#F0F5FA"
  >{displayValue}</text>

  <!-- Label name — small, muted, below pivot -->
  <text
    x={CX}
    y={CY + (compact ? 15 : 20)}
    text-anchor="middle"
    dominant-baseline="central"
    font-family="'Roboto Mono', monospace"
    font-size={LBL_FS}
    letter-spacing="1.5"
    fill="#6F8196"
  >{label}</text>
</svg>

<style>
  svg {
    display: block;
  }
</style>
