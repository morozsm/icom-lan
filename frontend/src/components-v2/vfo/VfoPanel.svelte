<script lang="ts">
  import LinearSMeter from '../meters/LinearSMeter.svelte';
  import FrequencyDisplay from '../display/FrequencyDisplay.svelte';
  import StatusBadge from '../controls/StatusBadge.svelte';
  import { getCapabilities, vfoLabel } from '$lib/stores/capabilities.svelte';
  import { findActiveBand } from '../controls/band-utils';
  import { formatBadges, formatRitOffset } from './vfo-utils';

  interface Props {
    receiver: 'main' | 'sub';
    freq: number;
    mode: string;
    filter: string;
    sValue: number;
    isActive: boolean;
    badges: Record<string, boolean | string>;
    rit?: { active: boolean; offset: number };
    onModeClick?: () => void;
    onVfoClick?: () => void;
  }

  let {
    receiver,
    freq,
    mode,
    filter,
    sValue,
    isActive,
    badges,
    rit,
    onModeClick,
    onVfoClick,
  }: Props = $props();

  let slot = $derived<'A' | 'B'>(receiver === 'main' ? 'A' : 'B');
  let label = $derived(vfoLabel(slot));
  let slotTag = $derived(label.startsWith('VFO ') ? label.slice(4) : label);
  let activeBand = $derived(findActiveBand(freq, getCapabilities()?.freqRanges ?? []));
  let badgeItems = $derived(formatBadges(badges));
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
  class="panel"
  class:active={isActive}
  onclick={onVfoClick}
  role={onVfoClick ? 'button' : undefined}
>
  <div class="panel-header">
    <div class="header-title-group">
      <span class="vfo-label">{label}</span>
      <span class="receiver-state" data-active={isActive}>{isActive ? 'ACTIVE' : 'STANDBY'}</span>
    </div>

    <div class="header-badges">
      <span class="header-tag meter-tag">BAR</span>
      <span class="header-tag slot-tag">{slotTag}</span>
    </div>
  </div>

  <div class="smeter-row panel-meter">
    <LinearSMeter value={sValue} compact label={slotTag} />
  </div>

  <div class="panel-body">
    <div class="display-row">
      <div class="freq-row">
        <FrequencyDisplay {freq} active={isActive} />
      </div>

      {#if rit?.active}
        <div class="rit-row">
          <span class="rit-label">RIT</span>
          <span class="rit-offset">{formatRitOffset(rit.offset)}</span>
        </div>
      {/if}
    </div>

    <div class="control-strip">
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <span
        class="mode-badge"
        onclick={(e) => { e.stopPropagation(); onModeClick?.(); }}
      >{mode}</span>

      <span class="slot-readout">{slotTag}</span>

      {#if activeBand}
        <span class="band-readout">{activeBand}</span>
      {/if}

      <span class="filter-badge">{filter}</span>

      {#each badgeItems as item (item.label)}
        <StatusBadge
          label={item.label}
          active={item.active}
          color={item.color as 'cyan' | 'green' | 'orange' | 'red' | 'muted'}
          compact
        />
      {/each}
    </div>
  </div>
</div>

<style>
  .panel {
    display: grid;
    grid-template-rows: 18px 34px 64px;
    min-height: 100%;
    background: linear-gradient(180deg, #0a1118 0%, #070c12 100%);
    border: 1px solid #1a2734;
    border-radius: 4px;
    overflow: hidden;
    font-family: 'Roboto Mono', monospace;
    transition: border-color 150ms ease;
  }

  .panel.active {
    border-color: rgba(0, 212, 255, 0.58);
    box-shadow: inset 0 0 0 1px rgba(0, 212, 255, 0.08);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 18px;
    padding: 6px 10px 0;
    border-bottom: none;
  }

  .header-title-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .vfo-label {
    color: #9db0c4;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .receiver-state {
    display: inline-flex;
    align-items: center;
    min-height: 14px;
    padding: 0 6px;
    border: 1px solid rgba(61, 110, 72, 0.9);
    border-radius: 4px;
    color: #9ef6ac;
    background: rgba(21, 74, 34, 0.68);
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .receiver-state[data-active='false'] {
    border-color: rgba(64, 81, 102, 0.86);
    color: #8a9caf;
    background: rgba(20, 27, 36, 0.74);
  }

  .header-badges {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .header-tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 18px;
    padding: 0 7px;
    border-radius: 4px;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .meter-tag {
    border: 1px solid rgba(0, 212, 255, 0.54);
    background: rgba(8, 53, 76, 0.62);
    color: #12dfff;
  }

  .slot-tag {
    border: 1px solid rgba(72, 91, 116, 0.56);
    background: rgba(16, 23, 31, 0.8);
    color: #8398ad;
  }

  .panel-meter {
    padding: 0 10px;
  }

  .mode-badge {
    font-family: 'Roboto Mono', monospace;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 15px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0 8px;
    border-radius: 4px;
    border: 1px solid rgba(0, 212, 255, 0.45);
    color: #eef6fc;
    background: rgba(8, 58, 85, 0.66);
    cursor: pointer;
    user-select: none;
    transition: border-color 150ms ease, color 150ms ease;
  }

  .mode-badge:hover {
    filter: brightness(1.2);
  }

  .filter-badge {
    font-family: 'Roboto Mono', monospace;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 15px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0 8px;
    border-radius: 4px;
    border: 1px solid rgba(61, 83, 105, 0.72);
    color: #88a2ba;
    background: rgba(15, 24, 34, 0.86);
    user-select: none;
  }

  .panel-body {
    display: grid;
    grid-template-rows: 41px 15px;
    gap: 8px;
    padding: 0 10px 8px;
    min-height: 0;
  }

  .display-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 41px;
  }

  .freq-row {
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .freq-row :global(.freq) {
    font-size: 52px;
    letter-spacing: 0.05em;
  }

  .freq-row :global(.sep) {
    opacity: 0.62;
    margin: 0 0.03em;
  }

  .rit-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .rit-label {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 18px;
    padding: 0 7px;
    border: 1px solid rgba(0, 212, 255, 0.48);
    border-radius: 4px;
    background: rgba(9, 39, 56, 0.5);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #00D4FF;
  }

  .rit-offset {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 18px;
    padding: 0 9px;
    border: 1px solid rgba(195, 126, 17, 0.82);
    border-radius: 4px;
    background: rgba(62, 31, 7, 0.6);
    font-size: 10px;
    font-weight: 700;
    color: #ffbf52;
  }

  .control-strip {
    display: flex;
    align-items: center;
    gap: 6px;
    min-height: 15px;
    overflow: hidden;
    white-space: nowrap;
  }

  .slot-readout,
  .band-readout {
    color: #6f88a0;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .control-strip :global(.badge) {
    min-height: 15px;
    font-size: 7px;
  }

  @media (max-width: 1280px) {
    .freq-row :global(.freq) {
      font-size: 44px;
    }
  }

  @media (max-width: 1024px) {
    .display-row {
      flex-wrap: wrap;
      align-items: flex-start;
    }

    .freq-row :global(.freq) {
      font-size: 32px;
    }

    .panel-body {
      grid-template-rows: auto auto;
    }

    .control-strip {
      white-space: normal;
      overflow: visible;
      flex-wrap: wrap;
    }
  }
</style>
