<script lang="ts">
  import { onMount } from 'svelte';
  import {
    LCD_CONTRAST_PRESETS,
    applyLcdContrast,
    getLcdContrastPreset,
    setLcdContrastPreset,
    stepLcdContrast,
    type LcdContrastPreset,
  } from '$lib/stores/lcd-contrast.svelte';

  // LCD contrast control — extracted from AmberLcdDisplay per issue #861.
  // Presets + Shift+[/] keyboard shortcut preserved verbatim from #833.
  let contrastPreset = $state<LcdContrastPreset>(getLcdContrastPreset());

  function selectContrast(p: LcdContrastPreset): void {
    setLcdContrastPreset(p);
    contrastPreset = p;
  }

  function handleContrastKey(event: KeyboardEvent): void {
    if (!event.shiftKey) return;
    // Ignore when focus is in a text field.
    const tag = (document.activeElement?.tagName ?? '').toUpperCase();
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    // Shift+[ and Shift+] produce '{' and '}' on most US/EU layouts.
    // Also accept the bare bracket keys in case the layout maps them directly.
    const key = event.key;
    let direction: 'up' | 'down' | null = null;
    if (key === '{' || key === '[') direction = 'down';
    else if (key === '}' || key === ']') direction = 'up';
    if (!direction) return;
    event.preventDefault();
    contrastPreset = stepLcdContrast(direction);
  }

  onMount(() => {
    applyLcdContrast();
    window.addEventListener('keydown', handleContrastKey);
    return () => {
      window.removeEventListener('keydown', handleContrastKey);
    };
  });
</script>

<div class="lcd-contrast-row" role="radiogroup" aria-label="LCD contrast preset">
  <span class="lcd-contrast-label">CONTRAST</span>
  {#each LCD_CONTRAST_PRESETS as p}
    <button
      type="button"
      class="lcd-contrast-btn"
      class:active={contrastPreset === p}
      role="radio"
      aria-checked={contrastPreset === p}
      aria-label="Contrast preset {p}"
      onclick={() => selectContrast(p)}
    >{p}</button>
  {/each}
</div>

<style>
  .lcd-contrast-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    padding: 4px 8px;
  }
  .lcd-contrast-label {
    font: 700 10px/1 'JetBrains Mono', monospace;
    letter-spacing: 0.1em;
    color: var(--v2-text-dim, rgba(200, 160, 48, 0.7));
  }
  .lcd-contrast-btn {
    font: 700 11px/1 'JetBrains Mono', monospace;
    color: var(--v2-text-dim, rgba(200, 160, 48, 0.7));
    background: transparent;
    border: 1px solid var(--v2-border-panel, rgba(200, 160, 48, 0.3));
    border-radius: 3px;
    padding: 3px 8px;
    cursor: pointer;
    transition: border-color 0.12s, color 0.12s;
  }
  .lcd-contrast-btn:hover {
    border-color: var(--v2-border-darker, rgba(200, 160, 48, 0.55));
    color: var(--v2-text, rgba(200, 160, 48, 0.9));
  }
  .lcd-contrast-btn.active {
    color: var(--v2-text, rgba(200, 160, 48, 1));
    border-color: var(--v2-border-darker, rgba(200, 160, 48, 0.7));
  }
</style>
