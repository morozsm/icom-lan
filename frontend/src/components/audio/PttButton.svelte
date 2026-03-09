<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { radio } from '../../lib/stores/radio.svelte';
  import { vibrate } from '../../lib/utils/haptics';

  let transmitting = $derived(radio.current?.ptt ?? false);
  let pending = $state(false);
  let pendingValue = $state(false);

  // Hold-to-talk state
  let pressing = $state(false);
  let holdTimer: ReturnType<typeof setTimeout> | null = null;
  const HOLD_DELAY_MS = 200;

  // Clear pending when server state catches up
  $effect(() => {
    if (pending && transmitting === pendingValue) {
      pending = false;
    }
  });

  function onPtt() {
    if (pending) return;
    const next = !transmitting;
    pending = true;
    pendingValue = next;
    sendCommand('ptt', { state: next });
  }

  // Hold-to-talk: pointer events on the button
  function onPressStart(e: PointerEvent) {
    if (pending) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    pressing = true;
    holdTimer = setTimeout(() => {
      holdTimer = null;
      if (pressing && !transmitting) {
        vibrate('ptt');
        pending = true;
        pendingValue = true;
        sendCommand('ptt', { state: true });
      }
    }, HOLD_DELAY_MS);
  }

  function onPressEnd() {
    pressing = false;
    if (holdTimer !== null) {
      clearTimeout(holdTimer);
      holdTimer = null;
      // Short press (< HOLD_DELAY_MS) — toggle like a normal click
      onPtt();
      return;
    }
    // If we activated TX via hold, release it
    if (transmitting) {
      vibrate('ptt');
      pending = true;
      pendingValue = false;
      sendCommand('ptt', { state: false });
    }
  }

  function onPressCancel() {
    pressing = false;
    if (holdTimer !== null) {
      clearTimeout(holdTimer);
      holdTimer = null;
    }
    // Pointer left button area — release TX if active or about to activate
    if (transmitting || (pending && pendingValue)) {
      vibrate('ptt');
      pending = true;
      pendingValue = false;
      sendCommand('ptt', { state: false });
    }
  }
</script>

<button
  class="ptt-btn"
  class:transmitting
  class:pending
  class:pressing
  onpointerdown={onPressStart}
  onpointerup={onPressEnd}
  onpointerleave={onPressCancel}
  onpointercancel={onPressCancel}
  aria-pressed={transmitting}
  aria-label={transmitting ? 'PTT active — release to stop TX' : 'Push to talk'}
  disabled={pending && !transmitting}
>
  {#if pending}
    <span class="ptt-label">…</span>
  {:else if transmitting}
    <span class="ptt-label">TX</span>
  {:else}
    <span class="ptt-label">PTT</span>
  {/if}
</button>

<style>
  .ptt-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 80px;
    min-height: var(--tap-target);
    padding: 0 var(--space-4);
    background: color-mix(in srgb, var(--danger) 15%, var(--panel));
    border: 2px solid color-mix(in srgb, var(--danger) 40%, transparent);
    border-radius: var(--radius);
    color: var(--danger);
    font-family: var(--font-mono);
    font-size: 0.9375rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    cursor: pointer;
    transition:
      background 0.15s,
      border-color 0.15s,
      color 0.15s,
      box-shadow 0.15s,
      transform 0.1s;
    user-select: none;
    touch-action: none;
  }

  .ptt-btn:hover:not(:disabled) {
    background: color-mix(in srgb, var(--danger) 25%, var(--panel));
    border-color: var(--danger);
  }

  .ptt-btn.pressing {
    transform: scale(0.95);
  }

  .ptt-btn.transmitting {
    background: var(--danger);
    border-color: var(--danger);
    color: #fff;
    box-shadow: 0 0 20px color-mix(in srgb, var(--danger) 60%, transparent);
    font-weight: 900;
    animation: ptt-pulse 1s ease-in-out infinite;
  }

  @keyframes ptt-pulse {
    0%,
    100% {
      box-shadow: 0 0 20px color-mix(in srgb, var(--danger) 60%, transparent);
    }
    50% {
      box-shadow:
        0 0 30px color-mix(in srgb, var(--danger) 80%, transparent),
        0 0 8px color-mix(in srgb, var(--danger) 40%, transparent);
    }
  }

  .ptt-btn.pending {
    opacity: 0.7;
    cursor: wait;
  }

  .ptt-btn:disabled {
    cursor: wait;
  }

  .ptt-label {
    display: block;
  }
</style>
