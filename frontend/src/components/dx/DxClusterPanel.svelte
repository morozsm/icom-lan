<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { onMessage, sendCommand } from '../../lib/transport/ws-client';
  import { radio } from '../../lib/stores/radio.svelte';
  import type { DxSpot } from '../../lib/types/protocol';

  const MAX_SPOTS = 100;

  // Band definitions for color-coding and filtering
  interface BandDef {
    name: string;
    minHz: number;
    maxHz: number;
    color: string;
  }

  const BANDS: BandDef[] = [
    { name: '160m', minHz: 1_800_000,  maxHz: 2_000_000,  color: '#ff6b6b' },
    { name: '80m',  minHz: 3_500_000,  maxHz: 4_000_000,  color: '#ffa07a' },
    { name: '60m',  minHz: 5_330_000,  maxHz: 5_410_000,  color: '#ffd700' },
    { name: '40m',  minHz: 7_000_000,  maxHz: 7_300_000,  color: '#90ee90' },
    { name: '30m',  minHz: 10_100_000, maxHz: 10_150_000, color: '#20b2aa' },
    { name: '20m',  minHz: 14_000_000, maxHz: 14_350_000, color: '#4db6ff' },
    { name: '17m',  minHz: 18_068_000, maxHz: 18_168_000, color: '#87ceeb' },
    { name: '15m',  minHz: 21_000_000, maxHz: 21_450_000, color: '#9370db' },
    { name: '12m',  minHz: 24_890_000, maxHz: 24_990_000, color: '#ff69b4' },
    { name: '10m',  minHz: 28_000_000, maxHz: 29_700_000, color: '#ff4500' },
    { name: '6m',   minHz: 50_000_000, maxHz: 54_000_000, color: '#ff8c00' },
  ];

  // DX cluster spots use kHz conventionally
  function spotFreqHz(spot: DxSpot): number {
    return spot.freq * 1_000;
  }

  function getBand(freqHz: number): BandDef | undefined {
    return BANDS.find((b) => freqHz >= b.minHz && freqHz <= b.maxHz);
  }

  let spots = $state<DxSpot[]>([]);
  let filterCurrentBand = $state(false);

  let currentFreq = $derived((radio.current?.active === 'SUB' ? radio.current?.sub : radio.current?.main)?.freqHz ?? 0);
  let receiverIdx = $derived(radio.current?.active === 'SUB' ? 1 : 0);

  let filteredSpots = $derived.by((): DxSpot[] => {
    if (!filterCurrentBand) return spots;
    const currentBand = getBand(currentFreq);
    if (!currentBand) return spots;
    return spots.filter((s) => getBand(spotFreqHz(s))?.name === currentBand.name);
  });

  function formatSpotFreq(spot: DxSpot): string {
    // spot.freq is in kHz, show as MHz
    return (spot.freq / 1_000).toFixed(3);
  }

  function addSpot(spot: DxSpot) {
    // Remove duplicate (same DX callsign + frequency), then prepend
    spots = [spot, ...spots.filter((s) => !(s.dx === spot.dx && s.freq === spot.freq))].slice(
      0,
      MAX_SPOTS,
    );
  }

  function tuneToSpot(spot: DxSpot) {
    sendCommand('set_freq', { freq: spotFreqHz(spot), receiver: receiverIdx });
  }

  onMount(() => {
    return onMessage((msg) => {
      if (msg.type === 'dx_spot') {
        addSpot(msg.spot);
      } else if (msg.type === 'dx_spots') {
        for (const spot of msg.spots) {
          addSpot(spot);
        }
      }
    });
  });
</script>

<div class="dx-panel">
  <div class="dx-header">
    <span class="dx-title">DX Cluster</span>
    <label class="filter-toggle">
      <input type="checkbox" bind:checked={filterCurrentBand} />
      <span>This band</span>
    </label>
  </div>

  {#if spots.length === 0}
    <div class="dx-empty">No DX cluster data</div>
  {:else}
    <div class="dx-list" role="list">
      {#each filteredSpots() as spot (spot.dx + spot.freq + spot.time)}
        {@const band = getBand(spotFreqHz(spot))}
        <button
          class="dx-spot"
          onclick={() => tuneToSpot(spot)}
          title={spot.comment || spot.spotter}
          in:fade={{ duration: 200 }}
        >
          <span class="spot-call" style="color: {band?.color ?? 'var(--text)'}">
            {spot.dx}
          </span>
          <span class="spot-freq">{formatSpotFreq(spot)}</span>
          <span class="spot-band">{band?.name ?? '—'}</span>
          <span class="spot-time">{spot.time}</span>
          <span class="spot-spotter">{spot.spotter}</span>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .dx-panel {
    display: flex;
    flex-direction: column;
    min-height: 0;
    flex: 1;
  }

  .dx-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-2);
    flex-shrink: 0;
  }

  .dx-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .filter-toggle {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.6875rem;
    color: var(--text-muted);
    cursor: pointer;
  }

  .filter-toggle input {
    width: 12px;
    height: 12px;
    cursor: pointer;
    accent-color: var(--accent);
  }

  .dx-empty {
    color: var(--text-muted);
    font-size: 0.75rem;
    text-align: center;
    padding: var(--space-4);
    border: 1px dashed var(--panel-border);
    border-radius: var(--radius);
  }

  .dx-list {
    display: flex;
    flex-direction: column;
    gap: 1px;
    overflow-y: auto;
    flex: 1;
    min-height: 0;
  }

  .dx-spot {
    display: grid;
    grid-template-columns: 1fr auto auto auto;
    grid-template-rows: auto auto;
    column-gap: var(--space-2);
    padding: 4px var(--space-2);
    border: none;
    border-radius: 4px;
    background: transparent;
    cursor: pointer;
    text-align: left;
    transition: background 0.1s;
  }

  .dx-spot:hover {
    background: var(--panel-border);
  }

  .spot-call {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    grid-row: 1;
    grid-column: 1;
  }

  .spot-freq {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text);
    grid-row: 1;
    grid-column: 2;
    white-space: nowrap;
  }

  .spot-band {
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    color: var(--text-muted);
    grid-row: 1;
    grid-column: 3;
    white-space: nowrap;
  }

  .spot-time {
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    color: var(--text-muted);
    grid-row: 1;
    grid-column: 4;
    white-space: nowrap;
  }

  .spot-spotter {
    font-size: 0.6875rem;
    color: var(--text-muted);
    grid-row: 2;
    grid-column: 1 / -1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
