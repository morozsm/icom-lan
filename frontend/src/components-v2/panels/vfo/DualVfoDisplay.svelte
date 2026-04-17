<!--
  DualVfoDisplay — side-by-side MAIN + SUB VFO tiles for dual-RX radios.

  Presentation-only: renders two VfoPanel tiles. The active tile is visually
  highlighted via the `.is-active` class. The inactive tile exposes a small
  dedicated "Activate" button so screen-reader / keyboard users can switch
  receivers without the tile container becoming a button that swallows its
  interactive descendants (tuning digits, mode badge) — which would violate
  WCAG 4.1.2 (no nested interactive content inside role="button").

  Wiring (set_vfo + optimistic patchRadioState) lives at the VfoHeader
  call-site.
-->
<script lang="ts">
  import VfoPanel from '../../../components-v2/vfo/VfoPanel.svelte';
  import type { VfoStateProps } from '../../../components-v2/layout/layout-utils';
  import type { VfoLayoutProfile } from '../../../components-v2/layout/vfo-layout-tokens';

  interface Props {
    main: VfoStateProps;
    sub: VfoStateProps;
    active: 'MAIN' | 'SUB';
    layoutProfile?: VfoLayoutProfile;
    onActivate?: (receiver: 'MAIN' | 'SUB') => void;
    onMainModeClick?: () => void;
    onSubModeClick?: () => void;
    onMainFreqChange?: (freq: number) => void;
    onSubFreqChange?: (freq: number) => void;
  }

  let {
    main,
    sub,
    active,
    layoutProfile = 'baseline',
    onActivate,
    onMainModeClick,
    onSubModeClick,
    onMainFreqChange,
    onSubFreqChange,
  }: Props = $props();

  function activate(receiver: 'MAIN' | 'SUB'): void {
    if (active === receiver) return;
    onActivate?.(receiver);
  }
</script>

<div
  class="dual-vfo-tile vfo-main-panel"
  class:is-active={active === 'MAIN'}
  data-receiver="main"
  data-layout-profile={layoutProfile}
>
  <VfoPanel
    {...main}
    {layoutProfile}
    onModeClick={onMainModeClick}
    onFreqChange={onMainFreqChange}
  />
  {#if active !== 'MAIN'}
    <button
      type="button"
      class="activate-chip"
      aria-label="Activate MAIN receiver"
      data-activate="main"
      onclick={() => activate('MAIN')}
    >
      Activate MAIN
    </button>
  {/if}
</div>

<div
  class="dual-vfo-tile vfo-sub-panel"
  class:is-active={active === 'SUB'}
  data-receiver="sub"
  data-layout-profile={layoutProfile}
>
  <VfoPanel
    {...sub}
    {layoutProfile}
    onModeClick={onSubModeClick}
    onFreqChange={onSubFreqChange}
  />
  {#if active !== 'SUB'}
    <button
      type="button"
      class="activate-chip"
      aria-label="Activate SUB receiver"
      data-activate="sub"
      onclick={() => activate('SUB')}
    >
      Activate SUB
    </button>
  {/if}
</div>

<style>
  .dual-vfo-tile {
    min-width: 0;
    display: block;
    position: relative;
    border-radius: 4px;
    transition: box-shadow 150ms ease;
  }

  .dual-vfo-tile.is-active {
    /* Active highlight is rendered by the inner VfoPanel.active class.
       This selector exists so tests and external CSS can target the
       outer tile without reaching into the panel. */
  }

  .activate-chip {
    position: absolute;
    top: 4px;
    right: 4px;
    z-index: 2;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--v2-accent-cyan, #00d4ff);
    background: rgba(0, 0, 0, 0.55);
    border: 1px solid var(--v2-accent-cyan, #00d4ff);
    border-radius: 999px;
    cursor: pointer;
    opacity: 0.75;
    transition:
      opacity 150ms ease,
      background-color 150ms ease;
  }

  .activate-chip:hover {
    opacity: 1;
    background: rgba(0, 0, 0, 0.75);
  }

  .activate-chip:focus-visible {
    outline: none;
    opacity: 1;
    box-shadow: 0 0 0 2px var(--v2-accent-cyan, #00d4ff);
  }
</style>
