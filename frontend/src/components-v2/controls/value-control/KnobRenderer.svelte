<script lang="ts">
  import './value-control.css';
  import {
    valueToPosition,
    calculateArcPath,
    calculateIndicatorPosition,
    generateTickPositions,
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
    arcAngle?: number;
    tickCount?: number;
    tickLabels?: string[];
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
    trackColor = 'var(--v2-bg-panel)',
    accentColor = 'var(--v2-accent-cyan)',
    showValue = true,
    showLabel = true,
    compact = false,
    arcAngle = 270,
    tickCount = 0,
    tickLabels = [],
    onChange,
    debounceMs = 0,
    disabled = false,
    unit = '',
    shortcutHint = null,
    title = null,
  }: Props = $props();

  let containerEl: HTMLDivElement | null = $state(null);
  let isDragging = $state(false);
  let dragStartY = $state(0);
  let dragStartValue = $state(0);

  // SVG dimensions (reactive based on compact prop)
  let size = $derived(compact ? 48 : 64);
  let cx = $derived(size / 2);
  let cy = $derived(size / 2);
  let radius = $derived((size - 12) / 2);
  let trackWidth = $derived(compact ? 4 : 5);
  let indicatorLength = $derived(radius - trackWidth - 4);

  // Derived values
  let effectiveDefault = $derived(defaultValue ?? min);
  let position = $derived(valueToPosition(value, min, max));
  let startAngle = $derived(-arcAngle / 2);
  let endAngle = $derived(arcAngle / 2);
  let currentAngle = $derived(startAngle + position * arcAngle);

  // Arc paths
  let trackPath = $derived(calculateArcPath(cx, cy, radius, startAngle, endAngle));
  let fillPath = $derived(calculateArcPath(cx, cy, radius, startAngle, currentAngle));

  // Indicator position
  let indicatorPos = $derived(calculateIndicatorPosition(cx, cy, indicatorLength, value, min, max, arcAngle));
  let indicatorEnd = $derived(calculateIndicatorPosition(cx, cy, radius - trackWidth - 2, value, min, max, arcAngle));

  // Tick marks
  let ticks = $derived(tickCount > 0
    ? generateTickPositions(cx, cy, radius + 2, radius + 6, tickCount, arcAngle)
    : []);

  // Gradient or solid fill
  let gradientId = $derived(`knob-gradient-${Math.random().toString(36).slice(2)}`);
  let hasGradient = $derived(fillGradient && fillGradient.length > 1);

  // Display value
  let displayValue = $derived(displayFn ? displayFn(value) : `${value}${unit ? unit : ''}`);

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
    if (disabled) return;

    e.preventDefault();
    const target = e.currentTarget as HTMLElement;
    target.setPointerCapture(e.pointerId);

    isDragging = true;
    dragStartY = e.clientY;
    dragStartValue = value;
  }

  function handlePointerMove(e: PointerEvent) {
    if (!isDragging || disabled) return;

    // Vertical drag: up = increase, down = decrease
    const deltaY = dragStartY - e.clientY;
    const sensitivity = e.shiftKey ? 0.5 : 2; // pixels per step
    const stepDelta = Math.round(deltaY / sensitivity);
    const effectiveStep = e.shiftKey ? step / fineStepDivisor : step;
    const newValue = clamp(
      snapToStep(dragStartValue + stepDelta * effectiveStep, effectiveStep, min),
      min,
      max
    );
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
    emitChange(effectiveDefault);
  }
</script>

<div
  class="vc-knob"
  class:compact
  class:disabled
  bind:this={containerEl}
  data-shortcut-hint={shortcutHint ?? undefined}
  title={title ?? shortcutHint ?? undefined}
  style="--vc-accent: {accentColor}; --vc-knob-size: {size}px;"
>
  {#if showLabel}
    <span class="vc-label">{label}</span>
  {/if}

  <div
    class="vc-knob-container"
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
    <svg
      width={size}
      height={size}
      viewBox="0 0 {size} {size}"
      class="vc-knob-svg"
    >
      {#if hasGradient}
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
            {#each fillGradient as color, i}
              <stop offset="{(i / (fillGradient.length - 1)) * 100}%" stop-color={color} />
            {/each}
          </linearGradient>
        </defs>
      {/if}

      <!-- Track arc -->
      <path
        d={trackPath}
        fill="none"
        stroke={trackColor}
        stroke-width={trackWidth}
        stroke-linecap="round"
        class="vc-knob-track"
      />

      <!-- Fill arc -->
      {#if position > 0}
        <path
          d={fillPath}
          fill="none"
          stroke={hasGradient ? `url(#${gradientId})` : (fillColor ?? accentColor)}
          stroke-width={trackWidth}
          stroke-linecap="round"
          class="vc-knob-fill"
        />
      {/if}

      <!-- Tick marks -->
      {#each ticks as tick}
        <line
          x1={tick.x1}
          y1={tick.y1}
          x2={tick.x2}
          y2={tick.y2}
          stroke="var(--v2-text-disabled)"
          stroke-width="1"
          class="vc-knob-tick"
        />
      {/each}

      <!-- Indicator line -->
      <line
        x1={cx}
        y1={cy}
        x2={indicatorEnd.x}
        y2={indicatorEnd.y}
        stroke="var(--v2-text-white)"
        stroke-width="2"
        stroke-linecap="round"
        class="vc-knob-indicator"
      />

      <!-- Center dot -->
      <circle
        cx={cx}
        cy={cy}
        r="3"
        fill="var(--v2-bg-gradient-panel)"
        stroke="var(--v2-text-disabled)"
        stroke-width="1"
        class="vc-knob-center"
      />
    </svg>

    {#if showValue}
      <div class="vc-knob-value">{displayValue}</div>
    {/if}
  </div>

  {#if tickLabels.length > 0}
    <div class="vc-tick-labels">
      {#each tickLabels as tickLabel}
        <span class="vc-tick-label">{tickLabel}</span>
      {/each}
    </div>
  {/if}
</div>

<style>
  .vc-knob {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    font-family: 'Roboto Mono', monospace;
  }

  .vc-label {
    color: var(--vc-text-label, var(--v2-text-dim));
    font-size: 10px;
    text-align: center;
  }

  .compact .vc-label {
    font-size: 9px;
  }

  .disabled {
    opacity: 0.4;
    pointer-events: none;
  }

  .vc-knob-container {
    position: relative;
    width: var(--vc-knob-size);
    height: var(--vc-knob-size);
    cursor: grab;
    outline: none;
    touch-action: none;
  }

  .vc-knob-container:active {
    cursor: grabbing;
  }

  .vc-knob-container:focus-visible {
    outline: var(--vc-focus-ring-width, 2px) solid var(--vc-accent);
    outline-offset: 4px;
    border-radius: 50%;
  }

  .vc-knob-svg {
    display: block;
  }

  .vc-knob-track {
    opacity: 0.6;
  }

  .vc-knob-fill {
    filter: drop-shadow(0 0 3px color-mix(in srgb, var(--vc-accent) 50%, transparent));
  }

  .vc-knob-indicator {
    filter: drop-shadow(0 0 2px rgba(255, 255, 255, 0.3));
  }

  .vc-knob-value {
    position: absolute;
    bottom: -2px;
    left: 50%;
    transform: translateX(-50%);
    color: var(--vc-text-value, var(--v2-text-bright));
    font-size: 10px;
    font-weight: 500;
    white-space: nowrap;
  }

  .compact .vc-knob-value {
    font-size: 9px;
    bottom: 0;
  }

  .vc-tick-labels {
    display: flex;
    justify-content: space-between;
    width: 100%;
    padding: 0 2px;
  }

  .vc-tick-label {
    color: var(--v2-text-dimmer);
    font-size: 8px;
  }
</style>
