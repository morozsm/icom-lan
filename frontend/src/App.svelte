<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchCapabilities, startPolling, setPollingMultiplier } from './lib/transport/http-client';
  import { connect, sendRaw } from './lib/transport/ws-client';
  import { initBatteryMonitor } from './lib/utils/battery';
  import { setCapabilities } from './lib/stores/capabilities.svelte';
  import { setRadioState } from './lib/stores/radio.svelte';
  import { initUiVersion, getUiVersion } from './lib/stores/ui-version.svelte';
  import AppShell from './components/layout/AppShell.svelte';
  import RadioLayoutV2 from './components-v2/layout/RadioLayout.svelte';
  import ControlButtonDemo from './components-v2/controls/ControlButtonDemo.svelte';
  import { initMediaSession, destroyMediaSession } from './lib/media/media-session';
  import { systemController } from './lib/runtime/system-controller';
  import './app.css';

  let backendError = $state<string | null>(null);
  let retrying = $state(false);
  let retryCount = 0;
  const MAX_RETRIES = 5;
  const RETRY_DELAYS = [3000, 5000, 10000, 20000, 30000];
  const demoMode = typeof window !== 'undefined'
    ? new URLSearchParams(window.location.search).get('demo')
    : null;

  onMount(() => {
    if (demoMode === 'control-buttons') {
      return;
    }

    // Initialize UI version from URL param or localStorage
    initUiVersion();

    initMediaSession();

    // Register polling lifecycle with SystemController for connect/disconnect
    systemController.registerPolling(() =>
      startPolling((state) => { setRadioState(state); }, 1000),
    );
    const stopPolling = startPolling((state) => {
      setRadioState(state);
    }, 1000);
    systemController.setStopPolling(stopPolling);

    let cleanupBattery: (() => void) | null = null;
    initBatteryMonitor((multiplier) => {
      setPollingMultiplier(multiplier);
    }).then(cleanup => { cleanupBattery = cleanup; });

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
      destroyMediaSession();
      cleanupBattery?.();
      stopPolling();
      if (retryTimer) clearTimeout(retryTimer);
    };
  });

  // Reactive UI version tracking
  let uiVersion = $derived(getUiVersion());
</script>

{#if demoMode === 'control-buttons'}
  <ControlButtonDemo />
{:else if backendError}
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
{:else if uiVersion === 'v2'}
  <RadioLayoutV2 />
{:else}
  <AppShell />
{/if}

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
