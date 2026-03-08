<script lang="ts">
  interface Props {
    power: number; // watts
    swr: number; // SWR ratio (1.0 = perfect)
    maxPower?: number; // configurable max watts
  }

  let { power, swr, maxPower = 100 }: Props = $props();

  let fillPercent = $derived(Math.min(100, Math.max(0, (power / maxPower) * 100)));

  // Color: green <50%, yellow 50-90%, red >90%
  let barColor = $derived(
    fillPercent < 50 ? 'var(--success)' : fillPercent < 90 ? 'var(--warning)' : 'var(--danger)',
  );

  let swrText = $derived(swr > 0 ? swr.toFixed(1) : '—');

  // SWR color: green ≤1.5, yellow ≤3.0, red >3.0
  let swrColor = $derived(
    swr <= 1.5 ? 'var(--success)' : swr <= 3.0 ? 'var(--warning)' : 'var(--danger)',
  );
</script>

<div class="power-meter">
  <div class="meter-row">
    <div class="meter-section">
      <div class="meter-header">
        <span class="meter-label">PWR</span>
        <span class="meter-value">{power}W</span>
      </div>
      <div class="meter-track">
        <div class="meter-fill" style="width: {fillPercent}%; background: {barColor}"></div>
      </div>
      <div class="scale-row">
        <span>0</span>
        <span style="left: 50%; transform: translateX(-50%); position: absolute"
          >{Math.round(maxPower / 2)}W</span
        >
        <span>{maxPower}W</span>
      </div>
    </div>

    <div class="swr-section">
      <span class="swr-label">SWR</span>
      <span class="swr-value" style="color: {swrColor}">{swrText}</span>
    </div>
  </div>
</div>

<style>
  .power-meter {
    display: flex;
    flex-direction: column;
  }

  .meter-row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }

  .meter-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .meter-header {
    display: flex;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 0.75rem;
  }

  .meter-label {
    color: var(--text-muted);
    font-weight: 700;
    letter-spacing: 0.1em;
    font-size: 0.65rem;
  }

  .meter-value {
    color: var(--text);
    font-weight: 700;
  }

  .meter-track {
    height: 8px;
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    overflow: hidden;
  }

  .meter-fill {
    height: 100%;
    border-radius: 4px;
    transition:
      width 0.12s ease-out,
      background-color 0.3s;
  }

  .scale-row {
    display: flex;
    justify-content: space-between;
    position: relative;
    font-family: var(--font-mono);
    font-size: 0.5rem;
    color: var(--text-muted);
    user-select: none;
  }

  .swr-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    min-width: 44px;
  }

  .swr-label {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    color: var(--text-muted);
    font-weight: 700;
    letter-spacing: 0.1em;
  }

  .swr-value {
    font-family: var(--font-mono);
    font-size: 0.875rem;
    font-weight: 700;
    transition: color 0.3s;
  }
</style>
