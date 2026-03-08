<script lang="ts">
  import { onMount } from 'svelte';

  let offline = $state(!navigator.onLine);

  onMount(() => {
    const goOnline = () => { offline = false; };
    const goOffline = () => { offline = true; };
    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  });
</script>

{#if offline}
  <div class="offline-banner" role="status" aria-live="polite">
    No network — using cached data
  </div>
{/if}

<style>
  .offline-banner {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 8900;
    text-align: center;
    padding: var(--space-1) var(--space-4);
    background: var(--warning);
    color: #000;
    font-size: 0.8125rem;
    font-weight: 600;
  }
</style>
