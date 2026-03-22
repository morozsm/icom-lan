<script lang="ts">
  import './value-control.css';
  import {
    getFillPercent,
    calculateClickValue,
    calculateDragValue,
    handleKeyboardStep,
    handleWheelStep,
    debounce,
    clamp,
    snapToStep,
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
    variant?: 'modern' | 'hardware' | 'hardware-illuminated';
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
    defaultValue,
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
    variant = 'modern',
    onChange,
    debounceMs = 0,
    disabled = false,
    unit = '',
    shortcutHint = null,
    title = null,
  }: Props = $props();

  let containerEl: HTMLDivElement | null = $state(null);
  let isDragging = $state(false);
  let dragStartValue = $state(0);
  let dragStartX = $state(0);

  // Derived values
  let fillPercent = $derived(getFillPercent(value, min, max));
  let effectiveDefault = $derived(defaultValue ?? min);
  let effectiveFill = $derived(fillGradient
    ? `linear-gradient(90deg, ${fillGradient.join(', ')})`
    : (fillColor ?? accentColor));
  let displayValue = $derived(displayFn ? displayFn(value) : `${value}${unit ? '\u00a0' + unit : ''}`);

  // Debounced change handler
  let debouncedOnChange = $derived.by<(...args: unknown[]) => void>(() => {
    if (debounceMs > 0) {
      return debounce((v: number) => onChange(v), debounceMs) as (...args: unknown[]) => void;
    }
    return ((v: number) => onChange(v)) as (...args: unknown[]) => void;
  });

  function emitChange(newValue: number, immediate = false) {
    if (newValue !== value) {
      if (immediate) {
        onChange(newValue);
      } else {
        debouncedOnChange(newValue);
      }
    }
  }

  function handlePointerDown(e: PointerEvent) {
    if (disabled || !containerEl) return;

    e.preventDefault();
    const target = e.currentTarget as HTMLElement;
    target.setPointerCapture(e.pointerId);

    isDragging = true;
    dragStartX = e.clientX;

    // Calculate value from click position
    const rect = containerEl.getBoundingClientRect();
    const newValue = calculateClickValue(e.clientX, rect.left, rect.width, min, max, step);
    dragStartValue = newValue;
    emitChange(newValue, true);
  }

  function handlePointerMove(e: PointerEvent) {
    if (!isDragging || disabled || !containerEl) return;

    const rect = containerEl.getBoundingClientRect();
    const newValue = calculateClickValue(e.clientX, rect.left, rect.width, min, max, step);
    emitChange(newValue, true);
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

    const wheelMultiplier = e.shiftKey ? 1 : 4;
    const effectiveStep = e.shiftKey ? step / fineStepDivisor : step * wheelMultiplier;
    const direction = e.deltaY > 0 ? -1 : 1;
    const newValue = clamp(
      snapToStep(value + direction * effectiveStep, effectiveStep, min),
      min,
      max,
    );
    emitChange(newValue, true);
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
    emitChange(effectiveDefault);
  }
</script>

<div
  class="vc-hbar"
  class:compact
  class:disabled
  class:hardware={variant === 'hardware'}
  class:hw-illum={variant === 'hardware-illuminated'}
  bind:this={containerEl}
  data-shortcut-hint={shortcutHint ?? undefined}
  title={title ?? shortcutHint ?? undefined}
  style="--vc-accent: {accentColor}; --vc-fill-color: {effectiveFill}; --vc-track-color: {trackColor}; --vc-fill-percent: {fillPercent}%; --vc-fill-ratio: {fillPercent / 100};"
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
    {#if variant === 'hardware-illuminated'}
      <!-- 5-layer illuminated slider -->
      <div class="hil-frame" aria-hidden="true">
        <div class="hil-channel">
          <div class="hil-slot"></div>
        </div>
      </div>
      <div class="hil-thumb" aria-hidden="true">
        <div class="hil-slit"></div>
      </div>
    {:else}
      <div class="vc-track" aria-hidden="true">
        <div class="vc-track-base"></div>
        <div class="vc-track-fill"></div>
      </div>
      <div class="vc-thumb" aria-hidden="true"></div>
    {/if}
  </div>
</div>

<style>
  .vc-hbar {
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

  .vc-track-base,
  .vc-track-fill {
    position: absolute;
    border-radius: 999px;
  }

  .vc-track-base {
    inset-inline: 0;
    height: var(--vc-bar-height, 4px);
    background: var(--vc-track-color, var(--v2-bg-gradient-start));
  }

  .compact .vc-track-base {
    height: var(--vc-bar-height-compact, 3px);
  }

  .vc-track-fill {
    left: 0;
    width: var(--vc-fill-percent);
    height: var(--vc-bar-height, 4px);
    background: var(--vc-fill-color);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--vc-accent) 6%, transparent);
  }

  .compact .vc-track-fill {
    height: var(--vc-bar-height-compact, 3px);
  }

  .vc-thumb {
    position: absolute;
    left: var(--vc-fill-percent);
    transform: translateX(-50%);
    width: var(--vc-thumb-size, 10px);
    height: var(--vc-thumb-size, 10px);
    border-radius: 2px;
    background: var(--v2-text-white);
    border: 1px solid var(--vc-accent);
    pointer-events: none;
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--vc-accent) 5%, transparent);
    transition: box-shadow var(--vc-transition-fast);
  }

  .compact .vc-thumb {
    width: var(--vc-thumb-size-compact, 7px);
    height: var(--vc-thumb-size-compact, 7px);
  }

  .vc-track-container:hover .vc-thumb {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--vc-accent) 10%, transparent);
  }

  /* ── Hardware variant ─────────────────────────────────────────────────── */

  /* Recessed groove track */
  .hardware .vc-track-base {
    height: 6px;
    border-radius: 1px;
    background: #060a0d;
    box-shadow:
      inset 0 2px 3px rgba(0, 0, 0, 0.9),
      inset 0 0 0 1px rgba(0, 0, 0, 0.5),
      0 1px 0 rgba(255, 255, 255, 0.04);
  }

  .hardware.compact .vc-track-base {
    height: 5px;
  }

  /* Flat warm fill — no glow, slightly dimmed */
  .hardware .vc-track-fill {
    border-radius: 0;
    box-shadow: none;
    opacity: 0.7;
  }

  /* Calibration scale marks — fine ticks + coarser every 5th */
  .hardware .vc-track-container::after {
    content: '';
    position: absolute;
    inset-inline: 0;
    bottom: 0px;
    height: 8px;
    pointer-events: none;
    /* Fine tick every 12px, brighter every 60px (5th) via layered gradients */
    background:
      repeating-linear-gradient(
        90deg,
        rgba(255, 255, 255, 0.22) 0px,
        rgba(255, 255, 255, 0.22) 1px,
        transparent 1px,
        transparent 60px
      ),
      repeating-linear-gradient(
        90deg,
        rgba(255, 255, 255, 0.09) 0px,
        rgba(255, 255, 255, 0.09) 1px,
        transparent 1px,
        transparent 12px
      );
    border-radius: 0 0 1px 1px;
  }

  /* Physical slider handle — wider, rounder, tactile */
  .hardware .vc-thumb {
    width: 8px;
    height: 22px;
    border-radius: 2px;
    /* Warm machined-metal gradient: cool shadow edges, warm incandescent peak */
    background: linear-gradient(
      to right,
      #505860 0%,
      #8a9298 18%,
      #c8d0d4 40%,
      #ece8de 52%,
      #ccc4b8 64%,
      #90888c 82%,
      #484c52 100%
    );
    border: 1px solid rgba(0, 0, 0, 0.7);
    box-shadow:
      0 2px 5px rgba(0, 0, 0, 0.8),
      inset 0 1px 0 rgba(255, 255, 255, 0.5),
      inset 0 -1px 0 rgba(0, 0, 0, 0.3);
  }

  .hardware.compact .vc-thumb {
    width: 6px;
    height: 16px;
  }

  .hardware .vc-track-container:hover .vc-thumb {
    box-shadow:
      0 2px 5px rgba(0, 0, 0, 0.8),
      inset 0 1px 0 rgba(255, 255, 255, 0.5),
      inset 0 -1px 0 rgba(0, 0, 0, 0.3),
      0 0 0 1px rgba(255, 248, 220, 0.12);
  }

  /* Warmer/brighter label text in hardware context */
  .hardware .vc-label {
    color: var(--vc-text-label, #8a9e78);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    font-size: 9px;
  }

  .hardware .vc-value {
    color: var(--vc-text-value, #c8d8a8);
  }

  /* ── Hardware Illuminated variant (5-layer) ──────────────────────────── */

  .hw-illum .vc-label {
    color: var(--vc-text-label, #8a9e78);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    font-size: 9px;
  }

  .hw-illum .vc-value {
    color: var(--vc-text-value, #c8d8a8);
  }

  .hw-illum .vc-track-container {
    min-height: 28px;
  }

  /* Layer 1: Outer diffuser frame — oval backlit plastic bezel */
  .hw-illum .hil-frame {
    position: absolute;
    inset: 2px 0;
    border-radius: 14px;
    border: 2px solid rgba(180, 140, 90, 0.15);
    background: transparent;
    box-shadow:
      0 0 8px rgba(210, 165, 110, calc(0.08 + 0.12 * var(--vc-fill-ratio, 0.5))),
      0 0 16px rgba(210, 165, 110, calc(0.04 + 0.06 * var(--vc-fill-ratio, 0.5))),
      inset 0 0 6px rgba(210, 165, 110, calc(0.03 + 0.05 * var(--vc-fill-ratio, 0.5)));
    pointer-events: none;
  }

  /* Layer 2: Recessed milled channel */
  .hw-illum .hil-channel {
    position: absolute;
    inset: 4px 8px;
    border-radius: 3px;
    background: #050708;
    box-shadow:
      inset 0 2px 4px rgba(0, 0, 0, 0.95),
      inset 0 -1px 2px rgba(0, 0, 0, 0.6),
      inset 0 0 0 1px rgba(0, 0, 0, 0.5);
  }

  /* Layer 3: Illuminated slot — light through opening */
  .hw-illum .hil-slot {
    position: absolute;
    top: 50%;
    left: 4px;
    right: 4px;
    height: 3px;
    transform: translateY(-50%);
    border-radius: 1.5px;
    background: linear-gradient(
      90deg,
      rgba(210, 165, 110, calc(0.15 + 0.25 * var(--vc-fill-ratio, 0.5))) 0%,
      rgba(220, 175, 120, calc(0.2 + 0.5 * var(--vc-fill-ratio, 0.5))) var(--vc-fill-percent),
      rgba(180, 140, 90, 0.06) calc(var(--vc-fill-percent) + 2%),
      rgba(120, 90, 60, 0.03) 100%
    );
    box-shadow:
      0 0 4px rgba(210, 165, 110, calc(0.1 + 0.3 * var(--vc-fill-ratio, 0.5))),
      0 0 8px rgba(210, 165, 110, calc(0.05 + 0.15 * var(--vc-fill-ratio, 0.5)));
  }

  /* Layer 4: Wide thumb carriage — machined metal, raised */
  .hw-illum .hil-thumb {
    position: absolute;
    left: var(--vc-fill-percent);
    top: 50%;
    transform: translate(-50%, -50%);
    width: 24px;
    height: 26px;
    border-radius: 3px;
    pointer-events: none;
    background: linear-gradient(
      to right,
      #3a3e44 0%,
      #585c62 8%,
      #6a6e74 20%,
      #787c82 35%,
      #848890 50%,
      #787c82 65%,
      #6a6e74 80%,
      #585c62 92%,
      #3a3e44 100%
    );
    border: 1px solid rgba(0, 0, 0, 0.8);
    box-shadow:
      0 3px 8px rgba(0, 0, 0, 0.9),
      0 1px 3px rgba(0, 0, 0, 0.7),
      inset 0 1px 0 rgba(255, 255, 255, 0.25),
      inset 0 -1px 0 rgba(0, 0, 0, 0.4),
      inset 1px 0 0 rgba(255, 255, 255, 0.08),
      inset -1px 0 0 rgba(255, 255, 255, 0.08);
  }

  /* Layer 5: Center slit — lamp light transmitted through carriage */
  .hw-illum .hil-slit {
    position: absolute;
    top: 3px;
    bottom: 3px;
    left: 50%;
    width: 2px;
    transform: translateX(-50%);
    border-radius: 1px;
    background: rgba(220, 175, 120, calc(0.3 + 0.5 * var(--vc-fill-ratio, 0.5)));
    box-shadow:
      0 0 4px rgba(210, 165, 110, calc(0.2 + 0.4 * var(--vc-fill-ratio, 0.5))),
      0 0 8px rgba(210, 165, 110, calc(0.1 + 0.2 * var(--vc-fill-ratio, 0.5)));
  }

  .hw-illum .vc-track-container:hover .hil-thumb {
    box-shadow:
      0 3px 8px rgba(0, 0, 0, 0.9),
      0 1px 3px rgba(0, 0, 0, 0.7),
      inset 0 1px 0 rgba(255, 255, 255, 0.3),
      inset 0 -1px 0 rgba(0, 0, 0, 0.4),
      inset 1px 0 0 rgba(255, 255, 255, 0.12),
      inset -1px 0 0 rgba(255, 255, 255, 0.12),
      0 0 0 1px rgba(210, 165, 110, 0.15);
  }
</style>
