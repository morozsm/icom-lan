<script lang="ts">
  import '../controls/control-button.css';
  import { hasDualReceiver, getVfoScheme } from '$lib/stores/capabilities.svelte';
  import { vfoSwapLabel, vfoCopyLabel, vfoEqualLabel, vfoTxLabel } from './vfo-ops-utils';

  interface Props {
    splitActive: boolean;
    dualWatchActive: boolean;
    txVfo: 'main' | 'sub';
    onSwap: () => void;
    onCopy: () => void;
    onEqual: () => void;
    onSplitToggle: () => void;
    onDualWatchToggle: () => void;
    onTxVfoChange: (v: string) => void;
  }

  let {
    splitActive,
    dualWatchActive,
    txVfo,
    onSwap,
    onCopy,
    onEqual,
    onSplitToggle,
    onDualWatchToggle,
    onTxVfoChange,
  }: Props = $props();

  let scheme = $derived(getVfoScheme());
  let swapLabel = $derived(vfoSwapLabel(scheme));
  let copyLabel = $derived(vfoCopyLabel(scheme));
  let equalLabel = $derived(vfoEqualLabel(scheme));
  let txMainLabel = $derived(vfoTxLabel(scheme, 'main'));
  let txSubLabel = $derived(vfoTxLabel(scheme, 'sub'));
  let dualRx = $derived(hasDualReceiver());
</script>

<div class:dual={dualRx} class="vfo-ops">
  <button type="button" class="bridge-button v2-control-button" data-active="false" data-color="muted" onclick={onCopy}>{copyLabel}</button>
  <button
    type="button"
    class="bridge-button v2-control-button"
    data-active={splitActive}
    data-color="cyan"
    onclick={onSplitToggle}
  >SPLIT</button>
  {#if dualRx}
    <button
      type="button"
      class="bridge-button v2-control-button"
      data-active={dualWatchActive}
      data-color="green"
      onclick={() => onDualWatchToggle(!dualWatchActive)}
    >DW</button>
  {/if}
  <button type="button" class="bridge-button v2-control-button" data-active="false" data-color="muted" onclick={onEqual}>{equalLabel}</button>
  {#if dualRx}
    <button
      type="button"
      class="bridge-button v2-control-button"
      data-active={txVfo === 'main'}
      data-color="orange"
      onclick={() => onTxVfoChange('main')}
    >{txMainLabel}</button>
    <button
      type="button"
      class="bridge-button v2-control-button"
      data-active={txVfo === 'sub'}
      data-color="orange"
      onclick={() => onTxVfoChange('sub')}
    >{txSubLabel}</button>
  {/if}
  <button type="button" class="bridge-button v2-control-button" data-active="false" data-color="muted" onclick={onSwap}>{swapLabel}</button>
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

  .bridge-button[data-color='orange'] {
    --control-accent: var(--v2-accent-orange-alt);
    --control-active-text: var(--v2-text-bright);
  }

  .vfo-ops:not(.dual) {
    grid-auto-flow: row;
  }

  /* Dual-rx layout: COPY | SPLIT | DW | = | TX-M | TX-S | SWAP
     Row 1: COPY, SPLIT
     Row 2: DW, =
     Row 3: TX-M, TX-S
     Row 4: SWAP (span 2) */
  .vfo-ops.dual .bridge-button:nth-child(1) { grid-column: 1; grid-row: 1; }  /* COPY */
  .vfo-ops.dual .bridge-button:nth-child(2) { grid-column: 2; grid-row: 1; }  /* SPLIT */
  .vfo-ops.dual .bridge-button:nth-child(3) { grid-column: 1; grid-row: 2; }  /* DW */
  .vfo-ops.dual .bridge-button:nth-child(4) { grid-column: 2; grid-row: 2; }  /* = */
  .vfo-ops.dual .bridge-button:nth-child(5) { grid-column: 1; grid-row: 3; }  /* TX-M */
  .vfo-ops.dual .bridge-button:nth-child(6) { grid-column: 2; grid-row: 3; }  /* TX-S */
  .vfo-ops.dual .bridge-button:nth-child(7) { grid-column: 1 / -1; grid-row: 4; }  /* SWAP */
</style>
