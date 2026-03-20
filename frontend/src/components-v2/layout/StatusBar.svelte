<script lang="ts">
  import { Radio, Cable, Activity, Volume2, ArrowDownUp, Power, Unplug, Palette } from 'lucide-svelte';
  import ThemePicker from '../controls/ThemePicker.svelte';
  import {
    getRadioStatus,
    getConnectionStatus,
    isScopeConnected,
    isAudioConnected,
    getHttpConnected,
  } from '$lib/stores/connection.svelte';

  let radioState = $derived(getRadioStatus());
  let controlState = $derived(getConnectionStatus());
  let scopeState = $derived(isScopeConnected() ? 'connected' : 'disconnected');
  let audioState = $derived(isAudioConnected() ? 'connected' : 'disconnected');
  let httpState = $derived(getHttpConnected() ? 'connected' : 'disconnected');

  function stateColor(state: string): string {
    switch (state) {
      case 'connected':
        return 'var(--v2-accent-green, #4ade80)';
      case 'connecting':
      case 'reconnecting':
      case 'partial':
      case 'degraded':
        return 'var(--v2-accent-yellow, #facc15)';
      case 'disconnected':
        return 'var(--v2-accent-red, #ef4444)';
      default:
        return 'var(--v2-text-dim, #666)';
    }
  }

  async function handleConnectionToggle() {
    const isConnected = radioState === 'connected';
    const action = isConnected ? 'Disconnect from' : 'Connect to';
    if (!confirm(`${action} radio?`)) return;
    try {
      const endpoint = isConnected ? '/api/v1/radio/disconnect' : '/api/v1/radio/connect';
      const response = await fetch(endpoint, { method: 'POST' });
      if (!response.ok) {
        const error = await response.text();
        alert(`Failed to ${action.toLowerCase()}: ${error}`);
      }
    } catch (err) {
      alert(`Error: ${err}`);
    }
  }

  async function handlePowerToggle() {
    const newState = radioState === 'connected' ? 'off' : 'on';
    const action = newState === 'on' ? 'Turn ON' : 'Turn OFF';
    if (!confirm(`${action} the radio?`)) return;
    try {
      const response = await fetch('/api/v1/radio/power', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: newState }),
      });
      if (!response.ok) {
        const error = await response.text();
        alert(`Failed to ${action.toLowerCase()}: ${error}`);
      }
    } catch (err) {
      alert(`Error: ${err}`);
    }
  }
</script>

<div class="status-bar">
  <div class="status-indicators">
    <span class="indicator" title="Radio ↔ Server: {radioState}" style="--indicator-color: {stateColor(radioState)}">
      <span class="indicator-dot"></span>
      <Radio size={12} color="currentColor" strokeWidth={2.5} />
    </span>
    <span class="indicator" title="Control WebSocket: {controlState}" style="--indicator-color: {stateColor(controlState)}">
      <span class="indicator-dot"></span>
      <Cable size={12} color="currentColor" strokeWidth={2.5} />
    </span>
    <span class="indicator" title="Scope WebSocket: {scopeState}" style="--indicator-color: {stateColor(scopeState)}">
      <span class="indicator-dot"></span>
      <Activity size={12} color="currentColor" strokeWidth={2.5} />
    </span>
    <span class="indicator" title="Audio WebSocket: {audioState}" style="--indicator-color: {stateColor(audioState)}">
      <span class="indicator-dot"></span>
      <Volume2 size={12} color="currentColor" strokeWidth={2.5} />
    </span>
    <span class="indicator" title="State HTTP: {httpState}" style="--indicator-color: {stateColor(httpState)}">
      <span class="indicator-dot"></span>
      <ArrowDownUp size={12} color="currentColor" strokeWidth={2.5} />
    </span>
  </div>

  <div class="status-info">
    <!-- server version and client count — future -->
  </div>

  <div class="status-controls">
    <ThemePicker />
    <button
      type="button"
      class="control-btn"
      onclick={handleConnectionToggle}
      title={radioState === 'connected' ? 'Disconnect from radio' : 'Connect to radio'}
    >
      <Unplug size={14} strokeWidth={2} />
      <span class="btn-label">{radioState === 'connected' ? 'Disconnect' : 'Connect'}</span>
    </button>
    <button
      type="button"
      class="control-btn"
      onclick={handlePowerToggle}
      title={radioState === 'connected' ? 'Power OFF radio' : 'Power ON radio'}
    >
      <Power size={14} strokeWidth={2} />
      <span class="btn-label">{radioState === 'connected' ? 'OFF' : 'ON'}</span>
    </button>
  </div>
</div>

<style>
  .status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 28px;
    padding: 0 10px;
    background: var(--v2-bg-darkest, #0a0a0f);
    border-bottom: 1px solid var(--v2-border-darker, #1a1a2e);
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    color: var(--v2-text-primary, #fff);
    user-select: none;
  }

  .status-indicators {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .indicator {
    position: relative;
    display: flex;
    align-items: center;
    cursor: pointer;
    color: var(--indicator-color);
    transition: transform 0.15s;
  }

  .indicator:hover {
    transform: scale(1.15);
  }

  .indicator-dot {
    position: absolute;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--indicator-color);
    box-shadow: 0 0 8px var(--indicator-color);
    top: -2px;
    right: -2px;
    pointer-events: none;
  }

  .status-info {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .status-controls {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .control-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: var(--v2-bg-input, #1a1a2e);
    border: 1px solid var(--v2-border, #2a2a3e);
    border-radius: 3px;
    color: var(--v2-text-primary, #fff);
    cursor: pointer;
    transition: all 0.15s ease;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .btn-label {
    white-space: nowrap;
  }

  .control-btn:hover {
    background: var(--v2-bg-card, #252540);
    border-color: var(--v2-accent-cyan, #06b6d4);
    color: var(--v2-text-primary, #fff);
  }

  .control-btn:active {
    transform: scale(0.95);
  }
</style>
