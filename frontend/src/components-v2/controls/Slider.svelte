<!--
  @deprecated Use ValueControl with renderer="hbar" instead.
  This component is kept for backwards compatibility only.

  Migration:
    <Slider value={x} min={0} max={100} label="Label" onchange={fn} />
    becomes:
    <ValueControl value={x} min={0} max={100} step={1} label="Label" renderer="hbar" onChange={fn} />
-->
<script lang="ts">
  interface Props {
    value: number;
    min?: number;
    max?: number;
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
    min = 0,
    max = 255,
    step = 1,
    label,
    unit = '',
    onchange,
    accentColor = 'var(--v2-accent-cyan)',
    compact = false,
    disabled = false,
    shortcutHint = null,
    title = null,
  }: Props = $props();

  let fillPercent = $derived(((value - min) / (max - min)) * 100);
  let isBipolar = $derived(min < 0 && max > 0);
  let centerPercent = $derived(((0 - min) / (max - min)) * 100);
  let fillStartPercent = $derived(isBipolar ? Math.min(centerPercent, fillPercent) : 0);
  let fillEndPercent = $derived(isBipolar ? Math.max(centerPercent, fillPercent) : fillPercent);

  function handleInput(e: Event) {
    const target = e.target as HTMLInputElement;
    onchange(Number(target.value));
  }
</script>

<div
  class="slider-wrapper"
  class:compact
  class:disabled
  class:bipolar={isBipolar}
  data-shortcut-hint={shortcutHint ?? undefined}
  title={title ?? shortcutHint ?? undefined}
  style="--accent: {accentColor}; --fill: {fillPercent}%; --center: {centerPercent}%; --fill-start: {fillStartPercent}%; --fill-end: {fillEndPercent}%;"
>
  <div class="slider-header">
    <span class="slider-label">{label}</span>
    <span class="slider-value">{value}{unit ? '\u00a0' + unit : ''}</span>
  </div>
  <div class="slider-shell">
    <div class="slider-track" aria-hidden="true">
      <div class="slider-track-base"></div>
      {#if isBipolar}
        <div class="slider-track-center"></div>
      {/if}
      <div class="slider-track-fill"></div>
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
</div>

<style>
  .slider-wrapper {
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
    color: var(--v2-text-dim);
    text-align: left;
  }

  .slider-value {
    color: var(--v2-text-bright);
    font-family: 'Roboto Mono', monospace;
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

  .slider-track-base,
  .slider-track-fill {
    position: absolute;
    border-radius: 999px;
  }

  .slider-track-base {
    inset-inline: 0;
    height: 4px;
    background: var(--v2-bg-gradient-start);
  }

  .slider-track-fill {
    left: var(--fill-start);
    width: calc(var(--fill-end) - var(--fill-start));
    height: 4px;
    background: var(--accent);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 14%, transparent);
  }

  .slider-track-center {
    position: absolute;
    left: calc(var(--center) - 1px);
    width: 2px;
    height: 10px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--v2-text-light) 30%, var(--v2-bg-gradient-start));
  }

  .compact .slider-track-base,
  .compact .slider-track-fill {
    height: 3px;
  }

  .compact .slider-track-center {
    height: 8px;
  }

  /* --- range input reset + custom styling --- */

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

  .compact .slider-input {
    height: 14px;
  }

  /* Webkit thumb */
  .slider-input::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 10px;
    height: 10px;
    border-radius: 2px;
    background: var(--v2-text-white);
    border: 1px solid var(--accent);
    cursor: pointer;
    box-shadow: none;
    transition: box-shadow 0.15s ease;
  }

  .compact .slider-input::-webkit-slider-thumb {
    width: 7px;
    height: 7px;
  }

  .slider-input::-webkit-slider-thumb:hover {
    box-shadow: none;
  }

  /* Moz thumb */
  .slider-input::-moz-range-thumb {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    background: var(--v2-text-white);
    border: 1px solid var(--accent);
    cursor: pointer;
    box-shadow: none;
  }

  .compact .slider-input::-moz-range-thumb {
    width: 7px;
    height: 7px;
  }

  /* Moz track override (Firefox ignores background gradient on input) */
  .slider-input::-moz-range-track {
    height: 4px;
    border-radius: 999px;
    background: transparent;
  }

  .compact .slider-input::-moz-range-track {
    height: 3px;
  }

  .slider-input::-moz-range-progress {
    height: 4px;
    border-radius: 999px;
    background: transparent;
  }

  .compact .slider-input::-moz-range-progress {
    height: 3px;
  }

  .slider-input:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 3px;
    border-radius: 2px;
  }
</style>
