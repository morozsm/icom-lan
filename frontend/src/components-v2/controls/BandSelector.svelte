<script lang="ts">
  import { HardwareButton } from '$lib/Button';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import { flattenBands, findActiveBand } from './band-utils';
  import { getShortcutHint } from '../layout/shortcut-hints';
  import { BROADCAST_SW_BANDS, findActiveBroadcastBand } from './broadcast-presets';

  interface Props {
    currentFreq: number;
    onBandSelect: (bandName: string, freq: number, bsrCode?: number) => void;
    onPresetSelect?: (freq: number, mode: string) => void;
  }

  let { currentFreq, onBandSelect, onPresetSelect }: Props = $props();

  let bandMode = $state<'ham' | 'broadcast'>('ham');

  let bands = $derived(flattenBands(getCapabilities()?.freqRanges ?? []));
  let activeBand = $derived(findActiveBand(currentFreq, getCapabilities()?.freqRanges ?? []));
  let activeBroadcast = $derived(findActiveBroadcastBand(currentFreq));

  function handleClick(name: string, defaultFreq: number, bsrCode?: number) {
    onBandSelect(name, defaultFreq, bsrCode);
  }

  function bandShortcut(bsrCode?: number): string | null {
    if (bsrCode === undefined) {
      return null;
    }
    return getShortcutHint('band_select', (binding) => Number(binding.params?.index) === bsrCode);
  }

</script>

<div class="band-tabs">
  <button
    class="band-tab"
    class:active={bandMode === 'ham'}
    onclick={() => { bandMode = 'ham'; }}
  >HAM</button>
  <button
    class="band-tab"
    class:active={bandMode === 'broadcast'}
    onclick={() => { bandMode = 'broadcast'; }}
  >SWL</button>
</div>

{#if bandMode === 'ham'}
  <div class="grid">
    {#each bands as band (band.name)}
      {@const isActive = activeBand === band.name}
      <HardwareButton
        active={isActive}
        indicator="edge-left"
        color="cyan"
        title={bandShortcut(band.bsrCode)}
        shortcutHint={bandShortcut(band.bsrCode)}
        onclick={() => handleClick(band.name, band.defaultFreq, band.bsrCode)}
      >
        {band.name}
      </HardwareButton>
    {/each}
  </div>
{:else}
  <div class="grid">
    {#each BROADCAST_SW_BANDS as preset (preset.name)}
      {@const isActive = activeBroadcast === preset.name}
      <HardwareButton
        active={isActive}
        indicator="edge-left"
        color="amber"
        onclick={() => onPresetSelect?.(preset.freq, preset.mode)}
      >
        {preset.name}
      </HardwareButton>
    {/each}
  </div>
{/if}

<style>
  .band-tabs {
    display: flex;
    gap: 2px;
    padding: 6px 7px 0;
  }

  .band-tab {
    flex: 1;
    height: 24px;
    border: 1px solid var(--v2-border-darker);
    border-radius: 3px;
    background: var(--v2-bg-card);
    color: var(--v2-text-muted);
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
  }

  .band-tab:hover {
    color: var(--v2-text-secondary);
  }

  .band-tab.active {
    color: var(--v2-accent-cyan);
    border-color: var(--v2-accent-cyan);
    background: var(--v2-bg-input);
  }

  .grid {
    padding: 6px 7px 7px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 3px;
  }

  .grid > :global(button) {
    min-width: 0;
  }
</style>
