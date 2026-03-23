<script lang="ts">
  import './control-button.css';
  import { SegmentedControl } from '$lib/SegmentedControl';
  import {
    buildAttControlModel,
    getAttOverflowLabel,
  } from '../panels/rf-frontend-utils';

  interface Props {
    values: number[];
    selected: number;
    onchange: (value: number) => void;
    accentColor?: string;
    shortcutHint?: string | null;
    title?: string | null;
  }

  let {
    values,
    selected,
    onchange,
    accentColor = 'var(--v2-accent-cyan)',
    shortcutHint = null,
    title = null,
  }: Props = $props();

  let menuOpen = $state(false);
  let menuStyle = $state('');
  let moreButtonEl: HTMLButtonElement | undefined = $state();
  let controlModel = $derived(buildAttControlModel(values));
  let overflowSelected = $derived(controlModel.overflowOptions.some((option) => option.value === selected));
  let overflowLabel = $derived(getAttOverflowLabel(selected, controlModel.overflowOptions));

  function handleQuickChange(value: string | number): void {
    onchange(value as number);
  }

  function handleOverflowSelect(value: number): void {
    onchange(value);
    menuOpen = false;
  }

  function openMenu(): void {
    if (moreButtonEl) {
      const rect = moreButtonEl.getBoundingClientRect();
      const menuWidth = 220;
      let left = rect.right - menuWidth;
      if (left < 8) left = 8;
      const top = rect.bottom + 6;
      menuStyle = `top: ${top}px; left: ${left}px;`;
    }
    menuOpen = true;
  }
 </script>

<div class="att-control" style="--control-accent: {accentColor};" data-shortcut-hint={shortcutHint ?? undefined} title={title ?? shortcutHint ?? undefined}>
  <SegmentedControl
    options={controlModel.quickOptions}
    selected={selected}
    onchange={handleQuickChange}
    accentColor={accentColor}
  />

  {#if controlModel.overflowOptions.length > 0}
    <button
      type="button"
      class="more-button v2-control-button"
      class:active={overflowSelected}
      bind:this={moreButtonEl}
      onclick={openMenu}
      aria-haspopup="dialog"
      aria-expanded={menuOpen}
      aria-label="More attenuator values"
    >
      {overflowLabel}
    </button>
  {/if}

  {#if menuOpen}
    <button
      type="button"
      class="menu-backdrop"
      aria-label="Close attenuator menu"
      onclick={() => (menuOpen = false)}
    ></button>

    <div class="menu" role="dialog" aria-label="More attenuator values" style={menuStyle}>
      <div class="menu-title">ATT Values</div>
      <div class="menu-grid">
        {#each controlModel.overflowOptions as option}
          <button
            type="button"
            class="menu-item v2-control-button"
            class:active={option.value === selected}
            onclick={() => handleOverflowSelect(option.value)}
          >
            {option.label}
          </button>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .att-control {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
    min-width: 0;
    width: 100%;
  }

  .att-control :global(.segmented-button) {
    width: 100%;
  }

  .att-control :global(.segment) {
    flex: 1 1 0;
    min-width: 0;
    text-transform: none;
  }

  .more-button {
    width: 100%;
    text-transform: none;
  }

  .menu-backdrop {
    position: fixed;
    inset: 0;
    z-index: 10000;
    background: var(--v2-attenuator-bg);
    border: 0;
    padding: 0;
    margin: 0;
  }

  .menu {
    position: fixed;
    z-index: 10001;
    min-width: 220px;
    padding: 8px;
    background: var(--v2-bg-darkest);
    border: 1px solid var(--v2-border-darker);
    border-radius: 4px;
    box-shadow: 0 10px 24px var(--v2-attenuator-shadow);
  }

  .menu-title {
    margin-bottom: 6px;
    color: var(--v2-text-subdued);
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .menu-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
  }

  .menu-item {
    text-transform: none;
  }
</style>