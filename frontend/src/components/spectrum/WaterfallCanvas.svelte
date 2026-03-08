<script lang="ts">
  import { onMount } from 'svelte';
  import {
    WaterfallRenderer,
    defaultWaterfallOptions,
    type WaterfallOptions,
  } from '../../lib/renderers/waterfall-renderer';
  import { gesture } from '../../lib/gestures/use-gesture';
  import { sendCommand } from '../../lib/transport/ws-client';
  import { getRadioState } from '../../lib/stores/radio.svelte';
  import { vibrate } from '../../lib/utils/haptics';

  interface Props {
    data: Uint8Array | null;
    options?: WaterfallOptions;
    onFreqClick?: (hz: number) => void;
  }

  let { data, options = defaultWaterfallOptions, onFreqClick }: Props = $props();

  let canvas: HTMLCanvasElement;
  let renderer = $state<WaterfallRenderer | null>(null);

  // Accumulated pan offset in Hz (applied on drag end)
  let panOffsetHz = $state(0);

  // Track last data reference to detect new scope frames
  let lastDataRef: Uint8Array | null = null;
  let rafId = 0;

  function tick() {
    if (data && renderer && data !== lastDataRef) {
      lastDataRef = data;
      renderer.pushRow(data);
    }
    rafId = requestAnimationFrame(tick);
  }

  // Sync options changes (colorMap, centerHz, spanHz) to the renderer
  $effect(() => {
    if (renderer && options) {
      renderer.updateOptions(options);
    }
  });

  // --- Hz per pixel helper ---
  function hzPerPixel(): number {
    if (!canvas || options.spanHz <= 0) return 0;
    const dpr = window.devicePixelRatio || 1;
    return options.spanHz / (canvas.getBoundingClientRect().width * dpr);
  }

  // --- Waterfall gesture callbacks ---
  const waterfallGestures = {
    onTap(x: number, y: number): void {
      if (!renderer || !onFreqClick) return;
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const freq = renderer.pixelToFreq((x - rect.left) * dpr);
      if (freq > 0) {
        vibrate('tap');
        onFreqClick(freq);
      }
    },

    onPinch(scale: number, _cx: number, _cy: number): void {
      if (options.spanHz <= 0) return;
      // Clamp span to reasonable radio range (2.5 kHz – 5 MHz)
      const newSpan = Math.max(2_500, Math.min(5_000_000, options.spanHz / scale));
      const half = Math.round(newSpan / 2);
      sendCommand('set_scope_fixed_edge', {
        edge: 1,
        start_hz: Math.max(0, options.centerHz - half),
        end_hz: options.centerHz + half,
      });
    },

    onPan(dx: number, _dy: number): void {
      const hpp = hzPerPixel();
      if (hpp <= 0) return;
      // Accumulate; visual feedback is implicit through options update from server
      panOffsetHz -= dx * hpp;
    },

    onPanEnd(): void {
      if (panOffsetHz === 0 || options.centerHz <= 0) return;
      const newCenter = Math.max(0, options.centerHz + panOffsetHz);
      const receiver = getRadioState()?.active === 'SUB' ? 1 : 0;
      sendCommand('set_freq', { freq: Math.round(newCenter), receiver });
      panOffsetHz = 0;
    },
  };

  onMount(() => {
    renderer = new WaterfallRenderer(canvas, options);
    rafId = requestAnimationFrame(tick);

    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      const dpr = window.devicePixelRatio || 1;
      const w = Math.max(1, Math.floor(rect.width * dpr));
      const h = Math.max(1, Math.floor(rect.height * dpr));
      canvas.width = w;
      canvas.height = h;
      renderer?.resize(w, h);
    });
    ro.observe(canvas);

    return () => {
      cancelAnimationFrame(rafId);
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
  }
</style>
