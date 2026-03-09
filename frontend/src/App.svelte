<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchCapabilities } from './lib/transport/http-client';
  import { connect, sendRaw } from './lib/transport/ws-client';
  import { setCapabilities } from './lib/stores/capabilities.svelte';
  import { setRadioState, getLastRevision } from './lib/stores/radio.svelte';
  import { setHttpConnected, markStateUpdated } from './lib/stores/connection.svelte';
  import AppShell from './components/layout/AppShell.svelte';
  import './app.css';

  let backendError = $state<string | null>(null);
  let retrying = $state(false);
  let retryCount = 0;
  const MAX_RETRIES = 5;
  const RETRY_DELAYS = [3000, 5000, 10000, 20000, 30000];

  // State poller: reads window.__RADIO_STATE__ written by index.html XHR
  // (index.html XHR polling works reliably across all browsers including iOS Safari)
  let pollInterval: ReturnType<typeof setInterval> | undefined;

  function startStatePoller() {
    pollInterval = setInterval(() => {
      const s = (window as any).__RADIO_STATE__;
      if (s && s.revision > getLastRevision()) {
        setRadioState(s);
        setHttpConnected(true);
        markStateUpdated();
      }
    }, 150);
  }

  onMount(() => {
    startStatePoller();

    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    (async () => {
      try {
        const caps = await fetchCapabilities();
        setCapabilities(caps);
        backendError = null;

        connect('/api/v1/ws');
        sendRaw({ type: 'subscribe', streams: ['events'] });
      } catch (err) {
        console.error('init error:', err);
        backendError = `Backend error: ${err}`;
        if (retryCount < MAX_RETRIES) {
          const delay = RETRY_DELAYS[Math.min(retryCount, RETRY_DELAYS.length - 1)];
          retrying = true;
          retryTimer = setTimeout(() => location.reload(), delay);
          retryCount++;
        } else {
          backendError = 'Server unreachable after multiple attempts. Check connection and reload manually.';
          retrying = false;
        }
      }
    })();

    return () => {
      if (pollInterval) clearInterval(pollInterval);
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
