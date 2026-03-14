<script lang="ts">
  import { sendCommand } from '../../lib/transport/ws-client';
  import ControlGroup from '../controls/ControlGroup.svelte';

  // Modulation levels — write-only (no state echo from server)
  let acc1Level = $state(50);
  let usbLevel = $state(50);
  let lanLevel = $state(50);

  function onAcc1Change(e: Event) {
    acc1Level = Math.round(Number((e.target as HTMLInputElement).value));
    sendCommand('set_acc1_mod_level', { level: acc1Level });
  }

  function onUsbChange(e: Event) {
    usbLevel = Math.round(Number((e.target as HTMLInputElement).value));
    sendCommand('set_usb_mod_level', { level: usbLevel });
  }

  function onLanChange(e: Event) {
    lanLevel = Math.round(Number((e.target as HTMLInputElement).value));
    sendCommand('set_lan_mod_level', { level: lanLevel });
  }
</script>

<div class="settings-panel">
  <ControlGroup title="Modulation Input Levels">
    <label class="level-row">
      <span class="level-key">ACC1</span>
      <input
        type="range"
        min="0"
        max="100"
        value={acc1Level}
        onchange={onAcc1Change}
        aria-label="ACC1 modulation level"
      />
      <span class="level-val">{acc1Level}</span>
    </label>

    <label class="level-row">
      <span class="level-key">USB</span>
      <input
        type="range"
        min="0"
        max="100"
        value={usbLevel}
        onchange={onUsbChange}
        aria-label="USB modulation level"
      />
      <span class="level-val">{usbLevel}</span>
    </label>

    <label class="level-row">
      <span class="level-key">LAN</span>
      <input
        type="range"
        min="0"
        max="100"
        value={lanLevel}
        onchange={onLanChange}
        aria-label="LAN modulation level"
      />
      <span class="level-val">{lanLevel}</span>
    </label>
  </ControlGroup>
</div>

<style>
  .settings-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .level-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    width: 100%;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    cursor: pointer;
  }

  .level-key {
    font-weight: 700;
    font-size: 0.625rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    min-width: 36px;
  }

  .level-row input[type='range'] {
    flex: 1;
    accent-color: var(--accent);
    cursor: pointer;
    min-width: 0;
  }

  .level-val {
    font-weight: 600;
    color: var(--text-muted);
    min-width: 28px;
    text-align: right;
  }
</style>
