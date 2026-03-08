<script lang="ts">
  import { getCapabilities } from '../../lib/stores/capabilities.svelte';
  import { getConnectionStatus } from '../../lib/stores/connection.svelte';
  import { getRadioState, getActiveReceiver } from '../../lib/stores/radio.svelte';

  let caps = $derived(getCapabilities());
  let status = $derived(getConnectionStatus());
  let state = $derived(getRadioState());
  let active = $derived(getActiveReceiver());

  let modelName = $derived(caps?.model ?? 'Radio');
  let isConnected = $derived(status === 'connected');
  let isPartial = $derived(status === 'partial');
  let isPtt = $derived(state?.ptt ?? false);

  // Format frequency: 14.074.000
  function formatFreq(hz: number): string {
    if (!hz) return '—';
    const mhz = Math.floor(hz / 1_000_000);
    const khz = Math.floor((hz % 1_000_000) / 1_000);
    const hz0 = hz % 1_000;
    return `${mhz}.${String(khz).padStart(3, '0')}.${String(hz0).padStart(3, '0')}`;
  }

  // UTC clock — update every second
  let utcTime = $state('');

  function updateClock() {
    const now = new Date();
    const hh = String(now.getUTCHours()).padStart(2, '0');
    const mm = String(now.getUTCMinutes()).padStart(2, '0');
    const ss = String(now.getUTCSeconds()).padStart(2, '0');
    utcTime = `${hh}:${mm}:${ss}`;
  }

  $effect(() => {
    updateClock();
    const id = setInterval(updateClock, 1_000);
    return () => clearInterval(id);
  });
</script>

<header class="status-bar">
  <!-- Left: model + connection -->
  <div class="left">
    <span
      class="dot"
      class:connected={isConnected}
      class:partial={isPartial}
      title={status}
    ></span>
    <span class="model">{modelName}</span>
  </div>

  <!-- Center: frequency -->
  <div class="center">
    {#if active}
      <span class="freq">{formatFreq(active.freqHz)}</span>
      <span class="mode">{active.mode}</span>
    {/if}
  </div>

  <!-- Right: UTC + TX/RX -->
  <div class="right">
    {#if isPtt}
      <span class="tx-badge">TX</span>
    {:else}
      <span class="rx-badge">RX</span>
    {/if}
    <span class="clock">{utcTime} UTC</span>
  </div>
</header>

<style>
  .status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 28px;
    padding: 0 var(--space-4);
    background: var(--panel);
    border-bottom: 1px solid var(--panel-border);
    flex-shrink: 0;
    font-size: 0.75rem;
    font-family: var(--font-mono);
    gap: var(--space-3);
  }

  .left,
  .right {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    min-width: 0;
    flex: 1;
  }

  .right {
    justify-content: flex-end;
  }

  .center {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-shrink: 0;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--danger);
    flex-shrink: 0;
    transition: background 0.3s;
  }

  .dot.connected {
    background: var(--success);
  }

  .dot.partial {
    background: var(--warning);
  }

  .model {
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .freq {
    color: var(--text);
    font-size: 0.8125rem;
    letter-spacing: 0.03em;
  }

  .mode {
    color: var(--accent);
    font-size: 0.6875rem;
  }

  .clock {
    color: var(--text-muted);
    white-space: nowrap;
  }

  .tx-badge,
  .rx-badge {
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.05em;
  }

  .tx-badge {
    background: var(--danger);
    color: #fff;
  }

  .rx-badge {
    background: var(--success);
    color: #000;
  }
</style>
