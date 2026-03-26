<script lang="ts">
  interface Props {
    freqHz: number;
  }

  let { freqHz }: Props = $props();

  // Format: 14.294.000 with digit grouping
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

<div class="amber-freq">
  <span class="freq-mhz">{formatted.mhz}</span>
  <span class="freq-dot">.</span>
  <span class="freq-khz">{formatted.khz}</span>
  <span class="freq-dot">.</span>
  <span class="freq-hz">{formatted.hertz}</span>
  <span class="freq-unit">MHz</span>
</div>

<style>
  .amber-freq {
    display: flex;
    align-items: baseline;
    gap: 0;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    color: #FF8C00;
    text-shadow: 0 0 12px rgba(255, 140, 0, 0.6), 0 0 4px rgba(255, 140, 0, 0.3);
    user-select: none;
  }

  .freq-mhz {
    font-size: clamp(32px, 5vw, 56px);
    font-weight: 700;
    letter-spacing: 2px;
  }

  .freq-dot {
    font-size: clamp(28px, 4vw, 48px);
    font-weight: 400;
    color: rgba(255, 140, 0, 0.6);
    margin: 0 1px;
  }

  .freq-khz {
    font-size: clamp(32px, 5vw, 56px);
    font-weight: 700;
    letter-spacing: 2px;
  }

  .freq-hz {
    font-size: clamp(24px, 3.5vw, 40px);
    font-weight: 500;
    letter-spacing: 2px;
    opacity: 0.7;
  }

  .freq-unit {
    font-size: 12px;
    font-weight: 400;
    color: rgba(255, 140, 0, 0.4);
    margin-left: 6px;
    align-self: flex-end;
    padding-bottom: 4px;
  }
</style>
