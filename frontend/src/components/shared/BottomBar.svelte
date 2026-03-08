<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import {
    getActiveReceiver,
    getRadioState,
    getIsTransmitting,
  } from '../../lib/stores/radio.svelte';
  import { getAudioState, toggleMute } from '../../lib/stores/audio.svelte';

  let audio = $derived(getAudioState());
  let rx = $derived(getActiveReceiver());
  let receiverIdx = $derived(getRadioState()?.active === 'SUB' ? 1 : 0);
  let transmitting = $derived(getIsTransmitting());
  let pending = $state(false);
  let pendingValue = $state(false);

  let afLevel = $derived(rx?.afLevel ?? audio.volume);
  let muted = $derived(audio.muted);

  $effect(() => {
    if (pending && transmitting === pendingValue) {
      pending = false;
    }
  });

  function onVolumeChange(e: Event) {
    const level = Math.round(Number((e.target as HTMLInputElement).value));
    sendCommand('set_af_level', { level, receiver: receiverIdx });
  }

  function onMute() {
    toggleMute();
  }

  function onPtt() {
    if (pending) return;
    const next = !transmitting;
    pending = true;
    pendingValue = next;
    sendCommand('ptt', { state: next });
  }
</script>

<footer class="bottom-bar">
  <!-- Left: volume + mute -->
  <div class="audio-section">
    <button
      class="mute-btn"
      class:muted
      onclick={onMute}
      aria-pressed={muted}
      aria-label={muted ? 'Unmute' : 'Mute'}
    >
      {muted ? '🔇' : '🔊'}
    </button>

    <input
      type="range"
      class="volume-slider"
      min="0"
      max="100"
      value={afLevel}
      onchange={onVolumeChange}
      aria-label="AF volume"
    />
  </div>

  <!-- Right: PTT button -->
  <button
    class="ptt-btn"
    class:transmitting
    class:pending
    onclick={onPtt}
    aria-pressed={transmitting}
    aria-label={transmitting ? 'PTT active — click to stop TX' : 'Push to talk'}
    disabled={pending && !transmitting}
  >
    {#if pending}
      …
    {:else if transmitting}
      TX
    {:else}
      PTT
    {/if}
  </button>
</footer>

<style>
  .bottom-bar {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    height: 56px;
    padding: 0 var(--space-4);
    background-color: var(--panel);
    border-top: 1px solid var(--panel-border);
    flex-shrink: 0;
  }

  .audio-section {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex: 1;
    min-width: 0;
  }

  .mute-btn {
    min-width: 44px;
    min-height: 44px;
    padding: 0 var(--space-2);
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    cursor: pointer;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: border-color 0.1s;
  }

  .mute-btn.muted {
    border-color: var(--warning);
  }

  .volume-slider {
    flex: 1;
    min-width: 0;
    accent-color: var(--accent);
    cursor: pointer;
    height: 4px;
  }

  .ptt-btn {
    min-width: 100px;
    min-height: 44px;
    padding: 0 var(--space-4);
    background: color-mix(in srgb, var(--danger) 15%, var(--panel));
    border: 2px solid color-mix(in srgb, var(--danger) 40%, transparent);
    border-radius: var(--radius);
    color: var(--danger);
    font-family: var(--font-mono);
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    cursor: pointer;
    flex-shrink: 0;
    transition: background 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s;
    user-select: none;
  }

  .ptt-btn:hover:not(:disabled) {
    background: color-mix(in srgb, var(--danger) 25%, var(--panel));
    border-color: var(--danger);
  }

  .ptt-btn.transmitting {
    background: var(--danger);
    border-color: var(--danger);
    color: #fff;
    box-shadow: 0 0 20px color-mix(in srgb, var(--danger) 60%, transparent);
    font-weight: 900;
  }

  .ptt-btn.pending {
    opacity: 0.7;
    cursor: wait;
  }

  .ptt-btn:disabled {
    cursor: wait;
  }
</style>
