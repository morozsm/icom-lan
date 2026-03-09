<script lang="ts">
  import { onMount } from 'svelte';
  import { audioManager } from '../../lib/audio/audio-manager';

  // Reactive tick — audioManager calls onChange to trigger re-render
  let tick = $state(0);
  onMount(() => {
    const unsub = audioManager.onChange(() => { tick++; });
    return () => unsub();
  });

  let rxOn = $derived(tick >= 0 && audioManager.rxEnabled);
  let txOn = $derived(tick >= 0 && audioManager.txEnabled);
  let wsOk = $derived(tick >= 0 && audioManager.wsConnected);
  let txOk = $derived(audioManager.txSupported);

  let statusText = $derived.by(() => {
    if (tick < 0) return ''; // never happens, keeps tick alive
    if (!rxOn && !txOn) return 'AUDIO OFF';
    if (!wsOk) return 'CONNECTING...';
    const parts: string[] = [];
    if (rxOn) parts.push('RX');
    if (txOn) parts.push('TX MIC');
    return parts.join(' + ') + ' ON';
  });

  let txError = $state('');

  function toggleRx() {
    if (rxOn) audioManager.stopRx();
    else audioManager.startRx();
  }

  async function toggleTx() {
    if (txOn) {
      audioManager.stopTx();
      txError = '';
    } else {
      const err = await audioManager.startTx();
      if (err) txError = err;
    }
  }
</script>

<div class="audio-panel">
  <div class="audio-header">
    <span class="dot" class:on={wsOk && (rxOn || txOn)}></span>
    <span class="label">AUDIO</span>
    <span class="status">{statusText}</span>
  </div>

  <div class="audio-buttons">
    <button
      class="audio-btn rx-btn"
      class:active={rxOn}
      onclick={toggleRx}
    >{rxOn ? 'RX AUDIO ON' : 'RX AUDIO'}</button>

    {#if txOk}
      <button
        class="audio-btn tx-btn"
        class:active={txOn}
        onclick={toggleTx}
      >{txOn ? 'TX MIC ON' : 'TX MIC'}</button>
    {/if}
  </div>

  {#if txError}
    <div class="tx-error">{txError}</div>
  {/if}
</div>

<style>
  .audio-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .audio-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-family: var(--font-mono);
    font-size: 0.6875rem;
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--text-muted);
    flex-shrink: 0;
  }

  .dot.on {
    background: #22c55e;
    box-shadow: 0 0 4px #22c55e;
  }

  .label {
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .status {
    color: var(--accent);
    margin-left: auto;
  }

  .audio-buttons {
    display: flex;
    gap: var(--space-2);
  }

  .audio-btn {
    flex: 1;
    min-height: 36px;
    padding: 0 var(--space-3);
    border-radius: var(--radius);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
  }

  .rx-btn {
    background: rgba(22, 101, 52, 0.3);
    border: 1px solid #15803d;
    color: #4ade80;
  }

  .rx-btn:hover {
    background: rgba(22, 101, 52, 0.5);
  }

  .rx-btn.active {
    background: #15803d;
    border-color: #22c55e;
    color: #fff;
  }

  .tx-btn {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    color: var(--text-muted);
  }

  .tx-btn:hover {
    background: var(--panel-hover, var(--panel));
  }

  .tx-btn.active {
    background: #b45309;
    border-color: #f59e0b;
    color: #fff;
  }

  .tx-error {
    font-size: 0.625rem;
    color: #ef4444;
    font-family: var(--font-mono);
  }
</style>
