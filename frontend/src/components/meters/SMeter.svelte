<script lang="ts">
  interface Props {
    value: number; // raw backend value 0-255
    label?: string;
  }

  let { value, label = 'S' }: Props = $props();

  // Raw value scale:
  // S0=0, S1=17, S2=34, ..., S9=153, S9+10=170, S9+20=187, S9+40=212, S9+60=237
  const MAX_RAW = 255;
  const S_UNIT = 17; // raw units per S-step
  const S9_RAW = 153; // 9 * 17

  let fillPercent = $derived(Math.min(100, (Math.max(0, value) / MAX_RAW) * 100));

  function sMeterLabel(v: number): string {
    if (v <= 0) return 'S0';
    if (v <= S9_RAW) {
      const s = Math.min(9, Math.round(v / S_UNIT));
      return `S${s}`;
    }
    const above = v - S9_RAW;
    if (above <= S_UNIT) return 'S9+10';
    if (above <= 2 * S_UNIT) return 'S9+20';
    if (above <= 59) return 'S9+40';
    return 'S9+60';
  }

  let displayLabel = $derived(sMeterLabel(value));

  // Color thresholds: green S1-S5 (≤85), yellow S6-S9 (≤153), red S9+
  let meterColor = $derived(
    value <= 85 ? 'var(--success)' : value <= S9_RAW ? 'var(--warning)' : 'var(--danger)',
  );

  // Positions for scale labels on the track (as % of MAX_RAW)
  const S5_PCT = (85 / MAX_RAW) * 100;
  const S9_PCT = (S9_RAW / MAX_RAW) * 100;
</script>

<div class="s-meter">
  <div class="meter-header">
    <span class="meter-label">{label}</span>
    <span class="meter-value" style="color: {meterColor}">{displayLabel}</span>
  </div>

  <div class="meter-bar-wrap">
    <div class="meter-track">
      <!-- Gradient fill bar -->
      <div class="meter-fill" style="width: {fillPercent}%"></div>
      <!-- S9 threshold marker -->
      <div class="threshold-mark" style="left: {S9_PCT}%"></div>
    </div>

    <div class="scale-row">
      <span class="scale-start">S1</span>
      <span class="scale-mid" style="left: {S5_PCT}%">S5</span>
      <span class="scale-s9" style="left: {S9_PCT}%">S9</span>
      <span class="scale-end">+60</span>
    </div>
  </div>
</div>

<style>
  .s-meter {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .meter-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
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
    font-weight: 700;
    font-size: 0.875rem;
    transition: color 0.2s;
    min-width: 48px;
    text-align: right;
  }

  .meter-bar-wrap {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .meter-track {
    position: relative;
    height: 8px;
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    overflow: hidden;
  }

  .meter-fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    border-radius: 4px;
    /* Color gradient: green → yellow → red, keyed to S5 and S9 positions */
    background: linear-gradient(
      to right,
      var(--success) 0%,
      var(--success) 33.3%,
      var(--warning) 33.3%,
      var(--warning) 60%,
      var(--danger) 60%,
      var(--danger) 100%
    );
    transition: width 0.12s ease-out;
  }

  .threshold-mark {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: rgba(255, 255, 255, 0.3);
    pointer-events: none;
  }

  .scale-row {
    position: relative;
    height: 12px;
    font-family: var(--font-mono);
    font-size: 0.5rem;
    color: var(--text-muted);
    user-select: none;
  }

  .scale-start {
    position: absolute;
    left: 0;
  }

  .scale-mid {
    position: absolute;
    transform: translateX(-50%);
  }

  .scale-s9 {
    position: absolute;
    transform: translateX(-50%);
    color: var(--warning);
  }

  .scale-end {
    position: absolute;
    right: 0;
    color: var(--danger);
  }
</style>
