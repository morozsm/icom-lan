<script lang="ts">
  import { formatFrequency } from './frequency-format';

  interface Props {
    freq: number;       // frequency in Hz (e.g. 14235000)
    compact?: boolean;  // smaller variant (~18px vs ~28px)
    active?: boolean;   // bright (#F0F5FA) vs dimmed (#4D6074)
  }

  let { freq, compact = false, active = true }: Props = $props();

  let parts = $derived(formatFrequency(freq));
</script>

<div class="freq" class:compact class:inactive={!active}>
  <span class="digits">{parts.mhz}</span><span class="sep">.</span><span
    class="digits">{parts.khz}</span><span class="sep">.</span><span
    class="digits">{parts.hz}</span>
</div>

<style>
  .freq {
    display: inline-flex;
    align-items: baseline;
    font-family: 'Roboto Mono', monospace;
    font-weight: 700;
    font-size: 28px;
    line-height: 1;
    letter-spacing: 0.04em;
    color: #F0F5FA;
    white-space: nowrap;
    user-select: none;
  }

  .freq.compact {
    font-size: 18px;
  }

  .freq.inactive {
    color: #4D6074;
  }

  .sep {
    opacity: 0.4;
    margin: 0 0.02em;
  }
</style>
