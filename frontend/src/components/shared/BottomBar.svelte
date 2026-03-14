<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { radio } from '../../lib/stores/radio.svelte';
  import { getAudioState, toggleMute } from '../../lib/stores/audio.svelte';
  import { audioManager } from '../../lib/audio/audio-manager';
  import { getWsConnected, isAudioAliveControlDead } from '../../lib/stores/connection.svelte';
  import { onMount } from 'svelte';

  let audioTick = $state(0);
  onMount(() => {
    const unsub = audioManager.onChange(() => { audioTick++; });
    return () => unsub();
  });
  let rxOn = $derived(audioTick >= 0 && audioManager.rxEnabled);
  let wsOk = $derived(audioTick >= 0 && audioManager.wsConnected);
  let controlOk = $derived(getWsConnected());
  let audioDeadZone = $derived(isAudioAliveControlDead());

  let audio = $derived(getAudioState());
  let rx = $derived(radio.current?.active === 'SUB' ? (radio.current?.sub ?? null) : (radio.current?.main ?? null));
  let receiverIdx = $derived(radio.current?.active === 'SUB' ? 1 : 0);
  let transmitting = $derived(radio.current?.ptt ?? false);
  let pending = $state(false);
  let pendingValue = $state(false);
  let pttTimeoutId = $state<number | null>(null);

  let afLevel = $derived(rx?.afLevel ?? audio.volume);
  let muted = $derived(audio.muted);

  $effect(() => {
    if (pending && transmitting === pendingValue) {
      pending = false;
    }
  });

  // PTT safety: auto-release after 30s or on WS disconnect
  $effect(() => {
    if (transmitting) {
      // Start 30s timeout when PTT goes active
      if (pttTimeoutId) clearTimeout(pttTimeoutId);
      pttTimeoutId = setTimeout(() => {
        console.warn('[PTT] 30s timeout — forcing PTT off');
        sendCommand('ptt', { state: false });
      }, 30_000) as unknown as number;
    } else {
      // Clear timeout when PTT goes inactive
      if (pttTimeoutId) {
        clearTimeout(pttTimeoutId);
        pttTimeoutId = null;
      }
    }
  });

  // Force PTT off if WS disconnects while transmitting
  $effect(() => {
    if (transmitting && !wsOk) {
      console.warn('[PTT] WS disconnected — forcing PTT off');
      sendCommand('ptt', { state: false });
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

    // Safety timeout — clear pending if server doesn't respond
    setTimeout(() => {
      if (pending) {
        pending = false;
      }
    }, 5000);
  }

  function toggleRxAudio() {
    if (rxOn) audioManager.stopRx();
    else audioManager.startRx();
  }
</script>

<footer class="bottom-bar">
  <!-- RX Audio toggle (first) -->
  <button
    class="rx-btn"
    class:active={rxOn}
    onclick={toggleRxAudio}
    aria-pressed={rxOn}
    aria-label={rxOn ? 'Stop RX audio' : 'Start RX audio'}
    disabled={!controlOk}
    title={!controlOk ? 'Control connection lost' : undefined}
  >
    <span class="rx-dot" class:on={rxOn}></span>RX
  </button>

  {#if audioDeadZone}
    <span class="audio-warn" title="Audio WS connected but control WS is down">Audio/ctrl mismatch</span>
  {/if}

  <!-- Volume -->
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

  <!-- PTT button -->
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

  .rx-btn {
    min-width: 52px;
    min-height: 44px;
    padding: 0 var(--space-3);
    background: rgba(22, 101, 52, 0.2);
    border: 2px solid rgba(22, 101, 52, 0.4);
    border-radius: var(--radius);
    color: #4ade80;
    font-family: var(--font-mono);
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    cursor: pointer;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: background 0.15s, border-color 0.15s;
  }

  .rx-btn.active {
    background: #15803d;
    border-color: #22c55e;
    color: #fff;
  }

  .rx-dot {
    display: inline-block;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #4ade8060;
  }

  .rx-dot.on {
    background: #22c55e;
    box-shadow: 0 0 4px #22c55e;
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

  .rx-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .audio-warn {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--warning);
    flex-shrink: 0;
  }
</style>
