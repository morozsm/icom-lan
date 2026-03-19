<script lang="ts">
  import Slider from '../controls/Slider.svelte';
  import StatusBadge from '../controls/StatusBadge.svelte';
  import { formatOffset, shouldShowPanel } from './rit-utils';
  import { getShortcutHint } from '../layout/shortcut-hints';

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
    onRitOffsetChange,
    onXitOffsetChange,
    onClear,
  }: Props = $props();

  let visible = $derived(shouldShowPanel(hasRit, hasXit));
  let offsetValue = $derived(xitActive && !ritActive ? xitOffset : ritOffset);
  const ritShortcut = getShortcutHint('toggle_rit');
  const xitShortcut = getShortcutHint('toggle_xit');
  const clearShortcut = getShortcutHint('clear_rit_xit');

  function handleOffsetChange(value: number) {
    if (xitActive && !ritActive) {
      onXitOffsetChange(value);
      return;
    }
    onRitOffsetChange(value);
  }
</script>

{#if visible}
  <div class="panel">
    <div class="panel-header">RIT / XIT</div>
    <div class="panel-body">
      {#if hasRit}
        <div class="row">
          <StatusBadge label="RIT" active={ritActive} color="cyan" onclick={onRitToggle} shortcutHint={ritShortcut} title={ritShortcut} />
          <span class="offset" class:active={ritActive}>{formatOffset(ritOffset)}</span>
        </div>
      {/if}
      {#if hasXit}
        <div class="row">
          <StatusBadge label="XIT" active={xitActive} color="orange" onclick={onXitToggle} shortcutHint={xitShortcut} title={xitShortcut} />
          <span class="offset" class:active={xitActive}>{formatOffset(xitOffset)}</span>
        </div>
      {/if}
      <Slider
        label="Offset"
        value={offsetValue}
        min={-9999}
        max={9999}
        step={50}
        unit="Hz"
        accentColor="#00D4FF"
        onchange={handleOffsetChange}
      />
      <div class="clear-row">
        <StatusBadge label="CLEAR" active={false} color="muted" onclick={onClear} shortcutHint={clearShortcut} title={clearShortcut} />
      </div>
    </div>
  </div>
{/if}

<style>
  .panel {
    background: #060A10;
    border: 1px solid #18202A;
    border-radius: 4px;
    overflow: hidden;
  }

  .panel-header {
    padding: 5px 8px;
    color: #8CA0B8;
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    border-bottom: 1px solid #18202A;
  }

  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 7px 8px;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .offset {
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
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
