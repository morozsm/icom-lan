<script lang="ts">
  import {
    TUNING_STEPS,
    getTuningStep,
    setTuningStep,
    formatStep,
    isAutoStep,
    setAutoStep,
  } from '../../lib/stores/tuning.svelte';
  import StepMenu from './StepMenu.svelte';

  let currentStep = $derived(getTuningStep());
  let auto = $derived(isAutoStep());
  let showStepMenu = $state(false);
  let pressTimer: ReturnType<typeof setTimeout>;

  function stepDown() {
    const idx = (TUNING_STEPS as readonly number[]).indexOf(currentStep);
    if (idx > 0) setTuningStep(TUNING_STEPS[idx - 1]);
  }

  function stepUp() {
    const idx = (TUNING_STEPS as readonly number[]).indexOf(currentStep);
    if (idx < TUNING_STEPS.length - 1) setTuningStep(TUNING_STEPS[idx + 1]);
  }

  function startLongPress() {
    pressTimer = setTimeout(() => (showStepMenu = true), 500);
  }

  function cancelLongPress() {
    clearTimeout(pressTimer);
  }
</script>

<div class="step-selector-compact">
  <span class="step-label">STEP</span>
  <button class="arrow-btn" onclick={stepDown} aria-label="Step down">◂</button>
  <button
    class="step-value"
    onpointerdown={startLongPress}
    onpointerup={cancelLongPress}
    onpointerleave={cancelLongPress}
    title="Long-press for step menu"
  >
    {formatStep(currentStep)}
  </button>
  <button class="arrow-btn" onclick={stepUp} aria-label="Step up">▸</button>
  <button class="auto-btn" class:active={auto} onclick={() => setAutoStep(!auto)}>AUTO</button>
</div>

{#if showStepMenu}
  <StepMenu
    onSelect={(step) => { setTuningStep(step); }}
    onClose={() => (showStepMenu = false)}
  />
{/if}

<style>
  .step-selector-compact {
    display: flex;
    align-items: center;
    gap: 2px;
  }

  .step-label {
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    color: var(--text-muted);
    user-select: none;
    margin-right: var(--space-1);
  }

  .arrow-btn {
    min-height: 28px;
    min-width: 28px;
    padding: 0;
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 0.75rem;
    cursor: pointer;
    transition: color 0.1s, border-color 0.1s;
  }

  .arrow-btn:hover {
    color: var(--text);
    border-color: var(--accent);
  }

  .step-value {
    min-height: 28px;
    padding: 0 var(--space-2);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    cursor: pointer;
    user-select: none;
    transition: border-color 0.1s;
  }

  .step-value:hover {
    border-color: var(--accent);
  }

  .auto-btn {
    min-height: 28px;
    padding: 0 var(--space-2);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    font-style: italic;
    cursor: pointer;
    transition: background 0.1s, color 0.1s, border-color 0.1s;
    margin-left: var(--space-1);
  }

  .auto-btn:hover {
    color: var(--text);
    border-color: var(--accent);
  }

  .auto-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
  }
</style>
