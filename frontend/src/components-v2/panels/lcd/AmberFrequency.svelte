<script lang="ts">
  interface Props {
    freqHz: number;
  }

  let { freqHz }: Props = $props();

  // Format: 14.195.000 — KX3 style grouping
  let formatted = $derived(formatFreq(freqHz));

  function formatFreq(hz: number): { mhz: string; khz: string; hertz: string } {
    if (hz <= 0) return { mhz: '--', khz: '---', hertz: '---' };
    const mhz = Math.floor(hz / 1_000_000);
    const khz = Math.floor((hz % 1_000_000) / 1_000);
    const hertz = Math.floor(hz % 1_000);
    return {
      mhz: mhz.toString(),
      khz: khz.toString().padStart(3, '0'),
      hertz: hertz.toString().padStart(3, '0'),
    };
  }
</script>

<div class="lcd-freq">
  <!-- Ghost segments (all-8s background for LCD look) -->
  <div class="lcd-freq-ghost" aria-hidden="true">
    <span class="seg-mhz">{formatted.mhz.replace(/./g, '8')}</span>
    <span class="seg-dot">.</span>
    <span class="seg-khz">888</span>
    <span class="seg-dot">.</span>
    <span class="seg-hz">888</span>
  </div>
  <!-- Active segments -->
  <div class="lcd-freq-active">
    <span class="seg-mhz">{formatted.mhz}</span>
    <span class="seg-dot">.</span>
    <span class="seg-khz">{formatted.khz}</span>
    <span class="seg-dot">.</span>
    <span class="seg-hz">{formatted.hertz}</span>
  </div>
</div>

<style>
  .lcd-freq {
    position: relative;
    display: inline-flex;
    user-select: none;
  }

  /* Ghost layer: faint "all segments on" for LCD realism */
  .lcd-freq-ghost {
    display: flex;
    align-items: baseline;
    font-family: 'DSEG7 Classic', monospace;
    font-weight: bold;
    color: rgba(0, 0, 0, 0.06);
  }

  /* Active layer: real digits overlaid on ghost */
  .lcd-freq-active {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: baseline;
    font-family: 'DSEG7 Classic', monospace;
    font-weight: bold;
    color: #1A1000;
  }

  .seg-mhz {
    font-size: clamp(36px, 6vw, 64px);
    letter-spacing: 2px;
  }

  .seg-dot {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: clamp(28px, 4vw, 48px);
    color: rgba(26, 16, 0, 0.7);
    margin: 0 2px;
    font-weight: 700;
  }

  .seg-khz {
    font-size: clamp(36px, 6vw, 64px);
    letter-spacing: 2px;
  }

  .seg-hz {
    font-size: clamp(28px, 4.5vw, 48px);
    letter-spacing: 2px;
    opacity: 0.7;
  }

  .lcd-freq-ghost .seg-dot {
    color: rgba(0, 0, 0, 0.04);
  }
</style>
