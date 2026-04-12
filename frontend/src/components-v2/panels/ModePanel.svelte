<script lang="ts">
  import { HardwareButton } from '$lib/Button';
  import { getShortcutHint } from '../layout/shortcut-hints';
  import { deriveModeProps, getModeHandlers } from '$lib/runtime/adapters/panel-adapters';

  const handlers = getModeHandlers();
  let p = $derived(deriveModeProps());

  // Destructure for template readability
  let currentMode = $derived(p.currentMode);
  let modes = $derived(p.modes);
  let dataMode = $derived(p.dataMode);
  let hasDataMode = $derived(p.hasDataMode);
  let dataModeCount = $derived(p.dataModeCount ?? 0);
  let dataModeLabels = $derived(p.dataModeLabels ?? { '0': 'OFF', '1': 'D1', '2': 'D2', '3': 'D3' });
  const onModeChange = handlers.onModeChange;
  const onDataModeChange = handlers.onDataModeChange;

  // Canonical display order — covers both IC-7610 and Yaesu naming conventions.
  const modeOrder = [
    'USB', 'LSB',
    'CW', 'CW-R', 'CW-U', 'CW-L',       // IC-7610: CW/CW-R, Yaesu: CW-U/CW-L
    'RTTY', 'RTTY-R', 'RTTY-L', 'RTTY-U', // IC-7610: RTTY/RTTY-R, Yaesu: RTTY-L/RTTY-U
    'PSK', 'PSK-R',
    'DATA-U', 'DATA-L', 'DATA-FM', 'DATA-FM-N',
    'AM', 'AM-N', 'FM', 'FM-N',
    'C4FM-DN', 'C4FM-VW',
  ];

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
        <HardwareButton
          active={currentMode === mode}
          indicator="edge-left"
          color="cyan"
          title={modeShortcut(mode)}
          shortcutHint={modeShortcut(mode)}
          onclick={() => onModeChange(mode)}
        >
          {mode}
        </HardwareButton>
      {/each}
    </div>

    {#if hasDataMode && dataOptions.length === 2}
      <HardwareButton
        active={dataMode > 0}
        indicator="edge-left"
        color="red"
        title={dataShortcut}
        shortcutHint={dataShortcut}
        onclick={() => onDataModeChange(dataMode > 0 ? 0 : 1)}
      >
        DATA
      </HardwareButton>
    {:else if hasDataMode && dataOptions.length > 2}
      <div class="section-label">DATA</div>
      <div class="data-grid">
        {#each dataOptions as option}
          <HardwareButton
            active={dataMode === option.value}
            indicator="edge-left"
            color="cyan"
            title={dataShortcut}
            shortcutHint={dataShortcut}
            onclick={() => onDataModeChange(option.value)}
          >
            {option.label}
          </HardwareButton>
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

  .mode-grid > :global(button),
  .data-grid > :global(button) {
    min-width: 0;
  }
  </style>