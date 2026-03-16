<script lang="ts">
  import { onDestroy } from 'svelte';
  import { sendCommand } from '../../lib/transport/ws-client';
  import { radio } from '../../lib/stores/radio.svelte';
  import { hasTx, getAttValues, getPreValues, getAgcModes, getAgcLabels, getAntennaCount, hasCapability } from '../../lib/stores/capabilities.svelte';
  import ControlGroup from './ControlGroup.svelte';
  import CapabilityMenu from './CapabilityMenu.svelte';

  let rx = $derived(radio.current?.active === 'SUB' ? (radio.current?.sub ?? null) : (radio.current?.main ?? null));
  let receiverIdx = $derived(radio.current?.active === 'SUB' ? 1 : 0);

  let nb      = $derived(rx?.nb      ?? false);
  let nr      = $derived(rx?.nr      ?? false);
  let digisel = $derived(rx?.digisel ?? false);
  let att  = $derived(rx?.att  ?? 0);
  let pre  = $derived(rx?.preamp ?? 0);
  let agc  = $derived(rx?.agc  ?? null);
  let comp = $derived(radio.current?.compressorOn ?? false);
  let powerLevel = $derived(radio.current?.powerLevel ?? 0);
  let isTx = $derived(hasTx());
  let attValues = $derived(getAttValues());
  let preValues = $derived(getPreValues());
  let antennaCount = $derived(getAntennaCount());
  let hasDigisel = $derived(hasCapability('digisel'));
  let agcModes = $derived(getAgcModes());
  let agcLabels = $derived(getAgcLabels());

  let showAttMenu = $state(false);
  let showPreMenu = $state(false);
  let attPressTimer: ReturnType<typeof setTimeout>;
  let prePressTimer: ReturnType<typeof setTimeout>;

  onDestroy(() => {
    clearTimeout(attPressTimer);
    clearTimeout(prePressTimer);
  });

  function toggleNb() {
    sendCommand('set_nb', { on: !nb, receiver: receiverIdx });
  }

  function toggleNr() {
    sendCommand('set_nr', { on: !nr, receiver: receiverIdx });
  }

  function toggleDigisel() {
    sendCommand('set_digisel', { on: !digisel, receiver: receiverIdx });
  }

  function toggleComp() {
    sendCommand('set_comp', { on: !comp });
  }

  function cycleAgc() {
    if (!agcModes.length) return;
    const idx = agcModes.indexOf(agc ?? 0);
    const next = idx >= 0 ? agcModes[(idx + 1) % agcModes.length] : agcModes[0];
    sendCommand('set_agc', { mode: next });
  }

  function agcLabel(v: number | null): string {
    if (v === null || v === 0) return 'OFF';
    return agcLabels[String(v)] ?? String(v);
  }

  function cycleAtt() {
    const idx = attValues.indexOf(att);
    const next = idx >= 0 ? attValues[(idx + 1) % attValues.length] : attValues[1] ?? 6;
    sendCommand('set_att', { db: next, receiver: receiverIdx });
  }

  function cyclePre() {
    const idx = preValues.indexOf(pre);
    const next = idx >= 0 ? preValues[(idx + 1) % preValues.length] : preValues[1] ?? 1;
    sendCommand('set_preamp', { level: next, receiver: receiverIdx });
  }

  function setAtt(db: number) {
    sendCommand('set_att', { db, receiver: receiverIdx });
  }

  function setPre(level: number) {
    sendCommand('set_preamp', { level, receiver: receiverIdx });
  }

  function startAttLongPress() {
    attPressTimer = setTimeout(() => (showAttMenu = true), 500);
  }

  function startPreLongPress() {
    prePressTimer = setTimeout(() => (showPreMenu = true), 500);
  }

  function cancelAttLongPress() {
    clearTimeout(attPressTimer);
  }

  function cancelPreLongPress() {
    clearTimeout(prePressTimer);
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

    {#if hasDigisel}
      <button
        class="toggle-btn"
        class:active={digisel}
        onclick={toggleDigisel}
        aria-pressed={digisel}
        title="Digital Selection (DIGI-SEL)"
      >DIGI</button>
    {/if}
  </ControlGroup>

  <ControlGroup title="RX">
    <button
      class="toggle-btn"
      class:active={att !== 0}
      onclick={cycleAtt}
      onpointerdown={startAttLongPress}
      onpointerup={cancelAttLongPress}
      onpointerleave={cancelAttLongPress}
      aria-pressed={att !== 0}
      title="Attenuator (click to cycle, long-press for menu)"
    >ATT <span class="val">{attLabel(att)}</span></button>

    <button
      class="toggle-btn"
      class:active={pre !== 0}
      onclick={cyclePre}
      onpointerdown={startPreLongPress}
      onpointerup={cancelPreLongPress}
      onpointerleave={cancelPreLongPress}
      aria-pressed={pre !== 0}
      title="Preamp (click to cycle, long-press for menu)"
    >PRE <span class="val">{preLabel(pre)}</span></button>

    {#if agcModes.length > 0}
      <button
        class="toggle-btn"
        class:active={agc !== null && agc !== 0}
        onclick={cycleAgc}
        title="AGC (click to cycle: {agcModes.map(m => agcLabels[String(m)] ?? m).join(' → ')})"
      >AGC <span class="val">{agcLabel(agc)}</span></button>
    {/if}
  </ControlGroup>

  <ControlGroup title="TX">
    <button
      class="toggle-btn"
      class:active={comp}
      onclick={toggleComp}
      aria-pressed={comp}
      title="Speech Compressor"
    >COMP</button>

    {#each { length: antennaCount } as _, i}
      <button
        class="toggle-btn"
        onclick={() => sendCommand(`set_antenna_${i + 1}`, { on: true })}
        title="Select ANT{i + 1}"
      >ANT{i + 1}</button>
    {/each}

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

{#if showAttMenu}
  <CapabilityMenu
    title="Attenuator"
    values={attValues}
    current={att}
    labels={attLabel}
    onSelect={setAtt}
    onClose={() => (showAttMenu = false)}
  />
{/if}

{#if showPreMenu}
  <CapabilityMenu
    title="Preamp"
    values={preValues}
    current={pre}
    labels={preLabel}
    onSelect={setPre}
    onClose={() => (showPreMenu = false)}
  />
{/if}

<style>
  .feature-toggles {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .toggle-btn {
    min-height: var(--tap-target);
    min-width: 5.5rem;
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
    text-align: center;
    white-space: nowrap;
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
