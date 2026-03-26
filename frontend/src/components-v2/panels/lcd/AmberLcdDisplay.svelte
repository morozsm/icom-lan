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

  let state = $derived(radio.current);
  let rx = $derived(state?.active === 'SUB' ? state?.sub : state?.main);
  let freqHz = $derived(rx?.freqHz ?? 0);
  let mode = $derived(rx?.mode ?? '---');
  let sValue = $derived(rx?.sMeter ?? 0);
  let txActive = $derived(state?.txActive ?? false);
  let ritActive = $derived(state?.ritActive ?? false);
  let ritOffset = $derived(state?.ritOffset ?? 0);
  let splitActive = $derived(state?.splitActive ?? false);

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

    <!-- Status indicators row -->
    <div class="lcd-status-row">
      {#if txActive}
        <span class="lcd-badge lcd-badge-tx">TX</span>
      {/if}
      {#if ritActive}
        <span class="lcd-badge lcd-badge-rit">RIT {ritOffset >= 0 ? '+' : ''}{ritOffset} Hz</span>
      {/if}
      {#if splitActive}
        <span class="lcd-badge lcd-badge-split">SPLIT</span>
      {/if}
      <span class="lcd-mode">{mode}</span>
    </div>

    <!-- Main frequency display -->
    <div class="lcd-freq-area">
      <AmberFrequency {freqHz} />
    </div>

    <!-- S-meter bar -->
    <div class="lcd-meter-area">
      <AmberSmeter value={sValue} {txActive} />
    </div>

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
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    overflow: hidden;
    box-shadow:
      inset 0 0 40px rgba(0, 0, 0, 0.1),
      0 0 8px rgba(0, 0, 0, 0.6);
  }

  /* Scanline overlay for LCD authenticity */
  .lcd-scanlines {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 1;
    background: repeating-linear-gradient(
      to bottom,
      transparent 0px,
      transparent 2px,
      rgba(0, 0, 0, 0.06) 2px,
      rgba(0, 0, 0, 0.06) 4px
    );
  }

  .lcd-status-row {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 20px;
    position: relative;
    z-index: 2;
  }

  .lcd-badge {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 11px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 2px;
    letter-spacing: 0.5px;
  }

  .lcd-badge-tx {
    background: #3A0800;
    color: #C8A030;
  }

  .lcd-badge-rit {
    background: rgba(0, 0, 0, 0.15);
    color: #2A2000;
    border: 1px solid rgba(0, 0, 0, 0.2);
  }

  .lcd-badge-split {
    background: rgba(0, 0, 0, 0.15);
    color: #2A2000;
    border: 1px solid rgba(0, 0, 0, 0.2);
  }

  .lcd-mode {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 14px;
    font-weight: 700;
    color: #1A1000;
    margin-left: auto;
    letter-spacing: 1px;
  }

  .lcd-freq-area {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 60px;
    position: relative;
    z-index: 2;
  }

  .lcd-meter-area {
    position: relative;
    z-index: 2;
    height: 28px;
    flex-shrink: 0;
  }

  .lcd-fft-area {
    position: relative;
    z-index: 2;
    height: 64px;
    flex-shrink: 0;
    border-top: 1px solid rgba(0, 0, 0, 0.12);
    padding-top: 4px;
  }

  .tx-active .lcd-screen {
    border-color: #5A2000;
    box-shadow:
      inset 0 0 40px rgba(180, 30, 0, 0.1),
      0 0 12px rgba(180, 30, 0, 0.2);
  }
</style>
