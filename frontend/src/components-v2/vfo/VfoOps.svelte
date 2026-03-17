<script lang="ts">
  import StatusBadge from '../controls/StatusBadge.svelte';
  import { hasDualReceiver, getVfoScheme } from '$lib/stores/capabilities.svelte';
  import { vfoSwapLabel, vfoCopyLabel, vfoEqualLabel, vfoTxLabel } from './vfo-ops-utils';

  interface Props {
    splitActive: boolean;
    txVfo: 'main' | 'sub';
    onSwap: () => void;
    onCopy: () => void;
    onEqual: () => void;
    onSplitToggle: () => void;
    onTxVfoChange: (v: string) => void;
  }

  let {
    splitActive,
    txVfo,
    onSwap,
    onCopy,
    onEqual,
    onSplitToggle,
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

<div class="vfo-ops">
  <StatusBadge label={swapLabel} active={false} color="muted" compact onclick={onSwap} />
  <StatusBadge label={copyLabel} active={false} color="muted" compact onclick={onCopy} />
  <StatusBadge label={equalLabel} active={false} color="muted" compact onclick={onEqual} />
  <StatusBadge
    label="SPLIT"
    active={splitActive}
    color="cyan"
    compact
    onclick={onSplitToggle}
  />
  {#if dualRx}
    <StatusBadge
      label={txMainLabel}
      active={txVfo === 'main'}
      color="orange"
      compact
      onclick={() => onTxVfoChange('main')}
    />
    <StatusBadge
      label={txSubLabel}
      active={txVfo === 'sub'}
      color="orange"
      compact
      onclick={() => onTxVfoChange('sub')}
    />
  {/if}
</div>

<style>
  .vfo-ops {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 4px;
    flex-wrap: wrap;
    font-family: 'Roboto Mono', monospace;
  }
</style>
