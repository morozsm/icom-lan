<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchCapabilities, startPolling } from './lib/transport/http-client';
  import { connect } from './lib/transport/ws-client';
  import { setCapabilities } from './lib/stores/capabilities.svelte';
  import { setRadioState } from './lib/stores/radio.svelte';
  import AppShell from './components/layout/AppShell.svelte';
  import './app.css';

  let backendError = $state<string | null>(null);

  onMount(() => {
    let stopPolling: (() => void) | undefined;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    async function init() {
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
  <div class="backend-error">{backendError}</div>
{/if}
<AppShell />
