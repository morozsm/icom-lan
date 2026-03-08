<script lang="ts">
  import { onMount } from 'svelte';

  interface Props {
    // TODO: powerLevel from backend (radio_state.py) is raw 0-255, not watts.
    // Need backend conversion before display is meaningful. For now treated as 0-100 scale via maxPower.
    power: number;
    swr: number; // SWR ratio (1.0 = perfect)
    maxPower?: number; // configurable max (default 100)
  }

  let { power, swr, maxPower = 100 }: Props = $props();

  let fillPercent = $derived(Math.min(100, Math.max(0, (power / maxPower) * 100)));

  // Color: green <50%, yellow 50-90%, red >90%
  let barColor = $derived(
    fillPercent < 50 ? 'var(--success)' : fillPercent < 90 ? 'var(--warning)' : 'var(--danger)',
  );

  let swrText = $derived(swr > 0 ? swr.toFixed(1) : '—');

  // SWR color: green ≤1.5, yellow ≤3.0, red >3.0
  let swrColor = $derived(
    swr <= 1.5 ? 'var(--success)' : swr <= 3.0 ? 'var(--warning)' : 'var(--danger)',
  );

  // Peak hold: track max fill, hold 2s then decay
  let peakFill = $state(0);
  let peakLastSet = 0;

  $effect(() => {
    if (fillPercent > peakFill) {
      peakFill = fillPercent;
      peakLastSet = Date.now();
    }
  });

  onMount(() => {
    const interval = setInterval(() => {
      if (peakFill > 0 && Date.now() - peakLastSet > 2000) {
        peakFill = Math.max(0, peakFill - 2);
      }
    }, 80);
    return () => clearInterval(interval);
  });
</script>

<div class="power-meter">
  <div class="meter-row">
    <div class="meter-section">
      <div class="meter-header">
        <span class="meter-label">PWR</span>
        <!-- Backend sends raw 0-255; show percentage until calibrated watts available -->
        <span class="meter-value">{fillPercent.toFixed(0)}%</span>
      </div>
      <div class="meter-track">
        <div class="meter-fill" style="width: {fillPercent}%; background: {barColor}"></div>
        {#if peakFill > 0}
          <div class="peak-mark" style="left: {peakFill}%"></div>
        {/if}
      </div>
      <div class="scale-row">
        <span>0</span>
        <span style="left: 50%; transform: translateX(-50%); position: absolute"
          >{Math.round(maxPower / 2)}W</span
        >
        <span>{maxPower}W</span>
      </div>
    </div>

    <div class="swr-section">
      <span class="swr-label">SWR</span>
      <span class="swr-value" style="color: {swrColor}">{swrText}</span>
    </div>
  </div>
</div>

<style>
  .power-meter {
    display: flex;
    flex-direction: column;
  }

  .meter-row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }

  .meter-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .meter-header {
    display: flex;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 0.75rem;
  }

  .meter-label {
    color: var(--text-muted);
    font-weight: 700;
    letter-spacing: 0.1em;
    font-size: 0.65rem;
  }

  .meter-value {
    color: var(--text);
    font-weight: 700;
  }

  .meter-track {
    position: relative;
    height: 8px;
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    overflow: hidden;
  }

  .meter-fill {
    height: 100%;
    border-radius: 4px;
    transition:
      width var(--transition-fast),
      background-color var(--transition-normal);
  }

  .peak-mark {
    position: absolute;
    top: 1px;
    bottom: 1px;
    width: 2px;
    background: rgba(255, 255, 255, 0.85);
    border-radius: 1px;
    pointer-events: none;
    transform: translateX(-1px);
    transition: left var(--transition-fast);
  }

  .scale-row {
    display: flex;
    justify-content: space-between;
    position: relative;
    font-family: var(--font-mono);
    font-size: 0.5rem;
    color: var(--text-muted);
    user-select: none;
  }

  .swr-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    min-width: 44px;
  }

  .swr-label {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    color: var(--text-muted);
    font-weight: 700;
    letter-spacing: 0.1em;
  }

  .swr-value {
    font-family: var(--font-mono);
    font-size: 0.875rem;
    font-weight: 700;
    transition: color 0.3s;
  }
</style>
