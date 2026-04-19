<script lang="ts">
  // Horizontal chip-scroll navigation for mobile IA.
  // Renders a row of section chips; one is active at a time.
  interface Chip {
    id: string;
    label: string;
  }

  interface Props {
    chips: Chip[];
    active: string;
    onSelect: (id: string) => void;
  }

  let { chips, active, onSelect }: Props = $props();
</script>

<nav class="m-chip-bar" aria-label="Mobile sections">
  {#each chips as chip}
    <button
      type="button"
      class="m-chip"
      class:m-chip-active={chip.id === active}
      aria-pressed={chip.id === active}
      onclick={() => onSelect(chip.id)}
    >
      {chip.label}
    </button>
  {/each}
</nav>

<style>
  .m-chip-bar {
    display: flex;
    gap: 6px;
    padding: 6px 8px;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
    background: var(--v2-bg-darker, #0a0a14);
    border-bottom: 1px solid var(--v2-border-darker, #1a1a2e);
    flex-shrink: 0;
  }

  .m-chip-bar::-webkit-scrollbar {
    display: none;
  }

  .m-chip {
    flex: 0 0 auto;
    min-height: 32px;
    padding: 4px 14px;
    border-radius: 16px;
    border: 1px solid var(--v2-border-panel, #333);
    background: var(--v2-bg-input, #1a1a2e);
    color: var(--v2-text-muted, #888);
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
    white-space: nowrap;
  }

  .m-chip:active {
    background: var(--v2-bg-card, #222);
  }

  .m-chip-active {
    background: rgba(34, 211, 238, 0.12);
    border-color: var(--v2-accent-cyan, #22d3ee);
    color: var(--v2-accent-cyan, #22d3ee);
  }
</style>
