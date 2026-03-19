<script lang="ts">
  import './control-button.css';
  import SegmentedButton from './SegmentedButton.svelte';
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
    accentColor = '#00D4FF',
    shortcutHint = null,
    title = null,
  }: Props = $props();

  let menuOpen = $state(false);
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
 </script>

<div class="att-control" data-shortcut-hint={shortcutHint ?? undefined} title={title ?? shortcutHint ?? undefined}>
  <SegmentedButton
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
      onclick={() => (menuOpen = true)}
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

    <div class="menu" role="dialog" aria-label="More attenuator values">
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
    --control-accent: #00d4ff;
    --control-active-text: #f0f5fa;
    text-transform: none;
  }

  .menu-backdrop {
    position: fixed;
    inset: 0;
    z-index: 40;
    background: rgba(3, 7, 12, 0.58);
    border: 0;
    padding: 0;
    margin: 0;
  }

  .menu {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    z-index: 41;
    min-width: min(220px, 100%);
    padding: 8px;
    background: #0a1016;
    border: 1px solid #1b2633;
    border-radius: 4px;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
  }

  .menu-title {
    margin-bottom: 6px;
    color: #8ca0b8;
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
    --control-accent: #00d4ff;
    --control-active-text: #f0f5fa;
    text-transform: none;
  }
</style>