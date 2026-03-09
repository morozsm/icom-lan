<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import { radio } from '../../lib/stores/radio.svelte';
  import { hasTx } from '../../lib/stores/capabilities.svelte';
  import ControlGroup from './ControlGroup.svelte';

  let rx = $derived(radio.current?.active === 'SUB' ? (radio.current?.sub ?? null) : (radio.current?.main ?? null));
  let receiverIdx = $derived(radio.current?.active === 'SUB' ? 1 : 0);

  let nb      = $derived(rx?.nb      ?? false);
  let nr      = $derived(rx?.nr      ?? false);
  let digisel = $derived(rx?.digisel ?? false);
  let att  = $derived(rx?.att  ?? 0);
  let pre  = $derived(rx?.preamp ?? 0);
  let agc  = $derived(rx?.agc  ?? null);
  // COMP state is display-only — no backend handler for set_comp
  let comp = $derived(radio.current?.compressorOn ?? false);
  let powerLevel = $derived(radio.current?.powerLevel ?? 0);
  let isTx = $derived(hasTx());

  function toggleNb() {
    sendCommand('set_nb', { on: !nb, receiver: receiverIdx });
  }

  function toggleNr() {
    sendCommand('set_nr', { on: !nr, receiver: receiverIdx });
  }

  function toggleDigisel() {
    sendCommand('set_digisel', { on: !digisel, receiver: receiverIdx });
  }

  function cycleAtt() {
    // IC-7610 ATT: 0 or 20dB
    sendCommand('set_att', { db: att === 0 ? 20 : 0, receiver: receiverIdx });
  }

  function cyclePre() {
    // IC-7610 PRE: 0 (off), 1 (preamp 1), 2 (preamp 2)
    const next = (pre + 1) % 3;
    sendCommand('set_preamp', { level: next, receiver: receiverIdx });
  }

  function attLabel(v: number): string {
    return v === 0 ? 'OFF' : `${v}dB`;
  }

  function preLabel(v: number): string {
    return v === 0 ? 'OFF' : `P${v}`;
  }
</script>

<div class="feature-toggles">
  <ControlGroup title="DSP">
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

    <button
      class="toggle-btn"
      class:active={digisel}
      onclick={toggleDigisel}
      aria-pressed={digisel}
      title="Digital Selection (DIGI-SEL)"
    >DIGI</button>
  </ControlGroup>

  <ControlGroup title="RX">
    <button
      class="toggle-btn"
      class:active={att !== 0}
      onclick={cycleAtt}
      aria-pressed={att !== 0}
      title="Attenuator (click to cycle)"
    >ATT <span class="val">{attLabel(att)}</span></button>

    <button
      class="toggle-btn"
      class:active={pre !== 0}
      onclick={cyclePre}
      aria-pressed={pre !== 0}
      title="Preamp (click to cycle)"
    >PRE <span class="val">{preLabel(pre)}</span></button>

    {#if agc !== null}
      <span class="value-badge" title="AGC">
        AGC <span class="val">{agc}</span>
      </span>
    {/if}
  </ControlGroup>

  <ControlGroup title="TX">
    <!-- COMP is display-only — no backend handler exists for set_comp -->
    <span class="value-badge" class:nonzero={comp} title="Compressor">
      COMP
    </span>

    <button
      class="toggle-btn"
      onclick={() => sendCommand('set_antenna_1', { on: true })}
      title="Select ANT1"
    >ANT1</button>

    <button
      class="toggle-btn"
      onclick={() => sendCommand('set_antenna_2', { on: true })}
      title="Select ANT2"
    >ANT2</button>

    {#if isTx}
      <label class="pwr-control" title="TX Power (0–255)">
        PWR
        <input
          type="range"
          min="0"
          max="255"
          value={powerLevel}
          onchange={(e) => sendCommand('set_power', { level: parseInt((e.currentTarget as HTMLInputElement).value) })}
        />
        <span class="val">{powerLevel}</span>
      </label>
    {/if}
  </ControlGroup>
</div>

<style>
  .feature-toggles {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
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

  .pwr-control {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    min-height: var(--tap-target);
    padding: 0 var(--space-2);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    cursor: default;
  }

  .pwr-control input[type='range'] {
    width: 72px;
    accent-color: var(--accent);
    cursor: pointer;
  }
</style>
