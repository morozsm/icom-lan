<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { isAudioFftScope, hasDualReceiver } from '$lib/stores/capabilities.svelte';
  import AmberFrequency from './AmberFrequency.svelte';
  import AmberSmeter from './AmberSmeter.svelte';
  import AmberFftStrip from './AmberFftStrip.svelte';
  import AmberAfScope from './AmberAfScope.svelte';
  import { getChannel } from '$lib/transport/ws-client';
  import { setScopeConnected, markScopeFrame } from '$lib/stores/connection.svelte';
  import { onMount } from 'svelte';

  interface ScopeFrame {
    receiver: number;
    startFreq: number;
    endFreq: number;
    pixels: Uint8Array;
  }

  function parseScopeFrame(buf: ArrayBuffer): ScopeFrame | null {
    const view = new DataView(buf);
    if (view.byteLength < 16 || view.getUint8(0) !== 0x01) return null;
    const receiver = view.getUint8(1);
    const startFreq = view.getUint32(3, true);
    const endFreq = view.getUint32(7, true);
    const pixelCount = view.getUint16(14, true);
    if (16 + pixelCount > view.byteLength) return null;
    return { receiver, startFreq, endFreq, pixels: new Uint8Array(buf, 16, pixelCount) };
  }

  let state = $derived(radio.current);
  let rx = $derived(state?.active === 'SUB' ? state?.sub : state?.main);
  let freqHz = $derived(rx?.freqHz ?? 0);
  let mode = $derived(rx?.mode ?? '---');
  let filter = $derived(rx?.filter ?? '');
  let sValue = $derived(rx?.sMeter ?? 0);
  let txActive = $derived(state?.ptt ?? false);
  let ritActive = $derived(state?.ritOn ?? false);
  let ritOffset = $derived(state?.ritFreq ?? 0);
  let splitActive = $derived(state?.split ?? false);
  let voxActive = $derived(state?.voxOn ?? false);
  let atuActive = $derived((state?.tunerStatus ?? 0) > 0);
  let preamp = $derived(rx?.preamp ?? 0);
  let attActive = $derived((rx?.att ?? 0) > 0);
  // FTX-1: no separate NB/NR on/off — level > 0 means active
  let nbLevel = $derived(rx?.nbLevel ?? 0);
  let nrLevel = $derived(rx?.nrLevel ?? 0);
  let nbActive = $derived((rx?.nb ?? false) || nbLevel > 0);
  let nrActive = $derived((rx?.nr ?? false) || nrLevel > 0);
  let agcMode = $derived(rx?.agc ?? 0);
  let notchActive = $derived(rx?.autoNotch ?? false);
  let compActive = $derived(state?.compressorOn ?? false);
  let compLevel = $derived(state?.compressorLevel ?? 0);
  let lockActive = $derived(state?.dialLock ?? false);
  let contourActive = $derived((rx?.contour ?? 0) > 0);
  let contourLevel = $derived(rx?.contour ?? 0);
  let filterWidthHz = $derived(rx?.filterWidth ?? 2400);
  let manualNotchOn = $derived(rx?.manualNotch ?? false);
  let notchFreqRaw = $derived(state?.notchFilter ?? 0);
  let activeVfo = $derived(state?.active === 'SUB' ? 'B' : 'A');

  let subRx = $derived(state?.active === 'SUB' ? state?.main : state?.sub);
  let subFreqHz = $derived(subRx?.freqHz ?? 0);
  let subMode = $derived(subRx?.mode ?? '');

  let fftPixels = $state<Uint8Array | null>(null);
  let fftPush: ((data: Uint8Array) => void) | null = null;
  let showFft = $derived(isAudioFftScope());

  // FTX-1 AGC: 0=OFF, 1=FAST, 2=MID, 3=SLOW, 4=AUTO-F, 5=AUTO-M, 6=AUTO-S
  const AGC_LABELS: Record<number, string> = {
    0: 'OFF', 1: 'FAST', 2: 'MID', 3: 'SLOW',
    4: 'A-F', 5: 'A-M', 6: 'A-S',
  };
  function agcLabel(m: number): string {
    return AGC_LABELS[m] ?? `${m}`;
  }

  onMount(() => {
    if (!isAudioFftScope()) return;
    const scopeCh = getChannel('scope');
    scopeCh.connect('/api/v1/scope');
    const unsubState = scopeCh.onStateChange((s) => {
      setScopeConnected(s === 'connected');
    });
    const unsubBinary = scopeCh.onBinary((buf) => {
      markScopeFrame();
      const frame = parseScopeFrame(buf);
      if (!frame) return;
      fftPixels = frame.pixels;
      fftPush?.(frame.pixels);
    });
    return () => {
      unsubState();
      unsubBinary();
      scopeCh.disconnect();
    };
  });
</script>

<div class="amber-lcd" class:tx-active={txActive}>
  <div class="lcd-screen">
    <div class="lcd-scanlines"></div>

    <!-- ═══ S-Meter (top) ═══ -->
    <div class="lcd-meter-row">
      <AmberSmeter value={sValue} {txActive} />
    </div>

    <!-- ═══ Indicators (below S-meter) — grouped by function ═══ -->
    <div class="lcd-ind-row">
      <!-- TX group -->
      <span class="lcd-ind" class:active={txActive} class:ind-tx={txActive}>TX</span>
      <span class="lcd-ind" class:active={voxActive}>VOX</span>
      <span class="lcd-ind" class:active={compActive}>PROC{compActive ? ` ${compLevel}` : ''}</span>

      <span class="ind-sep"></span>

      <!-- RF front-end -->
      <span class="lcd-ind" class:active={attActive}>ATT</span>
      <span class="lcd-ind active">{preamp === 0 ? 'IPO' : preamp === 1 ? 'AMP1' : 'AMP2'}</span>
      <span class="lcd-ind" class:active={atuActive}>ATU</span>

      <span class="ind-sep"></span>

      <!-- DSP / filters -->
      <span class="lcd-ind" class:active={nbActive}>NB{nbActive ? ` ${nbLevel}` : ''}</span>
      <span class="lcd-ind" class:active={nrActive}>NR{nrActive ? ` ${nrLevel}` : ''}</span>
      <span class="lcd-ind" class:active={contourActive}>CONT</span>
      <span class="lcd-ind" class:active={notchActive}>NOTCH</span>
      <span class="lcd-ind active">AGC {agcLabel(agcMode)}</span>

      <span class="ind-sep"></span>

      <!-- VFO / system -->
      <span class="lcd-ind" class:active={ritActive}>RIT</span>
      <span class="lcd-ind" class:active={splitActive}>SPLIT</span>
      <span class="lcd-ind" class:active={lockActive}>LOCK</span>
    </div>

    <!-- ═══ VFO A: main frequency ═══ -->
    <div class="lcd-vfo-row lcd-vfo-main">
      <span class="vfo-tag">{activeVfo}</span>
      <div class="vfo-freq">
        <AmberFrequency {freqHz} size="large" />
      </div>
      <span class="vfo-mode-box">{mode}{filter ? ` ${filter}` : ''}</span>
    </div>

    <!-- ═══ VFO B: sub frequency ═══ -->
    {#if hasDualReceiver()}
      <div class="lcd-vfo-row lcd-vfo-sub">
        <span class="vfo-tag vfo-tag-sub">{activeVfo === 'A' ? 'B' : 'A'}</span>
        <div class="vfo-freq">
          <AmberFrequency freqHz={subFreqHz} size="small" />
        </div>
        {#if subMode}
          <span class="vfo-mode vfo-mode-sub">{subMode}</span>
        {/if}
      </div>
    {/if}

    <!-- ═══ RIT offset (if active) ═══ -->
    {#if ritActive}
      <div class="lcd-rit-row">
        <span class="rit-label">RIT</span>
        <span class="rit-value">{ritOffset >= 0 ? '+' : ''}{ritOffset} Hz</span>
      </div>
    {/if}

    <!-- ═══ Audio AF Scope (LCD-style filter/FFT display) ═══ -->
    {#if showFft}
      <div class="lcd-fft-area">
        <AmberAfScope
          data={fftPixels}
          onRegisterPush={(fn) => { fftPush = fn; }}
          filterWidth={filterWidthHz}
          contour={contourLevel}
          manualNotch={manualNotchOn}
          notchFreq={notchFreqRaw}
          autoNotch={notchActive}
          {mode}
        />
      </div>
    {/if}
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
  }

  .lcd-screen {
    position: relative;
    width: 100%;
    background: #C8A030;
    border: 2px solid #8A7020;
    border-radius: 8px;
    padding: 12px 18px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    overflow: hidden;
    box-shadow:
      inset 0 0 50px rgba(0, 0, 0, 0.06),
      0 0 8px rgba(0, 0, 0, 0.5);
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
  }

  .ind-sep {
    width: 1px;
    height: 16px;
    background: rgba(26, 16, 0, 0.15);
    margin: 0 4px;
    flex-shrink: 0;
  }

  .lcd-ind {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: rgba(0, 0, 0, 0.08);
    border: 1.5px solid rgba(0, 0, 0, 0.06);
    border-radius: 3px;
    padding: 1px 6px;
    user-select: none;
  }

  .lcd-ind.active {
    color: #1A1000;
    border-color: rgba(26, 16, 0, 0.4);
  }

  .lcd-ind.ind-tx {
    color: #5A0800;
    border-color: rgba(90, 8, 0, 0.5);
    font-size: 15px;
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
    flex: 1;
    min-height: 0;
    align-items: center;
  }

  .vfo-tag {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 22px;
    font-weight: 700;
    color: #1A1000;
    border: 2px solid rgba(26, 16, 0, 0.4);
    border-radius: 4px;
    padding: 0 6px;
    line-height: 1.3;
    flex-shrink: 0;
  }

  .vfo-tag-sub {
    font-size: 16px;
    border-width: 1.5px;
    color: rgba(26, 16, 0, 0.5);
    border-color: rgba(26, 16, 0, 0.25);
    padding: 0 4px;
  }

  .vfo-freq {
    flex: 0 1 auto;
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .vfo-mode-box {
    flex-shrink: 0;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 18px;
    font-weight: 700;
    color: #1A1000;
    letter-spacing: 1px;
    border: 2px solid rgba(26, 16, 0, 0.4);
    border-radius: 4px;
    padding: 2px 8px;
    margin-left: 6px;
  }

  .vfo-mode-sub {
    font-size: 13px;
    color: rgba(26, 16, 0, 0.45);
  }

  /* ── S-Meter ── */
  .lcd-meter-row {
    position: relative;
    z-index: 2;
  }

  /* ── Sub VFO ── */
  .lcd-vfo-sub {
    border-top: 1px solid rgba(0, 0, 0, 0.08);
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
    color: rgba(26, 16, 0, 0.5);
  }

  .rit-value {
    font-family: 'DSEG7 Classic', monospace;
    font-weight: bold;
    font-size: 16px;
    color: rgba(26, 16, 0, 0.6);
  }

  /* ── FFT ── */
  .lcd-fft-area {
    position: relative;
    z-index: 2;
    height: 120px;
    flex-shrink: 0;
    border-top: 1px solid rgba(0, 0, 0, 0.08);
    padding-top: 3px;
  }

  /* ── TX glow ── */
  .tx-active .lcd-screen {
    border-color: #5A2000;
    box-shadow:
      inset 0 0 40px rgba(180, 30, 0, 0.08),
      0 0 10px rgba(180, 30, 0, 0.15);
  }
</style>
