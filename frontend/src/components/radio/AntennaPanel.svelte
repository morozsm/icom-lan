<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { getAntennaCount } from '../../lib/stores/capabilities.svelte';

  let antennaCount = $derived(getAntennaCount());
</script>

{#if antennaCount > 1}
<div class="antenna-panel">
  <div class="ant-row">
    <span class="ant-label">TX</span>
    {#each { length: antennaCount } as _, i}
      <button
        class="ant-btn"
        onclick={() => sendCommand(`set_antenna_${i + 1}`, {})}
        title="Select TX ANT{i + 1}"
      >ANT{i + 1}</button>
    {/each}
  </div>
  <div class="ant-row">
    <span class="ant-label">RX</span>
    {#each { length: antennaCount } as _, i}
      <button
        class="ant-btn"
        onclick={() => sendCommand(`set_rx_antenna_ant${i + 1}`, {})}
        title="Select RX ANT{i + 1}"
      >ANT{i + 1}</button>
    {/each}
  </div>
</div>
{/if}

<style>
  .antenna-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .ant-row {
    display: flex;
    align-items: center;
    gap: var(--space-1);
  }

  .ant-label {
    font-family: var(--font-mono);
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    min-width: 24px;
  }

  .ant-btn {
    min-height: var(--tap-target);
    padding: 0 var(--space-3);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 9999px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.1s, color 0.1s, border-color 0.1s;
  }

  .ant-btn:hover {
    color: var(--text);
    border-color: var(--accent);
  }

  .ant-btn:active {
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
  }
</style>
