<!--
  LcdDisplayModeControl — radio-group chooser for LCD display effects
  (#838). Mirrors the LcdContrastControl affordance for consistency;
  lives next to it in the LCD control strip.

  "clean" is the default — no extra effects on top of the base render.
  Vintage / CRT / Flicker are opt-in vanity modes; all layered via
  `panels/lcd/lcd-vintage.css` applied as `.lcd-mode-{mode}` class on
  `.lcd-frame` in LcdLayout.
-->
<script lang="ts">
  import {
    LCD_DISPLAY_MODES,
    getLcdDisplayMode,
    setLcdDisplayMode,
    type LcdDisplayMode,
  } from '$lib/runtime/adapters/lcd-chrome-adapter';

  let mode = $state<LcdDisplayMode>(getLcdDisplayMode());

  function selectMode(m: LcdDisplayMode): void {
    setLcdDisplayMode(m);
    mode = m;
  }

  function labelFor(m: LcdDisplayMode): string {
    switch (m) {
      case 'clean':   return 'CLEAN';
      case 'vintage': return 'VINTAGE';
      case 'crt':     return 'CRT';
      case 'flicker': return 'FLICKER';
    }
  }
</script>

<div class="lcd-mode-row" role="radiogroup" aria-label="LCD display mode">
  <span class="lcd-mode-label">DISPLAY</span>
  {#each LCD_DISPLAY_MODES as m}
    <button
      type="button"
      class="lcd-mode-btn"
      class:active={mode === m}
      role="radio"
      aria-checked={mode === m}
      aria-label="Display mode {labelFor(m)}"
      onclick={() => selectMode(m)}
    >{labelFor(m)}</button>
  {/each}
</div>

<style>
  .lcd-mode-row {
    display: flex;
    align-items: center;
    gap: 4px;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
  }

  .lcd-mode-label {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--v2-text-dim, #777);
    margin-right: 4px;
  }

  .lcd-mode-btn {
    font-family: inherit;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 2px 6px;
    border: 1px solid var(--v2-border-panel, #333);
    border-radius: 3px;
    background: transparent;
    color: var(--v2-text-dim, #888);
    cursor: pointer;
  }

  .lcd-mode-btn:hover {
    border-color: var(--v2-border-lighter, #555);
    color: var(--v2-text, #ddd);
  }

  .lcd-mode-btn.active {
    background: rgba(250, 204, 21, 0.12);
    border-color: var(--v2-accent-yellow, #facc15);
    color: var(--v2-accent-yellow, #facc15);
  }
</style>
