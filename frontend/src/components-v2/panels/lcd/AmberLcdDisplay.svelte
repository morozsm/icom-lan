<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { isAudioFftScope } from '$lib/stores/capabilities.svelte';
  import AmberFrequency from './AmberFrequency.svelte';
  import AmberSmeter from './AmberSmeter.svelte';
  import AmberFftStrip from './AmberFftStrip.svelte';
  import { getChannel } from '$lib/transport/ws-client';
  import { setScopeConnected, markScopeFrame } from '$lib/stores/connection.svelte';
  import { onMount } from 'svelte';

  // --- Scope frame binary protocol (same as SpectrumPanel) ---
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

  import { hasDualReceiver, vfoLabel } from '$lib/stores/capabilities.svelte';

  let state = $derived(radio.current);
  let rx = $derived(state?.active === 'SUB' ? state?.sub : state?.main);
  let freqHz = $derived(rx?.freqHz ?? 0);
  let mode = $derived(rx?.mode ?? '---');
  let filter = $derived(rx?.filter ?? '');
  let sValue = $derived(rx?.sMeter ?? 0);
  let txActive = $derived(state?.txActive ?? false);
  let ritActive = $derived(state?.ritActive ?? false);
  let ritOffset = $derived(state?.ritOffset ?? 0);
  let splitActive = $derived(state?.splitActive ?? false);
  let voxActive = $derived(state?.voxActive ?? false);
  let atuActive = $derived(state?.atuActive ?? false);
  let preamp = $derived(state?.pre ?? 0);
  let nbActive = $derived(state?.nbActive ?? false);
  let nrMode = $derived(state?.nrMode ?? 0);
  let agcMode = $derived(state?.agcMode ?? 0);
  let activeVfo = $derived(state?.active === 'SUB' ? 'B' : 'A');

  // Sub VFO info
  let subRx = $derived(state?.active === 'SUB' ? state?.main : state?.sub);
  let subFreqHz = $derived(subRx?.freqHz ?? 0);
  let subMode = $derived(subRx?.mode ?? '');

  let fftPixels = $state<Uint8Array | null>(null);
  let fftPush: ((data: Uint8Array) => void) | null = null;

  let showFft = $derived(isAudioFftScope());

  onMount(() => {
    // Subscribe to scope WS for FFT data (same pattern as SpectrumPanel)
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
    <!-- Scanline overlay -->
    <div class="lcd-scanlines"></div>

    <!-- Top row: S-meter + indicators -->
    <div class="lcd-top-row">
      <div class="lcd-meter-area">
        <AmberSmeter value={sValue} {txActive} />
      </div>
      <div class="lcd-indicators">
        <span class="lcd-ind" class:active={txActive} class:ind-tx={txActive}>TX</span>
        <span class="lcd-ind" class:active={voxActive}>VOX</span>
        <span class="lcd-ind" class:active={atuActive}>ATU</span>
        <span class="lcd-ind" class:active={preamp > 0}>PRE</span>
        <span class="lcd-ind" class:active={nbActive}>NB</span>
        <span class="lcd-ind" class:active={nrMode > 0}>NR</span>
      </div>
    </div>

    <!-- Main row: VFO label + frequency + mode -->
    <div class="lcd-main-row">
      <div class="lcd-vfo-label">
        <span class="vfo-letter">{activeVfo}</span>
      </div>
      <div class="lcd-freq-area">
        <AmberFrequency {freqHz} />
      </div>
      <div class="lcd-mode-area">
        <span class="lcd-mode">{mode}</span>
        {#if filter}
          <span class="lcd-filter">{filter}</span>
        {/if}
      </div>
    </div>

    <!-- Status row: RIT/SPLIT/AGC -->
    <div class="lcd-status-row">
      {#if ritActive}
        <span class="lcd-badge">RIT {ritOffset >= 0 ? '+' : ''}{ritOffset}</span>
      {/if}
      {#if splitActive}
        <span class="lcd-badge">SPLIT</span>
      {/if}
      {#if agcMode > 0}
        <span class="lcd-badge">AGC-{agcMode === 1 ? 'F' : agcMode === 2 ? 'M' : 'S'}</span>
      {/if}
      <span class="lcd-spacer"></span>
    </div>

    <!-- Sub VFO (if dual receiver) -->
    {#if hasDualReceiver() && subFreqHz > 0}
      <div class="lcd-sub-row">
        <span class="sub-vfo-label">{activeVfo === 'A' ? 'B' : 'A'}</span>
        <span class="sub-freq">{(subFreqHz / 1_000_000).toFixed(3)}</span>
        {#if subMode}
          <span class="sub-mode">{subMode}</span>
        {/if}
      </div>
    {/if}

    <!-- Audio FFT strip -->
    {#if showFft}
      <div class="lcd-fft-area">
        <AmberFftStrip
          data={fftPixels}
          onRegisterPush={(fn) => { fftPush = fn; }}
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
    justify-content: center;
    padding: 4px;
    box-sizing: border-box;
  }

  .lcd-screen {
    position: relative;
    width: 100%;
    background: #C8A030;
    border: 2px solid #8A7020;
    border-radius: 6px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    overflow: hidden;
    box-shadow:
      inset 0 0 40px rgba(0, 0, 0, 0.08),
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
      transparent 2px,
      rgba(0, 0, 0, 0.04) 2px,
      rgba(0, 0, 0, 0.04) 4px
    );
  }

  /* ── Top row: meter + indicators ── */
  .lcd-top-row {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    position: relative;
    z-index: 2;
  }

  .lcd-meter-area {
    flex: 1;
    min-width: 0;
  }

  .lcd-indicators {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  .lcd-ind {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: rgba(0, 0, 0, 0.08);
    padding: 1px 3px;
    user-select: none;
  }

  .lcd-ind.active {
    color: #1A1000;
  }

  .lcd-ind.ind-tx {
    color: #4A0800;
  }

  /* ── Main row: VFO + freq + mode ── */
  .lcd-main-row {
    display: flex;
    align-items: center;
    gap: 8px;
    position: relative;
    z-index: 2;
    flex: 1;
    min-height: 50px;
  }

  .lcd-vfo-label {
    flex-shrink: 0;
  }

  .vfo-letter {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 18px;
    font-weight: 700;
    color: #1A1000;
    border: 1.5px solid rgba(26, 16, 0, 0.4);
    border-radius: 3px;
    padding: 0 4px;
    line-height: 1.3;
  }

  .lcd-freq-area {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .lcd-mode-area {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
  }

  .lcd-mode {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 14px;
    font-weight: 700;
    color: #1A1000;
    letter-spacing: 1px;
  }

  .lcd-filter {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 10px;
    color: rgba(26, 16, 0, 0.5);
  }

  /* ── Status row: RIT/SPLIT/AGC ── */
  .lcd-status-row {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 14px;
    position: relative;
    z-index: 2;
  }

  .lcd-badge {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 10px;
    font-weight: 700;
    color: rgba(26, 16, 0, 0.6);
    letter-spacing: 0.5px;
  }

  .lcd-spacer {
    flex: 1;
  }

  /* ── Sub VFO row ── */
  .lcd-sub-row {
    display: flex;
    align-items: baseline;
    gap: 6px;
    position: relative;
    z-index: 2;
    border-top: 1px solid rgba(0, 0, 0, 0.08);
    padding-top: 3px;
  }

  .sub-vfo-label {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    font-weight: 700;
    color: rgba(26, 16, 0, 0.4);
    border: 1px solid rgba(26, 16, 0, 0.2);
    border-radius: 2px;
    padding: 0 3px;
  }

  .sub-freq {
    font-family: 'DSEG7 Classic', monospace;
    font-weight: bold;
    font-size: 20px;
    color: rgba(26, 16, 0, 0.5);
    letter-spacing: 1px;
  }

  .sub-mode {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 11px;
    color: rgba(26, 16, 0, 0.4);
  }

  /* ── FFT area ── */
  .lcd-fft-area {
    position: relative;
    z-index: 2;
    height: 64px;
    flex-shrink: 0;
    border-top: 1px solid rgba(0, 0, 0, 0.08);
    padding-top: 3px;
  }

  /* ── TX active state ── */
  .tx-active .lcd-screen {
    border-color: #5A2000;
    box-shadow:
      inset 0 0 40px rgba(180, 30, 0, 0.08),
      0 0 10px rgba(180, 30, 0, 0.15);
  }
</style>
