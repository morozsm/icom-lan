<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { radio } from '../../lib/stores/radio.svelte';
  import { getTuningStep, snapToStep, formatStep } from '../../lib/stores/tuning.svelte';
  import { vibrate } from '../../lib/utils/haptics';

  let wheelEl: HTMLDivElement;
  let dragging = false;
  let startX = 0;
  let accumDx = 0;

  // Pixels per step — how far to drag for one step
  const PX_PER_STEP = 30;

  function receiverIdx(): number {
    return radio.current?.active === 'SUB' ? 1 : 0;
  }

  function currentFreq(): number {
    const rx = radio.current?.active === 'SUB' ? radio.current?.sub : radio.current?.main;
    return rx?.freqHz ?? 0;
  }

  function tune(direction: number): void {
    const step = getTuningStep();
    const freq = currentFreq();
    if (freq <= 0) return;
    const newFreq = snapToStep(freq + direction * step);
    if (newFreq > 0 && newFreq !== freq) {
      sendCommand('set_freq', { freq: newFreq, receiver: receiverIdx() });
      vibrate('tick');
    }
  }

  function onPointerDown(e: PointerEvent): void {
    dragging = true;
    startX = e.clientX;
    accumDx = 0;
    wheelEl.setPointerCapture(e.pointerId);
  }

  function onPointerMove(e: PointerEvent): void {
    if (!dragging) return;
    const dx = e.clientX - startX;
    const totalSteps = Math.floor(dx / PX_PER_STEP);
    const prevSteps = Math.floor(accumDx / PX_PER_STEP);

    if (totalSteps !== prevSteps) {
      const delta = totalSteps - prevSteps;
      // Drag right = freq up, drag left = freq down
      tune(delta);
    }
    accumDx = dx;
  }

  function onPointerUp(e: PointerEvent): void {
    dragging = false;
    wheelEl.releasePointerCapture(e.pointerId);
  }

  function onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
      event.preventDefault();
      tune(-1);
      return;
    }

    if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
      event.preventDefault();
      tune(1);
    }
  }

  let step = $derived(getTuningStep());
</script>

<div class="tuning-wheel-container">
  <button class="tune-btn" onclick={() => tune(-1)} aria-label="Tune down">◀</button>
  <div
    class="tuning-wheel"
    bind:this={wheelEl}
    onpointerdown={onPointerDown}
    onpointermove={onPointerMove}
    onpointerup={onPointerUp}
    onpointercancel={onPointerUp}
    onkeydown={onKeyDown}
    role="button"
    tabindex="0"
    aria-label="Tuning wheel, drag left or right to tune frequency"
  >
    <div class="wheel-track">
      {#each Array(21) as _, i}
        <div class="tick" class:major={i % 5 === 0}></div>
      {/each}
    </div>
    <div class="wheel-label">{formatStep(step)}</div>
  </div>
  <button class="tune-btn" onclick={() => tune(1)} aria-label="Tune up">▶</button>
</div>

<style>
  .tuning-wheel-container {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--panel);
    border-top: 1px solid var(--panel-border);
    touch-action: none;
    user-select: none;
  }

  .tune-btn {
    min-width: 40px;
    min-height: 40px;
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 1rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .tune-btn:active {
    background: var(--accent);
    color: #000;
  }

  .tuning-wheel {
    flex: 1;
    height: 48px;
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    overflow: hidden;
    cursor: grab;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .tuning-wheel:active {
    cursor: grabbing;
  }

  .wheel-track {
    display: flex;
    align-items: flex-end;
    gap: 6px;
    height: 100%;
    padding: 0 8px;
    pointer-events: none;
  }

  .tick {
    width: 1px;
    height: 30%;
    background: var(--panel-border);
    flex-shrink: 0;
  }

  .tick.major {
    height: 55%;
    background: var(--text-muted);
  }

  .wheel-label {
    position: absolute;
    top: 4px;
    right: 8px;
    font-family: var(--font-mono);
    font-size: 0.625rem;
    color: var(--text-muted);
    pointer-events: none;
  }
</style>
