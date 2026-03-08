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
  }

  let { data, options = defaultSpectrumOptions }: Props = $props();

  let canvas: HTMLCanvasElement;
  let cssWidth = 1;
  let cssHeight = 1;
  let rafId = 0;

  function draw(): void {
    if (!canvas || !data || cssWidth <= 0 || cssHeight <= 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    renderSpectrum(ctx, data, cssWidth, cssHeight, options);
  }

  function scheduleRender(): void {
    cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(draw);
  }

  // Re-render when data or options change
  $effect(() => {
    if (data !== null || options) scheduleRender();
  });

  onMount(() => {
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
      scheduleRender();
    });
    ro.observe(canvas);
    return () => {
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
