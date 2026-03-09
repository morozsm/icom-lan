<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    title: string;
    collapsible?: boolean;
    collapsed?: boolean;
    children?: Snippet;
  }

  let { title, collapsible = false, collapsed = $bindable(false), children }: Props = $props();

  function toggle() {
    if (collapsible) collapsed = !collapsed;
  }
</script>

<div class="control-group">
  {#if collapsible}
    <button class="group-header clickable" onclick={toggle}>
      <span class="group-title">{title}</span>
      <span class="collapse-icon">{collapsed ? '▸' : '▾'}</span>
    </button>
  {:else}
    <div class="group-header">
      <span class="group-title">{title}</span>
    </div>
  {/if}
  {#if !collapsed}
    <div class="group-content">
      {@render children?.()}
    </div>
  {/if}
</div>

<style>
  .control-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    padding: var(--space-2);
    background: var(--panel);
  }

  .group-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    user-select: none;
  }

  button.group-header {
    background: none;
    border: none;
    padding: 0;
    width: 100%;
    cursor: pointer;
  }

  button.group-header:hover .group-title {
    color: var(--accent);
  }

  .group-title {
    font-family: var(--font-mono);
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    transition: color 0.2s;
  }

  .collapse-icon {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .group-content {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    align-items: center;
  }
</style>
