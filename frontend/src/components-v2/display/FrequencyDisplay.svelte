<script lang="ts">
  import { formatFrequency } from './frequency-format';

  interface Props {
    freq: number;       // frequency in Hz (e.g. 14235000)
    compact?: boolean;  // smaller variant (~18px vs ~28px)
    active?: boolean;   // bright (var(--v2-text-bright)) vs dimmed (var(--v2-text-disabled))
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
    font-size: 24px;
    line-height: 1;
    letter-spacing: 0.035em;
    color: var(--v2-accent-cyan-bright);
    white-space: nowrap;
    user-select: none;
  }

  .freq.compact {
    font-size: 14px;
  }

  .freq.inactive {
    color: var(--v2-text-muted);
  }

  .sep {
    opacity: 0.5;
    margin: 0 0.02em;
  }
</style>
