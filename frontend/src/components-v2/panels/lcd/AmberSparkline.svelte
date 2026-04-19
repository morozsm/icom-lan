<!--
  AmberSparkline — minimal inline SVG sparkline primitive for LCD tiles.

  Renders a single polyline scaled to the available container size.
  Uses `vector-effect: non-scaling-stroke` so the line stays visually
  consistent when the SVG is stretched via `preserveAspectRatio="none"`.
  No labels, no axes — it's a glanceable decoration only.

  Empty / insufficient data yields an empty SVG (no error state) —
  callers render the tile label beside it regardless.

  Part of #837 / epic #818 LCD telemetry strip.
-->
<script lang="ts">
  interface Props {
    /** Recent samples, oldest-first. Typical 20-60 points. */
    data: number[];
    /** Optional fixed range; when omitted, auto-scales to min/max. */
    min?: number;
    max?: number;
    /** Inline CSS color override (default picks up currentColor). */
    color?: string;
    /** SVG viewBox width — used purely for aspect; fits container via CSS. */
    viewW?: number;
    /** SVG viewBox height. */
    viewH?: number;
  }

  let { data, min, max, color, viewW = 60, viewH = 14 }: Props = $props();

  // Polyline points only when we have ≥ 2 samples to draw a line from.
  let pointsAttr = $derived.by(() => {
    if (!data || data.length < 2) return '';
    const lo = min ?? Math.min(...data);
    const hi = max ?? Math.max(...data);
    const span = hi - lo || 1;
    const stepX = viewW / (data.length - 1);
    return data
      .map((v, i) => {
        const x = i * stepX;
        const y = viewH - ((v - lo) / span) * viewH;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  });
</script>

<svg
  class="amber-sparkline"
  viewBox="0 0 {viewW} {viewH}"
  preserveAspectRatio="none"
  role="img"
  aria-hidden="true"
>
  {#if pointsAttr}
    <polyline
      points={pointsAttr}
      fill="none"
      stroke={color ?? 'currentColor'}
      stroke-width="1"
      vector-effect="non-scaling-stroke"
    />
  {/if}
</svg>

<style>
  .amber-sparkline {
    width: 100%;
    height: 100%;
    display: block;
  }
</style>
