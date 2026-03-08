<script lang="ts">
  import { onMount } from 'svelte';
  import { onMessage } from '../../lib/transport/ws-client';

  interface ToastItem {
    id: string;
    level: 'info' | 'warning' | 'error';
    message: string;
  }

  let toasts = $state<ToastItem[]>([]);

  function dismiss(id: string) {
    toasts = toasts.filter((t) => t.id !== id);
  }

  function addToast(level: 'info' | 'warning' | 'error', message: string) {
    const id = crypto.randomUUID();
    toasts = [...toasts, { id, level, message }];
    setTimeout(() => dismiss(id), 5_000);
  }

  onMount(() => {
    return onMessage((msg) => {
      if (msg.type === 'notification') {
        const lvl = msg.level === 'warning' || msg.level === 'error' ? msg.level : 'info';
        addToast(lvl as 'info' | 'warning' | 'error', msg.message as string);
      }
    });
  });
</script>

{#if toasts.length > 0}
  <div class="toast-container" aria-live="polite" aria-label="Notifications">
    {#each toasts as toast (toast.id)}
      <button
        class="toast"
        class:info={toast.level === 'info'}
        class:warning={toast.level === 'warning'}
        class:error={toast.level === 'error'}
        aria-label="Dismiss notification"
        onclick={() => dismiss(toast.id)}
      >
        <span class="toast-icon" aria-hidden="true">
          {#if toast.level === 'error'}✕{:else if toast.level === 'warning'}⚠{:else}ℹ{/if}
        </span>
        <span class="toast-msg">{toast.message}</span>
        <span class="toast-close" aria-hidden="true">×</span>
      </button>
    {/each}
  </div>
{/if}

<style>
  .toast-container {
    position: fixed;
    top: var(--space-4);
    right: var(--space-4);
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    max-width: 360px;
    pointer-events: none;
  }

  .toast {
    /* button reset */
    appearance: none;
    -webkit-appearance: none;
    border: none;
    font-family: inherit;
    font-size: inherit;
    text-align: left;
    width: 100%;

    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    padding: var(--space-3);
    border-radius: var(--radius);
    border-left: 3px solid;
    background: var(--panel);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    font-size: 0.8125rem;
    font-family: var(--font-sans);
    cursor: pointer;
    pointer-events: all;
    animation: slide-in 0.2s ease;
    transition: opacity 0.2s;
  }

  .toast:hover {
    opacity: 0.85;
  }

  .toast.info {
    border-color: var(--accent);
  }

  .toast.warning {
    border-color: var(--warning);
  }

  .toast.error {
    border-color: var(--danger);
  }

  .toast-icon {
    flex-shrink: 0;
    font-size: 0.75rem;
    margin-top: 1px;
  }

  .toast.info .toast-icon { color: var(--accent); }
  .toast.warning .toast-icon { color: var(--warning); }
  .toast.error .toast-icon { color: var(--danger); }

  .toast-msg {
    flex: 1;
    line-height: 1.4;
    word-break: break-word;
    color: var(--text);
  }

  .toast-close {
    flex-shrink: 0;
    color: var(--text-muted);
    font-size: 1rem;
    line-height: 1;
    cursor: pointer;
    padding: 0 2px;
    margin-left: var(--space-1);
  }

  .toast-close:hover {
    color: var(--text);
  }

  @keyframes slide-in {
    from {
      transform: translateX(calc(100% + var(--space-4)));
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
</style>
