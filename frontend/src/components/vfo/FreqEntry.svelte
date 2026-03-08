<script lang="ts">
  import { untrack } from 'svelte';

  interface Props {
    currentFreq: number;
    onconfirm?: (freq: number) => void;
    oncancel?: () => void;
  }

  let { currentFreq, onconfirm, oncancel }: Props = $props();

  // Capture initial frequency at modal open time — untrack prevents reactive re-init
  let inputStr = $state(untrack(() => formatForEntry(currentFreq)));

  function formatForEntry(hz: number): string {
    const mhz = hz / 1_000_000;
    // Show 3 decimal places (kHz resolution), trim trailing zeros
    return mhz.toFixed(6).replace(/0+$/, '').replace(/\.$/, '');
  }

  function appendChar(ch: string) {
    if (inputStr.length >= 12) return;
    if (ch === '.' && inputStr.includes('.')) return;
    inputStr += ch;
  }

  function backspace() {
    inputStr = inputStr.slice(0, -1);
  }

  function setMHz(mhz: number) {
    inputStr = mhz.toFixed(6).replace(/0+$/, '').replace(/\.$/, '');
  }

  function confirm() {
    const mhz = parseFloat(inputStr);
    if (!isNaN(mhz) && mhz > 0) {
      onconfirm?.(Math.round(mhz * 1_000_000));
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      oncancel?.();
    } else if (e.key === 'Enter') {
      confirm();
    } else if (e.key === 'Backspace') {
      e.preventDefault();
      backspace();
    } else if (/^[0-9.]$/.test(e.key)) {
      e.preventDefault();
      appendChar(e.key);
    }
  }

  // Quick-access FT8 frequencies (defaults). TODO: make configurable via user settings.
  const quickFreqs: Array<{ label: string; mhz: number }> = [
    { label: '3.573', mhz: 3.573 },
    { label: '7.074', mhz: 7.074 },
    { label: '14.074', mhz: 14.074 },
    { label: '21.074', mhz: 21.074 },
    { label: '28.074', mhz: 28.074 },
  ];

  let parsedHz = $derived(Math.round(parseFloat(inputStr || '0') * 1_000_000));
  let isValid = $derived(!isNaN(parsedHz) && parsedHz > 0 && parsedHz < 1_000_000_000);
</script>

<svelte:window onkeydown={handleKeyDown} />

<div
  class="overlay"
  onclick={(e) => { if (e.target === e.currentTarget) oncancel?.(); }}
  onkeydown={(e) => { if (e.key === 'Escape') oncancel?.(); }}
  role="dialog"
  aria-modal="true"
  aria-label="Frequency Entry"
  tabindex="-1"
>
  <div class="modal" role="document">
    <div class="modal-header">
      <span class="modal-title">ENTER FREQUENCY</span>
      <button class="close-btn" onclick={oncancel} aria-label="Close">✕</button>
    </div>

    <div class="freq-display">
      <span class="freq-input">{inputStr || '0'}</span>
      <span class="freq-unit">MHz</span>
    </div>

    <div class="quick-freqs">
      {#each quickFreqs as qf}
        <button class="quick-btn" onclick={() => setMHz(qf.mhz)}>{qf.label}</button>
      {/each}
    </div>

    <div class="numpad">
      {#each [7, 8, 9, 4, 5, 6, 1, 2, 3] as n}
        <button class="num-btn" onclick={() => appendChar(String(n))}>{n}</button>
      {/each}
      <button class="num-btn dot-btn" onclick={() => appendChar('.')}>.</button>
      <button class="num-btn" onclick={() => appendChar('0')}>0</button>
      <button class="num-btn back-btn" onclick={backspace}>⌫</button>
    </div>

    <div class="actions">
      <button class="cancel-btn" onclick={oncancel}>Cancel</button>
      <button class="confirm-btn" onclick={confirm} disabled={!isValid}>Enter</button>
    </div>
  </div>
</div>

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.75);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    width: 320px;
    max-width: 95vw;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-3);
  }

  .modal-title {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--text-muted);
    letter-spacing: 0.1em;
  }

  .close-btn {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 1rem;
    padding: 4px 8px;
    border-radius: var(--radius);
    line-height: 1;
    transition: all 0.15s;
  }

  .close-btn:hover {
    color: var(--text);
    background: var(--panel-border);
  }

  .freq-display {
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    padding: var(--space-3) var(--space-4);
    margin-bottom: var(--space-3);
    display: flex;
    align-items: baseline;
    justify-content: flex-end;
    gap: var(--space-2);
    min-height: 56px;
  }

  .freq-input {
    font-family: var(--font-mono);
    font-size: 1.75rem;
    color: var(--accent);
    letter-spacing: 0.05em;
  }

  .freq-unit {
    font-family: var(--font-mono);
    font-size: 0.875rem;
    color: var(--text-muted);
  }

  .quick-freqs {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    margin-bottom: var(--space-3);
  }

  .quick-btn {
    flex: 1;
    min-width: 72px;
    padding: var(--space-1) var(--space-2);
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    cursor: pointer;
    transition: all 0.15s;
    text-align: center;
  }

  .quick-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: rgba(77, 182, 255, 0.05);
  }

  .numpad {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-1);
    margin-bottom: var(--space-3);
  }

  .num-btn {
    padding: var(--space-3);
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: 1.25rem;
    cursor: pointer;
    transition: all 0.1s;
    text-align: center;
    min-height: var(--tap-target);
  }

  .num-btn:hover {
    background: var(--panel-border);
  }

  .num-btn:active {
    background: rgba(77, 182, 255, 0.1);
    color: var(--accent);
  }

  .dot-btn {
    font-size: 1.5rem;
    font-weight: 700;
  }

  .back-btn {
    color: var(--warning);
  }

  .actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-2);
  }

  .cancel-btn {
    padding: var(--space-3);
    background: var(--bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.15s;
    min-height: var(--tap-target);
  }

  .cancel-btn:hover {
    border-color: var(--text-muted);
    color: var(--text);
  }

  .confirm-btn {
    padding: var(--space-3);
    background: rgba(77, 182, 255, 0.15);
    border: 1px solid var(--accent);
    border-radius: var(--radius);
    color: var(--accent);
    font-family: var(--font-mono);
    font-size: 0.875rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
    min-height: var(--tap-target);
  }

  .confirm-btn:hover:not(:disabled) {
    background: rgba(77, 182, 255, 0.25);
  }

  .confirm-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
</style>
