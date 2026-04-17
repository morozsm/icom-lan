<script lang="ts">
  import '../controls/control-button.css';
  import { hasDualReceiver, getVfoScheme } from '$lib/stores/capabilities.svelte';
  import { vfoSwapLabel, vfoCopyLabel, vfoTxLabel } from './vfo-ops-utils';
  import { withDoubleClick } from '../wiring/double-click';

  interface Props {
    splitActive: boolean;
    dualWatchActive: boolean;
    /** Read-only indicator: which receiver transmits right now.
     *  Derived from split flag — see `toVfoOpsProps`. */
    txVfo: 'main' | 'sub';
    onSwap: () => void;
    /** Equalize MAIN→SUB (copy). Backend sends `0x07 0xB1`. */
    onEqual: () => void;
    /** Toggle SPLIT on/off. Double-click = Quick Split (equalize + ON). */
    onSplitToggle: () => void;
    onQuickSplit: () => void;
    /** Toggle Dual Watch on/off. Double-click = Quick DW (equalize + ON). */
    onDualWatchToggle: () => void;
    onQuickDw: () => void;
  }

  let {
    splitActive,
    dualWatchActive,
    txVfo,
    onSwap,
    onEqual,
    onSplitToggle,
    onQuickSplit,
    onDualWatchToggle,
    onQuickDw,
  }: Props = $props();

  let scheme = $derived(getVfoScheme());
  let swapLabel = $derived(vfoSwapLabel(scheme));
  let copyLabel = $derived(vfoCopyLabel(scheme));
  let txBadgeLabel = $derived(vfoTxLabel(scheme, txVfo));
  let dualRx = $derived(hasDualReceiver());

  // Double-click wiring: short tap = toggle, double tap = Quick action.
  // The inner handlers are rebuilt on each prop change so that stale
  // closures don't point at the previous handler identity.
  let dwClick = $derived(withDoubleClick(onDualWatchToggle, onQuickDw));
  let splitClick = $derived(withDoubleClick(onSplitToggle, onQuickSplit));
</script>

<div class:dual={dualRx} class="vfo-ops">
  <button
    type="button"
    class="bridge-button v2-control-button"
    data-active="false"
    data-color="muted"
    onclick={onEqual}
    title="Equalize — copy MAIN to SUB"
  >{copyLabel}</button>
  <button
    type="button"
    class="bridge-button v2-control-button"
    data-active={splitActive}
    data-color="cyan"
    onclick={splitClick}
    title="SPLIT — single click toggles, double click = Quick Split (equalize + ON)"
  >SPLIT</button>
  {#if dualRx}
    <button
      type="button"
      class="bridge-button v2-control-button"
      data-active={dualWatchActive}
      data-color="green"
      onclick={dwClick}
      title="DUAL WATCH — single click toggles, double click = Quick DW (equalize + ON)"
    >DW</button>
  {/if}
  <button
    type="button"
    class="bridge-button v2-control-button"
    data-active="false"
    data-color="muted"
    onclick={onSwap}
    title="Exchange — swap MAIN and SUB"
  >{swapLabel}</button>
  {#if dualRx}
    <!-- Read-only TX indicator; derives from split flag via state adapter. -->
    <div
      class="tx-indicator"
      data-testid="tx-indicator"
      data-tx={txVfo}
      aria-live="polite"
      title="Transmit receiver (read-only; follows SPLIT flag)"
    >{txBadgeLabel}</div>
  {/if}
</div>

<style>
  .vfo-ops {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: center;
    justify-items: stretch;
    gap: var(--vfo-ops-gap, 4px);
    padding: var(--vfo-ops-padding-y, 4px) 0;
    font-family: 'Roboto Mono', monospace;
  }

  .bridge-button {
    width: 100%;
    min-width: var(--vfo-ops-badge-width, 56px);
    min-height: var(--vfo-ops-badge-height, 18px);
    padding: 4px var(--vfo-ops-badge-padding-x, 6px);
    border-radius: var(--vfo-ops-badge-radius, 4px);
    font-size: var(--vfo-ops-badge-font-size, 10px);
    box-sizing: border-box;
  }

  .bridge-button[data-color='cyan'] {
    --control-accent: var(--v2-accent-cyan);
    --control-active-text: var(--v2-text-bright);
  }

  .bridge-button[data-color='green'] {
    --control-accent: var(--v2-accent-green-bright);
    --control-active-text: var(--v2-text-bright);
  }

  .tx-indicator {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: var(--vfo-ops-badge-height, 18px);
    padding: 4px var(--vfo-ops-badge-padding-x, 6px);
    border-radius: var(--vfo-ops-badge-radius, 4px);
    font-size: var(--vfo-ops-badge-font-size, 10px);
    font-weight: 600;
    color: var(--v2-accent-orange-alt, #ffa500);
    background: var(--v2-surface-muted, rgba(255, 255, 255, 0.04));
    border: 1px solid var(--v2-border-muted, rgba(255, 255, 255, 0.08));
    user-select: none;
    cursor: default;
  }

  .vfo-ops:not(.dual) {
    grid-auto-flow: row;
  }

  /* Dual-rx layout:
     Row 1: COPY   | SPLIT
     Row 2: DW     | SWAP
     Row 3: TX-indicator (span 2) */
  .vfo-ops.dual .bridge-button:nth-child(1) { grid-column: 1; grid-row: 1; }  /* COPY  (M→S) */
  .vfo-ops.dual .bridge-button:nth-child(2) { grid-column: 2; grid-row: 1; }  /* SPLIT */
  .vfo-ops.dual .bridge-button:nth-child(3) { grid-column: 1; grid-row: 2; }  /* DW */
  .vfo-ops.dual .bridge-button:nth-child(4) { grid-column: 2; grid-row: 2; }  /* SWAP (M↔S) */
  .vfo-ops.dual .tx-indicator { grid-row: 3; }
</style>
