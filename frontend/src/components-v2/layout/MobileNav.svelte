<script lang="ts">
  import { TABS, DEFAULT_TAB, getVisibleTabs, type TabId } from './mobile-nav-utils';
  import { hasTx } from '$lib/stores/capabilities.svelte';

  let activeTab: TabId = $state(DEFAULT_TAB);

  let visibleTabs = $derived(getVisibleTabs({ hasTx: hasTx() }));
</script>

<nav class="mobile-nav" role="tablist" aria-label="Radio navigation">
  {#each visibleTabs as tab (tab.id)}
    <button
      role="tab"
      aria-selected={activeTab === tab.id}
      class="nav-tab"
      class:active={activeTab === tab.id}
      onclick={() => { activeTab = tab.id; }}
    >
      <span class="tab-icon" aria-hidden="true">{tab.icon}</span>
      <span class="tab-label">{tab.label}</span>
    </button>
  {/each}
</nav>

<style>
  .mobile-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    align-items: stretch;
    height: 56px;
    background: var(--v2-bg-card, #060A10);
    border-top: 1px solid var(--v2-border, #18202A);
    z-index: 100;
  }

  .nav-tab {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--v2-text-muted, #4D6074);
    cursor: pointer;
    padding: 0;
    font-family: var(--v2-font-mono, 'Roboto Mono', monospace);
    transition: color 0.15s, border-color 0.15s;
  }

  .nav-tab:hover {
    color: var(--v2-text-secondary, #8DA2B8);
  }

  .nav-tab.active {
    color: var(--v2-accent-cyan, #00D4FF);
    border-bottom-color: var(--v2-accent-cyan, #00D4FF);
  }

  .tab-icon {
    font-size: 16px;
    line-height: 1;
  }

  .tab-label {
    font-size: var(--v2-font-size-sm, 9px);
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }
</style>
