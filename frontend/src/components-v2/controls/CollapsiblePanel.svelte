<script lang="ts">
  import { onMount } from 'svelte';

  interface Props {
    title: string;
    panelId: string;
    collapsible?: boolean;
    children?: any;
  }

  let { title, panelId, collapsible = true, children }: Props = $props();

  let collapsed = $state(false);

  const STORAGE_KEY = 'icom-lan:panel-collapsed';

  // Load collapsed state from localStorage
  onMount(() => {
    if (!collapsible) {
      return;
    }

    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const data = JSON.parse(stored);
        collapsed = data[panelId] === true;
      }
    } catch (e) {
      // Ignore parsing errors
    }
  });

  function toggle() {
    if (!collapsible) {
      return;
    }

    collapsed = !collapsed;

    // Save to localStorage
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      const data = stored ? JSON.parse(stored) : {};
      data[panelId] = collapsed;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (e) {
      // Ignore storage errors
    }
  }
</script>

<div class="collapsible-panel" data-panel-id={panelId} data-collapsed={collapsed}>
  <button
    type="button"
    class="panel-header"
    class:collapsible
    aria-expanded={!collapsed}
    onclick={toggle}
    disabled={!collapsible}
  >
    {#if collapsible}
      <span class="chevron" aria-hidden="true">{collapsed ? '▸' : '▾'}</span>
    {/if}
    <span class="title">{title}</span>
  </button>

  <div
    class="panel-content"
    class:collapsed
    style:max-height={collapsed ? '0' : '2000px'}
  >
    <div class="panel-content-inner">
      {@render children?.()}
    </div>
  </div>
</div>

<style>
  .collapsible-panel {
    display: flex;
    flex-direction: column;
    background: var(--v2-collapsible-bg);
    border: 1px solid var(--v2-collapsible-border);
    border-radius: 4px;
    overflow: hidden;
    font-family: 'Roboto Mono', monospace;
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 5px 8px;
    background: var(--v2-collapsible-header-bg);
    border: none;
    border-bottom: 1px solid var(--v2-collapsible-border);
    color: var(--v2-collapsible-header-text);
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    text-align: left;
    cursor: default;
    transition: background 0.15s ease;
  }

  .panel-header.collapsible {
    cursor: pointer;
  }

  .panel-header.collapsible:hover {
    background: var(--v2-collapsible-header-hover-bg);
  }

  .chevron {
    display: inline-block;
    color: var(--v2-collapsible-chevron);
    font-size: 10px;
    line-height: 1;
    transition: color 0.15s ease;
    user-select: none;
  }

  .panel-header.collapsible:hover .chevron {
    color: var(--v2-collapsible-chevron-hover);
  }

  .title {
    flex: 1;
  }

  .panel-content {
    overflow: hidden;
    transition: max-height 0.2s ease;
  }

  .panel-content.collapsed {
    max-height: 0 !important;
  }

  .panel-content-inner {
    /* Content wrapper for proper spacing */
  }
</style>
