<script lang="ts">
  import '../controls/control-button.css';

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
</script>

<div class="panel" data-mode-panel="true" data-highlight={undefined}>
  <div class="panel-header">MODE</div>
  <div class="panel-body">
    <div class="mode-grid">
      {#each visibleModes as mode}
        <button
          type="button"
          class="mode-button v2-control-button"
          class:active={currentMode === mode}
          style="--control-accent:#00D4FF; --control-active-text:#FFFFFF"
          data-mode={mode}
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
            style="--control-accent:#00D4FF; --control-active-text:#FFFFFF"
            data-data-mode={option.value}
            onclick={() => onDataModeChange(option.value)}
          >
            {option.label}
          </button>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .panel {
    background: #060A10;
    border: 1px solid #18202A;
    border-radius: 4px;
    overflow: hidden;
    transition: box-shadow 180ms ease, border-color 180ms ease;
  }

  .panel[data-highlight='true'] {
    border-color: #00D4FF;
    box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.18);
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

  .mode-grid,
  .data-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 4px;
  }

  .section-label {
    color: #6F8196;
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