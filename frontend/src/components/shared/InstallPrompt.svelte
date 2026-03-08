<script lang="ts">
  import { onMount } from 'svelte';

  const DISMISS_KEY = 'pwa-install-dismissed';
  const DISMISS_DAYS = 7;

  let visible = $state(false);
  let deferredPrompt = $state<BeforeInstallPromptEvent | null>(null);

  function isStandalone(): boolean {
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      ('standalone' in navigator && (navigator as { standalone?: boolean }).standalone === true)
    );
  }

  function isDismissed(): boolean {
    const ts = localStorage.getItem(DISMISS_KEY);
    if (!ts) return false;
    return Date.now() - Number(ts) < DISMISS_DAYS * 86400 * 1000;
  }

  onMount(() => {
    if (isStandalone() || isDismissed()) return;

    const handler = (e: Event) => {
      e.preventDefault();
      deferredPrompt = e as BeforeInstallPromptEvent;
      visible = true;
    };

    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  });

  async function install() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      visible = false;
      deferredPrompt = null;
    }
  }

  function dismiss() {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    visible = false;
  }
</script>

{#if visible}
  <div class="install-banner" role="banner">
    <span class="install-text">Install icom-lan for quick access</span>
    <div class="install-actions">
      <button class="btn-install" onclick={install}>Install</button>
      <button class="btn-later" onclick={dismiss}>Later</button>
    </div>
  </div>
{/if}

<style>
  .install-banner {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 9000;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: var(--panel);
    border-top: 1px solid var(--panel-border);
    box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.3);
  }

  .install-text {
    font-size: 0.875rem;
    color: var(--text);
    flex: 1;
  }

  .install-actions {
    display: flex;
    gap: var(--space-2);
    flex-shrink: 0;
  }

  .btn-install {
    padding: var(--space-1) var(--space-3);
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: var(--radius);
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-install:hover {
    opacity: 0.85;
  }

  .btn-later {
    padding: var(--space-1) var(--space-3);
    background: transparent;
    color: var(--text-muted);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    font-size: 0.875rem;
    cursor: pointer;
  }

  .btn-later:hover {
    color: var(--text);
  }
</style>
