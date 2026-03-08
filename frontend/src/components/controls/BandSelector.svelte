<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { getFrequency, getRadioState } from '../../lib/stores/radio.svelte';

  interface Band {
    name: string;
    defaultHz: number;
    minHz: number;
    maxHz: number;
  }

  // Bands cover IC-7610 frequency range: HF (160m–10m) + 6m. No 2m/70cm — IC-7610 is HF+6m only.
  const BANDS: Band[] = [
    { name: '160m', defaultHz: 1_825_000,  minHz: 1_800_000,  maxHz: 2_000_000  },
    { name: '80m',  defaultHz: 3_700_000,  minHz: 3_500_000,  maxHz: 4_000_000  },
    { name: '60m',  defaultHz: 5_357_000,  minHz: 5_330_000,  maxHz: 5_410_000  },
    { name: '40m',  defaultHz: 7_100_000,  minHz: 7_000_000,  maxHz: 7_300_000  },
    { name: '30m',  defaultHz: 10_130_000, minHz: 10_100_000, maxHz: 10_150_000 },
    { name: '20m',  defaultHz: 14_200_000, minHz: 14_000_000, maxHz: 14_350_000 },
    { name: '17m',  defaultHz: 18_120_000, minHz: 18_068_000, maxHz: 18_168_000 },
    { name: '15m',  defaultHz: 21_200_000, minHz: 21_000_000, maxHz: 21_450_000 },
    { name: '12m',  defaultHz: 24_940_000, minHz: 24_890_000, maxHz: 24_990_000 },
    { name: '10m',  defaultHz: 28_500_000, minHz: 28_000_000, maxHz: 29_700_000 },
    { name: '6m',   defaultHz: 50_200_000, minHz: 50_000_000, maxHz: 54_000_000 },
  ];

  let freq = $derived(getFrequency());
  let receiverIdx = $derived(getRadioState()?.active === 'SUB' ? 1 : 0);
  let activeBand = $derived(BANDS.find(b => freq >= b.minHz && freq <= b.maxHz)?.name ?? null);

  function selectBand(band: Band) {
    sendCommand('set_freq', { freq: band.defaultHz, receiver: receiverIdx });
  }
</script>

<div class="band-selector">
  <div class="btn-bar" role="group" aria-label="Band selector">
    {#each BANDS as band}
      <button
        class="band-btn"
        class:active={activeBand === band.name}
        onclick={() => selectBand(band)}
        aria-pressed={activeBand === band.name}
      >{band.name}</button>
    {/each}
  </div>
  <select
    class="band-select"
    value={activeBand ?? ''}
    onchange={(e) => {
      const found = BANDS.find(b => b.name === (e.target as HTMLSelectElement).value);
      if (found) selectBand(found);
    }}
    aria-label="Band selector"
  >
    <option value="" disabled>Band</option>
    {#each BANDS as band}
      <option value={band.name}>{band.name}</option>
    {/each}
  </select>
</div>

<style>
  .band-selector {
    display: contents;
  }

  .btn-bar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
  }

  .band-btn {
    min-height: var(--tap-target);
    padding: 0 var(--space-3);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.1s, color 0.1s, border-color 0.1s;
  }

  .band-btn:hover {
    color: var(--text);
    border-color: var(--accent);
  }

  .band-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
  }

  .band-select {
    display: none;
    min-height: var(--tap-target);
    width: 100%;
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: 0.875rem;
    padding: 0 var(--space-3);
    cursor: pointer;
  }

  @media (max-width: 640px) {
    .btn-bar { display: none; }
    .band-select { display: block; }
  }
</style>
