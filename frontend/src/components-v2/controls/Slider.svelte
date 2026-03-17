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
  }

  let {
    value,
    min = 0,
    max = 255,
    step = 1,
    label,
    unit = '',
    onchange,
    accentColor = '#00D4FF',
    compact = false,
    disabled = false,
  }: Props = $props();

  let fillPercent = $derived(((value - min) / (max - min)) * 100);

  function handleInput(e: Event) {
    const target = e.target as HTMLInputElement;
    onchange(Number(target.value));
  }
</script>

<div class="slider-wrapper" class:compact class:disabled style="--accent: {accentColor}; --fill: {fillPercent}%">
  <div class="slider-header">
    <span class="slider-label">{label}</span>
    <span class="slider-value">{value}{unit ? '\u00a0' + unit : ''}</span>
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
    color: #6F8196;
    text-align: left;
  }

  .slider-value {
    color: #F0F5FA;
    font-family: 'Roboto Mono', monospace;
  }

  .disabled {
    opacity: 0.4;
    pointer-events: none;
  }

  /* --- range input reset + custom styling --- */

  .slider-input {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 3px;
    border-radius: 1px;
    outline: none;
    cursor: pointer;
    background: linear-gradient(
      to right,
      var(--accent) 0%,
      var(--accent) var(--fill),
      #0D1117 var(--fill),
      #0D1117 100%
    );
    border: none;
    padding: 0;
    margin: 0;
  }

  .compact .slider-input {
    height: 2px;
  }

  /* Webkit thumb */
  .slider-input::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 10px;
    height: 10px;
    border-radius: 2px;
    background: #ffffff;
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
    background: #ffffff;
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
    height: 3px;
    border-radius: 1px;
    background: #0D1117;
  }

  .compact .slider-input::-moz-range-track {
    height: 2px;
  }

  .slider-input::-moz-range-progress {
    height: 3px;
    border-radius: 1px 0 0 1px;
    background: var(--accent);
  }

  .compact .slider-input::-moz-range-progress {
    height: 2px;
  }

  .slider-input:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 3px;
    border-radius: 2px;
  }
</style>
