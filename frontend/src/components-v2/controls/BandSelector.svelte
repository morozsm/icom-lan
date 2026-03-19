<script lang="ts">
  import './control-button.css';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import { flattenBands, findActiveBand } from './band-utils';
  import { getShortcutHint } from '../layout/shortcut-hints';

  interface Props {
    currentFreq: number;
    onBandSelect: (bandName: string, freq: number, bsrCode?: number) => void;
  }

  let { currentFreq, onBandSelect }: Props = $props();

  let bands = $derived(flattenBands(getCapabilities()?.freqRanges ?? []));
  let activeBand = $derived(findActiveBand(currentFreq, getCapabilities()?.freqRanges ?? []));

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

<div class="panel">
  <div class="header">BAND</div>
  <div class="grid">
    {#each bands as band (band.name)}
      {@const isActive = activeBand === band.name}
      <button
        type="button"
        class="band-btn v2-control-button"
        class:active={isActive}
        style="--control-accent:#00D4FF; --control-active-text:#FFFFFF"
        data-band={band.name}
        data-active={isActive}
        data-shortcut-hint={bandShortcut(band.bsrCode) ?? undefined}
        title={bandShortcut(band.bsrCode) ?? undefined}
        onclick={() => handleClick(band.name, band.defaultFreq, band.bsrCode)}
      >
        {band.name}
      </button>
    {/each}
  </div>
</div>

<style>
  .panel {
    background: #060A10;
    border: 1px solid #18202A;
    border-radius: 4px;
    padding: 6px 7px 7px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .header {
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    color: #8CA0B8;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 3px;
  }

  .band-btn {
    min-width: 0;
  }
</style>
