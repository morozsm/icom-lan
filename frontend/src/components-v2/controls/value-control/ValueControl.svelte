<script lang="ts">
  import HBarRenderer from './HBarRenderer.svelte';
  import BipolarRenderer from './BipolarRenderer.svelte';
  import KnobRenderer from './KnobRenderer.svelte';
  import DiscreteRenderer from './DiscreteRenderer.svelte';

  interface Props {
    value: number;
    min: number;
    max: number;
    step: number;
    defaultValue?: number;
    fineStepDivisor?: number;
    label: string;
    displayFn?: (v: number) => string;
    renderer: 'hbar' | 'bipolar' | 'knob' | 'discrete';
    accentColor?: string;
    showValue?: boolean;
    showLabel?: boolean;
    compact?: boolean;
    variant?: 'modern' | 'hardware' | 'hardware-illuminated';
    // Knob-specific
    arcAngle?: number;
    tickCount?: number;
    tickLabels?: string[];
    /** Discrete renderer: when false, only draw ticks for the first tickLabels.length steps from min. */
    showAllTicks?: boolean;
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
    accentColor = 'var(--v2-accent-cyan)',
    showValue = true,
    showLabel = true,
    compact = false,
    variant = 'modern',
    arcAngle = 270,
    tickCount = 0,
    tickLabels = [],
    showAllTicks = true,
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
    accentColor,
    showValue,
    showLabel,
    compact,
    variant,
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

  let discreteProps = $derived({
    ...commonProps,
    tickLabels,
    showAllTicks,
  });
</script>

{#if renderer === 'hbar'}
  <HBarRenderer {...commonProps} />
{:else if renderer === 'bipolar'}
  <BipolarRenderer {...commonProps} />
{:else if renderer === 'knob'}
  <KnobRenderer {...knobProps} />
{:else if renderer === 'discrete'}
  <DiscreteRenderer {...discreteProps} />
{/if}
