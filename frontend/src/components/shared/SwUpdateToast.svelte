<script lang="ts">
  import { onMount } from 'svelte';

  let visible = $state(false);
  let registration = $state<ServiceWorkerRegistration | null>(null);

  onMount(() => {
    if (!('serviceWorker' in navigator)) return;

    const handleUpdate = (reg: ServiceWorkerRegistration) => {
      registration = reg;
      visible = true;
    };

    // vite-plugin-pwa fires this custom event when SW update is available
    window.addEventListener('vite-pwa:sw-update', (e) => {
      handleUpdate((e as CustomEvent<ServiceWorkerRegistration>).detail);
    });

    // Also check for waiting SW on page load
    navigator.serviceWorker.getRegistration().then((reg) => {
      if (reg?.waiting) {
        registration = reg;
        visible = true;
      }
    });
  });

  function applyUpdate() {
    if (!registration?.waiting) return;
    registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    registration.waiting.addEventListener('statechange', (e) => {
      if ((e.target as ServiceWorker).state === 'activated') {
        window.location.reload();
      }
    });
    visible = false;
  }
</script>

{#if visible}
  <button class="sw-toast" onclick={applyUpdate} aria-live="polite">
    <span class="sw-icon" aria-hidden="true">↑</span>
    <span class="sw-msg">Update available — tap to refresh</span>
  </button>
{/if}

<style>
  .sw-toast {
    position: fixed;
    top: var(--space-4);
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: var(--radius);
    font-size: 0.875rem;
    font-family: var(--font-sans);
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    animation: drop-in 0.2s ease;
  }

  .sw-toast:hover {
    opacity: 0.9;
  }

  .sw-icon {
    font-size: 1rem;
    font-weight: 700;
  }

  @keyframes drop-in {
    from { transform: translateX(-50%) translateY(-100%); opacity: 0; }
    to   { transform: translateX(-50%) translateY(0);    opacity: 1; }
  }
</style>
