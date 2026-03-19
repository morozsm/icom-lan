<script lang="ts">
  import LinearSMeter from './LinearSMeter.svelte';

  const FIXED_VALUES: ReadonlyArray<{ label: string; value: number }> = [
    { label: 'S0  (raw 0)',    value: 0 },
    { label: 'S3  (raw 54)',   value: 54 },
    { label: 'S7  (raw 126)',  value: 126 },
    { label: 'S9  (raw 162)', value: 162 },
    { label: 'S9+20 (raw 202)', value: 202 },
    { label: 'S9+40 (raw 241)', value: 241 },
  ];

  let sliderValue = $state(90);
</script>

<div class="demo-root">
  <h1>LinearSMeter Demo</h1>

  <section>
    <h2>Full variant — fixed values</h2>
    {#each FIXED_VALUES as item}
      <div class="row">
        <span class="row-label">{item.label}</span>
        <LinearSMeter value={item.value} />
      </div>
    {/each}
  </section>

  <section>
    <h2>Compact variant — fixed values</h2>
    {#each FIXED_VALUES as item}
      <div class="row">
        <span class="row-label">{item.label}</span>
        <LinearSMeter value={item.value} compact={true} />
      </div>
    {/each}
  </section>

  <section>
    <h2>Interactive sweep (0 – 255)</h2>
    <div class="sweep-row">
      <input
        type="range"
        min="0"
        max="255"
        bind:value={sliderValue}
        class="slider"
      />
      <span class="slider-val">raw {sliderValue}</span>
    </div>
    <div class="meter-group">
      <p class="variant-label">Full</p>
      <LinearSMeter value={sliderValue} label="MAIN" />
    </div>
    <div class="meter-group">
      <p class="variant-label">Compact</p>
      <LinearSMeter value={sliderValue} compact={true} label="SUB" />
    </div>
  </section>
</div>

<style>
  .demo-root {
    background: var(--v2-bg-darkest);
    min-height: 100vh;
    padding: 24px 32px;
    font-family: 'Roboto Mono', monospace;
    color: var(--v2-text-light);
  }

  h1 {
    font-size: 20px;
    font-weight: 700;
    color: var(--v2-text-lighter);
    margin-bottom: 32px;
  }

  h2 {
    font-size: 13px;
    font-weight: 600;
    color: var(--v2-text-dim);
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  section {
    margin-bottom: 40px;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .row-label {
    width: 160px;
    font-size: 11px;
    color: var(--v2-text-muted);
    flex-shrink: 0;
  }

  .row > :global(svg) {
    flex: 1;
  }

  .sweep-row {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
  }

  .slider {
    flex: 1;
    max-width: 400px;
    accent-color: var(--v2-accent-green-medium);
  }

  .slider-val {
    font-size: 12px;
    color: var(--v2-text-dim);
    min-width: 64px;
  }

  .meter-group {
    margin-bottom: 16px;
  }

  .variant-label {
    font-size: 11px;
    color: var(--v2-text-muted);
    margin-bottom: 4px;
  }
</style>
