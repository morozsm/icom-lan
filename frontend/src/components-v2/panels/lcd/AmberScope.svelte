<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { hasAudioFft, getCapabilities } from '$lib/stores/capabilities.svelte';
  import { toTxProps, toFilterProps } from '../../wiring/state-adapter';
  import AmberFrequency from './AmberFrequency.svelte';
  import AmberAfScope from './AmberAfScope.svelte';
  import { createAudioScopeConnection } from '$lib/runtime/adapters/scope-adapter';

  // Band lookup by frequency (LCD-specific, mirrors AmberCockpit)
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

  let tx = $derived(toTxProps(radioState, null));
  let filterProps = $derived(toFilterProps(radioState, caps));

  // Active receiver data (single-RX — use active receiver; dual-RX handled in #897)
  let rx = $derived(radioState?.active === 'SUB' ? radioState?.sub : radioState?.main);
  let mainFreqHz = $derived(rx?.freqHz ?? 0);
  let rxMode = $derived(rx?.mode ?? '---');
  let mainBand = $derived(freqToBand(mainFreqHz));

  // Filter width label (e.g. "2.4 kHz")
  let filterWidthLabel = $derived.by(() => {
    const w = filterProps.filterWidth;
    if (!w || w <= 0) return '';
    return w >= 1000 ? `${(w / 1000).toFixed(1)} kHz` : `${w} Hz`;
  });

  // FFT scope connection — reactive to capabilities
  let fftPixels = $state<Uint8Array | null>(null);
  let fftBandwidth = $state<number | undefined>(undefined);
  let fftPush: ((data: Uint8Array) => void) | null = null;
  let showFft = $derived(hasAudioFft());

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
  AmberScope — IC-7300-style scope-dominant layout.
  60/40 grid: top 40% = compact VFO header, bottom 60% = dominant AfScope.
  Issue #896 / epic #887 C-PR2 (single-RX only; dual-RX reserved for #897).
-->
<div class="amber-lcd amber-lcd-scope" class:tx-active={tx.txActive}>
  <div class="lcd-screen">
    <div class="lcd-scanlines"></div>

    <!-- ═══ Header: compact VFO one-liner (40%) ═══ -->
    <div class="lcd-header" style:grid-area="header">
      <span class="vfo-tag">►A</span>
      <div class="vfo-freq">
        <AmberFrequency freqHz={mainFreqHz} size="large" />
      </div>
      <div class="vfo-badges">
        {#if mainBand}
          <span class="vfo-band-box">{mainBand}</span>
        {/if}
        <span class="vfo-mode-box">{rxMode}</span>
        {#if filterWidthLabel}
          <span class="vfo-filter-box">{filterWidthLabel}</span>
        {/if}
      </div>
    </div>

    <!-- ═══ Scope: dominant AfScope (60%) ═══ -->
    <div class="lcd-scope" style:grid-area="scope">
      {#if showFft}
        <AmberAfScope
          data={fftPixels}
          onRegisterPush={(fn) => { fftPush = fn; }}
          filterWidth={filterProps.filterWidth}
          filterWidthMax={filterProps.filterWidthMax}
          ifShift={filterProps.ifShift}
          bandwidth={fftBandwidth}
          mode="dominant"
        />
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
    /* Contrast tokens — identical defaults to AmberCockpit. */
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

    /* 60/40 scope-dominant grid (issue #896) */
    display: grid;
    grid-template-rows: 40% 60%;
    grid-template-areas:
      "header"
      "scope";
    grid-template-columns: minmax(0, 1fr);
    gap: 6px;
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

  /* ── Header: compact VFO one-liner ── */
  .lcd-header {
    display: flex;
    align-items: center;
    gap: 10px;
    position: relative;
    z-index: 2;
    min-height: 0;
    overflow: hidden;
  }

  .vfo-tag {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 20px;
    font-weight: 700;
    color: rgba(26, 16, 0, var(--lcd-alpha-active));
    border: 2px solid rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.4));
    border-radius: 4px;
    padding: 0 6px;
    line-height: 1.3;
    flex-shrink: 0;
  }

  .vfo-freq {
    flex: 0 1 auto;
    display: flex;
    align-items: center;
    min-width: 0;
    overflow: hidden;
  }

  .vfo-badges {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .vfo-band-box,
  .vfo-mode-box,
  .vfo-filter-box {
    flex-shrink: 0;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 16px;
    font-weight: 700;
    color: rgba(26, 16, 0, var(--lcd-alpha-active));
    letter-spacing: 1px;
    border: 2px solid rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.4));
    border-radius: 4px;
    padding: 2px 8px;
  }

  .vfo-band-box {
    background: rgba(26, 16, 0, var(--lcd-alpha-ghost));
  }

  .vfo-filter-box {
    font-size: 14px;
    color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.7));
    border-color: rgba(26, 16, 0, calc(var(--lcd-alpha-active) * 0.25));
  }

  /* ── Scope cell: fills 60% row ── */
  .lcd-scope {
    position: relative;
    z-index: 2;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
  }

  /* ── TX glow ── */
  .tx-active .lcd-screen {
    border-color: #5A2000;
    box-shadow:
      inset 0 0 40px rgba(180, 30, 0, 0.08),
      0 0 10px rgba(180, 30, 0, 0.15);
  }
</style>
