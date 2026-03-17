<script lang="ts">
  import StatusBadge from '../controls/StatusBadge.svelte';
  import { formatOffset, shouldShowPanel } from './rit-utils';

  interface Props {
    ritActive: boolean;
    ritOffset: number;
    xitActive: boolean;
    xitOffset: number;
    hasRit: boolean;
    hasXit: boolean;
    onRitToggle: () => void;
    onXitToggle: () => void;
    onRitOffsetChange: (v: number) => void;
    onXitOffsetChange: (v: number) => void;
    onClear: () => void;
  }

  let {
    ritActive,
    ritOffset,
    xitActive,
    xitOffset,
    hasRit,
    hasXit,
    onRitToggle,
    onXitToggle,
    onClear,
  }: Props = $props();

  let visible = $derived(shouldShowPanel(hasRit, hasXit));
</script>

{#if visible}
  <div class="panel">
    <div class="panel-header">RIT / XIT</div>
    <div class="panel-body">
      {#if hasRit}
        <div class="row">
          <StatusBadge label="RIT" active={ritActive} color="cyan" onclick={onRitToggle} />
          <span class="offset" class:active={ritActive}>{formatOffset(ritOffset)}</span>
        </div>
      {/if}
      {#if hasXit}
        <div class="row">
          <StatusBadge label="XIT" active={xitActive} color="orange" onclick={onXitToggle} />
          <span class="offset" class:active={xitActive}>{formatOffset(xitOffset)}</span>
        </div>
      {/if}
      <div class="clear-row">
        <StatusBadge label="CLEAR" active={false} color="muted" onclick={onClear} />
      </div>
    </div>
  </div>
{/if}

<style>
  .panel {
    background: #060A10;
    border: 1px solid #18202A;
    border-radius: 10px;
    overflow: hidden;
  }

  .panel-header {
    padding: 6px 10px;
    color: #8CA0B8;
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    border-bottom: 1px solid #18202A;
  }

  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .offset {
    font-family: 'Roboto Mono', monospace;
    font-size: 12px;
    color: #4D6074;
    transition: color 150ms ease;
  }

  .offset.active {
    color: #E0EAF4;
  }

  .clear-row {
    display: flex;
    justify-content: flex-end;
    padding-top: 2px;
  }
</style>
