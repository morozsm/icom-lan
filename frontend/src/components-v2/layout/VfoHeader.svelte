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

  let dualReceiver = $derived(hasDualReceiver());
</script>

<div class="vfo-header" class:dual={dualReceiver}>
  <div class="vfo-main-panel">
    <VfoPanel
      {...mainVfo}
      onVfoClick={onMainVfoClick}
      onModeClick={onMainModeClick}
    />
  </div>

  <div class="vfo-bridge-panel">
    <VfoOps
      {splitActive}
      {txVfo}
      {onSwap}
      {onCopy}
      {onEqual}
      {onSplitToggle}
      {onTxVfoChange}
    />
  </div>

  {#if dualReceiver}
    <div class="vfo-sub-panel">
      <VfoPanel
        {...subVfo}
        onVfoClick={onSubVfoClick}
        onModeClick={onSubModeClick}
      />
    </div>
  {/if}
</div>

<style>
  .vfo-header {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'main'
      'bridge';
    gap: 4px;
    min-height: 0;
  }

  .vfo-header.dual {
    grid-template-columns: minmax(0, 1fr) 132px minmax(0, 1fr);
    grid-template-areas: 'main bridge sub';
    align-items: stretch;
  }

  .vfo-main-panel {
    grid-area: main;
    min-width: 0;
  }

  .vfo-bridge-panel {
    grid-area: bridge;
    min-width: 0;
    display: flex;
    align-items: stretch;
    justify-content: center;
    border: 1px solid #18222d;
    border-radius: 4px;
    background: linear-gradient(180deg, rgba(9, 14, 19, 0.96) 0%, rgba(6, 10, 15, 0.96) 100%);
  }

  .vfo-bridge-panel :global(.vfo-ops) {
    flex-direction: column;
    justify-content: center;
    width: 100%;
  }

  .vfo-sub-panel {
    grid-area: sub;
    min-width: 0;
  }

  @media (max-width: 1024px) {
    .vfo-header.dual {
      grid-template-columns: minmax(0, 1fr);
      grid-template-areas:
        'main'
        'bridge'
        'sub';
    }

    .vfo-bridge-panel :global(.vfo-ops) {
      flex-direction: row;
      flex-wrap: wrap;
    }
  }
</style>
