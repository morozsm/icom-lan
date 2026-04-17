<!--
  DualVfoDisplay — side-by-side MAIN + SUB VFO tiles for dual-RX radios.

  Presentation-only: renders two VfoPanel tiles wrapped in keyboard/a11y
  containers. The active tile is visually highlighted and announced via
  aria-pressed. Clicking or pressing Enter/Space on an inactive tile fires
  the onActivate callback with the receiver id.

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

  function handleKeydown(event: KeyboardEvent, receiver: 'MAIN' | 'SUB'): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      activate(receiver);
    }
  }
</script>

<div
  class="dual-vfo-tile vfo-main-panel"
  class:is-active={active === 'MAIN'}
  role="button"
  tabindex="0"
  aria-pressed={active === 'MAIN'}
  aria-label={active === 'MAIN' ? 'MAIN receiver (active)' : 'Activate MAIN receiver'}
  data-receiver="main"
  data-layout-profile={layoutProfile}
  onclick={() => activate('MAIN')}
  onkeydown={(e) => handleKeydown(e, 'MAIN')}
>
  <VfoPanel
    {...main}
    {layoutProfile}
    onModeClick={onMainModeClick}
    onFreqChange={onMainFreqChange}
  />
</div>

<div
  class="dual-vfo-tile vfo-sub-panel"
  class:is-active={active === 'SUB'}
  role="button"
  tabindex="0"
  aria-pressed={active === 'SUB'}
  aria-label={active === 'SUB' ? 'SUB receiver (active)' : 'Activate SUB receiver'}
  data-receiver="sub"
  data-layout-profile={layoutProfile}
  onclick={() => activate('SUB')}
  onkeydown={(e) => handleKeydown(e, 'SUB')}
>
  <VfoPanel
    {...sub}
    {layoutProfile}
    onModeClick={onSubModeClick}
    onFreqChange={onSubFreqChange}
  />
</div>

<style>
  .dual-vfo-tile {
    min-width: 0;
    display: block;
    cursor: pointer;
    border-radius: 4px;
    outline: none;
    transition: box-shadow 150ms ease;
  }

  .dual-vfo-tile:focus-visible {
    box-shadow: 0 0 0 2px var(--v2-accent-cyan, #00d4ff);
  }

  .dual-vfo-tile.is-active {
    /* Active highlight is rendered by the inner VfoPanel.active class.
       This selector exists so tests and external CSS can target the
       outer tile without reaching into the panel. */
  }
</style>
