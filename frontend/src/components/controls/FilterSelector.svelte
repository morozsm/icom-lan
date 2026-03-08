<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { getActiveReceiver, getRadioState } from '../../lib/stores/radio.svelte';
  import { getSupportedFilters } from '../../lib/stores/capabilities.svelte';

  const DEFAULT_FILTERS = ['FIL1', 'FIL2', 'FIL3'];

  let filters = $derived(getSupportedFilters().length ? getSupportedFilters() : DEFAULT_FILTERS);
  let currentFilter = $derived(getActiveReceiver()?.filter ?? 1);
  let receiverIdx = $derived(getRadioState()?.active === 'SUB' ? 1 : 0);

  function filterNum(name: string): number {
    return parseInt(name.replace('FIL', ''), 10) || 1;
  }

  function setFilter(fil: string) {
    sendCommand('set_filter', { filter: fil, receiver: receiverIdx });
  }
</script>

<div class="filter-selector" role="group" aria-label="Filter">
  {#each filters as fil}
    <button
      class="fil-btn"
      class:active={currentFilter === filterNum(fil)}
      onclick={() => setFilter(fil)}
      aria-pressed={currentFilter === filterNum(fil)}
    >{fil}</button>
  {/each}
</div>

<style>
  .filter-selector {
    display: flex;
    gap: var(--space-1);
  }

  .fil-btn {
    flex: 1;
    min-height: var(--tap-target);
    padding: 0 var(--space-2);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.1s, color 0.1s, border-color 0.1s;
  }

  .fil-btn:hover {
    color: var(--text);
    border-color: var(--accent);
  }

  .fil-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
  }
</style>
