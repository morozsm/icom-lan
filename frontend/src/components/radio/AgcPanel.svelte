<script lang="ts">
  import { radio } from '../../lib/stores/radio.svelte';

  let rx = $derived(
    radio.current?.active === 'SUB'
      ? (radio.current?.sub ?? null)
      : (radio.current?.main ?? null),
  );

  let agc = $derived(rx?.agc ?? null);
  let agcTimeConstant = $derived(rx?.agcTimeConstant ?? null);

  const AGC_LABELS: Record<number, string> = {
    0: 'OFF',
    1: 'FAST',
    2: 'MID',
    3: 'SLOW',
    4: 'AUTO',
  };

  let agcLabel = $derived(agc !== null ? (AGC_LABELS[agc] ?? String(agc)) : '—');
  let isOff = $derived(agc === 0);
</script>

{#if agc !== null}
<div class="agc-panel">
  <span class="agc-key">AGC</span>
  <span class="agc-val" class:off={isOff}>{agcLabel}</span>
  {#if agcTimeConstant !== null}
    <span class="agc-tc">{agcTimeConstant}ms</span>
  {/if}
</div>
{/if}

<style>
  .agc-panel {
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
    user-select: none;
  }

  .agc-key {
    font-weight: 700;
    font-size: 0.625rem;
    letter-spacing: 0.08em;
    color: var(--text-muted);
  }

  .agc-val {
    font-weight: 600;
    color: var(--accent);
  }

  .agc-val.off {
    color: var(--text-muted);
  }

  .agc-tc {
    font-weight: 400;
    font-size: 0.7rem;
    color: var(--text-muted);
    opacity: 0.75;
  }
</style>
