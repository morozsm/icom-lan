<script lang="ts">
  interface Props {
    title: string;
    values: number[];
    current: number;
    labels?: (v: number) => string;
    onSelect: (v: number) => void;
    onClose: () => void;
  }

  let { title, values, current, labels, onSelect, onClose }: Props = $props();
</script>

<div class="backdrop" onclick={onClose} role="presentation"></div>
<div class="menu" role="dialog" aria-label={title}>
  <div class="menu-title">{title}</div>
  <div class="grid">
    {#each values as v}
      <button
        class="item"
        class:active={v === current}
        onclick={() => { onSelect(v); onClose(); }}
      >
        {labels ? labels(v) : String(v)}
      </button>
    {/each}
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: rgba(0, 0, 0, 0.5);
  }

  .menu {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 101;
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    padding: var(--space-3);
    min-width: 160px;
  }

  .menu-title {
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    color: var(--text-muted);
    margin-bottom: var(--space-2);
    text-align: center;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-2);
  }

  @media (max-width: 480px) {
    .grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  .item {
    min-height: 44px;
    padding: 0 var(--space-2);
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    cursor: pointer;
    transition: border-color 0.1s, color 0.1s, background 0.1s;
  }

  .item:hover {
    border-color: var(--accent);
  }

  .item.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
  }
</style>
