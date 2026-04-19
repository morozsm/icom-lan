<!--
  AmberMemoryStrip — compact aux-row widget showing 5 memory slots
  (M1-M5) and the last 3 auto-QSY entries.

  Memory slots (M1-M5) are placeholder-only in this first pass — the
  repo has no frontend memory store yet, so slots render "—". The
  backend-memory plumbing is tracked as a followup; once it exists,
  `memoryStore.get(n)` plugs in here without touching the component
  contract.

  QSY entries come from `$lib/stores/qsy-history` — a local ring
  buffer that debounces frequency changes into intentional QSYs
  (≥ 500 Hz delta, 1.5s stability). Each entry is a clickable chip
  that fires `onQsy(freqHz, mode)` so the parent can call into
  `runtime.send('set_freq', ...)`.

  Part of #836 / epic #818 LCD aux-row content.
-->
<script lang="ts">
  import { qsyHistory } from '$lib/stores/qsy-history.svelte';

  interface Props {
    /** Invoked when a recent-QSY chip is tapped. Parent routes to runtime. */
    onQsy?: (freqHz: number, mode: string) => void;
  }

  let { onQsy }: Props = $props();

  // Show last 3 entries, newest-first.
  let recentQsy = $derived<{ freqHz: number; mode: string; at: number }[]>(
    qsyHistory.recent.slice(-3).reverse() as { freqHz: number; mode: string; at: number }[],
  );

  // Memory slots — placeholder until a store lands.
  const memorySlots = [1, 2, 3, 4, 5];

  function formatFreqShort(hz: number): string {
    if (!hz || hz <= 0) return '—';
    // Compact: "14.074" for HF, "144.52" for VHF.
    const mhz = hz / 1_000_000;
    return mhz >= 1000
      ? `${(mhz / 1000).toFixed(3)}G`
      : mhz >= 100
        ? `${mhz.toFixed(3)}`
        : `${mhz.toFixed(3)}`;
  }

  function handleQsyClick(freqHz: number, mode: string) {
    onQsy?.(freqHz, mode);
  }
</script>

<div class="amber-memory-strip">
  <div class="section mem-section">
    <span class="section-tag">MEM</span>
    {#each memorySlots as slot}
      <button class="slot slot-empty" disabled title={`Memory slot M${slot} — not wired yet`}>
        <span class="slot-index">M{slot}</span>
        <span class="slot-value">—</span>
      </button>
    {/each}
  </div>

  <div class="section qsy-section" class:qsy-empty={recentQsy.length === 0}>
    <span class="section-tag">QSY</span>
    {#if recentQsy.length === 0}
      <span class="qsy-placeholder">—</span>
    {:else}
      {#each recentQsy as entry (entry.at)}
        <button
          type="button"
          class="slot slot-qsy"
          onclick={() => handleQsyClick(entry.freqHz, entry.mode)}
          title={`Return to ${formatFreqShort(entry.freqHz)} MHz ${entry.mode}`}
        >
          <span class="slot-value">{formatFreqShort(entry.freqHz)}</span>
          <span class="slot-mode">{entry.mode}</span>
        </button>
      {/each}
    {/if}
  </div>
</div>

<style>
  .amber-memory-strip {
    display: flex;
    gap: 10px;
    align-items: center;
    width: 100%;
    min-height: 18px;
    color: rgba(26, 16, 0, var(--lcd-alpha-active));
    font-family: 'JetBrains Mono', 'Courier New', monospace;
  }

  .section {
    display: flex;
    gap: 4px;
    align-items: center;
    min-width: 0;
  }

  .mem-section {
    flex-shrink: 0;
  }

  .qsy-section {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .qsy-empty {
    opacity: 0.45;
  }

  .section-tag {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.55));
    flex-shrink: 0;
  }

  .qsy-placeholder {
    font-size: 10px;
    color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.4));
  }

  .slot {
    display: inline-flex;
    align-items: baseline;
    gap: 3px;
    padding: 0 4px;
    height: 16px;
    border: 1px solid rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.2));
    border-radius: 2px;
    background: transparent;
    color: inherit;
    font: inherit;
    cursor: pointer;
    white-space: nowrap;
  }

  .slot:disabled,
  .slot-empty {
    cursor: default;
    opacity: 0.45;
  }

  .slot-qsy {
    border-color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.4));
  }

  .slot-qsy:hover {
    border-color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.65));
    background: rgba(26, 16, 0, var(--lcd-alpha-ghost));
  }

  .slot-index {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.6));
  }

  .slot-value {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .slot-mode {
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.55));
  }
</style>
