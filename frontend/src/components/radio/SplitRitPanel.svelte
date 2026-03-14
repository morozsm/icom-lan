<script lang="ts">
  import { radio } from '../../lib/stores/radio.svelte';

  let split = $derived(radio.current?.split ?? false);
  let ritOn = $derived(radio.current?.ritOn ?? false);
  let ritFreq = $derived(radio.current?.ritFreq ?? 0);
  let ritTx = $derived(radio.current?.ritTx ?? false);

  function formatRitFreq(hz: number): string {
    const sign = hz >= 0 ? '+' : '';
    return `${sign}${hz} Hz`;
  }
</script>

<div class="split-rit-panel">
  <div class="indicator" class:on={split}>
    <span class="ind-key">SPLIT</span>
    <span class="ind-val">{split ? 'ON' : 'OFF'}</span>
  </div>

  <div class="indicator" class:on={ritOn}>
    <span class="ind-key">RIT</span>
    <span class="ind-val">{ritOn ? 'ON' : 'OFF'}</span>
    {#if ritOn}
      <span class="rit-freq">{formatRitFreq(ritFreq)}</span>
    {/if}
  </div>

  {#if ritTx}
    <div class="indicator on">
      <span class="ind-key">RIT-TX</span>
      <span class="ind-val">ON</span>
    </div>
  {/if}
</div>

<style>
  .split-rit-panel {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .indicator {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    padding: 0 var(--space-3);
    height: var(--tap-target);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 9999px;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-muted);
    user-select: none;
    transition: border-color 0.2s, color 0.2s;
  }

  .indicator.on {
    border-color: var(--accent);
    color: var(--accent);
  }

  .ind-key {
    font-weight: 700;
    font-size: 0.625rem;
    letter-spacing: 0.08em;
  }

  .ind-val {
    font-weight: 400;
    opacity: 0.85;
  }

  .rit-freq {
    font-weight: 400;
    font-size: 0.7rem;
    opacity: 0.75;
    margin-left: var(--space-1);
  }
</style>
