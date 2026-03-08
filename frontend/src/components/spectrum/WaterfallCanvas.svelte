<script lang="ts">
  import { onMount } from 'svelte';
  import {
    WaterfallRenderer,
    defaultWaterfallOptions,
    type WaterfallOptions,
  } from '../../lib/renderers/waterfall-renderer';

  interface Props {
    data: Uint8Array | null;
    options?: WaterfallOptions;
    onFreqClick?: (hz: number) => void;
  }

  let { data, options = defaultWaterfallOptions, onFreqClick }: Props = $props();

  let canvas: HTMLCanvasElement;
  let renderer = $state<WaterfallRenderer | null>(null);

  // Push new scope row when data changes
  $effect(() => {
    if (data && renderer) {
      renderer.pushRow(data);
    }
  });

  // Sync options changes (colorMap, centerHz, spanHz) to the renderer
  $effect(() => {
    if (renderer && options) {
      renderer.updateOptions(options);
    }
  });

  function handleClick(e: MouseEvent): void {
    if (!renderer || !onFreqClick) return;
    const rect = (e.currentTarget as HTMLCanvasElement).getBoundingClientRect();
    const freq = renderer.pixelToFreq(e.clientX - rect.left);
    if (freq > 0) onFreqClick(freq);
  }

  onMount(() => {
    renderer = new WaterfallRenderer(canvas, options);

    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      const w = Math.max(1, Math.floor(rect.width));
      const h = Math.max(1, Math.floor(rect.height));
      canvas.width = w;
      canvas.height = h;
      renderer?.resize(w, h);
    });
    ro.observe(canvas);

    return () => {
      ro.disconnect();
      renderer?.destroy();
      renderer = null;
    };
  });
</script>

<canvas bind:this={canvas} onclick={handleClick}></canvas>

<style>
  canvas {
    display: block;
    width: 100%;
    height: 100%;
    cursor: crosshair;
  }
</style>
