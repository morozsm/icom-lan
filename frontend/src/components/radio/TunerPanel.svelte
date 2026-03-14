<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { radio } from '../../lib/stores/radio.svelte';

  // tunerStatus: 0=OFF, 1=ON, 2=TUNING
  let tunerStatus = $derived(radio.current?.tunerStatus ?? 0);
  let isTuning = $derived(tunerStatus === 2);

  const LABELS: Record<number, string> = { 0: 'OFF', 1: 'ON', 2: 'TUNING…' };
  let statusLabel = $derived(LABELS[tunerStatus] ?? 'OFF');

  function setTuner(value: number) {
    sendCommand('set_tuner_status', { value });
  }
</script>

<div class="tuner-panel">
  <div class="tuner-header">
    <span class="label">TUNER</span>
    <span class="status" class:tuning={isTuning} class:on={tunerStatus === 1}>{statusLabel}</span>
  </div>
  <div class="tuner-btns">
    <button
      class="tuner-btn"
      class:active={tunerStatus === 0}
      onclick={() => setTuner(0)}
    >OFF</button>
    <button
      class="tuner-btn"
      class:active={tunerStatus === 1}
      onclick={() => setTuner(1)}
    >ON</button>
    <button
      class="tuner-btn tune-btn"
      class:active={isTuning}
      onclick={() => setTuner(2)}
    >TUNE</button>
  </div>
</div>

<style>
  .tuner-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .tuner-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .label {
    font-family: var(--font-mono);
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
  }

  .status {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    transition: color 0.2s;
  }

  .status.on {
    color: var(--accent);
  }

  .status.tuning {
    color: var(--warning);
    animation: blink 0.8s ease-in-out infinite;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .tuner-btns {
    display: flex;
    gap: var(--space-1);
  }

  .tuner-btn {
    flex: 1;
    min-height: var(--tap-target);
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

  .tuner-btn:hover {
    color: var(--text);
    border-color: var(--accent);
  }

  .tuner-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
  }

  .tune-btn.active {
    background: var(--warning);
    border-color: var(--warning);
    color: #000;
  }
</style>
