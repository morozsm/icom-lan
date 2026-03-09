<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { radio } from '../../lib/stores/radio.svelte';
  import { vibrate } from '../../lib/utils/haptics';
  import { getCapabilities } from '../../lib/stores/capabilities.svelte';

  interface Band {
    name: string;
    defaultHz: number;
    minHz: number;
    maxHz: number;
  }

  const caps = getCapabilities();
  const BANDS: Band[] = caps?.freqRanges
    ?.flatMap(r => r.bands ?? [])
    ?.map(b => ({ name: b.name, defaultHz: b.default, minHz: b.start, maxHz: b.end }))
    ?? [];

  let freq = $derived((radio.current?.active === 'SUB' ? radio.current?.sub : radio.current?.main)?.freqHz ?? 0);
  let receiverIdx = $derived(radio.current?.active === 'SUB' ? 1 : 0);
  let activeBand = $derived(BANDS.find(b => freq >= b.minHz && freq <= b.maxHz)?.name ?? null);

  function selectBand(band: Band) {
    vibrate('tap');
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
