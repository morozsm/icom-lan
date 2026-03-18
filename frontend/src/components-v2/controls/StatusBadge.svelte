<script lang="ts">
  import './control-button.css';
  import {
    badgeStyleString,
    getBadgeControlButtonVars,
    type BadgeColor,
  } from './status-badge-style';

  interface Props {
    label: string;
    active?: boolean;
    color?: BadgeColor;
    compact?: boolean;
    onclick?: () => void;
  }

  let { label, active = false, color = 'cyan', compact = false, onclick }: Props = $props();

  let style = $derived(badgeStyleString({
    active,
    color,
    compact,
    clickable: !!onclick,
  }));
  let buttonVars = $derived(getBadgeControlButtonVars(color));
</script>

{#if onclick && !compact}
  <button
    type="button"
    class="badge badge-button v2-control-button"
    class:active={active}
    style="--control-accent: {buttonVars.accent}; --control-active-text: {buttonVars.text};"
    {onclick}
    data-active={active}
    data-color={color}
    data-compact={compact}
  >
    {label}
  </button>
{:else}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <span
    class="badge"
    class:clickable={!!onclick}
    {style}
    {onclick}
    data-active={active}
    data-color={color}
    data-compact={compact}
  >
    {label}
  </span>
{/if}

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    border-radius: 3px;
    font-family: 'Roboto Mono', monospace;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    white-space: nowrap;
    user-select: none;
    transition: background 150ms ease, border-color 150ms ease, color 150ms ease, box-shadow 150ms ease;
  }

  .badge.clickable:hover {
    filter: brightness(1.2);
  }

  .badge-button {
    border-radius: 3px;
  }
</style>
