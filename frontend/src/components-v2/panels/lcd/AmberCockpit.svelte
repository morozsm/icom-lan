<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { hasAudioFft, hasDualReceiver, getCapabilities, hasCapability } from '$lib/stores/capabilities.svelte';
  import {
    toTxProps, toRitXitProps, toVfoOpsProps, toMeterProps,
    toRfFrontEndProps, toAgcProps, toDspProps, toFilterProps,
  } from '../../wiring/state-adapter';
  import AmberFrequency from './AmberFrequency.svelte';
  import AmberSmeter from './AmberSmeter.svelte';
  import AmberAfScope from './AmberAfScope.svelte';
  import { createAudioScopeConnection } from '$lib/runtime/adapters/scope-adapter';

  // Band lookup by frequency (LCD-specific)
  const BANDS: [string, number, number][] = [
    ['160m', 1800000, 2000000],
    ['80m',  3500000, 4000000],
    ['60m',  5351500, 5366500],
    ['40m',  7000000, 7300000],
    ['30m',  10100000, 10150000],
    ['20m',  14000000, 14350000],
    ['17m',  18068000, 18168000],
    ['15m',  21000000, 21450000],
    ['12m',  24890000, 24990000],
    ['10m',  28000000, 29700000],
    ['6m',   50000000, 54000000],
    ['4m',   70000000, 70500000],
    ['2m',   144000000, 148000000],
    ['70cm', 420000000, 450000000],
    ['MW',   530000, 1710000],
    ['SW',   2300000, 30000000],
  ];
  function freqToBand(hz: number): string {
    for (const [name, lo, hi] of BANDS) {
      if (hz >= lo && hz <= hi) return name;
    }
    if (hz >= 88000000 && hz <= 108000000) return 'FM';
    if (hz >= 108000000 && hz <= 137000000) return 'AIR';
    return '';
  }

  let radioState = $derived(radio.current);
  let caps = $derived(getCapabilities());

  // ── Adapter-derived state ──
  let tx = $derived(toTxProps(radioState, null));
  let ritXit = $derived(toRitXitProps(radioState, null));
  let vfoOps = $derived(toVfoOpsProps(radioState, null));
  let meter = $derived(toMeterProps(radioState));
  let rf = $derived(toRfFrontEndProps(radioState, null));
  let agc = $derived(toAgcProps(radioState, null));
  let dsp = $derived(toDspProps(radioState, null));
  let filterProps = $derived(toFilterProps(radioState, caps));

  // ── LCD-specific derivations (no adapter equivalent) ──
  let rx = $derived(radioState?.active === 'SUB' ? radioState?.sub : radioState?.main);
  let freqHz = $derived(rx?.freqHz ?? 0);
  let bandLabel = $derived(freqToBand(freqHz));
  let mode = $derived(rx?.mode ?? '---');
  let filter = $derived(rx?.filter ?? '');
  let subSValue = $derived(radioState?.sub?.sMeter ?? 0);

  type MeterSource = 'S' | 'PO' | 'SWR' | 'ALC' | 'COMP';
  const METER_SOURCES: MeterSource[] = ['S', 'PO', 'SWR', 'ALC', 'COMP'];
  let userMeterSource = $state<MeterSource>('S');

  // Auto-switch to PO during TX if user hasn't selected a TX meter
  let activeMeterSource = $derived<MeterSource>(
    tx.txActive && userMeterSource === 'S' ? 'PO' : userMeterSource
  );

  let meterValue = $derived.by(() => {
    switch (activeMeterSource) {
      case 'PO': return meter.rfPower;
      case 'SWR': return meter.swr;
      case 'ALC': return meter.alc;
      case 'COMP': return meter.comp;
      default: return rx?.sMeter ?? 0;  // active receiver, not always main
    }
  });

  function cycleMeterSource() {
    const idx = METER_SOURCES.indexOf(userMeterSource);
    userMeterSource = METER_SOURCES[(idx + 1) % METER_SOURCES.length];
  }

  // LCD-specific: NB/NR active includes level > 0
  let nbActive = $derived(dsp.nbActive || dsp.nbLevel > 0);
  let nrActive = $derived(dsp.nrMode > 0 || dsp.nrLevel > 0);
  let notchActive = $derived(dsp.notchMode === 'manual');
  let lockActive = $derived(radioState?.dialLock ?? false);
  let contourActive = $derived((rx?.contour ?? 0) > 0);
  let contourLevel = $derived(rx?.contour ?? 0);
  let anfActive = $derived(rx?.autoNotch ?? false);
  let dataActive = $derived(!!rx?.dataMode);
  let activeVfo = $derived(radioState?.active === 'SUB' ? 'B' : 'A');

  let subRx = $derived(radioState?.active === 'SUB' ? radioState?.main : radioState?.sub);
  let subFreqHz = $derived(subRx?.freqHz ?? 0);
  let subMode = $derived(subRx?.mode ?? '');

  let fftPixels = $state<Uint8Array | null>(null);
  let fftBandwidth = $state<number | undefined>(undefined);
  let fftPush: ((data: Uint8Array) => void) | null = null;
  let showFft = $derived(hasAudioFft());

  // FTX-1 AGC: 0=OFF, 1=FAST, 2=MID, 3=SLOW, 4=AUTO-F, 5=AUTO-M, 6=AUTO-S
  const AGC_LABELS: Record<number, string> = {
    0: 'OFF', 1: 'FAST', 2: 'MID', 3: 'SLOW',
    4: 'A-F', 5: 'A-M', 6: 'A-S',
  };
  function agcLabel(m: number): string {
    return AGC_LABELS[m] ?? `${m}`;
  }

  // Scope WS connection — reactive to capabilities (may load after mount)
  $effect(() => {
    if (!hasAudioFft()) return;

    const scope = createAudioScopeConnection((frame) => {
      fftPixels = frame.pixels;
      fftBandwidth = frame.endFreq > frame.startFreq ? frame.endFreq - frame.startFreq : undefined;
      fftPush?.(frame.pixels);
    });

    return () => scope.disconnect();
  });
</script>

<!--
  Grid scaffold (issue #844 / plan §9.1):
  - Two column templates selected by `hasDualReceiver()`:
    single-RX = 1 column (12u), dual-RX = 2 columns (6u + 6u).
  - Shared row heights so capability collapse does NOT reflow peer cells.
  - Dedicated full-width `filter` row at a consistent position.
  - Soft buttons (A↔B, A=B, DW, SPLIT, XIT, CLR, TUNE, BK-OFF) evicted
    to sidebar `VfoControlPanel` — display surfaces state, not commands.
  - No content changes: VFO B stays compact, status tokens unchanged,
    filter-viz keeps `compact` prop (wide mode is #835).
-->
<div class="amber-lcd" class:tx-active={tx.txActive}>
  <div class="lcd-screen" class:dual={hasDualReceiver()}>
    <div class="lcd-scanlines"></div>

    <!-- ═══ Indicators (status row) ═══ -->
    <div class="lcd-ind-row" style:grid-area="indicators">
      <span class="lcd-ind" class:active={tx.txActive} class:ind-tx={tx.txActive}>TX</span>
      {#if hasCapability('vox')}<span class="lcd-ind" class:active={tx.voxActive}>VOX</span>{/if}
      {#if hasCapability('compressor')}<span class="lcd-ind" class:active={tx.compActive}>PROC{tx.compActive ? ` ${tx.compLevel}` : ''}</span>{/if}

      <span class="ind-sep"></span>

      {#if hasCapability('attenuator')}<span class="lcd-ind" class:active={rf.att > 0}>ATT</span>{/if}
      {#if hasCapability('preamp')}<span class="lcd-ind active">{rf.pre === 0 ? 'IPO' : rf.pre === 1 ? 'AMP1' : 'AMP2'}</span>{/if}
      {#if hasCapability('digisel')}<span class="lcd-ind" class:active={rf.digiSel}>DIGI-SEL</span>{/if}
      {#if hasCapability('ip_plus')}<span class="lcd-ind" class:active={rf.ipPlus}>IP+</span>{/if}
      {#if hasCapability('tuner')}<span class="lcd-ind" class:active={tx.atuActive} class:ind-tuning={tx.atuTuning}>{tx.atuTuning ? 'TUNE' : 'ATU'}</span>{/if}

      <span class="ind-sep"></span>

      {#if hasCapability('nb')}<span class="lcd-ind" class:active={nbActive}>NB{nbActive ? ` ${dsp.nbLevel}` : ''}</span>{/if}
      {#if hasCapability('nr')}<span class="lcd-ind" class:active={nrActive}>NR{nrActive ? ` ${dsp.nrLevel}` : ''}</span>{/if}
      {#if hasCapability('contour')}<span class="lcd-ind" class:active={contourActive}>CONT</span>{/if}
      {#if hasCapability('notch')}<span class="lcd-ind" class:active={notchActive}>NOTCH</span>{/if}
      {#if hasCapability('notch')}<span class="lcd-ind" class:active={anfActive}>ANF</span>{/if}
      <span class="lcd-ind active">AGC {agcLabel(agc.agcMode)}</span>

      <span class="ind-sep"></span>

      {#if hasCapability('rf_gain')}<span class="lcd-ind" class:active={rf.rfGain < 255}>RFG</span>{/if}
      {#if hasCapability('squelch')}<span class="lcd-ind" class:active={rf.squelch > 0}>SQL</span>{/if}
      {#if hasCapability('rit')}<span class="lcd-ind" class:active={ritXit.ritActive}>RIT</span>{/if}
      {#if hasCapability('split')}<span class="lcd-ind" class:active={vfoOps.splitActive}>SPLIT</span>{/if}
      {#if dataActive}<span class="lcd-ind active">DATA</span>{/if}
      {#if hasCapability('dial_lock')}<span class="lcd-ind" class:active={lockActive}>LOCK</span>{/if}
    </div>

    <!-- ═══ Meter A (main / active RX) ═══ -->
    <div class="lcd-meter-row" style:grid-area="meter-a">
      <AmberSmeter value={meterValue} txActive={tx.txActive} source={activeMeterSource} />
      <button class="lcd-meter-src-btn" onclick={cycleMeterSource}>{activeMeterSource}</button>
    </div>

    <!-- ═══ Meter B (sub RX, dual-RX only) — stays compact per #844 scope ═══ -->
    {#if hasDualReceiver()}
      <div class="lcd-meter-row lcd-meter-sub" style:grid-area="meter-b">
        {#if !tx.txActive}
          <AmberSmeter value={subSValue} source="S" />
        {/if}
      </div>
    {/if}

    <!-- ═══ VFO A ═══ -->
    <div class="lcd-vfo-row lcd-vfo-main" style:grid-area="vfo-a">
      <span class="vfo-tag">{activeVfo}</span>
      <div class="vfo-freq">
        <AmberFrequency {freqHz} size="large" />
      </div>
      <div class="vfo-badges">
        <span class="vfo-mode-box">{mode}{filter ? ` ${filter}` : ''}</span>
        {#if bandLabel}
          <span class="vfo-band-box">{bandLabel}</span>
        {/if}
      </div>
    </div>

    <!-- ═══ VFO B — compact form preserved (peer promotion is #845) ═══ -->
    {#if hasDualReceiver()}
      <div class="lcd-vfo-row lcd-vfo-sub" style:grid-area="vfo-b">
        <span class="vfo-tag vfo-tag-sub">{activeVfo === 'A' ? 'B' : 'A'}</span>
        <div class="vfo-freq">
          <AmberFrequency freqHz={subFreqHz} size="small" />
        </div>
        {#if subMode}
          <span class="vfo-mode vfo-mode-sub">{subMode}</span>
        {/if}
      </div>
    {/if}

    <!-- ═══ RIT / XIT offset (pb row) ═══ -->
    {#if ritXit.ritActive || ritXit.xitActive}
      <div class="lcd-rit-row" style:grid-area="pb">
        <span class="rit-label">{ritXit.ritActive ? 'RIT' : 'XIT'}</span>
        <span class="rit-value">{ritXit.ritOffset >= 0 ? '+' : ''}{ritXit.ritOffset} Hz</span>
      </div>
    {/if}

    <!-- ═══ Filter-viz (full-width row, compact prop preserved) ═══ -->
    <div class="lcd-filter-row" style:grid-area="filter">
      {#if showFft}
        <div class="lcd-scope-strip">
          <AmberAfScope
            data={fftPixels}
            onRegisterPush={(fn) => { fftPush = fn; }}
            filterWidth={filterProps.filterWidth}
            filterWidthMax={filterProps.filterWidthMax}
            ifShift={filterProps.ifShift}
            contour={contourLevel}
            manualNotch={dsp.notchMode === 'manual'}
            notchFreq={dsp.notchFreq}
            autoNotch={notchActive}
            bandwidth={fftBandwidth}
            {mode}
            compact
          />
        </div>
      {/if}
    </div>

  </div>
</div>

<style>
  .amber-lcd {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: stretch;
    padding: 4px;
    box-sizing: border-box;
    min-height: 0;
  }

  .lcd-screen {
    /* Contrast tokens — see plan §2.4. Defaults match MID preset (today's
       visual). `applyLcdContrast()` overrides these inline on mount and
       on every preset change. */
    --lcd-alpha-active: 1;
    --lcd-alpha-inactive: 0.08;
    --lcd-alpha-ghost: 0.06;

    position: relative;
    width: 100%;
    background: #C8A030;
    border: 2px solid #8A7020;
    border-radius: 8px;
    padding: 12px 18px;
    overflow: hidden;
    box-shadow:
      inset 0 0 50px rgba(0, 0, 0, 0.06),
      0 0 8px rgba(0, 0, 0, 0.5);
    min-height: 0;

    /* ── Grid scaffold (issue #844) ──
       Two templates with IDENTICAL row heights — collapsing VFO-B / meter-B
       does not reflow peer cells (plan §9.1 P2). A dedicated full-width
       `filter` row (~120 px) sits at a consistent position regardless of
       capability. */
    display: grid;
    gap: 6px;
    /* Prevent auto-tracks (e.g. `pb` when RIT/XIT inactive) from stretching
       to fill extra LCD height on taller viewports. Without this, the empty
       `pb` row would grow and leave a blank gap before the filter row. */
    align-content: start;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows:
      28px              /* indicators */
      28px              /* meter */
      72px              /* vfo */
      auto              /* pb (RIT/XIT offset; collapses when inactive) */
      minmax(0, 120px); /* filter */
    grid-template-areas:
      "indicators"
      "meter-a"
      "vfo-a"
      "pb"
      "filter";
  }

  .lcd-screen.dual {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    grid-template-areas:
      "indicators indicators"
      "meter-a    meter-b"
      "vfo-a      vfo-b"
      "pb         pb"
      "filter     filter";
  }

  .lcd-scanlines {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 1;
    background: repeating-linear-gradient(
      to bottom,
      transparent 0px,
      transparent 3px,
      rgba(0, 0, 0, 0.03) 3px,
      rgba(0, 0, 0, 0.03) 6px
    );
  }

  /* ── Indicators ── */
  .lcd-ind-row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    position: relative;
    z-index: 2;
    padding: 2px 0;
    flex-shrink: 1;
    overflow: hidden;
  }

  .ind-sep {
    width: 1px;
    height: 16px;
    background: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.15));
    margin: 0 4px;
    flex-shrink: 0;
  }

  .lcd-ind {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: rgba(26, 16, 0, var(--lcd-alpha-inactive));
    border: 1.5px solid rgba(26, 16, 0, var(--lcd-alpha-ghost));
    border-radius: 3px;
    padding: 1px 6px;
    user-select: none;
  }

  .lcd-ind.active {
    color: rgba(26, 16, 0, var(--lcd-alpha-active));
    border-color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.4));
  }

  .lcd-ind.ind-tx {
    color: #5A0800;
    border-color: rgba(90, 8, 0, 0.5);
    font-size: 15px;
  }
  .lcd-ind.ind-tuning {
    animation: lcd-blink 0.6s steps(1) infinite;
  }
  @keyframes lcd-blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0.15; }
  }

  /* ── VFO rows ── */
  .lcd-vfo-row {
    display: flex;
    align-items: center;
    gap: 10px;
    position: relative;
    z-index: 2;
  }

  .lcd-vfo-main {
    /* issue #860: use explicit 3-col grid so freq digits (DSEG7 fixed metrics)
       cannot overflow into mode/band badges. Column 2 `minmax(0,1fr)` lets the
       freq cell shrink; `overflow:hidden` on `.vfo-freq` clips digits rather
       than overlapping siblings. */
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 10px;
    flex: 1;
    min-height: 0;
    align-items: center;
  }

  .vfo-badges {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .vfo-tag {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 22px;
    font-weight: 700;
    color: rgba(26, 16, 0, var(--lcd-alpha-active));
    border: 2px solid rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.4));
    border-radius: 4px;
    padding: 0 6px;
    line-height: 1.3;
    flex-shrink: 0;
  }

  .vfo-tag-sub {
    font-size: 16px;
    border-width: 1.5px;
    color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.5));
    border-color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.25));
    padding: 0 4px;
  }

  .vfo-freq {
    flex: 0 1 auto;
    display: flex;
    align-items: center;
    min-width: 0;
    overflow: hidden;
  }

  .vfo-band-box {
    flex-shrink: 0;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 18px;
    font-weight: 700;
    color: rgba(26, 16, 0, var(--lcd-alpha-active));
    letter-spacing: 1px;
    border: 2px solid rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.4));
    border-radius: 4px;
    padding: 2px 8px;
    background: rgba(26, 16, 0, var(--lcd-alpha-ghost));
  }

  .vfo-mode-box {
    flex-shrink: 0;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 18px;
    font-weight: 700;
    color: rgba(26, 16, 0, var(--lcd-alpha-active));
    letter-spacing: 1px;
    border: 2px solid rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.4));
    border-radius: 4px;
    padding: 2px 8px;
  }

  .vfo-mode-sub {
    font-size: 13px;
    color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.45));
  }

  /* ── S-Meter ── */
  .lcd-meter-row {
    position: relative;
    z-index: 2;
    display: flex;
    align-items: center;
    flex-shrink: 1;
    min-height: 0;
  }
  .lcd-meter-row :global(.lcd-smeter) {
    flex: 1;
  }
  .lcd-meter-src-btn {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    color: rgba(26, 16, 0, var(--lcd-alpha-active));
    background: transparent;
    border: 1.5px solid rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.3));
    border-radius: 3px;
    padding: 2px 6px;
    margin-right: 4px;
    cursor: pointer;
    min-width: 36px;
    text-align: center;
  }
  .lcd-meter-src-btn:hover {
    border-color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.5));
  }
  .lcd-meter-sub {
    opacity: 0.6;
    transform: scaleY(0.7);
    transform-origin: top;
    margin-top: -4px;
  }

  /* ── Sub VFO ── */
  .lcd-vfo-sub {
    border-top: 1px solid rgba(26, 16, 0, var(--lcd-alpha-inactive));
    padding-top: 4px;
  }

  /* ── RIT row ── */
  .lcd-rit-row {
    display: flex;
    gap: 6px;
    align-items: baseline;
    position: relative;
    z-index: 2;
  }

  .rit-label {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    font-weight: 700;
    color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.5));
  }

  .rit-value {
    font-family: 'DSEG7 Classic', monospace;
    font-weight: bold;
    font-size: 16px;
    color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.6));
  }

  /* ── Filter / AF Scope row (full-width grid cell) ── */
  .lcd-filter-row {
    position: relative;
    z-index: 2;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
  }
  .lcd-scope-strip {
    position: relative;
    z-index: 2;
    width: 100%;
    height: 100%;
    min-height: 0;
  }

  /* ── TX glow ── */
  .tx-active .lcd-screen {
    border-color: #5A2000;
    box-shadow:
      inset 0 0 40px rgba(180, 30, 0, 0.08),
      0 0 10px rgba(180, 30, 0, 0.15);
  }
</style>
