<script lang="ts">
  import { Radio, Cable, Activity, Volume2, ArrowDownUp, Power, Unplug, Palette, Monitor, Tv } from 'lucide-svelte';
  import ThemePicker from '../controls/ThemePicker.svelte';
  import { runtime } from '$lib/runtime';
  import {
    getRadioStatus,
    getConnectionStatus,
    isScopeConnected,
    isAudioConnected,
    getHttpConnected,
    getRadioPowerOn,
    getRigConnected,
  } from '$lib/stores/connection.svelte';
  import { getFrequency } from '$lib/stores/radio.svelte';
  import { hasAnyScope, hasAudio, hasSpectrum } from '$lib/stores/capabilities.svelte';
  import { getLayoutMode, cycleLayoutMode } from '$lib/stores/layout.svelte';

  let layoutMode = $derived(getLayoutMode());
  let hasAnyScopeAvail = $derived(hasAnyScope());
  const layoutLabels: Record<string, string> = { auto: 'AUTO', lcd: 'LCD', standard: 'STD' };
  const layoutTitles: Record<string, string> = { auto: 'Auto layout', lcd: 'Force LCD layout', standard: 'Force standard layout' };

  let radioPowerOn = $derived(getRadioPowerOn());
  let isPoweredOff = $derived(radioPowerOn === false);

  // When radio is powered off, override statuses that depend on the radio
  let radioState = $derived(isPoweredOff ? 'disconnected' : getRadioStatus());
  let controlState = $derived(getConnectionStatus()); // server link — always real
  let scopeState = $derived(isPoweredOff ? 'disconnected' : (isScopeConnected() ? 'connected' : 'disconnected'));
  let audioState = $derived(isPoweredOff ? 'disconnected' : (isAudioConnected() ? 'connected' : 'disconnected'));
  let httpState = $derived(getHttpConnected() ? 'connected' : 'disconnected'); // server link — always real
  let rigConnected = $derived(getRigConnected());
  // Effective radio indicator: downgrade to 'disconnected' when rigCtld reports radio offline
  let radioIndicatorState = $derived(radioState === 'connected' && !rigConnected ? 'degraded' : radioState);

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

  function handleConnectionToggle() {
    const isConnected = controlState === 'connected';
    const action = isConnected ? 'Disconnect' : 'Connect';
    if (!confirm(`${action}?`)) return;
    if (isConnected) {
      runtime.system.disconnect();
    } else {
      runtime.system.connect();
    }
  }

  async function handlePowerToggle() {
    if (radioPowerOn === true) {
      if (!confirm('Turn OFF the radio?')) return;
      try {
        await runtime.system.powerOff();
      } catch (err) {
        alert(`Failed to turn off radio: ${err}`);
      }
    } else {
      if (!confirm('Turn ON the radio?')) return;
      try {
        await runtime.system.powerOn();
      } catch (err) {
        alert(`Failed to turn on radio: ${err}`);
      }
    }
  }

  // ── Now Playing (EiBi identification) ──
  let nowPlaying = $state<any>(null);
  let nowPlayingExpanded = $state(false);
  let identifyTimer: ReturnType<typeof setTimeout> | null = null;
  let lastIdentifiedFreq = 0;

  // Poll frequency and identify station
  $effect(() => {
    const freq = getFrequency();
    if (!freq || Math.abs(freq - lastIdentifiedFreq) < 500) return;

    // Debounce: wait 800ms after freq stops changing
    // Don't update while popup is expanded (prevents flicker)
    if (identifyTimer) clearTimeout(identifyTimer);
    identifyTimer = setTimeout(async () => {
      if (nowPlayingExpanded) return;
      lastIdentifiedFreq = freq;
      const result = await runtime.system.identifyFrequency(freq);
      nowPlaying = result?.stations?.length ? result.stations[0] : null;
    }, 800);

    return () => {
      if (identifyTimer) clearTimeout(identifyTimer);
    };
  });

</script>

{#if controlState === 'disconnected'}
  <div class="control-link-lost">Control link lost</div>
{/if}
<div class="status-bar">
  <div class="status-indicators">
    <span class="indicator" tabindex="0" role="status" title="Radio ↔ Server: {radioState}{!rigConnected && radioState === 'connected' ? ' (rig offline)' : ''}" style="--indicator-color: {stateColor(radioIndicatorState)}">
      <span class="indicator-dot"></span>
      <Radio size={12} color="currentColor" strokeWidth={2.5} />
    </span>
    <span class="indicator" tabindex="0" role="status" title="Control WebSocket: {controlState}" style="--indicator-color: {stateColor(controlState)}">
      <span class="indicator-dot"></span>
      <Cable size={12} color="currentColor" strokeWidth={2.5} />
    </span>
    {#if hasAnyScope()}
      <span class="indicator" tabindex="0" role="status" title="Scope WebSocket: {scopeState}" style="--indicator-color: {stateColor(scopeState)}">
        <span class="indicator-dot"></span>
        <Activity size={12} color="currentColor" strokeWidth={2.5} />
      </span>
    {/if}
    {#if hasAudio()}
      <span class="indicator" tabindex="0" role="status" title="Audio WebSocket: {audioState}" style="--indicator-color: {stateColor(audioState)}">
        <span class="indicator-dot"></span>
        <Volume2 size={12} color="currentColor" strokeWidth={2.5} />
      </span>
    {/if}
    <span class="indicator" tabindex="0" role="status" title="State HTTP: {httpState}" style="--indicator-color: {stateColor(httpState)}">
      <span class="indicator-dot"></span>
      <ArrowDownUp size={12} color="currentColor" strokeWidth={2.5} />
      {#if httpState === 'disconnected'}
        <span class="http-lost-label">offline</span>
      {/if}
    </span>
  </div>

  <div class="status-info">
    {#if nowPlaying}
      <button type="button" class="now-playing" onclick={() => (nowPlayingExpanded = !nowPlayingExpanded)} onkeydown={(e) => { if (e.key === 'Escape') nowPlayingExpanded = false; }} aria-expanded={nowPlayingExpanded} aria-haspopup="dialog">
        <span class="np-icon">📻</span>
        <span class="np-station">{nowPlaying.station}</span>
        <span class="np-lang">{nowPlaying.city ? `${nowPlaying.city}, ${nowPlaying.state}` : nowPlaying.language_name}</span>
        {#if nowPlaying.on_air}<span class="np-live">LIVE</span>{/if}
      </button>
      {#if nowPlayingExpanded}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="np-backdrop" onclick={() => (nowPlayingExpanded = false)} onkeydown={(e) => { if (e.key === 'Escape') nowPlayingExpanded = false; }}>
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="np-detail" role="dialog" aria-modal="true" aria-label="Station details" onclick={(e) => e.stopPropagation()} onkeydown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); nowPlayingExpanded = false; } }}>
            <div class="np-detail-header">
              <span>📻 {nowPlaying.station}</span>
              <button class="np-close" onclick={() => (nowPlayingExpanded = false)}>✕</button>
            </div>
            <div class="np-detail-grid">
              <span class="np-label">Frequency:</span><span>{nowPlaying.freq_khz} kHz</span>
              {#if nowPlaying.city}
                <span class="np-label">Location:</span><span>{nowPlaying.city}, {nowPlaying.state}</span>
              {/if}
              <span class="np-label">Language:</span><span>{nowPlaying.language_name}</span>
              {#if !nowPlaying.city}
                <span class="np-label">Country:</span><span>{nowPlaying.country}</span>
                <span class="np-label">Target:</span><span>{nowPlaying.target}</span>
              {/if}
              {#if nowPlaying.time_str !== 'local'}
                <span class="np-label">Schedule:</span><span>{nowPlaying.time_str} UTC {nowPlaying.days || '(daily)'}</span>
              {/if}
              <span class="np-label">Band:</span><span>{nowPlaying.band}</span>
              {#if nowPlaying.remarks}
                <span class="np-label">Details:</span><span>{nowPlaying.remarks}</span>
              {/if}
              {#if nowPlaying.source}
                <span class="np-label">Source:</span><span class="np-source">{nowPlaying.source}</span>
              {/if}
            </div>
          </div>
        </div>
      {/if}
    {/if}
  </div>

  <div class="status-controls">
    <button
      type="button"
      class="control-btn layout-btn"
      onclick={() => cycleLayoutMode(hasAnyScopeAvail)}
      title={layoutTitles[layoutMode]}
    >
      {#if layoutMode === 'lcd'}
        <Tv size={14} strokeWidth={2} />
      {:else}
        <Monitor size={14} strokeWidth={2} />
      {/if}
      <span class="btn-label">{layoutLabels[layoutMode]}</span>
    </button>
    <ThemePicker />
    <button
      type="button"
      class="control-btn"
      onclick={handleConnectionToggle}
      title={controlState === 'connected' ? 'Disconnect' : 'Connect'}
    >
      <Unplug size={14} strokeWidth={2} />
      <span class="btn-label">{controlState === 'connected' ? 'Disconnect' : 'Connect'}</span>
    </button>
    <button
      type="button"
      class="control-btn power-toggle-btn"
      class:is-on={radioPowerOn === true}
      onclick={handlePowerToggle}
      title={radioPowerOn === true ? 'Power OFF radio' : 'Power ON radio'}
    >
      <Power size={14} strokeWidth={2} />
      <span class="btn-label">{radioPowerOn === true ? 'OFF' : 'ON'}</span>
    </button>
  </div>
</div>

<style>
  .control-link-lost {
    background: var(--v2-accent-red, #ef4444);
    color: #fff;
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    text-align: center;
    padding: 2px 0;
    user-select: none;
  }

  .http-lost-label {
    font-size: 9px;
    color: var(--v2-accent-red, #ef4444);
    font-weight: 700;
    margin-left: 2px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

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

  .control-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    pointer-events: none;
  }

  .power-toggle-btn {
    border-color: var(--v2-accent-green, #4ade80);
    color: var(--v2-accent-green, #4ade80);
  }

  .power-toggle-btn:hover {
    border-color: var(--v2-accent-green, #4ade80);
    background: rgba(74, 222, 128, 0.1);
  }

  .power-toggle-btn.is-on {
    border-color: var(--v2-accent-red, #ef4444);
    color: var(--v2-accent-red, #ef4444);
  }

  .power-toggle-btn.is-on:hover {
    border-color: var(--v2-accent-red, #ef4444);
    background: rgba(239, 68, 68, 0.1);
  }

  /* Now Playing badge */
  .status-info {
    position: relative;
  }

  .now-playing {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 8px;
    background: rgba(192, 132, 252, 0.08);
    border: 1px solid rgba(192, 132, 252, 0.2);
    border-radius: 4px;
    cursor: pointer;
    max-width: 350px;
    overflow: hidden;
    transition: background 0.15s;
    font-family: 'Roboto Mono', monospace;
    color: inherit;
  }

  .now-playing:hover {
    background: rgba(192, 132, 252, 0.15);
    border-color: rgba(192, 132, 252, 0.4);
  }

  .np-icon {
    font-size: 11px;
    flex-shrink: 0;
  }

  .np-station {
    font-size: 11px;
    font-weight: 600;
    color: var(--v2-text-primary, #e0e0e0);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .np-lang {
    font-size: 9px;
    color: var(--v2-text-dim, #888);
    white-space: nowrap;
  }

  .np-live {
    font-size: 8px;
    font-weight: 700;
    color: #4ade80;
    background: rgba(74, 222, 128, 0.15);
    padding: 1px 4px;
    border-radius: 2px;
    letter-spacing: 0.05em;
    flex-shrink: 0;
  }

  .np-backdrop {
    position: fixed;
    inset: 0;
    z-index: 999;
  }

  .np-detail {
    position: fixed;
    top: 36px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--v2-bg-primary, #0f0f1a);
    border: 1px solid rgba(192, 132, 252, 0.4);
    border-radius: 8px;
    padding: 0;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
    z-index: 1000;
    min-width: 280px;
    max-width: 400px;
  }

  .np-detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid rgba(192, 132, 252, 0.2);
    font-size: 13px;
    font-weight: 600;
    color: #C084FC;
  }

  .np-close {
    background: none;
    border: none;
    color: var(--v2-text-dim, #666);
    cursor: pointer;
    font-size: 14px;
    padding: 0 2px;
  }

  .np-close:hover {
    color: #ff4444;
  }

  .np-source {
    font-size: 9px;
    color: var(--v2-text-dim, #555);
  }

  .np-detail-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 12px;
    padding: 10px 12px;
    font-size: 11px;
    color: var(--v2-text-primary, #ccc);
  }

  .np-label {
    color: var(--v2-text-dim, #666);
    font-weight: 600;
  }
</style>
