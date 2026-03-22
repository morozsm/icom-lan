<script lang="ts">
  import { ValueControl } from '../controls/value-control';
  import { FillButton, HardwarePlainButton } from '../../lib/Button';
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
    <div class="panel-body">
      {#if hasRit}
        <div class="row">
          <FillButton active={ritActive} color="cyan" onclick={onRitToggle} shortcutHint={ritShortcut} title={ritShortcut}>RIT</FillButton>
          <span class="offset" class:active={ritActive}>{formatOffset(ritOffset)}</span>
        </div>
      {/if}
      {#if hasXit}
        <div class="row">
          <FillButton active={xitActive} color="orange" onclick={onXitToggle} shortcutHint={xitShortcut} title={xitShortcut}>XIT</FillButton>
          <span class="offset" class:active={xitActive}>{formatOffset(xitOffset)}</span>
        </div>
      {/if}
      <ValueControl
        label="Offset"
        value={offsetValue}
        min={-9999}
        max={9999}
        step={50}
        unit="Hz"
        renderer="bipolar"
        accentColor="var(--v2-accent-cyan)"
        onChange={handleOffsetChange}
      variant="hardware-illuminated"
      />
      <div class="clear-row">
        <!-- action-button: momentary command, no sustained state -->
        <HardwarePlainButton onclick={onClear} title={clearShortcut} shortcutHint={clearShortcut}>CLEAR</HardwarePlainButton>
      </div>
    </div>
{/if}

<style>
  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px 8px;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .offset {
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    color: var(--v2-text-disabled);
    transition: color 150ms ease;
  }

  .offset.active {
    color: var(--v2-text-light);
  }

  .clear-row {
    display: flex;
    justify-content: flex-end;
    padding-top: 2px;
  }

</style>
