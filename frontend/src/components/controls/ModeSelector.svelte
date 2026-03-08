<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { makeCommandId } from '../../lib/types/protocol';
  import { getMode, getRadioState } from '../../lib/stores/radio.svelte';
  import { getSupportedModes } from '../../lib/stores/capabilities.svelte';

  let currentMode = $derived(getMode());
  let modes = $derived(getSupportedModes());
  let receiverIdx = $derived(getRadioState()?.active === 'SUB' ? 1 : 0);

  function setMode(mode: string) {
    sendCommand({ type: 'set_mode', id: makeCommandId(), mode, receiver: receiverIdx });
  }
</script>

<div class="mode-selector">
  {#if modes.length > 0}
    <div class="btn-bar" role="group" aria-label="Mode selector">
      {#each modes as mode}
        <button
          class="mode-btn"
          class:active={currentMode === mode}
          onclick={() => setMode(mode)}
          aria-pressed={currentMode === mode}
        >{mode}</button>
      {/each}
    </div>
  {:else}
    <select
      class="mode-select"
      value={currentMode}
      onchange={(e) => setMode((e.target as HTMLSelectElement).value)}
      aria-label="Mode"
    >
      <option value={currentMode}>{currentMode || '—'}</option>
    </select>
  {/if}
</div>

<style>
  .mode-selector {
    display: contents;
  }

  .btn-bar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
  }

  .mode-btn {
    min-height: var(--tap-target);
    padding: 0 var(--space-3);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.8125rem;
    cursor: pointer;
    transition: background 0.1s, color 0.1s, border-color 0.1s;
  }

  .mode-btn:hover {
    color: var(--text);
    border-color: var(--accent);
  }

  .mode-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
  }

  .mode-select {
    min-height: var(--tap-target);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: 0.875rem;
    padding: 0 var(--space-3);
  }
</style>
