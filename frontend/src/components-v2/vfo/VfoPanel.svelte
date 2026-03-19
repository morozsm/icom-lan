<script lang="ts">
  import LinearSMeter from '../meters/LinearSMeter.svelte';
  import FrequencyDisplay from '../display/FrequencyDisplay.svelte';
  import StatusBadge from '../controls/StatusBadge.svelte';
  import { getCapabilities, vfoLabel } from '$lib/stores/capabilities.svelte';
  import { findActiveBand } from '../controls/band-utils';
  import { formatBadges, formatRitOffset } from './vfo-utils';
  import type { VfoLayoutProfile } from '../layout/vfo-layout-tokens';

  interface Props {
    receiver: 'main' | 'sub';
    freq: number;
    mode: string;
    filter: string;
    sValue: number;
    isActive: boolean;
    badges: Record<string, boolean | string>;
    rit?: { active: boolean; offset: number };
    layoutProfile?: VfoLayoutProfile;
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
    layoutProfile = 'baseline',
    onModeClick,
    onVfoClick,
  }: Props = $props();

  let slot = $derived<'A' | 'B'>(receiver === 'main' ? 'A' : 'B');
  let label = $derived(vfoLabel(slot));
  let slotTag = $derived(label.startsWith('VFO ') ? label.slice(4) : label);
  let activeBand = $derived(findActiveBand(freq, getCapabilities()?.freqRanges ?? []));
  let badgeItems = $derived(formatBadges(badges));
  let meterVariant = $derived(layoutProfile === 'wide' ? 'vfo-wide' : 'vfo');
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
  class="panel"
  class:active={isActive}
  onclick={onVfoClick}
  role={onVfoClick ? 'button' : undefined}
  data-layout-profile={layoutProfile}
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
    <LinearSMeter value={sValue} compact label={slotTag} variant={meterVariant} />
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
    grid-template-rows:
      var(--vfo-panel-header-height, 18px)
      var(--vfo-panel-meter-height, 58px)
      var(--vfo-panel-body-height, 64px);
    min-height: 100%;
    background: linear-gradient(180deg, var(--v2-bg-gradient-start) 0%, var(--v2-bg-darkest) 100%);
    border: 1px solid var(--v2-border-darker);
    border-radius: 4px;
    overflow: hidden;
    font-family: 'Roboto Mono', monospace;
    transition: border-color 150ms ease;
  }

  .panel.active {
    border-color: var(--v2-border-cyan-bright);
    box-shadow: inset 0 0 0 1px rgba(0, 212, 255, 0.08);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: var(--vfo-panel-header-height, 18px);
    padding:
      var(--vfo-badge-inset-y, 3px)
      var(--vfo-panel-pad-x, 10px)
      0;
    border-bottom: none;
  }

  .header-title-group {
    display: flex;
    align-items: center;
    gap: var(--vfo-header-group-gap, 5px);
  }

  .vfo-label {
    color: var(--v2-text-secondary);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .receiver-state {
    display: inline-flex;
    align-items: center;
    min-height: var(--vfo-header-badge-height, 12px);
    padding: 0 var(--vfo-header-badge-padding-x, 5px);
    border: 1px solid rgba(61, 110, 72, 0.9);
    border-radius: var(--vfo-panel-badge-radius, 3px);
    color: var(--v2-accent-green-bright);
    background: rgba(21, 74, 34, 0.68);
    font-size: var(--vfo-control-badge-font-size, 7px);
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .receiver-state[data-active='false'] {
    border-color: rgba(64, 81, 102, 0.86);
    color: var(--v2-text-subdued);
    background: rgba(20, 27, 36, 0.74);
  }

  .header-badges {
    display: flex;
    align-items: center;
    gap: var(--vfo-header-badge-gap, 3px);
  }

  .header-tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: var(--vfo-header-badge-height, 12px);
    padding: 0 var(--vfo-header-badge-padding-x, 5px);
    border-radius: var(--vfo-panel-badge-radius, 3px);
    font-size: var(--vfo-control-badge-font-size, 7px);
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .meter-tag {
    border: 1px solid var(--v2-border-cyan-bright);
    background: rgba(8, 53, 76, 0.62);
    color: var(--v2-accent-cyan);
  }

  .slot-tag {
    border: 1px solid var(--v2-border-soft);
    background: rgba(16, 23, 31, 0.8);
    color: var(--v2-text-muted);
  }

  .panel-meter {
    padding: 0 var(--vfo-panel-meter-pad-x, 6px);
  }

  .mode-badge {
    font-family: 'Roboto Mono', monospace;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: var(--vfo-control-badge-height, 16px);
    font-size: var(--vfo-control-badge-font-size, 7px);
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0 var(--vfo-control-badge-padding-x, 6px);
    border-radius: var(--vfo-panel-badge-radius, 3px);
    border: 1px solid var(--v2-border-cyan-bright);
    color: var(--v2-text-primary);
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
    min-height: var(--vfo-control-badge-height, 16px);
    font-size: var(--vfo-control-badge-font-size, 7px);
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0 var(--vfo-control-badge-padding-x, 6px);
    border-radius: var(--vfo-panel-badge-radius, 3px);
    border: 1px solid var(--v2-border-soft);
    color: var(--v2-text-subdued);
    background: rgba(15, 24, 34, 0.86);
    user-select: none;
  }

  .panel-body {
    display: grid;
    grid-template-rows:
      var(--vfo-display-row-height, 38px)
      var(--vfo-control-strip-height, 22px);
    gap: var(--vfo-panel-body-gap, 4px);
    padding:
      0
      var(--vfo-panel-body-pad-x, 10px)
      var(--vfo-panel-body-pad-bottom, 0px);
    min-height: 0;
  }

  .display-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--vfo-display-row-gap, 12px);
    min-height: var(--vfo-display-row-height, 38px);
  }

  .freq-row {
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .freq-row :global(.freq) {
    font-size: var(--vfo-frequency-size, 24px);
    letter-spacing: var(--vfo-frequency-letter-spacing, 0.03em);
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
    border: 1px solid var(--v2-border-cyan-bright);
    border-radius: 4px;
    background: rgba(9, 39, 56, 0.5);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--v2-accent-cyan);
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
    color: var(--v2-accent-yellow);
  }

  .control-strip {
    display: flex;
    align-items: center;
    gap: var(--vfo-control-strip-gap, 4px);
    min-height: var(--vfo-control-strip-height, 22px);
    overflow: hidden;
    white-space: nowrap;
  }

  .slot-readout,
  .band-readout {
    color: var(--v2-text-muted);
    font-size: var(--vfo-control-badge-font-size, 7px);
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .control-strip :global(.badge) {
    min-height: var(--vfo-control-badge-min-height, 16px);
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
