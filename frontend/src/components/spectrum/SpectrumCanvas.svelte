<script lang="ts">
  import { onMount } from 'svelte';
  import {
    renderSpectrum,
    defaultSpectrumOptions,
    type SpectrumOptions,
  } from '../../lib/renderers/spectrum-renderer';
  interface Props {
    data: Uint8Array | null;
    options?: SpectrumOptions;
    onRegisterPush?: (fn: (data: Uint8Array) => void) => void;
  }

  let { data, options = defaultSpectrumOptions, onRegisterPush }: Props = $props();

  let canvas: HTMLCanvasElement;
  let cssWidth = 1;
  let cssHeight = 1;
  let rafId = 0;
  let visible = true;

  // Latest scope pixels — updated directly from WS binary, not via Svelte props
  let latestPixels: Uint8Array | null = null;

  function draw(): void {
    if (!visible) return; // will be restarted by visibilitychange
    const pixels = latestPixels ?? data;
    if (canvas && pixels && cssWidth > 0 && cssHeight > 0) {
      const ctx = canvas.getContext('2d');
      if (ctx) renderSpectrum(ctx, pixels, cssWidth, cssHeight, options);
    }
    // Always schedule next frame — data may arrive at any time
    rafId = requestAnimationFrame(draw);
  }

  function onVisibilityChange() {
    visible = !document.hidden;
    if (visible && rafId === 0) {
      rafId = requestAnimationFrame(draw);
    }
  }

  onMount(() => {
    // Register push callback with parent — parent handles WS subscription
    onRegisterPush?.((pixels: Uint8Array) => {
      latestPixels = pixels;
    });

    document.addEventListener('visibilitychange', onVisibilityChange);

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
      document.removeEventListener('visibilitychange', onVisibilityChange);
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
