<script lang="ts">
  import VfoPanel from '../vfo/VfoPanel.svelte';
  import VfoOps from '../vfo/VfoOps.svelte';
  import { hasDualReceiver } from '$lib/stores/capabilities.svelte';
  import { formatFrequency } from '../display/frequency-format';
  import type { VfoLayoutProfile } from './vfo-layout-tokens';
  import type { VfoStateProps } from './layout-utils';

  interface Props {
    mainVfo: VfoStateProps;
    subVfo: VfoStateProps;
    layoutProfile?: VfoLayoutProfile;
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
    layoutProfile = 'baseline',
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

  function formatBridgeFrequency(freq: number): string {
    const { mhz, khz } = formatFrequency(freq);
    return `${mhz}.${khz}`;
  }

  let rxFrequency = $derived(formatBridgeFrequency(txVfo === 'main' ? subVfo.freq : mainVfo.freq));
  let txFrequency = $derived(formatBridgeFrequency(txVfo === 'main' ? mainVfo.freq : subVfo.freq));
</script>

<div class="vfo-header" class:dual={dualReceiver}>
  <div class="vfo-main-panel">
    <VfoPanel
      {...mainVfo}
      {layoutProfile}
      onVfoClick={onMainVfoClick}
      onModeClick={onMainModeClick}
    />
  </div>

  <div class="vfo-bridge-panel">
    <div class="vfo-bridge-stack">
      <VfoOps
        {splitActive}
        {txVfo}
        {onSwap}
        {onCopy}
        {onEqual}
        {onSplitToggle}
        {onTxVfoChange}
      />

      {#if dualReceiver}
        <div class:inactive={!splitActive} class="split-status">
          <span class="split-status-title">SPLIT</span>
          <span class="split-status-row">RX {rxFrequency} TX {txFrequency}</span>
        </div>
      {/if}
    </div>
  </div>

  {#if dualReceiver}
    <div class="vfo-sub-panel">
      <VfoPanel
        {...subVfo}
        {layoutProfile}
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
    grid-template-columns: minmax(0, 1fr) var(--vfo-bridge-width, 132px) minmax(0, 1fr);
    grid-template-areas: 'main bridge sub';
    align-items: stretch;
  }

  .vfo-main-panel {
    grid-area: main;
    min-width: 0;
  }

  .vfo-bridge-panel {
    grid-area: bridge;
    min-width: var(--vfo-bridge-width, 132px);
    display: flex;
    align-items: stretch;
    justify-content: center;
    border: 1px solid var(--v2-border-panel);
    border-radius: 4px;
    background: linear-gradient(180deg, var(--v2-vfo-header-gradient-top) 0%, var(--v2-vfo-header-gradient-bottom) 100%);
    padding: 0 var(--vfo-bridge-pad-x, 4px);
    box-sizing: border-box;
  }

  .vfo-bridge-stack {
    display: flex;
    flex: 1;
    min-height: 0;
    flex-direction: column;
    justify-content: space-between;
    align-items: stretch;
    padding:
      var(--vfo-badge-inset-y, 3px)
      0;
    box-sizing: border-box;
  }

  .vfo-bridge-panel :global(.vfo-ops) {
    flex-direction: column;
    justify-content: center;
    width: 100%;
  }

  .split-status {
    display: flex;
    flex-direction: column;
    gap: 3px;
    margin-top: auto;
    padding:
      var(--vfo-ops-secondary-padding-top, 4px)
      0
      0;
    border-top: 1px solid var(--v2-vfo-header-border);
    font-family: 'Roboto Mono', monospace;
    text-transform: uppercase;
    align-items: center;
  }

  .split-status.inactive {
    opacity: 0.64;
  }

  .split-status-title {
    color: var(--v2-text-muted);
    font-size: 7px;
    font-weight: 700;
    letter-spacing: 0.1em;
  }

  .split-status-row {
    color: var(--v2-text-secondary);
    font-size: 7px;
    font-weight: 700;
    letter-spacing: 0.08em;
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

    .split-status {
      align-items: flex-start;
    }
  }
</style>
