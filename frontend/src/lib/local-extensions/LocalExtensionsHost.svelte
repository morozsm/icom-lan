<script lang="ts">
  import { onMount, tick } from 'svelte';
  import {
    loadLocalExtensionManifest,
    type LocalExtensionDescriptor,
  } from './manifest';
  import {
    createDefaultLocalExtensionHostApi,
    installLocalExtensionHostApi,
    type LocalExtensionRegistration,
  } from './host-api';

  let extensions = $state<LocalExtensionDescriptor[]>([]);
  const disposers = new Map<string, () => void>();

  function disposeExtension(id: string): void {
    const dispose = disposers.get(id);
    if (dispose) {
      dispose();
      disposers.delete(id);
    }
  }

  function registerExtension(extension: LocalExtensionRegistration): void {
    if (typeof extension.id !== 'string' || extension.id.trim() === '') {
      return;
    }

    const container = document.querySelector<HTMLElement>(
      `[data-local-extension-container="${CSS.escape(extension.id)}"]`,
    );
    if (!container) {
      return;
    }

    disposeExtension(extension.id);
    container.replaceChildren();
    const dispose = extension.render(container, api);
    if (typeof dispose === 'function') {
      disposers.set(extension.id, dispose);
    }
  }

  const api = createDefaultLocalExtensionHostApi(registerExtension);

  async function loadExtensionAssets(list: LocalExtensionDescriptor[]): Promise<void> {
    await tick();
    for (const extension of list) {
      if (extension.style) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = extension.style;
        link.dataset.localExtensionId = extension.id;
        document.head.appendChild(link);
      }

      const script = document.createElement('script');
      script.src = extension.entry;
      script.async = true;
      script.dataset.localExtensionId = extension.id;
      document.body.appendChild(script);
    }
  }

  function unloadExtensionAssets(): void {
    for (const extension of extensions) {
      disposeExtension(extension.id);
    }
    document
      .querySelectorAll('[data-local-extension-id]')
      .forEach((node) => node.parentNode?.removeChild(node));
  }

  onMount(() => {
    let disposed = false;
    const uninstallApi = installLocalExtensionHostApi(window, api);

    // Public host boundary: this component only mounts generic same-origin
    // extension URLs from the local manifest. Extension implementations stay
    // behind the local endpoint and are never imported into the open frontend.
    void loadLocalExtensionManifest().then((manifest) => {
      if (!disposed) {
        extensions = manifest?.extensions ?? [];
        void loadExtensionAssets(extensions);
      }
    });

    return () => {
      disposed = true;
      unloadExtensionAssets();
      extensions = [];
      uninstallApi();
    };
  });
</script>

{#if extensions.length > 0}
  <aside class="local-extension-host" aria-label="Local extensions">
    {#each extensions as extension (extension.id)}
      <section class="local-extension-panel" data-local-extension-mount={extension.mount}>
        {#if extension.title}
          <div class="local-extension-title">{extension.title}</div>
        {/if}
        <div
          class="local-extension-content"
          data-local-extension-container={extension.id}
        ></div>
      </section>
    {/each}
  </aside>
{/if}

<style>
  .local-extension-host {
    position: fixed;
    right: 12px;
    bottom: 12px;
    z-index: 1250;
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: min(420px, calc(100vw - 24px));
    pointer-events: none;
  }

  .local-extension-panel {
    min-height: 240px;
    overflow: hidden;
    border: 1px solid var(--v2-border-panel, var(--panel-border));
    border-radius: 4px;
    background: var(--v2-bg-card, var(--panel));
    box-shadow: var(--v2-shadow-md, 0 12px 30px rgba(0, 0, 0, 0.35));
    pointer-events: auto;
  }

  .local-extension-title {
    padding: 6px 8px;
    border-bottom: 1px solid var(--v2-border-panel, var(--panel-border));
    color: var(--v2-text-secondary, var(--text-muted));
    font: 600 11px/1.2 var(--v2-font-mono, var(--font-mono));
    text-transform: uppercase;
  }

  .local-extension-content {
    display: block;
    width: 100%;
    min-height: 240px;
    background: transparent;
  }
</style>
