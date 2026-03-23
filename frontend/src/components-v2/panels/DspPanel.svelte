<script lang="ts">
  import { SegmentedControl } from '$lib/SegmentedControl';
  import { ValueControl, rawToPercentDisplay } from '../controls/value-control';
  import { FillButton } from '$lib/Button';
  import { hasCapability } from '$lib/stores/capabilities.svelte';
  import { buildNrOptions, buildNotchOptions } from './dsp-utils';

  interface Props {
    nrMode: number;
    nrLevel: number;
    nbActive: boolean;
    nbLevel: number;
    notchMode: 'off' | 'auto' | 'manual';
    notchFreq: number;
    onNrModeChange: (v: number) => void;
    onNrLevelChange: (v: number) => void;
    onNbToggle: (v: boolean) => void;
    onNbLevelChange: (v: number) => void;
    onNotchModeChange: (v: string) => void;
    onNotchFreqChange: (v: number) => void;
  }

  let {
    nrMode,
    nrLevel,
    nbActive,
    nbLevel,
    notchMode,
    notchFreq,
    onNrModeChange,
    onNrLevelChange,
    onNbToggle,
    onNbLevelChange,
    onNotchModeChange,
    onNotchFreqChange,
  }: Props = $props();

  let showNr = $derived(hasCapability('nr'));
  let showNb = $derived(hasCapability('nb'));

  let nrOptions = $derived(buildNrOptions());
  let notchOptions = $derived(buildNotchOptions());

  let nrActive = $derived(nrMode > 0);
  let notchToggleActive = $derived(notchMode === 'auto' || notchMode === 'manual');

  type ModalId = 'nr' | 'nb' | 'notch';
  let openModal = $state<ModalId | null>(null);
  let nrModalStyle = $state('');
  let nbModalStyle = $state('');
  let notchModalStyle = $state('');

  let nrAnchorEl: HTMLDivElement | undefined = $state();
  let nbAnchorEl: HTMLDivElement | undefined = $state();
  let notchAnchorEl: HTMLDivElement | undefined = $state();

  /** Local NR mode for modal (supports 2 when server only reports on/off). */
  let nrModalMode = $state(0);
  let notchModalMode = $state<'off' | 'auto' | 'manual'>('off');

  function computeModalStyle(anchor: HTMLElement | undefined): string {
    if (!anchor) {
      return 'top: 8px; left: 8px; width: 220px;';
    }
    const rect = anchor.getBoundingClientRect();
    const menuWidth = 220;
    let left = rect.left;
    if (left + menuWidth > window.innerWidth - 8) {
      left = window.innerWidth - 8 - menuWidth;
    }
    if (left < 8) {
      left = 8;
    }
    const top = rect.bottom + 6;
    return `top: ${top}px; left: ${left}px; width: ${menuWidth}px;`;
  }

  function openModalFor(kind: ModalId): void {
    if (kind === 'nr') {
      nrModalMode = nrMode;
      nrModalStyle = computeModalStyle(nrAnchorEl);
    } else if (kind === 'nb') {
      nbModalStyle = computeModalStyle(nbAnchorEl);
    } else {
      notchModalMode = notchMode;
      notchModalStyle = computeModalStyle(notchAnchorEl);
    }
    openModal = kind;
  }

  function closeModal(): void {
    openModal = null;
  }

  function toggleNrShort(): void {
    if (nrMode === 0) {
      onNrModeChange(1);
    } else {
      onNrModeChange(0);
    }
  }

  function toggleNotchShort(): void {
    if (notchMode === 'off') {
      onNotchModeChange('auto');
    } else {
      onNotchModeChange('off');
    }
  }

  function handleNrModalMode(v: string | number): void {
    const n = v as number;
    nrModalMode = n;
    onNrModeChange(n);
  }

  function handleNotchModalMode(v: string | number): void {
    const m = v as 'off' | 'auto' | 'manual';
    notchModalMode = m;
    onNotchModeChange(m);
  }

  $effect(() => {
    if (openModal === 'nr') {
      nrModalStyle = computeModalStyle(nrAnchorEl);
    } else if (openModal === 'nb') {
      nbModalStyle = computeModalStyle(nbAnchorEl);
    } else if (openModal === 'notch') {
      notchModalStyle = computeModalStyle(notchAnchorEl);
    }
  });

  const LONG_PRESS_MS = 500;
  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  let suppressNextToggle: ModalId | null = null;

  function startLongPress(kind: ModalId): void {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
    }
    longPressTimer = setTimeout(() => {
      longPressTimer = null;
      suppressNextToggle = kind;
      openModalFor(kind);
    }, LONG_PRESS_MS);
  }

  function endLongPressPointer(): void {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
  }

  function onNrClick(): void {
    if (suppressNextToggle === 'nr') {
      suppressNextToggle = null;
      return;
    }
    toggleNrShort();
  }

  function onNbClick(): void {
    if (suppressNextToggle === 'nb') {
      suppressNextToggle = null;
      return;
    }
    onNbToggle(!nbActive);
  }

  function onNotchClick(): void {
    if (suppressNextToggle === 'notch') {
      suppressNextToggle = null;
      return;
    }
    toggleNotchShort();
  }
</script>

<div class="dsp-panel">
  <div class="dsp-toggle-row">
    {#if showNr}
      <div class="dsp-toggle-cell" bind:this={nrAnchorEl}>
        <div
          class="dsp-toggle-hit"
          role="presentation"
          onpointerdown={() => startLongPress('nr')}
          onpointerup={endLongPressPointer}
          onpointercancel={endLongPressPointer}
          onpointerleave={endLongPressPointer}
        >
          <FillButton
            compact
            active={nrActive}
            color="cyan"
            title="NR — click to toggle; long-press or ⚙ for settings"
            onclick={onNrClick}
          >NR</FillButton>
        </div>
        <button
          type="button"
          class="dsp-settings-btn"
          aria-label="NR settings"
          onclick={() => openModalFor('nr')}
        >
          <span class="dsp-settings-icon" aria-hidden="true">⚙</span>
        </button>
      </div>
    {/if}

    {#if showNb}
      <div class="dsp-toggle-cell" bind:this={nbAnchorEl}>
        <div
          class="dsp-toggle-hit"
          role="presentation"
          onpointerdown={() => startLongPress('nb')}
          onpointerup={endLongPressPointer}
          onpointercancel={endLongPressPointer}
          onpointerleave={endLongPressPointer}
        >
          <FillButton
            compact
            active={nbActive}
            color="orange"
            title="NB — click to toggle; long-press or ⚙ for settings"
            onclick={onNbClick}
          >NB</FillButton>
        </div>
        <button
          type="button"
          class="dsp-settings-btn"
          aria-label="NB settings"
          onclick={() => openModalFor('nb')}
        >
          <span class="dsp-settings-icon" aria-hidden="true">⚙</span>
        </button>
      </div>
    {/if}

    <div class="dsp-toggle-cell" bind:this={notchAnchorEl}>
      <div
        class="dsp-toggle-hit"
        role="presentation"
        onpointerdown={() => startLongPress('notch')}
        onpointerup={endLongPressPointer}
        onpointercancel={endLongPressPointer}
        onpointerleave={endLongPressPointer}
      >
        <FillButton
          compact
          active={notchToggleActive}
          color="cyan"
          title="Notch — click: off ↔ auto; long-press or ⚙ for settings"
          onclick={onNotchClick}
        >NOTCH</FillButton>
      </div>
      <button
        type="button"
        class="dsp-settings-btn"
        aria-label="Notch settings"
        onclick={() => openModalFor('notch')}
      >
        <span class="dsp-settings-icon" aria-hidden="true">⚙</span>
      </button>
    </div>
  </div>
</div>

{#if openModal}
  <button
    type="button"
    class="menu-backdrop"
    aria-label="Close DSP settings"
    onclick={closeModal}
  ></button>
{/if}

{#if openModal === 'nr'}
  <div
    class="dsp-modal"
    role="dialog"
    aria-label="Noise reduction settings"
    style={nrModalStyle}
  >
    <div class="menu-title">Noise reduction</div>
    <div class="dsp-modal-block">
      <SegmentedControl
        options={nrOptions}
        selected={nrModalMode}
        onchange={handleNrModalMode}
        indicatorStyle="fill"
        surface="hardware"
        indicatorColor="cyan"
      />
    </div>
    <ValueControl
      label="NR Level"
      value={nrLevel}
      min={0}
      max={15}
      step={1}
      renderer="hbar"
      accentColor="var(--v2-accent-cyan)"
      onChange={onNrLevelChange}
      variant="hardware-illuminated"
    />
  </div>
{/if}

{#if openModal === 'nb'}
  <div class="dsp-modal" role="dialog" aria-label="Noise blanker settings" style={nbModalStyle}>
    <div class="menu-title">Noise blanker</div>
    <div class="dsp-modal-block dsp-modal-row">
      <span class="dsp-modal-inline-label">NB</span>
      <FillButton active={nbActive} color="orange" onclick={() => onNbToggle(!nbActive)}>
        {nbActive ? 'ON' : 'OFF'}
      </FillButton>
    </div>
    <ValueControl
      label="NB Level"
      value={nbLevel}
      min={0}
      max={255}
      step={1}
      renderer="hbar"
      displayFn={rawToPercentDisplay}
      accentColor="var(--v2-accent-yellow)"
      onChange={onNbLevelChange}
      variant="hardware-illuminated"
    />
  </div>
{/if}

{#if openModal === 'notch'}
  <div class="dsp-modal" role="dialog" aria-label="Notch filter settings" style={notchModalStyle}>
    <div class="menu-title">Notch</div>
    <div class="dsp-modal-block">
      <SegmentedControl
        options={notchOptions}
        selected={notchModalMode}
        onchange={handleNotchModalMode}
        indicatorStyle="fill"
        surface="hardware"
        indicatorColor="cyan"
      />
    </div>
    {#if notchModalMode === 'manual'}
      <ValueControl
        label="Notch Freq"
        value={notchFreq}
        min={0}
        max={3000}
        step={1}
        unit="Hz"
        renderer="hbar"
        accentColor="var(--v2-accent-cyan)"
        onChange={onNotchFreqChange}
        variant="hardware-illuminated"
      />
    {/if}
  </div>
{/if}

<style>
  .dsp-panel {
    padding: 8px 8px;
  }

  .dsp-toggle-row {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }

  .dsp-toggle-cell {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 4px;
  }

  .dsp-toggle-hit {
    display: inline-flex;
  }

  .dsp-settings-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 22px;
    min-height: 22px;
    padding: 0;
    border: 1px solid var(--v2-border);
    border-radius: 4px;
    background: var(--v2-sidebar-footer-bg);
    color: var(--v2-text-secondary);
    cursor: pointer;
  }

  .dsp-settings-btn:hover {
    color: var(--v2-text-primary);
    border-color: var(--v2-border-darker);
  }

  .dsp-settings-icon {
    font-size: 12px;
    line-height: 1;
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

  .dsp-modal {
    position: fixed;
    z-index: 10001;
    box-sizing: border-box;
    min-width: 200px;
    max-width: 240px;
    padding: 8px;
    background: var(--v2-bg-darkest);
    border: 1px solid var(--v2-border-darker);
    border-radius: 4px;
    box-shadow: 0 10px 24px var(--v2-attenuator-shadow);
  }

  .menu-title {
    margin-bottom: 8px;
    color: var(--v2-text-subdued);
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .dsp-modal-block {
    margin-bottom: 8px;
  }

  .dsp-modal-block:last-child {
    margin-bottom: 0;
  }

  .dsp-modal-row {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }

  .dsp-modal-inline-label {
    flex: 0 0 auto;
    color: var(--v2-text-header);
    font-family: 'Roboto Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }
</style>
