<script lang="ts">
  import type { FilterModeConfig } from '$lib/types/capabilities';
  import '../controls/control-button.css';
  import { ValueControl } from '../controls/value-control';
  import { formatFilterWidth } from './filter-utils';
  import { getShortcutHint, joinShortcutHints } from '../layout/shortcut-hints';

  interface Props {
    currentMode: string;
    currentFilter: number;
    filterShape: number;
    filterLabels?: string[];
    filterWidth: number;
    filterWidthMin?: number;
    filterWidthMax?: number;
    filterConfig?: FilterModeConfig | null;
    ifShift: number;
    pbtInner?: number;
    pbtOuter?: number;
    hasPbt?: boolean;
    onFilterChange?: (filter: number) => void;
    onFilterWidthChange: (v: number) => void;
    onFilterShapeChange?: (shape: number) => void;
    onFilterPresetChange?: (filter: number, width: number) => void;
    onFilterDefaults?: (defaults: number[]) => void;
    onIfShiftChange: (v: number) => void;
    onPbtInnerChange?: (v: number) => void;
    onPbtOuterChange?: (v: number) => void;
    onPbtReset?: () => void;
  }

  let {
    currentMode,
    currentFilter,
    filterShape,
    filterLabels = ['FIL1', 'FIL2', 'FIL3'],
    filterWidth,
    filterWidthMin = 50,
    filterWidthMax = 9999,
    filterConfig = null,
    ifShift,
    pbtInner = 0,
    pbtOuter = 0,
    hasPbt = false,
    onFilterChange,
    onFilterWidthChange,
    onFilterShapeChange,
    onFilterPresetChange,
    onFilterDefaults,
    onIfShiftChange,
    onPbtInnerChange,
    onPbtOuterChange,
    onPbtReset,
  }: Props = $props();

  let modalOpen = $state(false);
  let draftWidths = $state<number[]>([]);

  let normalizedLabels = $derived(filterLabels.length > 0 ? filterLabels : ['FIL1', 'FIL2', 'FIL3']);
  let factoryDefaults = $derived.by(() => {
    const fallback = Array.from({ length: normalizedLabels.length }, () => filterWidth);
    const defaults = filterConfig?.defaults?.slice(0, normalizedLabels.length) ?? fallback;
    while (defaults.length < normalizedLabels.length) {
      defaults.push(defaults[defaults.length - 1] ?? filterWidth);
    }
    return defaults;
  });
  let visibleWidths = $derived.by(() => {
    const values = [...factoryDefaults];
    const activeIndex = Math.max(0, Math.min(normalizedLabels.length - 1, currentFilter - 1));
    values[activeIndex] = filterWidth;
    return values;
  });
  let modalMin = $derived(filterConfig?.minHz ?? filterWidthMin);
  let modalMax = $derived(filterConfig?.maxHz ?? filterWidthMax);
  let modalStep = $derived(filterConfig?.stepHz ?? filterConfig?.segments?.[0]?.stepHz ?? 50);
  const cycleFilterShortcut = joinShortcutHints(
    getShortcutHint('cycle_filter'),
    getShortcutHint('cycle_filter', (binding) => Number(binding.params?.step ?? 0) === -1),
  );
  const filterSettingsShortcut = getShortcutHint('open_filter_settings');

  $effect(() => {
    if (!modalOpen) {
      draftWidths = [...visibleWidths];
    }
  });

  function formatWidthDisplay(hz: number): string {
    const formatted = formatFilterWidth(hz);
    return formatted.includes('k') ? `${formatted}Hz` : `${formatted} Hz`;
  }

  function openSettings(): void {
    draftWidths = [...visibleWidths];
    modalOpen = true;
  }

  function closeSettings(): void {
    modalOpen = false;
  }

  function handlePresetChange(index: number, width: number): void {
    draftWidths = draftWidths.map((value, draftIndex) => (draftIndex === index ? width : value));
    onFilterPresetChange?.(index + 1, width);
  }

  function handleRestoreDefaults(): void {
    draftWidths = [...factoryDefaults];
    onFilterDefaults?.([...factoryDefaults]);
  }
</script>

<div class="panel-body">
    <div class="filter-top-row">
      <div class="filter-grid">
        {#each normalizedLabels as label, index}
          <button
            type="button"
            class="filter-select-button v2-control-button"
            class:active={currentFilter === index + 1}
            style="--control-accent:var(--v2-accent-cyan); --control-active-text:var(--v2-text-white)"
            data-shortcut-hint={cycleFilterShortcut ?? undefined}
            title={cycleFilterShortcut ?? undefined}
            onclick={() => onFilterChange?.(index + 1)}
          >
            {label}
          </button>
        {/each}
      </div>

      <button
        type="button"
        class="settings-button v2-control-button"
        style="--control-accent:var(--v2-text-disabled); --control-active-text:var(--v2-text-bright)"
        aria-label="Open filter settings"
        aria-haspopup="dialog"
        aria-expanded={modalOpen}
        data-shortcut-hint={filterSettingsShortcut ?? undefined}
        title={filterSettingsShortcut ?? undefined}
        onclick={openSettings}
      >
        ⚙
      </button>
    </div>

    <div class="bw-row">
      <span class="bw-label">BW</span>
      <span class="bw-value">{formatWidthDisplay(filterWidth)}</span>
    </div>

    <ValueControl
      label="IF Shift"
      value={ifShift}
      min={-1200}
      max={1200}
      step={25}
      unit="Hz"
      renderer="bipolar"
      accentColor="var(--v2-accent-cyan)"
      onChange={onIfShiftChange}
    />
    {#if hasPbt}
      <ValueControl
        label="PBT Inner"
        value={pbtInner}
        min={-1200}
        max={1200}
        step={25}
        unit="Hz"
        renderer="bipolar"
        accentColor="var(--v2-accent-cyan)"
        onChange={onPbtInnerChange ?? (() => {})}
      />
      <ValueControl
        label="PBT Outer"
        value={pbtOuter}
        min={-1200}
        max={1200}
        step={25}
        unit="Hz"
        renderer="bipolar"
        accentColor="var(--v2-accent-green-bright)"
        onChange={onPbtOuterChange ?? (() => {})}
      />
    {/if}

    <div class="filter-actions">
      <button
        type="button"
        class="pbt-reset-button v2-control-button"
        style="--control-accent:var(--v2-text-disabled); --control-active-text:var(--v2-text-bright)"
        onclick={() => onPbtReset?.()}
      >
        Reset
      </button>
    </div>
  </div>

{#if modalOpen}
  <button
    type="button"
    class="modal-backdrop"
    aria-label="Close filter settings"
    onclick={closeSettings}
  ></button>

  <div class="filter-modal" role="dialog" aria-modal="true" aria-label={`Filter settings ${currentMode}`}>
    <div class="modal-header">
      <div>
        <div class="modal-title">FILTER SETTINGS</div>
        <div class="modal-subtitle">{currentMode}</div>
      </div>
      <button
        type="button"
        class="modal-close v2-control-button"
        style="--control-accent:var(--v2-text-disabled); --control-active-text:var(--v2-text-bright)"
        onclick={closeSettings}
      >
        Close
      </button>
    </div>

    <div class="modal-body">
      {#each normalizedLabels as label, index}
        <div class="modal-filter-row" class:active={currentFilter === index + 1}>
          <div class="modal-filter-meta">
            <span class="modal-filter-label">{label}</span>
            {#if currentFilter === index + 1}
              <span class="modal-filter-active">ACTIVE</span>
            {/if}
          </div>

          {#if filterConfig?.fixed}
            <div class="modal-fixed-value">{formatWidthDisplay(draftWidths[index] ?? visibleWidths[index] ?? factoryDefaults[index])}</div>
          {:else}
            <ValueControl
              label={label}
              value={draftWidths[index] ?? visibleWidths[index] ?? factoryDefaults[index]}
              min={modalMin}
              max={modalMax}
              step={modalStep}
              unit="Hz"
              renderer="hbar"
              accentColor={currentFilter === index + 1 ? 'var(--v2-accent-cyan)' : 'var(--v2-accent-green-bright)'}
              onChange={(value) => handlePresetChange(index, value)}
            />
          {/if}
        </div>
      {/each}

      <div class="shape-section">
        <div class="shape-title">Shape</div>
        <div class="shape-buttons">
          <button
            type="button"
            class="shape-button v2-control-button"
            class:active={filterShape === 0}
            style="--control-accent:var(--v2-accent-cyan); --control-active-text:var(--v2-text-white)"
            onclick={() => onFilterShapeChange?.(0)}
          >
            SHARP
          </button>
          <button
            type="button"
            class="shape-button v2-control-button"
            class:active={filterShape === 1}
            style="--control-accent:var(--v2-accent-green-bright); --control-active-text:var(--v2-bg-darkest)"
            onclick={() => onFilterShapeChange?.(1)}
          >
            SOFT
          </button>
        </div>
      </div>

      {#if filterConfig?.fixed}
        <div class="modal-note">This mode uses fixed filter widths.</div>
      {:else}
        <div class="modal-range">Range: {modalMin} - {modalMax} Hz · Step: {modalStep} Hz</div>
      {/if}
    </div>

    <div class="modal-actions">
      {#if !filterConfig?.fixed}
        <button
          type="button"
          class="defaults-button v2-control-button"
          style="--control-accent:var(--v2-accent-green-bright); --control-active-text:var(--v2-bg-darkest)"
          onclick={handleRestoreDefaults}
        >
          Restore Defaults
        </button>
      {/if}
    </div>
  </div>
{/if}

<style>
  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 7px 8px;
  }

  .filter-top-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 6px;
    align-items: start;
  }

  .filter-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 4px;
  }

  .filter-select-button,
  .settings-button,
  .modal-close,
  .defaults-button {
    min-width: 0;
  }

  .bw-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    padding: 4px 2px 1px;
    color: var(--v2-text-light);
    font-family: 'Roboto Mono', monospace;
  }

  .bw-label {
    color: var(--v2-text-dim);
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .bw-value {
    font-size: 14px;
    font-weight: 700;
  }

  .filter-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 2px;
  }

  .pbt-reset-button {
    min-width: 88px;
  }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 60;
    background: var(--v2-popup-bg);
    border: 0;
    padding: 0;
    margin: 0;
  }

  .filter-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    z-index: 61;
    width: min(560px, calc(100vw - 24px));
    max-height: min(88vh, 720px);
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 14px;
    background: linear-gradient(180deg, var(--v2-bg-gradient-start) 0%, var(--v2-bg-darkest) 100%);
    border: 1px solid var(--v2-border-darker);
    border-radius: 8px;
    box-shadow: 0 18px 48px var(--v2-popup-shadow);
    overflow: auto;
  }

  .modal-header,
  .modal-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .modal-title,
  .modal-subtitle,
  .modal-note,
  .modal-range,
  .modal-filter-meta,
  .modal-fixed-value {
    font-family: 'Roboto Mono', monospace;
  }

  .modal-title {
    color: var(--v2-text-light);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .modal-subtitle {
    color: var(--v2-text-dim);
    font-size: 11px;
    margin-top: 3px;
  }

  .modal-body {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .shape-section {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-top: 2px;
  }

  .shape-title {
    color: var(--v2-text-subdued);
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .shape-buttons {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
  }

  .shape-button {
    min-width: 0;
  }

  .modal-filter-row {
    border: 1px solid var(--v2-border-darker);
    border-radius: 6px;
    padding: 8px;
    background: var(--v2-overlay-light);
  }

  .modal-filter-row.active {
    border-color: var(--v2-border-soft);
    box-shadow: 0 0 0 1px var(--v2-popup-border-glow);
  }

  .modal-filter-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
  }

  .modal-filter-label {
    color: var(--v2-text-light);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.06em;
  }

  .modal-filter-active {
    color: var(--v2-accent-cyan);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .modal-fixed-value,
  .modal-note,
  .modal-range {
    color: var(--v2-text-subdued);
    font-size: 12px;
  }

  @media (max-width: 640px) {
    .filter-modal {
      width: calc(100vw - 16px);
      padding: 12px;
    }

    .modal-header,
    .modal-actions {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
