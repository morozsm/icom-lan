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
  let contentElement = $state<HTMLDivElement | null>(null);
  let contentHeight = $state<number>(0);

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

    // Measure content height for smooth animation
    if (contentElement) {
      contentHeight = contentElement.scrollHeight;
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
    bind:this={contentElement}
    style:max-height={collapsed ? '0' : `${contentHeight || 2000}px`}
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
    background: #060a10;
    border: 1px solid #18202a;
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
    background: #1a1a2e;
    border: none;
    border-bottom: 1px solid #18202a;
    color: #e0e0e0;
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
    background: #222238;
  }

  .chevron {
    display: inline-block;
    color: #888;
    font-size: 10px;
    line-height: 1;
    transition: color 0.15s ease;
    user-select: none;
  }

  .panel-header.collapsible:hover .chevron {
    color: #00d4ff;
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
