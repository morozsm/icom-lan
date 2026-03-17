<script lang="ts">
  import LinearSMeter from '../meters/LinearSMeter.svelte';
  import FrequencyDisplay from '../display/FrequencyDisplay.svelte';
  import StatusBadge from '../controls/StatusBadge.svelte';
  import { vfoLabel } from '$lib/stores/capabilities.svelte';
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
    <span class="vfo-label">{label}</span>

    <div class="header-badges">
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <span
        class="mode-badge"
        onclick={(e) => { e.stopPropagation(); onModeClick?.(); }}
      >{mode}</span>

      <span class="filter-badge">{filter}</span>
    </div>
  </div>

  <div class="panel-body">
    <div class="freq-row">
      <FrequencyDisplay {freq} active={isActive} />
    </div>

    {#if rit?.active}
      <div class="rit-row">
        <span class="rit-label">RIT</span>
        <span class="rit-offset">{formatRitOffset(rit.offset)}</span>
      </div>
    {/if}

    <div class="smeter-row">
      <LinearSMeter value={sValue} compact label={receiver.toUpperCase()} />
    </div>

    {#if badgeItems.length > 0}
      <div class="badge-row">
        {#each badgeItems as item (item.label)}
          <StatusBadge
            label={item.label}
            active={item.active}
            color={item.color as 'cyan' | 'green' | 'orange' | 'red' | 'muted'}
            compact
          />
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .panel {
    background: #060A10;
    border: 1px solid #18202A;
    border-radius: 10px;
    overflow: hidden;
    font-family: 'Roboto Mono', monospace;
    transition: border-color 150ms ease;
  }

  .panel.active {
    border-color: rgba(0, 212, 255, 0.3);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 10px;
    border-bottom: 1px solid #18202A;
  }

  .vfo-label {
    color: #8CA0B8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .header-badges {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .mode-badge {
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 9999px;
    border: 1px solid rgba(255, 106, 0, 0.5);
    color: #FF6A00;
    cursor: pointer;
    user-select: none;
    transition: border-color 150ms ease, color 150ms ease;
  }

  .mode-badge:hover {
    filter: brightness(1.2);
  }

  .filter-badge {
    font-family: 'Roboto Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 9999px;
    border: 1px solid rgba(0, 212, 255, 0.35);
    color: #00D4FF;
    user-select: none;
  }

  .panel-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
  }

  .freq-row {
    display: flex;
    justify-content: center;
  }

  .rit-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }

  .rit-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #00D4FF;
  }

  .rit-offset {
    font-size: 11px;
    font-weight: 700;
    color: #F0F5FA;
  }

  .smeter-row {
    width: 100%;
  }

  .badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }
</style>
