<script lang="ts">
  interface Props {
    value: number;      // Raw S-meter 0-260
    txActive?: boolean;
  }

  let { value, txActive = false }: Props = $props();

  // S-meter scale: S0=0, S1=18, S2=36 ... S9=162, +10=180, +20=198, +40=234, +60=260
  const S_TICKS = [
    { label: 'S1', raw: 18 },
    { label: '3', raw: 54 },
    { label: '5', raw: 90 },
    { label: '7', raw: 126 },
    { label: '9', raw: 162 },
    { label: '+20', raw: 198 },
    { label: '+40', raw: 234 },
    { label: '+60', raw: 260 },
  ];

  const MAX_RAW = 260;

  let percent = $derived(Math.min(100, Math.max(0, (value / MAX_RAW) * 100)));
  // S9 threshold at ~62%
  let s9Percent = $derived((162 / MAX_RAW) * 100);
  let overS9 = $derived(percent > s9Percent);
</script>

<div class="amber-smeter">
  <div class="meter-ticks">
    {#each S_TICKS as tick}
      <span
        class="tick"
        class:over-s9={tick.raw > 162}
        style="left: {(tick.raw / MAX_RAW) * 100}%"
      >{tick.label}</span>
    {/each}
  </div>
  <div class="meter-bar-bg">
    <div
      class="meter-bar-fill"
      class:over-s9={overS9}
      class:tx-fill={txActive}
      style="width: {percent}%"
    ></div>
    <!-- S9 marker line -->
    <div class="s9-marker" style="left: {s9Percent}%"></div>
  </div>
</div>

<style>
  .amber-smeter {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .meter-ticks {
    position: relative;
    height: 12px;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 9px;
    color: rgba(26, 16, 0, 0.45);
  }

  .tick {
    position: absolute;
    transform: translateX(-50%);
    white-space: nowrap;
  }

  .tick.over-s9 {
    color: rgba(60, 10, 0, 0.7);
  }

  .meter-bar-bg {
    position: relative;
    height: 12px;
    background: rgba(0, 0, 0, 0.06);
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 2px;
    overflow: hidden;
  }

  .meter-bar-fill {
    height: 100%;
    background: linear-gradient(
      to right,
      rgba(26, 16, 0, 0.5) 0%,
      rgba(26, 16, 0, 0.85) 100%
    );
    transition: width 60ms linear;
  }

  .meter-bar-fill.over-s9 {
    background: linear-gradient(
      to right,
      rgba(26, 16, 0, 0.5) 0%,
      rgba(26, 16, 0, 0.85) 62%,
      rgba(80, 10, 0, 0.9) 100%
    );
  }

  .meter-bar-fill.tx-fill {
    background: linear-gradient(
      to right,
      rgba(80, 10, 0, 0.5) 0%,
      rgba(80, 10, 0, 0.9) 100%
    );
  }

  .s9-marker {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: rgba(0, 0, 0, 0.2);
  }
</style>
