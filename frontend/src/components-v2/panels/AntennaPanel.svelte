<script lang="ts">
  import { HardwareButton } from '$lib/Button';

  interface Props {
    txAntenna: number;
    rxAnt1: boolean;
    rxAnt2: boolean;
    antennaCount: number;
    hasRxAntenna: boolean;
    onSelectAnt1: () => void;
    onSelectAnt2: () => void;
    onToggleRxAnt1: () => void;
    onToggleRxAnt2: () => void;
  }

  let {
    txAntenna,
    rxAnt1,
    rxAnt2,
    antennaCount,
    hasRxAntenna,
    onSelectAnt1,
    onSelectAnt2,
    onToggleRxAnt1,
    onToggleRxAnt2,
  }: Props = $props();
</script>

{#if antennaCount > 1}
  <div class="controls">
    <div class="control-row">
      <span class="control-label">TX</span>
      <div class="button-group">
        <HardwareButton
          active={txAntenna === 1}
          indicator="edge-left"
          color="cyan"
          onclick={onSelectAnt1}
        >
          ANT1
        </HardwareButton>
        <HardwareButton
          active={txAntenna === 2}
          indicator="edge-left"
          color="cyan"
          onclick={onSelectAnt2}
        >
          ANT2
        </HardwareButton>
      </div>
    </div>

    {#if hasRxAntenna}
      <div class="control-row">
        <span class="control-label">RX</span>
        <div class="button-group">
          <HardwareButton
            active={rxAnt1}
            indicator="edge-left"
            color="green"
            onclick={onToggleRxAnt1}
          >
            RX ANT1
          </HardwareButton>
          <HardwareButton
            active={rxAnt2}
            indicator="edge-left"
            color="green"
            onclick={onToggleRxAnt2}
          >
            RX ANT2
          </HardwareButton>
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .controls {
    padding: 8px 10px 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .control-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;
  }

  .control-label {
    color: var(--v2-text-dim);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    flex-shrink: 0;
    min-width: 34px;
  }

  .button-group {
    display: flex;
    gap: 4px;
    flex: 1 1 auto;
    min-width: 0;
  }

  .button-group > :global(button) {
    flex: 1 1 0;
    min-width: 0;
  }
</style>
