<script lang="ts">
  /**
   * VfoControlPanel — sidebar soft-button panel for the LCD skin.
   *
   * Evicted from the LCD surface per issue #844 / plan §9.1 (P5):
   * the display surfaces state, not command entry. These buttons
   * (A↔B, A=B, DW, SPLIT, XIT, CLR, TUNE, BK-OFF) were previously
   * rendered inside `AmberLcdDisplay` (`.lcd-vfo-ctrl-row`) and are
   * relocated here unchanged. Commands dispatched via the same
   * wiring/command-bus handlers as before.
   */
  import { radio } from '$lib/stores/radio.svelte';
  import { hasCapability } from '$lib/stores/capabilities.svelte';
  import {
    toRitXitProps,
    toVfoOpsProps,
  } from '../../wiring/state-adapter';
  import {
    makeVfoHandlers,
    makeRitXitHandlers,
    makeCwPanelHandlers,
  } from '../../wiring/command-bus';
  import { runtime } from '$lib/runtime';

  const vfoHandlers = makeVfoHandlers();
  const ritXitHandlers = makeRitXitHandlers();
  const cwHandlers = makeCwPanelHandlers();

  let radioState = $derived(radio.current);
  let ritXit = $derived(toRitXitProps(radioState, null));
  let vfoOps = $derived(toVfoOpsProps(radioState, null));
  let rx = $derived(radioState?.active === 'SUB' ? radioState?.sub : radioState?.main);
  let mode = $derived(rx?.mode ?? '---');
  let isCwMode = $derived(mode === 'CW' || mode === 'CW-R');
  let breakInMode = $derived(radioState?.breakIn ?? 0);
</script>

<div class="vfo-ctrl-panel">
  <button class="lcd-btn" onclick={vfoHandlers.onSwap}>A↔B</button>
  <button class="lcd-btn" onclick={vfoHandlers.onEqual}>A=B</button>
  {#if hasCapability('dual_rx')}
    <button class="lcd-btn" class:active={vfoOps.dualWatch} onclick={() => vfoHandlers.onDualWatchToggle(!vfoOps.dualWatch)}>DW</button>
  {/if}
  {#if hasCapability('split')}
    <button class="lcd-btn" class:active={vfoOps.splitActive} onclick={vfoHandlers.onSplitToggle}>SPLIT</button>
  {/if}
  {#if hasCapability('rit')}
    <button class="lcd-btn" class:active={ritXit.xitActive} onclick={ritXitHandlers.onXitToggle}>XIT</button>
    <button class="lcd-btn" onclick={ritXitHandlers.onClear}>CLR</button>
  {/if}
  {#if hasCapability('tuner')}
    <button class="lcd-btn" onclick={() => runtime.send('set_tuner_status', { value: 2 })}>TUNE</button>
  {/if}
  {#if isCwMode && hasCapability('cw') && hasCapability('break_in')}
    <button class="lcd-btn" class:active={breakInMode > 0} onclick={() => cwHandlers.onBreakInModeChange(breakInMode === 0 ? 1 : breakInMode === 1 ? 2 : 0)}>{breakInMode === 0 ? 'BK-OFF' : breakInMode === 1 ? 'SEMI' : 'FULL'}</button>
  {/if}
</div>

<style>
  .vfo-ctrl-panel {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px;
    border: 1px solid var(--v2-border-panel);
    border-radius: 4px;
    background:
      linear-gradient(180deg, var(--v2-panel-bg-gradient-top) 0%, var(--v2-panel-bg-gradient-bottom) 100%);
    box-shadow: var(--v2-shadow-sm);
    box-sizing: border-box;
  }

  .lcd-btn {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--v2-text-dim);
    background: transparent;
    border: 1.5px solid var(--v2-border-panel);
    border-radius: 3px;
    padding: 3px 8px;
    cursor: pointer;
    user-select: none;
  }
  .lcd-btn:hover {
    color: var(--v2-text);
    border-color: var(--v2-border);
  }
  .lcd-btn:active,
  .lcd-btn.active {
    color: var(--v2-text);
    border-color: var(--v2-accent, var(--v2-border));
  }
</style>
