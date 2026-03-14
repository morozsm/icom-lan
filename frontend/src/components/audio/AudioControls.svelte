<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { radio } from '../../lib/stores/radio.svelte';
  import { getAudioState, toggleMute } from '../../lib/stores/audio.svelte';
  import { getWsConnected } from '../../lib/stores/connection.svelte';

  let audio = $derived(getAudioState());
  let rx = $derived(radio.current?.active === 'SUB' ? (radio.current?.sub ?? null) : (radio.current?.main ?? null));
  let receiverIdx = $derived(radio.current?.active === 'SUB' ? 1 : 0);

  // Radio AF level from server state; fall back to local volume
  let afLevel = $derived(rx?.afLevel ?? audio.volume);
  let muted = $derived(audio.muted);
  let rxActive = $derived(audio.rxEnabled);
  let controlOk = $derived(getWsConnected());

  function onVolumeChange(e: Event) {
    const level = Math.round(Number((e.target as HTMLInputElement).value));
    sendCommand('set_af_level', { level, receiver: receiverIdx });
  }

  function onMute() {
    // Mute is client-side only — toggleMute() handles local audio muting
    toggleMute();
  }
</script>

<div class="audio-controls">
  <div class="rx-indicator" class:active={rxActive} title="RX audio">
    <span class="dot"></span>
    <span class="label">RX</span>
  </div>

  <button
    class="mute-btn"
    class:muted
    onclick={onMute}
    aria-pressed={muted}
    aria-label={muted ? 'Unmute' : 'Mute'}
    title={muted ? 'Unmute' : 'Mute'}
    disabled={!controlOk}
  >
    {muted ? '🔇' : '🔊'}
  </button>

  <label class="volume-label" for="af-volume">VOL</label>
  <input
    id="af-volume"
    type="range"
    class="volume-slider"
    min="0"
    max="100"
    value={afLevel}
    onchange={onVolumeChange}
    aria-label="AF volume"
    disabled={!controlOk}
  />
  <span class="volume-val">{afLevel}</span>
</div>

<style>
  .audio-controls {
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }

  .rx-indicator {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-muted);
    flex-shrink: 0;
  }

  .rx-indicator.active .dot {
    background: var(--success);
    box-shadow: 0 0 6px var(--success);
  }

  .rx-indicator.active .label {
    color: var(--success);
  }

  .mute-btn {
    min-width: var(--tap-target);
    min-height: var(--tap-target);
    padding: 0 var(--space-2);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    cursor: pointer;
    font-size: 1rem;
    transition: border-color 0.1s;
  }

  .mute-btn.muted {
    border-color: var(--warning);
  }

  .volume-label {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-muted);
    user-select: none;
  }

  .volume-slider {
    flex: 1;
    min-width: 80px;
    accent-color: var(--accent);
    cursor: pointer;
  }

  .volume-val {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-muted);
    min-width: 2ch;
    text-align: right;
    user-select: none;
  }
</style>
