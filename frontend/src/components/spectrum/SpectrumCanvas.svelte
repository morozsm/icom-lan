<script lang="ts">
  import { onMount } from 'svelte';
  import {
    renderSpectrum,
    defaultSpectrumOptions,
    type SpectrumOptions,
  } from '../../lib/renderers/spectrum-renderer';
  import { getChannel } from '../../lib/transport/ws-client';

  interface Props {
    data: Uint8Array | null;
    options?: SpectrumOptions;
  }

  let { data, options = defaultSpectrumOptions }: Props = $props();

  let canvas: HTMLCanvasElement;
  let cssWidth = 1;
  let cssHeight = 1;
  let rafId = 0;

  // Latest scope pixels — updated directly from WS binary, not via Svelte props
  let latestPixels: Uint8Array | null = null;

  function draw(): void {
    const pixels = latestPixels ?? data;
    if (canvas && pixels && cssWidth > 0 && cssHeight > 0) {
      const ctx = canvas.getContext('2d');
      if (ctx) renderSpectrum(ctx, pixels, cssWidth, cssHeight, options);
    }
    // Always schedule next frame — data may arrive at any time
    rafId = requestAnimationFrame(draw);
  }

  onMount(() => {
    // Direct scope binary subscription — bypasses Svelte prop reactivity
    // which cannot track Uint8Array changes at 100+ fps
    const scopeCh = getChannel('scope');
    const unsubBinary = scopeCh.onBinary((buf: ArrayBuffer) => {
      if (buf.byteLength < 16) return;
      const view = new DataView(buf);
      if (view.getUint8(0) !== 0x01) return;
      const pxCount = view.getUint16(14, true);
      if (16 + pxCount > buf.byteLength) return;
      latestPixels = new Uint8Array(buf, 16, pxCount);
    });

    // Continuous RAF loop for smooth rendering
    rafId = requestAnimationFrame(draw);

    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      cssWidth = Math.max(1, Math.floor(rect.width));
      cssHeight = Math.max(1, Math.floor(rect.height));
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(cssWidth * dpr);
      canvas.height = Math.round(cssHeight * dpr);
      const ctx = canvas.getContext('2d');
      ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
    });
    ro.observe(canvas);

    return () => {
      unsubBinary();
      ro.disconnect();
      cancelAnimationFrame(rafId);
    };
  });
</script>

<canvas bind:this={canvas}></canvas>

<style>
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
</style>
