<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import RfFrontEnd from '../panels/RfFrontEnd.svelte';
  import ModePanel from '../panels/ModePanel.svelte';
  import FilterPanel from '../panels/FilterPanel.svelte';
  import AgcPanel from '../panels/AgcPanel.svelte';
  import RitXitPanel from '../panels/RitXitPanel.svelte';
  import AntennaPanel from '../panels/AntennaPanel.svelte';
  import BandSelector from '../controls/BandSelector.svelte';
  import CollapsiblePanel from '../controls/CollapsiblePanel.svelte';
  import {
    toRfFrontEndProps,
    toModeProps,
    toFilterProps,
    toAgcProps,
    toRitXitProps,
    toBandSelectorProps,
    toAntennaProps,
  } from '../wiring/state-adapter';
  import {
    makeRfFrontEndHandlers,
    makeModeHandlers,
    makeFilterHandlers,
    makeAgcHandlers,
    makeRitXitHandlers,
    makeBandHandlers,
    makePresetHandlers,
    makeAntennaHandlers,
  } from '../wiring/command-bus';

  // Reactive state + capabilities
  let radioState = $derived(radio.current);
  let caps = $derived(getCapabilities());

  // --- Panel reorder ---
  const PANEL_ORDER_KEY = 'icom-lan:panel-order';
  const DEFAULT_ORDER = ['rf-front-end', 'mode', 'filter', 'agc', 'rit-xit', 'band', 'antenna'];

  function loadPanelOrder(): string[] {
    try {
      const stored = localStorage.getItem(PANEL_ORDER_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length === DEFAULT_ORDER.length &&
            DEFAULT_ORDER.every((id) => parsed.includes(id))) {
          return parsed;
        }
      }
    } catch { /* ignore */ }
    return [...DEFAULT_ORDER];
  }

  let panelOrder = $state(loadPanelOrder());

  // Persist order changes
  $effect(() => {
    const order = panelOrder;
    try {
      localStorage.setItem(PANEL_ORDER_KEY, JSON.stringify(order));
    } catch { /* ignore */ }
  });

  function resetPanelOrder() {
    panelOrder = [...DEFAULT_ORDER];
    try { localStorage.removeItem(PANEL_ORDER_KEY); } catch { /* ignore */ }
  }

  function orderOf(panelId: string): number {
    return panelOrder.indexOf(panelId);
  }

  // --- Drag state ---
  let dragPanelId = $state<string | null>(null);
  let dropTargetIndex = $state<number>(-1);

  function handleDragStart(panelId: string, event: PointerEvent) {
    const handle = event.currentTarget as HTMLElement;
    handle.setPointerCapture(event.pointerId);
    dragPanelId = panelId;
    dropTargetIndex = panelOrder.indexOf(panelId);

    const sidebar = handle.closest('.left-sidebar') as HTMLElement;
    if (!sidebar) return;

    const panels = Array.from(sidebar.querySelectorAll<HTMLElement>('[data-panel-id]'));
    const rects = new Map<string, DOMRect>();
    for (const p of panels) {
      const id = p.dataset.panelId!;
      rects.set(id, p.getBoundingClientRect());
    }

    function onMove(e: PointerEvent) {
      const y = e.clientY;
      // Find which slot the pointer is over
      let closest = 0;
      let minDist = Infinity;
      for (let i = 0; i < panelOrder.length; i++) {
        const id = panelOrder[i];
        const rect = rects.get(id);
        if (!rect) continue;
        const mid = rect.top + rect.height / 2;
        const dist = Math.abs(y - mid);
        if (dist < minDist) {
          minDist = dist;
          closest = i;
        }
      }
      dropTargetIndex = closest;
    }

    function onUp() {
      if (dragPanelId && dropTargetIndex >= 0) {
        const fromIndex = panelOrder.indexOf(dragPanelId);
        if (fromIndex !== dropTargetIndex) {
          const newOrder = [...panelOrder];
          const [moved] = newOrder.splice(fromIndex, 1);
          newOrder.splice(dropTargetIndex, 0, moved);
          panelOrder = newOrder;
        }
      }
      dragPanelId = null;
      dropTargetIndex = -1;
      handle.removeEventListener('pointermove', onMove);
      handle.removeEventListener('pointerup', onUp);
      handle.removeEventListener('pointercancel', onUp);
    }

    handle.addEventListener('pointermove', onMove);
    handle.addEventListener('pointerup', onUp);
    handle.addEventListener('pointercancel', onUp);
  }

  // Derived props via state adapter
  let rfFrontEnd = $derived(toRfFrontEndProps(radioState, caps));
  let mode = $derived(toModeProps(radioState, caps));
  let filter = $derived(toFilterProps(radioState, caps));
  let agc = $derived(toAgcProps(radioState, caps));
  let ritXit = $derived(toRitXitProps(radioState, caps));
  let band = $derived(toBandSelectorProps(radioState));
  let antenna = $derived(toAntennaProps(radioState, caps));
  // Command handlers via command-bus
  const rfHandlers = makeRfFrontEndHandlers();
  const modeHandlers = makeModeHandlers();
  const filterHandlers = makeFilterHandlers();
  const agcHandlers = makeAgcHandlers();
  const ritXitHandlers = makeRitXitHandlers();
  const bandHandlers = makeBandHandlers();
  const presetHandlers = makePresetHandlers();
  const antennaHandlers = makeAntennaHandlers();
</script>

<aside class="left-sidebar">
  <CollapsiblePanel title="RF FRONT END" panelId="rf-front-end" dataPanel="rf-frontend"
    draggable={true} onDragStart={handleDragStart}
    style="order:{orderOf('rf-front-end')}{dragPanelId === 'rf-front-end' ? ';opacity:0.5;transform:scale(0.98)' : ''}{dropTargetIndex === orderOf('rf-front-end') && dragPanelId && dragPanelId !== 'rf-front-end' ? ';border-top:2px solid var(--v2-accent, #4af)' : ''}">
    <RfFrontEnd
      rfGain={rfFrontEnd.rfGain}
      squelch={rfFrontEnd.squelch}
      att={rfFrontEnd.att}
      pre={rfFrontEnd.pre}
      digiSel={rfFrontEnd.digiSel}
      ipPlus={rfFrontEnd.ipPlus}
      onRfGainChange={rfHandlers.onRfGainChange}
      onSquelchChange={rfHandlers.onSquelchChange}
      onAttChange={rfHandlers.onAttChange}
      onPreChange={rfHandlers.onPreChange}
      onDigiSelToggle={rfHandlers.onDigiSelToggle}
      onIpPlusToggle={rfHandlers.onIpPlusToggle}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="MODE" panelId="mode"
    draggable={true} onDragStart={handleDragStart}
    style="order:{orderOf('mode')}{dragPanelId === 'mode' ? ';opacity:0.5;transform:scale(0.98)' : ''}{dropTargetIndex === orderOf('mode') && dragPanelId && dragPanelId !== 'mode' ? ';border-top:2px solid var(--v2-accent, #4af)' : ''}">
    <ModePanel
      currentMode={mode.currentMode}
      modes={mode.modes}
      dataMode={mode.dataMode}
      hasDataMode={mode.hasDataMode}
      dataModeCount={mode.dataModeCount}
      dataModeLabels={mode.dataModeLabels}
      onModeChange={modeHandlers.onModeChange}
      onDataModeChange={modeHandlers.onDataModeChange}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="FILTER" panelId="filter"
    draggable={true} onDragStart={handleDragStart}
    style="order:{orderOf('filter')}{dragPanelId === 'filter' ? ';opacity:0.5;transform:scale(0.98)' : ''}{dropTargetIndex === orderOf('filter') && dragPanelId && dragPanelId !== 'filter' ? ';border-top:2px solid var(--v2-accent, #4af)' : ''}">
    <FilterPanel
      currentMode={filter.currentMode}
      currentFilter={filter.currentFilter}
      filterShape={filter.filterShape}
      filterLabels={filter.filterLabels}
      filterWidth={filter.filterWidth}
      filterWidthMin={filter.filterWidthMin}
      filterWidthMax={filter.filterWidthMax}
      filterConfig={filter.filterConfig}
      ifShift={filter.ifShift}
      hasPbt={filter.hasPbt}
      pbtInner={filter.pbtInner}
      pbtOuter={filter.pbtOuter}
      onFilterChange={filterHandlers.onFilterChange}
      onFilterWidthChange={filterHandlers.onFilterWidthChange}
      onFilterShapeChange={filterHandlers.onFilterShapeChange}
      onFilterPresetChange={filterHandlers.onFilterPresetChange}
      onFilterDefaults={filterHandlers.onFilterDefaults}
      onIfShiftChange={filterHandlers.onIfShiftChange}
      onPbtInnerChange={filterHandlers.onPbtInnerChange}
      onPbtOuterChange={filterHandlers.onPbtOuterChange}
      onPbtReset={filterHandlers.onPbtReset}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="AGC" panelId="agc"
    draggable={true} onDragStart={handleDragStart}
    style="order:{orderOf('agc')}{dragPanelId === 'agc' ? ';opacity:0.5;transform:scale(0.98)' : ''}{dropTargetIndex === orderOf('agc') && dragPanelId && dragPanelId !== 'agc' ? ';border-top:2px solid var(--v2-accent, #4af)' : ''}">
    <AgcPanel
      agcMode={agc.agcMode}
      onAgcModeChange={agcHandlers.onAgcModeChange}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="RIT / XIT" panelId="rit-xit"
    draggable={true} onDragStart={handleDragStart}
    style="order:{orderOf('rit-xit')}{dragPanelId === 'rit-xit' ? ';opacity:0.5;transform:scale(0.98)' : ''}{dropTargetIndex === orderOf('rit-xit') && dragPanelId && dragPanelId !== 'rit-xit' ? ';border-top:2px solid var(--v2-accent, #4af)' : ''}">
    <RitXitPanel
      ritActive={ritXit.ritActive}
      ritOffset={ritXit.ritOffset}
      xitActive={ritXit.xitActive}
      xitOffset={ritXit.xitOffset}
      hasRit={ritXit.hasRit}
      hasXit={ritXit.hasXit}
      onRitToggle={ritXitHandlers.onRitToggle}
      onXitToggle={ritXitHandlers.onXitToggle}
      onRitOffsetChange={ritXitHandlers.onRitOffsetChange}
      onXitOffsetChange={ritXitHandlers.onXitOffsetChange}
      onClear={ritXitHandlers.onClear}
    />
  </CollapsiblePanel>

  <CollapsiblePanel title="BAND" panelId="band"
    draggable={true} onDragStart={handleDragStart}
    style="order:{orderOf('band')}{dragPanelId === 'band' ? ';opacity:0.5;transform:scale(0.98)' : ''}{dropTargetIndex === orderOf('band') && dragPanelId && dragPanelId !== 'band' ? ';border-top:2px solid var(--v2-accent, #4af)' : ''}">
    <BandSelector
      currentFreq={band.currentFreq}
      onBandSelect={bandHandlers.onBandSelect}
      onPresetSelect={presetHandlers.onPresetSelect}
    />
  </CollapsiblePanel>

  {#if antenna.antennaCount > 1}
    <CollapsiblePanel title="ANTENNA" panelId="antenna" dataPanel="antenna"
      draggable={true} onDragStart={handleDragStart}
      style="order:{orderOf('antenna')}{dragPanelId === 'antenna' ? ';opacity:0.5;transform:scale(0.98)' : ''}{dropTargetIndex === orderOf('antenna') && dragPanelId && dragPanelId !== 'antenna' ? ';border-top:2px solid var(--v2-accent, #4af)' : ''}">
      <AntennaPanel
        txAntenna={antenna.txAntenna}
        rxAnt={antenna.rxAnt}
        antennaCount={antenna.antennaCount}
        hasRxAntenna={antenna.hasRxAntenna}
        onSelectAnt1={antennaHandlers.onSelectAnt1}
        onSelectAnt2={antennaHandlers.onSelectAnt2}
        onToggleRxAnt={antennaHandlers.onToggleRxAnt}
      />
    </CollapsiblePanel>
  {/if}

  <div class="sidebar-footer" style="order:99">
    <button type="button" class="reset-order-btn" onclick={resetPanelOrder}>
      Reset panel order
    </button>
  </div>
</aside>

<style>
  .left-sidebar {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
    padding: 6px 6px 16px;
    width: 100%;
    box-sizing: border-box;
  }

  .sidebar-footer {
    display: flex;
    justify-content: center;
    padding-top: 4px;
  }

  .reset-order-btn {
    background: none;
    border: 1px solid var(--v2-collapsible-border, #444);
    color: var(--v2-collapsible-chevron, #888);
    font-family: 'Roboto Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 3px;
    cursor: pointer;
    transition: color 0.15s ease, border-color 0.15s ease;
  }

  .reset-order-btn:hover {
    color: var(--v2-collapsible-header-text, #ccc);
    border-color: var(--v2-collapsible-header-text, #ccc);
  }
</style>
