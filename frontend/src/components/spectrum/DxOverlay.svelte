<script lang="ts">
  import type { DxSpot } from '../../lib/types/protocol';

  interface Props {
    spots: DxSpot[];
    startFreq: number; // Hz
    endFreq: number;   // Hz
    onTune?: (hz: number) => void;
  }

  let { spots, startFreq, endFreq, onTune }: Props = $props();

  interface PositionedSpot {
    spot: DxSpot;
    pct: number;
  }

  let positioned = $derived(
    endFreq > startFreq && spots.length > 0
      ? spots
          .filter((s) => s.freq >= startFreq && s.freq <= endFreq)
          .map((s) => ({
            spot: s,
            pct: ((s.freq - startFreq) / (endFreq - startFreq)) * 100,
          }))
      : ([] as PositionedSpot[]),
  );

  function handleClick(spot: DxSpot, e: MouseEvent): void {
    e.stopPropagation();
    onTune?.(spot.freq);
  }
</script>

<div class="dx-overlay" aria-hidden="true">
  {#each positioned as { spot, pct } (`${spot.dx}@${spot.freq}@${spot.spotter}`)}
    <button
      class="dx-badge"
      style="left: {pct}%"
      onclick={(e) => handleClick(spot, e)}
      title="{spot.dx} — {spot.spotter}: {spot.comment}"
    >
      {spot.dx}
    </button>
  {/each}
</div>

<style>
  .dx-overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
  }

  .dx-badge {
    position: absolute;
    top: 4px;
    transform: translateX(-50%);
    pointer-events: all;
    background: rgba(0, 0, 0, 0.75);
    border: 1px solid var(--accent);
    border-radius: 3px;
    color: var(--accent);
    font-size: 9px;
    font-family: var(--font-mono);
    padding: 1px 4px;
    cursor: pointer;
    white-space: nowrap;
    line-height: 1.4;
  }

  .dx-badge:hover {
    background: var(--accent);
    color: var(--bg);
  }
</style>
