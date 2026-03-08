<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchCapabilities, fetchState, startPolling } from './lib/transport/http-client';
  import { connect } from './lib/transport/ws-client';
  import { setCapabilities } from './lib/stores/capabilities.svelte';
  import { setRadioState } from './lib/stores/radio.svelte';
  import { setConnected } from './lib/stores/connection.svelte';
  import AppShell from './components/layout/AppShell.svelte';
  import './app.css';

  onMount(() => {
    let stopPolling: (() => void) | undefined;

    void (async () => {
      const caps = await fetchCapabilities();
      setCapabilities(caps);
      stopPolling = startPolling(async () => {
        const state = await fetchState();
        setRadioState(state);
        setConnected(true);
      });
      connect('/api/v1/ws');
    })();

    return () => stopPolling?.();
  });
</script>

<AppShell />
