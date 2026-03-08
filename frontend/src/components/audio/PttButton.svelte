<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { makeCommandId } from '../../lib/types/protocol';
  import { getIsTransmitting, getRadioState } from '../../lib/stores/radio.svelte';

  let transmitting = $derived(getIsTransmitting());
  let pending = $state(false);
  let pendingValue = $state(false);

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
    sendCommand({ type: 'ptt', id: makeCommandId(), state: next });
  }
</script>

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

  .ptt-label {
    display: block;
  }
</style>
