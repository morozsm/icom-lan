<script lang="ts">
  import {
    getVisibleSegments,
    SEGMENT_COLORS,
    SEGMENT_BORDER_COLORS,
    SEGMENT_LABEL_COLORS,
    type BandSegmentMode,
  } from '../../lib/data/arrl-band-plan';

  interface Props {
    startFreq: number;
    endFreq: number;
    visible?: boolean;
    hiddenLayers?: string[];
  }

  let { startFreq, endFreq, visible = true, hiddenLayers = [] }: Props = $props();

  let containerWidth = $state(0);

  // Remote segments from REST API
  interface RemoteSegment {
    start: number;
    end: number;
    mode: string;
    label: string;
    color: string;
    opacity: number;
    band: string;
    layer: string;
    priority: number;
    url?: string | null;
    notes?: string | null;
    station?: string | null;
    language?: string | null;
    schedule?: string | null;
    license?: string | null;
  }

  let remoteSegments = $state<RemoteSegment[]>([]);
  let lastFetchRange = $state({ start: 0, end: 0 });
  let fetchTimeout: ReturnType<typeof setTimeout> | null = null;

  // Popup state
  let popupSegment = $state<{
    label: string;
    band: string;
    mode: string;
    start: number;
    end: number;
    layer: string;
    notes?: string | null;
    station?: string | null;
    url?: string | null;
    language?: string | null;
    schedule?: string | null;
    license?: string | null;
    x: number;
    y: number;
  } | null>(null);

  // Debounced fetch from REST API
  function fetchSegments(start: number, end: number) {
    const span = end - start;
    if (
      lastFetchRange.start > 0 &&
      Math.abs(start - lastFetchRange.start) < span * 0.01 &&
      Math.abs(end - lastFetchRange.end) < span * 0.01
    ) {
      return;
    }

    if (fetchTimeout) clearTimeout(fetchTimeout);
    fetchTimeout = setTimeout(async () => {
      try {
        const margin = Math.round(span * 0.5);
        const fetchStart = Math.max(0, start - margin);
        const fetchEnd = end + margin;
        const resp = await fetch(
          `/api/v1/band-plan/segments?start=${fetchStart}&end=${fetchEnd}`
        );
        if (resp.ok) {
          const data = await resp.json();
          remoteSegments = data.segments ?? [];
          lastFetchRange = { start: fetchStart, end: fetchEnd };
        }
      } catch {
        // Silently fall back to local data
      }
    }, 100);
  }

  // Trigger fetch when frequency range changes
  $effect(() => {
    if (visible && startFreq > 0 && endFreq > startFreq) {
      fetchSegments(startFreq, endFreq);
    }
  });

  // Close popup when frequency changes
  $effect(() => {
    void startFreq;
    void endFreq;
    popupSegment = null;
  });

  function formatFreq(hz: number): string {
    if (hz >= 1_000_000) return `${(hz / 1_000_000).toFixed(3)} MHz`;
    if (hz >= 1_000) return `${(hz / 1_000).toFixed(1)} kHz`;
    return `${hz} Hz`;
  }

  // Use remote segments if available, fall back to local
  let segments = $derived(() => {
    if (!visible || endFreq <= startFreq) return [];
    const span = endFreq - startFreq;

    if (remoteSegments.length > 0) {
      return remoteSegments
        .filter((s) => s.end > startFreq && s.start < endFreq)
        .filter((s) => !hiddenLayers.includes(s.layer))
        .map((s) => {
          const rawLeft = ((s.start - startFreq) / span) * 100;
          const rawRight = ((s.end - startFreq) / span) * 100;
          const leftPct = Math.max(0, Math.min(100, rawLeft));
          const rightPct = Math.max(0, Math.min(100, rawRight));
          const widthPct = rightPct - leftPct;
          const widthPx = (widthPct / 100) * containerWidth;
          return {
            start: s.start,
            end: s.end,
            label: s.label,
            mode: s.mode,
            band: s.band,
            layer: s.layer,
            color: `rgba(${hexToRgb(s.color)}, ${s.opacity})`,
            borderColor: `rgba(${hexToRgb(s.color)}, ${Math.min(1, s.opacity + 0.3)})`,
            labelColor: s.color,
            leftPct,
            widthPct,
            widthPx,
            notes: s.notes,
            url: s.url,
            station: s.station,
            language: s.language,
            schedule: s.schedule,
            license: s.license,
          };
        });
    }

    // Fallback to local hardcoded data
    return getVisibleSegments(startFreq, endFreq).map(({ segment }) => {
      const rawLeft = ((segment.startHz - startFreq) / span) * 100;
      const rawRight = ((segment.endHz - startFreq) / span) * 100;
      const leftPct = Math.max(0, Math.min(100, rawLeft));
      const rightPct = Math.max(0, Math.min(100, rawRight));
      const widthPct = rightPct - leftPct;
      const widthPx = (widthPct / 100) * containerWidth;
      return {
        start: segment.startHz,
        end: segment.endHz,
        label: segment.label,
        mode: segment.mode,
        band: '',
        layer: 'local',
        color: SEGMENT_COLORS[segment.mode as BandSegmentMode] ?? 'rgba(156,163,175,0.20)',
        borderColor: SEGMENT_BORDER_COLORS[segment.mode as BandSegmentMode] ?? 'rgba(156,163,175,0.50)',
        labelColor: SEGMENT_LABEL_COLORS[segment.mode as BandSegmentMode] ?? 'rgb(156,163,175)',
        leftPct,
        widthPct,
        widthPx,
        notes: null as string | null,
        url: null as string | null,
        station: null as string | null,
        language: null as string | null,
        schedule: null as string | null,
        license: null as string | null,
      };
    });
  });

  function hexToRgb(hex: string): string {
    const h = hex.replace('#', '');
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b = parseInt(h.substring(4, 6), 16);
    return `${r},${g},${b}`;
  }

  function handleSegmentClick(seg: typeof segments extends () => (infer T)[] ? T : never, e: MouseEvent) {
    e.stopPropagation();
    popupSegment = {
      label: seg.label,
      band: seg.band,
      mode: seg.mode,
      start: seg.start,
      end: seg.end,
      layer: seg.layer,
      notes: seg.notes,
      station: seg.station,
      url: seg.url,
      language: seg.language,
      schedule: seg.schedule,
      license: seg.license,
      x: e.clientX,
      y: e.clientY,
    };
  }
</script>

{#if visible && segments().length > 0}
<div class="bandplan-overlay" aria-hidden="true" bind:clientWidth={containerWidth}>
  {#each segments() as seg (seg.start + seg.layer)}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="band-segment"
      style="left:{seg.leftPct}%;width:{seg.widthPct}%;background:{seg.color};border-left:1px solid {seg.borderColor}"
      title={seg.notes ?? seg.label}
      onclick={(e) => handleSegmentClick(seg, e)}
    >
      {#if seg.widthPx > 40}
        <span class="segment-label" style="color:{seg.labelColor}">
          {seg.label}
        </span>
      {/if}
    </div>
  {/each}
</div>
{/if}

{#if popupSegment}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="popup-backdrop" onclick={() => (popupSegment = null)}>
    <div
      class="segment-popup"
      style="left:{Math.min(popupSegment.x, window.innerWidth - 260)}px;top:{popupSegment.y + 8}px"
      onclick={(e) => e.stopPropagation()}
    >
      <div class="popup-header">
        <span class="popup-label">{popupSegment.label}</span>
        {#if popupSegment.band}
          <span class="popup-band">{popupSegment.band}</span>
        {/if}
        <button class="popup-close" onclick={() => (popupSegment = null)}>✕</button>
      </div>
      <div class="popup-body">
        <div class="popup-row">
          <span class="popup-key">Freq</span>
          <span class="popup-val">{formatFreq(popupSegment.start)} — {formatFreq(popupSegment.end)}</span>
        </div>
        <div class="popup-row">
          <span class="popup-key">Mode</span>
          <span class="popup-val">{popupSegment.mode.toUpperCase()}</span>
        </div>
        <div class="popup-row">
          <span class="popup-key">Layer</span>
          <span class="popup-val">{popupSegment.layer}</span>
        </div>
        {#if popupSegment.license}
          <div class="popup-row">
            <span class="popup-key">License</span>
            <span class="popup-val">{popupSegment.license}</span>
          </div>
        {/if}
        {#if popupSegment.station}
          <div class="popup-row">
            <span class="popup-key">Station</span>
            <span class="popup-val">{popupSegment.station}</span>
          </div>
        {/if}
        {#if popupSegment.language}
          <div class="popup-row">
            <span class="popup-key">Language</span>
            <span class="popup-val">{popupSegment.language}</span>
          </div>
        {/if}
        {#if popupSegment.schedule}
          <div class="popup-row">
            <span class="popup-key">Schedule</span>
            <span class="popup-val">{popupSegment.schedule}</span>
          </div>
        {/if}
        {#if popupSegment.notes}
          <div class="popup-notes">{popupSegment.notes}</div>
        {/if}
        {#if popupSegment.url}
          <a class="popup-link" href={popupSegment.url} target="_blank" rel="noopener">{popupSegment.url}</a>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .bandplan-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 16px;
    pointer-events: none;
    overflow: hidden;
    z-index: 2;
  }

  .band-segment {
    position: absolute;
    top: 0;
    bottom: 0;
    pointer-events: auto;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .band-segment:hover {
    opacity: 0.8;
    outline: 1px solid rgba(255, 255, 255, 0.3);
  }

  .segment-label {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-family: 'Roboto Mono', monospace;
    font-size: 8px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
    opacity: 0.9;
    pointer-events: none;
  }

  /* Popup */
  .popup-backdrop {
    position: fixed;
    inset: 0;
    z-index: 200;
  }

  .segment-popup {
    position: fixed;
    z-index: 201;
    min-width: 200px;
    max-width: 280px;
    background: var(--v2-bg-darkest, #0a0a0f);
    border: 1px solid var(--v2-border, #2a2a3e);
    border-radius: 6px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
    font-family: 'Roboto Mono', monospace;
    font-size: 10px;
    color: var(--v2-text-primary, #e0e0e0);
    overflow: hidden;
  }

  .popup-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: rgba(255, 255, 255, 0.04);
    border-bottom: 1px solid var(--v2-border, #2a2a3e);
  }

  .popup-label {
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .popup-band {
    color: var(--v2-text-dim, #888);
    font-size: 9px;
  }

  .popup-close {
    margin-left: auto;
    background: none;
    border: none;
    color: var(--v2-text-dim, #888);
    cursor: pointer;
    font-size: 12px;
    padding: 0 2px;
    line-height: 1;
  }

  .popup-close:hover {
    color: var(--v2-text-primary, #fff);
  }

  .popup-body {
    padding: 6px 10px 8px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .popup-row {
    display: flex;
    gap: 8px;
  }

  .popup-key {
    color: var(--v2-text-dim, #888);
    min-width: 56px;
    flex-shrink: 0;
    text-transform: uppercase;
    font-size: 9px;
    letter-spacing: 0.03em;
    padding-top: 1px;
  }

  .popup-val {
    color: var(--v2-text-primary, #e0e0e0);
    word-break: break-word;
  }

  .popup-notes {
    margin-top: 4px;
    padding-top: 4px;
    border-top: 1px solid var(--v2-border, #2a2a3e);
    color: var(--v2-text-dim, #aaa);
    font-size: 9px;
    line-height: 1.4;
  }

  .popup-link {
    display: block;
    margin-top: 4px;
    color: var(--v2-accent-cyan, #06b6d4);
    font-size: 9px;
    text-decoration: none;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .popup-link:hover {
    text-decoration: underline;
  }
</style>
