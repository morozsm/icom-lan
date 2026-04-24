<script lang="ts">
  import { radio } from '$lib/stores/radio.svelte';
  import { resolveFilterModeConfig } from '../../wiring/state-adapter';
  import { getCapabilities } from '$lib/stores/capabilities.svelte';
  import { runtime } from '$lib/runtime';
  import AudioSpectrumCanvas from './AudioSpectrumCanvas.svelte';

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

  // Scope subscription — delegates lifecycle to ScopeController (ADR INV-2, INV-5)
  $effect(() => {
    return runtime.scope.subscribe((frame) => {
      fftPixels = frame.pixels;
      if (frame.endFreq > frame.startFreq) {
        fftBandwidth = frame.endFreq - frame.startFreq;
      }
      fftPush?.(frame.pixels);
    });
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
