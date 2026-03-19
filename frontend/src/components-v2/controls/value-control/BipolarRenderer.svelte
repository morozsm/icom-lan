<script lang="ts">
  import './value-control.css';
  import {
    getCenterPercent,
    getBipolarFill,
    calculateClickValue,
    handleKeyboardStep,
    handleWheelStep,
    debounce,
    formatBipolarValue,
  } from './value-control-core';

  interface Props {
    value: number;
    min: number;
    max: number;
    step: number;
    defaultValue?: number;
    fineStepDivisor?: number;
    label: string;
    displayFn?: (v: number) => string;
    fillColor?: string;
    fillGradient?: string[];
    trackColor?: string;
    accentColor?: string;
    showValue?: boolean;
    showLabel?: boolean;
    compact?: boolean;
    onChange: (value: number) => void;
    debounceMs?: number;
    disabled?: boolean;
    unit?: string;
    shortcutHint?: string | null;
    title?: string | null;
  }

  let {
    value,
    min,
    max,
    step,
    defaultValue = 0,
    fineStepDivisor = 10,
    label,
    displayFn,
    fillColor,
    fillGradient,
    trackColor = 'var(--v2-bg-gradient-start)',
    accentColor = 'var(--v2-accent-cyan)',
    showValue = true,
    showLabel = true,
    compact = false,
    onChange,
    debounceMs = 0,
    disabled = false,
    unit = '',
    shortcutHint = null,
    title = null,
  }: Props = $props();

  let containerEl: HTMLDivElement | null = $state(null);
  let isDragging = $state(false);

  // Derived values
  let centerPercent = $derived(getCenterPercent(min, max));
  let bipolarFill = $derived(getBipolarFill(value, min, max));
  let effectiveFill = $derived(fillGradient
    ? `linear-gradient(90deg, ${fillGradient.join(', ')})`
    : (fillColor ?? accentColor));
  let displayValue = $derived(displayFn
    ? displayFn(value)
    : `${formatBipolarValue(value)}${unit ? '\u00a0' + unit : ''}`);

  // Debounced change handler
  let debouncedOnChange = $derived.by(() => {
    if (debounceMs > 0) {
      return debounce((v: number) => onChange(v), debounceMs);
    }
    return (v: number) => onChange(v);
  });

  function emitChange(newValue: number) {
    if (newValue !== value) {
      debouncedOnChange(newValue);
    }
  }

  function handlePointerDown(e: PointerEvent) {
    if (disabled || !containerEl) return;

    e.preventDefault();
    const target = e.currentTarget as HTMLElement;
    target.setPointerCapture(e.pointerId);

    isDragging = true;

    // Calculate value from click position
    const rect = containerEl.getBoundingClientRect();
    const newValue = calculateClickValue(e.clientX, rect.left, rect.width, min, max, step);
    emitChange(newValue);
  }

  function handlePointerMove(e: PointerEvent) {
    if (!isDragging || disabled || !containerEl) return;

    const rect = containerEl.getBoundingClientRect();
    const newValue = calculateClickValue(e.clientX, rect.left, rect.width, min, max, step);
    emitChange(newValue);
  }

  function handlePointerUp(e: PointerEvent) {
    if (!isDragging) return;

    const target = e.currentTarget as HTMLElement;
    target.releasePointerCapture(e.pointerId);
    isDragging = false;
  }

  function handleWheel(e: WheelEvent) {
    if (disabled) return;
    e.preventDefault();

    const newValue = handleWheelStep(value, e.deltaY, step, fineStepDivisor, min, max, e.shiftKey);
    emitChange(newValue);
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (disabled) return;

    const newValue = handleKeyboardStep(value, e.key, step, fineStepDivisor, min, max, e.shiftKey);
    if (newValue !== null) {
      e.preventDefault();
      emitChange(newValue);
    }
  }

  function handleDoubleClick() {
    if (disabled) return;
    emitChange(defaultValue);
  }
</script>

<div
  class="vc-bipolar"
  class:compact
  class:disabled
  bind:this={containerEl}
  data-shortcut-hint={shortcutHint ?? undefined}
  title={title ?? shortcutHint ?? undefined}
  style="--vc-accent: {accentColor}; --vc-fill-color: {effectiveFill}; --vc-track-color: {trackColor}; --vc-center: {centerPercent}%; --vc-fill-start: {bipolarFill.fillStart}%; --vc-fill-end: {bipolarFill.fillEnd}%;"
>
  {#if showLabel || showValue}
    <div class="vc-header">
      {#if showLabel}
        <span class="vc-label">{label}</span>
      {/if}
      {#if showValue}
        <span class="vc-value">{displayValue}</span>
      {/if}
    </div>
  {/if}

  <div
    class="vc-track-container"
    role="slider"
    tabindex={disabled ? -1 : 0}
    aria-label={label}
    aria-valuemin={min}
    aria-valuemax={max}
    aria-valuenow={value}
    aria-disabled={disabled}
    onpointerdown={handlePointerDown}
    onpointermove={handlePointerMove}
    onpointerup={handlePointerUp}
    onpointercancel={handlePointerUp}
    onwheel={handleWheel}
    onkeydown={handleKeyDown}
    ondblclick={handleDoubleClick}
  >
    <div class="vc-track" aria-hidden="true">
      <div class="vc-track-base">
        <div class="vc-track-fill"></div>
        <div class="vc-track-center"></div>
      </div>
    </div>
    <div class="vc-thumb" aria-hidden="true"></div>
  </div>

  <div class="vc-axis" aria-hidden="true">
    <span class="axis-negative">-</span>
    <span class="axis-zero">0</span>
    <span class="axis-positive">+</span>
  </div>
</div>

<style>
  .vc-bipolar {
    display: flex;
    flex-direction: column;
    gap: var(--vc-gap, 3px);
    width: 100%;
    font-family: 'Roboto Mono', monospace;
  }

  .vc-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 10px;
    line-height: 1.4;
  }

  .compact .vc-header {
    font-size: 9px;
  }

  .vc-label {
    color: var(--vc-text-label, var(--v2-text-dim));
    text-align: left;
  }

  .vc-value {
    color: var(--vc-text-value, var(--v2-text-bright));
    font-family: 'Roboto Mono', monospace;
  }

  .disabled {
    opacity: 0.4;
    pointer-events: none;
  }

  .vc-track-container {
    position: relative;
    display: flex;
    align-items: center;
    min-height: 16px;
    cursor: pointer;
    outline: none;
    touch-action: none;
  }

  .compact .vc-track-container {
    min-height: 14px;
  }

  .vc-track-container:focus-visible {
    outline: var(--vc-focus-ring-width, 2px) solid var(--vc-accent);
    outline-offset: 3px;
    border-radius: 2px;
  }

  .vc-track {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    pointer-events: none;
  }

  .vc-track-base {
    position: absolute;
    inset-inline: 0;
    height: var(--vc-bar-height, 4px);
    border-radius: 999px;
    background: var(--vc-track-color, var(--v2-bg-gradient-start));
    overflow: hidden;
  }

  .compact .vc-track-base {
    height: var(--vc-bar-height-compact, 3px);
  }

  .vc-track-base::before {
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

  .vc-track-fill {
    position: absolute;
    left: var(--vc-fill-start);
    width: calc(var(--vc-fill-end) - var(--vc-fill-start));
    height: 100%;
    background: var(--vc-fill-color);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--vc-accent) 16%, transparent);
  }

  .vc-track-center {
    position: absolute;
    left: calc(var(--vc-center) - 1px);
    top: 50%;
    width: 2px;
    height: var(--vc-center-height, 12px);
    transform: translateY(-50%);
    border-radius: 999px;
    background: color-mix(in srgb, var(--v2-text-light) 35%, var(--v2-bg-gradient-start));
    box-shadow: 0 0 0 1px rgba(215, 226, 238, 0.04);
  }

  .compact .vc-track-center {
    height: var(--vc-center-height-compact, 10px);
  }

  .vc-thumb {
    position: absolute;
    left: var(--vc-fill-end);
    transform: translateX(-50%);
    width: var(--vc-thumb-size, 10px);
    height: var(--vc-thumb-size, 10px);
    border-radius: 2px;
    background: var(--v2-text-white);
    border: 1px solid var(--vc-accent);
    pointer-events: none;
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--vc-accent) 12%, transparent);
    transition: box-shadow var(--vc-transition-fast);
  }

  .compact .vc-thumb {
    width: var(--vc-thumb-size-compact, 7px);
    height: var(--vc-thumb-size-compact, 7px);
  }

  .vc-track-container:hover .vc-thumb {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--vc-accent) 20%, transparent);
  }

  .vc-axis {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    align-items: center;
    color: var(--v2-text-dimmer);
    font-size: 8px;
    letter-spacing: 0.06em;
    line-height: 1;
    user-select: none;
  }

  .compact .vc-axis {
    font-size: 7px;
  }

  .axis-negative {
    justify-self: start;
  }

  .axis-zero {
    justify-self: center;
    color: var(--v2-text-subtle);
  }

  .axis-positive {
    justify-self: end;
  }
</style>
