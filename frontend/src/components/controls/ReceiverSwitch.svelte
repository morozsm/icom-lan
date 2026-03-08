<script lang="ts">
  interface Props {
    active: 'MAIN' | 'SUB';
    dualWatch?: boolean;
    hasDualReceiver?: boolean;
    onswitch?: (receiver: 'MAIN' | 'SUB') => void;
    ondwtoggle?: () => void;
  }

  let { active, dualWatch = false, hasDualReceiver = false, onswitch, ondwtoggle }: Props = $props();
</script>

<div class="receiver-switch">
  <button
    class="rx-btn"
    class:active={active === 'MAIN'}
    onclick={() => onswitch?.('MAIN')}
    aria-pressed={active === 'MAIN'}
  >
    MAIN
  </button>

  {#if hasDualReceiver}
    <button
      class="rx-btn"
      class:active={active === 'SUB'}
      onclick={() => onswitch?.('SUB')}
      aria-pressed={active === 'SUB'}
    >
      SUB
    </button>
  {/if}

  {#if dualWatch}
    <button class="dw-badge" onclick={() => ondwtoggle?.()} title="Dual Watch active — click to toggle">DW</button>
  {/if}
</div>

<style>
  .receiver-switch {
    display: flex;
    align-items: center;
    gap: var(--space-1);
  }

  .rx-btn {
    padding: var(--space-1) var(--space-3);
    min-height: 32px;
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    cursor: pointer;
    transition: all 0.15s;
  }

  .rx-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
  }

  .rx-btn.active {
    background: rgba(77, 182, 255, 0.15);
    border-color: var(--accent);
    color: var(--accent);
  }

  .dw-badge {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--warning);
    padding: 2px 6px;
    border: 1px solid var(--warning);
    border-radius: 4px;
    background: rgba(210, 153, 34, 0.1);
  }
</style>
