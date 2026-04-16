<script lang="ts">
  import { onMount } from 'svelte';
  import {
    WaterfallRenderer,
    defaultWaterfallOptions,
    type WaterfallOptions,
  } from '../../lib/renderers/waterfall-renderer';
  import { gesture } from '../../lib/gestures/use-gesture';
  import { vibrate } from '../../lib/utils/haptics';

  interface Props {
    options?: WaterfallOptions;
    onFreqClick?: (hz: number) => void;
    onRegisterPush?: (fn: (data: Uint8Array) => void) => void;
  }

  let { options = defaultWaterfallOptions, onFreqClick, onRegisterPush }: Props = $props();

  let canvas: HTMLCanvasElement;
  let renderer = $state<WaterfallRenderer | null>(null);

  function directPush(pixels: Uint8Array): void {
    if (document.hidden) return;
    renderer?.pushRow(pixels);
  }

  $effect(() => {
    if (renderer && options) {
      renderer.updateOptions(options);
    }
  });

  // Tap-to-tune only — drag-to-pan handled by SpectrumPanel (parent).
  const waterfallGestures = {
    onTap(x: number, _y: number): void {
      if (!renderer || !onFreqClick) return;
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const freq = renderer.pixelToFreq((x - rect.left) * dpr);
      if (freq > 0) {
        vibrate('tap');
        onFreqClick(freq);
      }
    },
  };

  onMount(() => {
    renderer = new WaterfallRenderer(canvas, options);
    onRegisterPush?.(directPush);

    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      const dpr = window.devicePixelRatio || 1;
      const w = Math.max(1, Math.floor(rect.width * dpr));
      const h = Math.max(1, Math.floor(rect.height * dpr));
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

<canvas bind:this={canvas} use:gesture={waterfallGestures}></canvas>

<style>
  canvas {
    display: block;
    width: 100%;
    height: 100%;
    cursor: crosshair;
    background: #001020;
  }
</style>
