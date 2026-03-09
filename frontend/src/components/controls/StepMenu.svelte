<script lang="ts">
  import { TUNING_STEPS, formatStep } from '../../lib/stores/tuning.svelte';

  interface Props {
    onSelect: (step: number) => void;
    onClose: () => void;
  }

  let { onSelect, onClose }: Props = $props();
</script>

<div class="backdrop" onclick={onClose} role="presentation"></div>
<div class="menu" role="dialog" aria-label="Select tuning step">
  <div class="menu-title">TUNING STEP</div>
  <div class="grid">
    {#each TUNING_STEPS as step}
      <button class="item" onclick={() => { onSelect(step); onClose(); }}>
        {formatStep(step)}
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
    min-width: 200px;
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
    transition: border-color 0.1s, color 0.1s;
  }

  .item:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
</style>
