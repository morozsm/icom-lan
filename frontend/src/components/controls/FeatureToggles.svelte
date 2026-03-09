<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { radio } from '../../lib/stores/radio.svelte';

  let rx = $derived(radio.current?.active === 'SUB' ? (radio.current?.sub ?? null) : (radio.current?.main ?? null));
  let receiverIdx = $derived(radio.current?.active === 'SUB' ? 1 : 0);

  let nb   = $derived(rx?.nb   ?? false);
  let nr   = $derived(rx?.nr   ?? false);
  let att  = $derived(rx?.att  ?? 0);
  let pre  = $derived(rx?.preamp ?? 0);
  let agc  = $derived(rx?.agc  ?? null);
  // COMP state is display-only — no backend handler for set_comp
  let comp = $derived(radio.current?.compressorOn ?? false);

  function toggleNb() {
    sendCommand('set_nb', { on: !nb, receiver: receiverIdx });
  }

  function toggleNr() {
    sendCommand('set_nr', { on: !nr, receiver: receiverIdx });
  }

  function attLabel(v: number): string {
    return v === 0 ? 'OFF' : `${v}dB`;
  }

  function preLabel(v: number): string {
    return v === 0 ? 'OFF' : `P${v}`;
  }
</script>

<div class="feature-toggles" role="group" aria-label="DSP features">
  <button
    class="toggle-btn"
    class:active={nb}
    onclick={toggleNb}
    aria-pressed={nb}
    title="Noise Blanker"
  >NB</button>

  <button
    class="toggle-btn"
    class:active={nr}
    onclick={toggleNr}
    aria-pressed={nr}
    title="Noise Reduction"
  >NR</button>

  <!-- COMP is display-only — no backend handler exists for set_comp -->
  <span class="value-badge" class:nonzero={comp} title="Compressor">
    COMP
  </span>

  <!-- ATT/PRE are display-only — backend set_att/set_preamp commands exist but UI controls not yet implemented -->
  <span class="value-badge" class:nonzero={att !== 0} title="Attenuator">
    ATT <span class="val">{attLabel(att)}</span>
  </span>

  <span class="value-badge" class:nonzero={pre !== 0} title="Preamp">
    PRE <span class="val">{preLabel(pre)}</span>
  </span>

  {#if agc !== null}
    <span class="value-badge" title="AGC">
      AGC <span class="val">{agc}</span>
    </span>
  {/if}
</div>

<style>
  .feature-toggles {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    align-items: center;
  }

  .toggle-btn {
    min-height: var(--tap-target);
    padding: 0 var(--space-3);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 9999px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.1s, color 0.1s, border-color 0.1s;
  }

  .toggle-btn:hover {
    color: var(--text);
    border-color: var(--accent);
  }

  .toggle-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #000;
  }

  .value-badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    min-height: var(--tap-target);
    padding: 0 var(--space-3);
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 9999px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    user-select: none;
  }

  .value-badge.nonzero {
    border-color: var(--warning);
    color: var(--warning);
  }

  .val {
    font-weight: 400;
    opacity: 0.85;
  }
</style>
