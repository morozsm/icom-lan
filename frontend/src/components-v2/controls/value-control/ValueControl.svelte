<script lang="ts">
  import HBarRenderer from './HBarRenderer.svelte';
  import BipolarRenderer from './BipolarRenderer.svelte';
  import KnobRenderer from './KnobRenderer.svelte';

  interface Props {
    value: number;
    min: number;
    max: number;
    step: number;
    defaultValue?: number;
    fineStepDivisor?: number;
    label: string;
    displayFn?: (v: number) => string;
    renderer: 'hbar' | 'bipolar' | 'knob';
    fillColor?: string;
    fillGradient?: string[];
    trackColor?: string;
    accentColor?: string;
    showValue?: boolean;
    showLabel?: boolean;
    compact?: boolean;
    // Knob-specific
    arcAngle?: number;
    tickCount?: number;
    tickLabels?: string[];
    // Behavior
    onChange: (value: number) => void;
    debounceMs?: number;
    disabled?: boolean;
    // Compat with existing sliders
    unit?: string;
    shortcutHint?: string | null;
    title?: string | null;
    // Legacy alias for onChange
    onchange?: (value: number) => void;
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
    renderer,
    fillColor,
    fillGradient,
    trackColor,
    accentColor = '#00D4FF',
    showValue = true,
    showLabel = true,
    compact = false,
    arcAngle = 270,
    tickCount = 0,
    tickLabels = [],
    onChange,
    debounceMs = 50,
    disabled = false,
    unit = '',
    shortcutHint = null,
    title = null,
    onchange,
  }: Props = $props();

  // Support both onChange and onchange (legacy)
  let effectiveOnChange = $derived(onChange ?? onchange ?? (() => {}));

  // Common props for all renderers
  let commonProps = $derived({
    value,
    min,
    max,
    step,
    defaultValue,
    fineStepDivisor,
    label,
    displayFn,
    fillColor,
    fillGradient,
    trackColor,
    accentColor,
    showValue,
    showLabel,
    compact,
    onChange: effectiveOnChange,
    debounceMs,
    disabled,
    unit,
    shortcutHint,
    title,
  });

  // Knob-specific props
  let knobProps = $derived({
    ...commonProps,
    arcAngle,
    tickCount,
    tickLabels,
  });
</script>

{#if renderer === 'hbar'}
  <HBarRenderer {...commonProps} />
{:else if renderer === 'bipolar'}
  <BipolarRenderer {...commonProps} />
{:else if renderer === 'knob'}
  <KnobRenderer {...knobProps} />
{/if}
