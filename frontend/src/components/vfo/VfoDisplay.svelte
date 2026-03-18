<script lang="ts">
  import VfoDigit from './VfoDigit.svelte';
  import FreqEntry from './FreqEntry.svelte';
  import { gesture } from '../../lib/gestures/use-gesture';
  import { vibrate } from '../../lib/utils/haptics';

  interface Props {
    label?: string; // 'VFO A' | 'VFO B'
    freq: number;
    mode: string;
    filter: number;
    active: boolean;
    dataMode?: number | boolean;
    att?: number;
    preamp?: number;
    ontune?: (newFreq: number) => void;
  }

  let {
    label = 'VFO A',
    freq,
    mode,
    filter,
    active,
    dataMode = 0,
    att = 0,
    preamp = 0,
    ontune,
  }: Props = $props();

  let selectedPosition = $state<number | null>(null);
  let freqEntryOpen = $state(false);

  // Decompose Hz into digit array with separator positions
  function buildDigits(hz: number): Array<{ char: string; position: number | null }> {
    const clamped = Math.max(0, Math.min(999_999_999, Math.round(hz)));
    const padded = String(clamped).padStart(9, '0');

    // Groups: MHz (3 chars), kHz (3 chars), Hz (3 chars)
    const mhzRaw = padded.slice(0, 3);
    const khzGroup = padded.slice(3, 6);
    const hzGroup = padded.slice(6, 9);

    // Remove leading zeros from MHz group but keep at least 1 digit
    const mhzGroup = mhzRaw.replace(/^0+(?=\d)/, '') || '0';
    const mhzOffset = 3 - mhzGroup.length;

    const result: Array<{ char: string; position: number | null }> = [];

    // MHz digits (positions 8=100MHz, 7=10MHz, 6=1MHz)
    for (let i = 0; i < mhzGroup.length; i++) {
      result.push({ char: mhzGroup[i], position: 8 - mhzOffset - i });
    }

    result.push({ char: '.', position: null });

    // kHz digits (positions 5=100kHz, 4=10kHz, 3=1kHz)
    for (let i = 0; i < 3; i++) {
      result.push({ char: khzGroup[i], position: 5 - i });
    }

    result.push({ char: '.', position: null });

    // Hz digits (positions 2=100Hz, 1=10Hz, 0=1Hz)
    for (let i = 0; i < 3; i++) {
      result.push({ char: hzGroup[i], position: 2 - i });
    }

    return result;
  }

  let digits = $derived(buildDigits(freq));

  // Brief flash when frequency changes
  let freqFlash = $state(false);
  let prevFreq = 0;

  $effect(() => {
    const f = freq;
    if (prevFreq !== 0 && f !== prevFreq) {
      freqFlash = true;
      setTimeout(() => { freqFlash = false; }, 300);
    }
    prevFreq = f;
  });

  function handleSelect(position: number) {
    selectedPosition = position;
  }

  function handleIncrement(position: number, delta: number) {
    const step = Math.pow(10, position);
    const newFreq = Math.max(0, Math.min(999_999_999, freq + delta * step));
    ontune?.(newFreq);
  }

  function handleFreqEntryConfirm(newFreq: number) {
    freqEntryOpen = false;
    ontune?.(newFreq);
  }

  function openFreqEntry(e: MouseEvent | KeyboardEvent) {
    if (e instanceof KeyboardEvent && e.key !== 'Enter') return;
    freqEntryOpen = true;
  }

  // Swipe-to-tune: velocity determines step size
  // Slow (<0.3 px/ms): 100 Hz, Medium (<1 px/ms): 1 kHz, Fast: 10 kHz
  let swipeOffset = $state(0);

  const freqGestures = {
    onSwipe(dir: 'left' | 'right' | 'up' | 'down', velocity: number, _distance: number) {
      if (dir !== 'left' && dir !== 'right') return;
      let step: number;
      if (velocity < 0.3) {
        step = 100;
      } else if (velocity < 1) {
        step = 1_000;
      } else {
        step = 10_000;
      }
      const delta = dir === 'right' ? 1 : -1;
      const newFreq = Math.max(0, Math.min(999_999_999, freq + delta * step));
      vibrate('tune');
      ontune?.(newFreq);
    },
  };
</script>

<div class="vfo-display" class:active class:inactive={!active}>
  <div
    class="vfo-header"
    onclick={openFreqEntry}
    onkeydown={openFreqEntry}
    role="button"
    tabindex="0"
    title="Click to enter frequency directly"
  >
    <span class="vfo-label">{label}</span>
    <span class="vfo-meta">
      {mode}{dataMode ? '-D' : ''} · FIL{filter}
      {#if att > 0} · ATT{att}{/if}
      {#if preamp > 0} · PRE{preamp}{/if}
    </span>
    <!-- Design choice: badge shows role ("MAIN"/"sub") not VFO letter ("A"/"B"),
         matching IC-7610 panel conventions where active receiver is "MAIN". -->
    {#if active}
      <span class="active-badge">MAIN</span>
    {:else}
      <span class="sub-badge">sub</span>
    {/if}
  </div>

  <div class="vfo-freq" class:freq-flash={freqFlash} role="group" aria-label="Frequency {freq} Hz" use:gesture={freqGestures}>
    {#each digits as item, i (item.position ?? `dot-${i}`)}
      {#if item.position === null}
        <span class="dot">.</span>
      {:else}
        <VfoDigit
          digit={item.char}
          position={item.position}
          selected={selectedPosition === item.position}
          onselect={handleSelect}
          onincrement={handleIncrement}
        />
      {/if}
    {/each}
  </div>
</div>

{#if freqEntryOpen}
  <FreqEntry
    currentFreq={freq}
    onconfirm={handleFreqEntryConfirm}
    oncancel={() => (freqEntryOpen = false)}
  />
{/if}

<style>
  .vfo-display {
    background-color: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    padding: var(--space-2) var(--space-3);
    transition: border-color 0.2s, box-shadow 0.2s, opacity 0.2s;
  }

  .vfo-display.active {
    border-color: var(--accent);
    box-shadow: 0 0 12px rgba(77, 182, 255, 0.12);
  }

  .vfo-display.inactive {
    opacity: 0.5;
  }

  .vfo-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-1);
    font-family: var(--font-mono);
    font-size: 0.6875rem;
    cursor: pointer;
    padding: 2px 0;
    border-radius: 4px;
    user-select: none;
  }

  .vfo-header:hover .vfo-label {
    color: var(--text);
  }

  .vfo-label {
    font-weight: 700;
    color: var(--text-muted);
    letter-spacing: 0.08em;
    transition: color 0.15s;
  }

  .vfo-meta {
    color: var(--text-muted);
    flex: 1;
    letter-spacing: 0.04em;
  }

  .active-badge {
    font-size: 0.65rem;
    padding: 1px 6px;
    background-color: rgba(77, 182, 255, 0.15);
    color: var(--accent);
    border: 1px solid rgba(77, 182, 255, 0.35);
    border-radius: 4px;
    font-weight: 700;
    letter-spacing: 0.1em;
  }

  .sub-badge {
    font-size: 0.65rem;
    padding: 1px 6px;
    background-color: rgba(139, 148, 158, 0.1);
    color: var(--text-muted);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    font-weight: 700;
    letter-spacing: 0.1em;
  }

  .vfo-freq {
    display: flex;
    align-items: baseline;
    color: var(--text);
    font-family: var(--font-mono);
  }

  .vfo-display.active .vfo-freq {
    color: var(--accent);
  }

  .dot {
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 2rem;
    line-height: 1;
    padding: 0 1px;
    user-select: none;
  }

  .vfo-display.active .dot {
    color: rgba(77, 182, 255, 0.5);
  }

  .vfo-freq.freq-flash {
    animation: freq-flash var(--transition-slow);
  }

  @media (max-width: 1200px) {
    .dot {
      font-size: 1.5rem;
    }
  }

  @media (max-width: 768px) {
    .dot {
      font-size: 1.25rem;
    }
  }
</style>
