<script lang="ts">
  import VfoPanel from '../vfo/VfoPanel.svelte';
  import VfoOps from '../vfo/VfoOps.svelte';
  import { hasDualReceiver } from '$lib/stores/capabilities.svelte';
  import type { VfoStateProps } from './layout-utils';

  interface Props {
    mainVfo: VfoStateProps;
    subVfo: VfoStateProps;
    splitActive: boolean;
    txVfo: 'main' | 'sub';
    onSwap?: () => void;
    onCopy?: () => void;
    onEqual?: () => void;
    onSplitToggle?: () => void;
    onTxVfoChange?: (v: string) => void;
    onMainVfoClick?: () => void;
    onSubVfoClick?: () => void;
    onMainModeClick?: () => void;
    onSubModeClick?: () => void;
  }

  let {
    mainVfo,
    subVfo,
    splitActive,
    txVfo,
    onSwap = () => {},
    onCopy = () => {},
    onEqual = () => {},
    onSplitToggle = () => {},
    onTxVfoChange = () => {},
    onMainVfoClick,
    onSubVfoClick,
    onMainModeClick,
    onSubModeClick,
  }: Props = $props();
</script>

<div class="vfo-header">
  <VfoPanel
    {...mainVfo}
    onVfoClick={onMainVfoClick}
    onModeClick={onMainModeClick}
  />

  <VfoOps
    {splitActive}
    {txVfo}
    {onSwap}
    {onCopy}
    {onEqual}
    {onSplitToggle}
    {onTxVfoChange}
  />

  {#if hasDualReceiver()}
    <VfoPanel
      {...subVfo}
      onVfoClick={onSubVfoClick}
      onModeClick={onSubModeClick}
    />
  {/if}
</div>

<style>
  .vfo-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
</style>
