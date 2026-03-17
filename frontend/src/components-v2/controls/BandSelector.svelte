<script lang="ts">
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import { flattenBands, findActiveBand } from './band-utils';

  interface Props {
    currentFreq: number;
    onBandSelect: (bandName: string, freq: number) => void;
  }

  let { currentFreq, onBandSelect }: Props = $props();

  let bands = $derived(flattenBands(getCapabilities()?.freqRanges ?? []));
  let activeBand = $derived(findActiveBand(currentFreq, getCapabilities()?.freqRanges ?? []));

  function handleClick(name: string, defaultFreq: number) {
    onBandSelect(name, defaultFreq);
  }

  function buttonStyle(isActive: boolean): string {
    if (isActive) {
      return [
        'background:#0D3B66',
        'border:1px solid #00D4FF',
        'color:#FFFFFF',
        'box-shadow:0 0 6px 0 rgba(0,212,255,0.25)',
      ].join(';');
    }
    return [
      'background:transparent',
      'border:1px solid #1A2028',
      'color:#4D6074',
      'box-shadow:none',
    ].join(';');
  }
</script>

<div class="panel">
  <div class="header">BAND</div>
  <div class="grid">
    {#each bands as band (band.name)}
      {@const isActive = activeBand === band.name}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <span
        class="band-btn"
        class:active={isActive}
        style={buttonStyle(isActive)}
        data-band={band.name}
        data-active={isActive}
        onclick={() => handleClick(band.name, band.defaultFreq)}
      >
        {band.name}
      </span>
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
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 3px;
    font-family: 'Roboto Mono', monospace;
    font-size: 8px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    white-space: nowrap;
    user-select: none;
    cursor: pointer;
    height: 18px;
    padding: 0 6px;
    transition: background 150ms ease, border-color 150ms ease, color 150ms ease, box-shadow 150ms ease;
  }

  .band-btn:hover {
    filter: brightness(1.2);
  }
</style>
