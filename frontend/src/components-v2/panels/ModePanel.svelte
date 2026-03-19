<script lang="ts">
  import '../controls/control-button.css';
  import { getShortcutHint } from '../layout/shortcut-hints';

  interface Props {
    currentMode: string;
    modes: string[];
    dataMode: number;
    hasDataMode: boolean;
    dataModeCount?: number;
    dataModeLabels?: Record<string, string>;
    onModeChange: (mode: string) => void;
    onDataModeChange: (mode: number) => void;
  }

  let {
    currentMode,
    modes,
    dataMode,
    hasDataMode,
    dataModeCount = 0,
    dataModeLabels = { '0': 'OFF', '1': 'D1', '2': 'D2', '3': 'D3' },
    onModeChange,
    onDataModeChange,
  }: Props = $props();

  const modeOrder = ['USB', 'LSB', 'CW', 'CW-R', 'RTTY', 'RTTY-R', 'PSK', 'PSK-R', 'AM', 'FM'];

  let orderedModes = $derived(modeOrder.filter((mode) => modes.includes(mode)));
  let extraModes = $derived(modes.filter((mode) => !modeOrder.includes(mode)));
  let visibleModes = $derived([...orderedModes, ...extraModes]);
  let dataOptions = $derived(
    Array.from({ length: Math.max(0, dataModeCount) + 1 }, (_, index) => ({
      value: index,
      label: dataModeLabels[String(index)] ?? (index === 0 ? 'OFF' : `D${index}`),
    })),
  );

  function modeShortcut(mode: string): string | null {
    return getShortcutHint('mode_select', (binding) => binding.params?.mode === mode);
  }

  const dataShortcut = getShortcutHint('cycle_data_mode');
</script>

<div class="panel-body" data-mode-panel="true" data-highlight={undefined}>
    <div class="mode-grid">
      {#each visibleModes as mode}
        <button
          type="button"
          class="mode-button v2-control-button"
          class:active={currentMode === mode}
          style="--control-accent:var(--v2-accent-cyan); --control-active-text:var(--v2-text-white)"
          data-mode={mode}
          data-shortcut-hint={modeShortcut(mode) ?? undefined}
          title={modeShortcut(mode) ?? undefined}
          onclick={() => onModeChange(mode)}
        >
          {mode}
        </button>
      {/each}
    </div>

    {#if hasDataMode && dataOptions.length > 1}
      <div class="section-label">DATA</div>
      <div class="data-grid">
        {#each dataOptions as option}
          <button
            type="button"
            class="data-button v2-control-button"
            class:active={dataMode === option.value}
            style="--control-accent:var(--v2-accent-cyan); --control-active-text:var(--v2-text-white)"
            data-data-mode={option.value}
            data-shortcut-hint={dataShortcut ?? undefined}
            title={dataShortcut ?? undefined}
            onclick={() => onDataModeChange(option.value)}
          >
            {option.label}
          </button>
        {/each}
      </div>
    {/if}
  </div>

<style>
  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 7px 8px;
  }

  .mode-grid,
  .data-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 4px;
  }

  .section-label {
    color: var(--v2-text-dim);
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .mode-button,
  .data-button {
    min-width: 0;
  }
  </style>