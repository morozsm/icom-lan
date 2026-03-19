<script lang="ts">
  interface Props {
    value: number;
    min: number;
    max: number;
    step?: number;
    label: string;
    unit?: string;
    onchange: (v: number) => void;
    accentColor?: string;
    compact?: boolean;
    disabled?: boolean;
    shortcutHint?: string | null;
    title?: string | null;
  }

  let {
    value,
    min,
    max,
    step = 1,
    label,
    unit = '',
    onchange,
    accentColor = '#00D4FF',
    compact = false,
    disabled = false,
    shortcutHint = null,
    title = null,
  }: Props = $props();

  let safeRange = $derived(Math.max(max - min, 1));
  let normalizedPercent = $derived(((value - min) / safeRange) * 100);
  let centerPercent = $derived(((0 - min) / safeRange) * 100);
  let fillStartPercent = $derived(Math.min(centerPercent, normalizedPercent));
  let fillEndPercent = $derived(Math.max(centerPercent, normalizedPercent));
  let displayValue = $derived(
    value === 0 ? '0' : value > 0 ? `+${value}` : `${value}`,
  );

  function handleInput(e: Event) {
    const target = e.target as HTMLInputElement;
    onchange(Number(target.value));
  }
</script>

<div
  class="bipolar-slider-wrapper"
  class:compact
  class:disabled
  data-shortcut-hint={shortcutHint ?? undefined}
  title={title ?? shortcutHint ?? undefined}
  style="--accent: {accentColor}; --center: {centerPercent}%; --fill-start: {fillStartPercent}%; --fill-end: {fillEndPercent}%;"
>
  <div class="slider-header">
    <span class="slider-label">{label}</span>
    <span class="slider-value">{displayValue}{unit ? '\u00a0' + unit : ''}</span>
  </div>

  <div class="slider-shell">
    <div class="slider-track" aria-hidden="true">
      <div class="slider-track-base">
        <div class="slider-track-fill"></div>
        <div class="slider-track-center"></div>
      </div>
    </div>
    <input
      type="range"
      {min}
      {max}
      {step}
      {value}
      {disabled}
      oninput={handleInput}
      class="slider-input"
      aria-label={label}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
    />
  </div>

  <div class="slider-axis" aria-hidden="true">
    <span class="axis-negative">-</span>
    <span class="axis-zero">0</span>
    <span class="axis-positive">+</span>
  </div>
</div>

<style>
  .bipolar-slider-wrapper {
    display: flex;
    flex-direction: column;
    gap: 3px;
    width: 100%;
    font-family: 'Roboto Mono', monospace;
  }

  .slider-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 10px;
    line-height: 1.4;
  }

  .compact .slider-header {
    font-size: 9px;
  }

  .slider-label {
    color: #6f8196;
    text-align: left;
  }

  .slider-value {
    color: #f0f5fa;
  }

  .disabled {
    opacity: 0.4;
    pointer-events: none;
  }

  .slider-shell {
    position: relative;
    display: flex;
    align-items: center;
    min-height: 16px;
  }

  .slider-track {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    pointer-events: none;
  }

  .slider-track-base {
    position: absolute;
    inset-inline: 0;
    height: 4px;
    border-radius: 999px;
    background: #0d1117;
    overflow: hidden;
  }

  .slider-track-base::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
      90deg,
      rgba(105, 121, 140, 0.04) 0%,
      rgba(105, 121, 140, 0.02) 50%,
      rgba(105, 121, 140, 0.04) 100%
    );
  }

  .slider-track-fill {
    position: absolute;
    left: var(--fill-start);
    width: calc(var(--fill-end) - var(--fill-start));
    height: 100%;
    background: var(--accent);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 16%, transparent);
  }

  .slider-track-center {
    position: absolute;
    left: calc(var(--center) - 1px);
    top: 50%;
    width: 2px;
    height: 12px;
    transform: translateY(-50%);
    border-radius: 999px;
    background: color-mix(in srgb, #d7e2ee 35%, #0d1117);
    box-shadow: 0 0 0 1px rgba(215, 226, 238, 0.04);
  }

  .slider-input {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 16px;
    border-radius: 999px;
    outline: none;
    cursor: pointer;
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
    position: relative;
    z-index: 1;
  }

  .slider-input::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 10px;
    height: 10px;
    border-radius: 2px;
    background: #ffffff;
    border: 1px solid var(--accent);
    cursor: pointer;
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 12%, transparent);
  }

  .slider-input::-moz-range-thumb {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    background: #ffffff;
    border: 1px solid var(--accent);
    cursor: pointer;
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 12%, transparent);
  }

  .slider-input::-moz-range-track,
  .slider-input::-moz-range-progress {
    background: transparent;
    height: 4px;
    border-radius: 999px;
  }

  .slider-input:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 3px;
    border-radius: 3px;
  }

  .slider-axis {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    align-items: center;
    color: #546578;
    font-size: 8px;
    letter-spacing: 0.06em;
    line-height: 1;
    user-select: none;
  }

  .axis-negative {
    justify-self: start;
  }

  .axis-zero {
    justify-self: center;
    color: #7b8da1;
  }

  .axis-positive {
    justify-self: end;
  }

  .compact .slider-track-base {
    height: 3px;
  }

  .compact .slider-track-center {
    height: 10px;
  }

  .compact .slider-input {
    height: 14px;
  }

  .compact .slider-input::-webkit-slider-thumb,
  .compact .slider-input::-moz-range-thumb {
    width: 7px;
    height: 7px;
  }

  .compact .slider-axis {
    font-size: 7px;
  }
</style>