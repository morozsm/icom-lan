<script lang="ts">
  import {
    TUNING_STEPS,
    getTuningStep,
    setTuningStep,
    formatStep,
    isAutoStep,
    setAutoStep,
  } from '../../lib/stores/tuning.svelte';

  let currentStep = $derived(getTuningStep());
  let auto = $derived(isAutoStep());
</script>

<div class="step-selector">
  <span class="step-label">STEP</span>
  <div class="btn-bar" role="group" aria-label="Tuning step">
    {#each TUNING_STEPS as step}
      <button
        class="step-btn"
        class:active={currentStep === step && !auto}
        onclick={() => setTuningStep(step)}
        aria-pressed={currentStep === step}
      >{formatStep(step)}</button>
    {/each}
    <button
      class="step-btn auto-btn"
      class:active={auto}
      onclick={() => setAutoStep(true)}
      aria-pressed={auto}
      title="Auto step based on mode"
    >AUTO</button>
  </div>
</div>

<style>
  .step-selector {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .step-label {
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    color: var(--text-muted);
    user-select: none;
  }

  .btn-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
  }

  .step-btn {
    min-height: 28px;
    padding: 0 var(--space-2);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    cursor: pointer;
    transition: background 0.1s, color 0.1s, border-color 0.1s;
  }

  .step-btn:hover {
    color: var(--text);
    border-color: var(--accent);
  }

  .step-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
  }

  .auto-btn {
    font-style: italic;
  }
</style>
