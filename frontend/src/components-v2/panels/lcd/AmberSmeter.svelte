<script lang="ts">
  interface Props {
    value: number;      // Raw S-meter 0-260
    txActive?: boolean;
  }

  let { value, txActive = false }: Props = $props();

  // KX3-style segmented bargraph
  // S1=18, S3=54, S5=90, S7=126, S9=162, +20=198, +40=234, +60=260
  const SEGMENTS = 30; // total bar segments
  const MAX_RAW = 260;
  const S9_RAW = 162;
  const S9_SEG = Math.round((S9_RAW / MAX_RAW) * SEGMENTS); // ~18

  const TICK_LABELS = [
    { label: '1', seg: Math.round((18 / MAX_RAW) * SEGMENTS) },
    { label: '3', seg: Math.round((54 / MAX_RAW) * SEGMENTS) },
    { label: '5', seg: Math.round((90 / MAX_RAW) * SEGMENTS) },
    { label: '7', seg: Math.round((126 / MAX_RAW) * SEGMENTS) },
    { label: '9', seg: Math.round((162 / MAX_RAW) * SEGMENTS) },
    { label: '+20', seg: Math.round((198 / MAX_RAW) * SEGMENTS) },
    { label: '+40', seg: Math.round((234 / MAX_RAW) * SEGMENTS) },
    { label: '+60', seg: SEGMENTS },
  ];

  let filledSegs = $derived(Math.round(Math.min(SEGMENTS, Math.max(0, (value / MAX_RAW) * SEGMENTS))));
</script>

<div class="lcd-smeter">
  <div class="meter-label">S</div>
  <div class="meter-ticks">
    {#each TICK_LABELS as tick}
      <span
        class="tick"
        class:over-s9={tick.seg > S9_SEG}
        style="left: {(tick.seg / SEGMENTS) * 100}%"
      >{tick.label}</span>
    {/each}
  </div>
  <div class="meter-segments">
    {#each Array(SEGMENTS) as _, i}
      <div
        class="seg"
        class:filled={i < filledSegs}
        class:over-s9={i >= S9_SEG}
        class:tx={txActive}
      ></div>
    {/each}
  </div>
</div>

<style>
  .lcd-smeter {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .meter-label {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 10px;
    font-weight: 700;
    color: rgba(26, 16, 0, 0.5);
    letter-spacing: 1px;
    margin-bottom: -1px;
  }

  .meter-ticks {
    position: relative;
    height: 11px;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 8px;
    font-weight: 600;
    color: rgba(26, 16, 0, 0.4);
  }

  .tick {
    position: absolute;
    transform: translateX(-50%);
    white-space: nowrap;
  }

  .tick.over-s9 {
    color: rgba(80, 10, 0, 0.5);
  }

  .meter-segments {
    display: flex;
    gap: 1px;
    height: 10px;
  }

  .seg {
    flex: 1;
    background: rgba(0, 0, 0, 0.06);
    border-radius: 1px;
  }

  .seg.filled {
    background: rgba(26, 16, 0, 0.75);
  }

  .seg.filled.over-s9 {
    background: rgba(80, 10, 0, 0.85);
  }

  .seg.filled.tx {
    background: rgba(80, 10, 0, 0.8);
  }

  .seg.filled.tx.over-s9 {
    background: rgba(120, 0, 0, 0.9);
  }
</style>
