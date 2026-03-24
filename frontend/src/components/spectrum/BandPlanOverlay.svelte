<script lang="ts">
  import {
    getVisibleSegments,
    SEGMENT_COLORS,
    SEGMENT_BORDER_COLORS,
    SEGMENT_LABEL_COLORS,
  } from '../../lib/data/arrl-band-plan';

  interface Props {
    startFreq: number;
    endFreq: number;
    visible?: boolean;
  }

  let { startFreq, endFreq, visible = true }: Props = $props();

  let containerWidth = $state(0);

  let segments = $derived(() => {
    if (!visible || endFreq <= startFreq) return [];
    const span = endFreq - startFreq;
    return getVisibleSegments(startFreq, endFreq).map(({ segment, band: _band }) => {
      const rawLeft = ((segment.startHz - startFreq) / span) * 100;
      const rawRight = ((segment.endHz - startFreq) / span) * 100;
      const leftPct = Math.max(0, Math.min(100, rawLeft));
      const rightPct = Math.max(0, Math.min(100, rawRight));
      const widthPct = rightPct - leftPct;
      const widthPx = (widthPct / 100) * containerWidth;
      return { segment, leftPct, widthPct, widthPx };
    });
  });
</script>

{#if visible && segments().length > 0}
<div class="bandplan-overlay" aria-hidden="true" bind:clientWidth={containerWidth}>
  {#each segments() as { segment, leftPct, widthPct, widthPx } (segment.startHz)}
    <div
      class="band-segment"
      style="left:{leftPct}%;width:{widthPct}%;background:{SEGMENT_COLORS[segment.mode]};border-left:1px solid {SEGMENT_BORDER_COLORS[segment.mode]}"
    >
      {#if widthPx > 40}
        <span class="segment-label" style="color:{SEGMENT_LABEL_COLORS[segment.mode]}">
          {segment.label}
        </span>
      {/if}
    </div>
  {/each}
</div>
{/if}

<style>
  .bandplan-overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
    z-index: 2; /* below DxOverlay (z-index 3) and tune-line (z-index 5) */
  }

  .band-segment {
    position: absolute;
    top: 0;
    bottom: 0;
  }

  .segment-label {
    position: absolute;
    bottom: 4px;
    left: 50%;
    transform: translateX(-50%);
    font-family: 'Roboto Mono', monospace;
    font-size: 8px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
    opacity: 0.8;
    pointer-events: none;
  }
</style>
