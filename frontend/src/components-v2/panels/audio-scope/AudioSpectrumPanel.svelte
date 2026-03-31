<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { resolveFilterModeConfig } from '../../wiring/state-adapter';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import { getChannel } from '$lib/transport/ws-client';
  import { markScopeFrame } from '$lib/stores/connection.svelte';
  import AudioSpectrumCanvas from './AudioSpectrumCanvas.svelte';

  // ── Scope frame parser (same as AmberLcdDisplay) ──

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

  // ── Radio state extraction ──

  let radioState = $derived(radio.current);
  let rx = $derived(radioState?.active === 'SUB' ? radioState?.sub : radioState?.main);

  let filterWidthHz = $derived(rx?.filterWidth ?? 2400);
  let filterWidthMax = $derived.by(() => {
    const caps = getCapabilities();
    const config = resolveFilterModeConfig(caps, rx?.mode, rx?.dataMode);
    if (config?.table?.length) return config.table[config.table.length - 1];
    return config?.maxHz ?? caps?.filterWidthMax ?? 4000;
  });

  let pbtInner = $derived(rx?.pbtInner ?? 128);
  let pbtOuter = $derived(rx?.pbtOuter ?? 128);
  let manualNotchOn = $derived(rx?.manualNotch ?? false);
  let notchFreqRaw = $derived(radioState?.notchFilter ?? 0);
  let contourLevel = $derived(rx?.contour ?? 0);
  let contourFreqRaw = $derived(128); // Default center; contourFreq not exposed in state yet

  // ── Scope WS connection ──

  let fftPixels = $state<Uint8Array | null>(null);
  let fftBandwidth = $state(48000);
  let fftPush: ((data: Uint8Array) => void) | null = null;

  $effect(() => {
    const scopeCh = getChannel('audio-scope');
    scopeCh.connect('/api/v1/audio-scope');
    const unsubBinary = scopeCh.onBinary((buf) => {
      markScopeFrame();
      const frame = parseScopeFrame(buf);
      if (!frame) return;
      fftPixels = frame.pixels;
      if (frame.endFreq > frame.startFreq) {
        fftBandwidth = frame.endFreq - frame.startFreq;
      }
      fftPush?.(frame.pixels);
    });

    return () => {
      unsubBinary();
      scopeCh.disconnect();
    };
  });
</script>

<div class="audio-spectrum-panel">
  <AudioSpectrumCanvas
    data={fftPixels}
    onRegisterPush={(fn) => { fftPush = fn; }}
    bandwidth={fftBandwidth}
    filterWidth={filterWidthHz}
    filterWidthMax={filterWidthMax}
    pbtInner={pbtInner}
    pbtOuter={pbtOuter}
    manualNotch={manualNotchOn}
    notchFreq={notchFreqRaw}
    contour={contourLevel}
    contourFreq={contourFreqRaw}
  />
</div>

<style>
  .audio-spectrum-panel {
    width: 100%;
    height: 100%;
    min-height: 80px;
    background: var(--panel, #121922);
    border: 1px solid var(--panel-border, #1e293b);
    border-radius: var(--radius, 8px);
    overflow: hidden;
  }
</style>
