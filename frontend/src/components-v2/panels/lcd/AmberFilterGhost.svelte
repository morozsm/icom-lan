<script lang="ts">
  interface Props {
    /** Filter width in Hz (raw from radio) */
    filterWidth?: number;
    /** Max filter width value in Hz for normalization */
    filterWidthMax?: number;
  }

  let { filterWidth = 2400, filterWidthMax = 9999 }: Props = $props();

  // viewBox dimensions
  const VW = 100;
  const VH = 40;

  // Trapezoid geometry mirrors AmberAfScope proportions, adapted to viewBox units.
  // totalHalfW is 42% of VW; slopeExtra is 35% of trap height.
  const trapTop = 0;
  const trapH = VH;
  const cx = VW / 2;
  const totalHalfW = VW * 0.42;
  const slopeExtra = trapH * 0.35;

  // Filter ratio: clamp to [0.05, 1]
  let filterRatio = $derived(
    Math.max(0.05, Math.min(1, filterWidth / Math.max(1, filterWidthMax))),
  );

  // Top edge half-width scales with filter ratio
  let maxTopHalfW = $derived(totalHalfW - slopeExtra);
  let topHalfW = $derived(Math.max(trapH * 0.1 * (VH / 100), maxTopHalfW * filterRatio));

  // Trapezoid corners
  let tl = $derived(cx - topHalfW);
  let tr = $derived(cx + topHalfW);
  let bl = $derived(cx - topHalfW - slopeExtra);
  let br = $derived(cx + topHalfW + slopeExtra);
  let whiskerLeft = $derived(cx - totalHalfW);
  let whiskerRight = $derived(cx + totalHalfW);

  // Passband polygon points (trapezoid + whiskers as open path via polygon)
  // We use a polyline for the open shape: whiskerLeft,VH → bl,VH → tl,trapTop → tr,trapTop → br,VH → whiskerRight,VH
  let passbandPoints = $derived(
    `${whiskerLeft},${VH} ${bl},${VH} ${tl},${trapTop} ${tr},${trapTop} ${br},${VH} ${whiskerRight},${VH}`,
  );
</script>

<!--
  AmberFilterGhost — static ghost graticule + passband outline shown when
  hasAudioFft() returns false. Uses --lcd-alpha-ghost token for "turned-off
  glass etching" aesthetic. Issue #900.
-->
<svg
  class="ghost"
  viewBox="0 0 {VW} {VH}"
  preserveAspectRatio="none"
  aria-hidden="true"
>
  <!-- Graticule: 9 vertical lines -->
  {#each Array.from({ length: 9 }, (_, i) => 10 * (i + 1)) as x (x)}
    <line x1={x} y1="0" x2={x} y2={VH} class="graticule-line" />
  {/each}

  <!-- Graticule: 3 horizontal lines -->
  {#each [10, 20, 30] as y (y)}
    <line x1="0" y1={y} x2={VW} y2={y} class="graticule-line" />
  {/each}

  <!-- Passband trapezoid outline (open polyline matching AmberAfScope shape) -->
  <polyline points={passbandPoints} class="passband" />
</svg>

<style>
  .ghost {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    display: block;
  }

  .graticule-line,
  .passband {
    stroke: rgba(26, 16, 0, var(--lcd-alpha-ghost, 0.06));
    fill: none;
    vector-effect: non-scaling-stroke;
  }

  .graticule-line {
    stroke-width: 1;
  }

  .passband {
    stroke-width: 2;
  }
</style>
