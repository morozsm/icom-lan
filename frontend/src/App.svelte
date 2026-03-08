<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchCapabilities, startPolling } from './lib/transport/http-client';
  import { connect } from './lib/transport/ws-client';
  import { setCapabilities } from './lib/stores/capabilities.svelte';
  import { setRadioState } from './lib/stores/radio.svelte';
  import AppShell from './components/layout/AppShell.svelte';
  import './app.css';

  let backendError = $state<string | null>(null);
  let retrying = $state(false);

  onMount(() => {
    let stopPolling: (() => void) | undefined;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    async function init() {
      retrying = false;
      try {
        const caps = await fetchCapabilities();
        setCapabilities(caps);
        backendError = null;
        stopPolling = startPolling((state) => {
          setRadioState(state);
        });
        connect('/api/v1/ws');
      } catch (err) {
        console.error('Failed to fetch capabilities:', err);
        backendError = 'Backend unreachable — retrying in 5s…';
        retrying = true;
        retryTimer = setTimeout(() => void init(), 5000);
      }
    }

    void init();

    return () => {
      stopPolling?.();
      if (retryTimer) clearTimeout(retryTimer);
    };
  });
</script>

{#if backendError}
  <div class="error-overlay" role="alert" aria-live="assertive">
    <div class="error-box">
      <div class="error-icon">⚠</div>
      <p class="error-msg">{backendError}</p>
      {#if retrying}
        <div class="retry-indicator">
          <span class="spinner"></span>
          <span>Connecting…</span>
        </div>
      {/if}
    </div>
  </div>
{/if}
<AppShell />

<style>
  .error-overlay {
    position: fixed;
    inset: 0;
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(11, 15, 20, 0.85);
    backdrop-filter: blur(4px);
  }

  .error-box {
    background: var(--panel);
    border: 1px solid var(--danger);
    border-radius: var(--radius-lg);
    padding: var(--space-6);
    max-width: 360px;
    width: 90%;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
  }

  .error-icon {
    font-size: 2rem;
    color: var(--warning);
  }

  .error-msg {
    color: var(--text);
    font-size: 0.9375rem;
    margin: 0;
    line-height: 1.5;
  }

  .retry-indicator {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--text-muted);
    font-size: 0.8125rem;
    font-family: var(--font-mono);
  }

  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid var(--panel-border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
