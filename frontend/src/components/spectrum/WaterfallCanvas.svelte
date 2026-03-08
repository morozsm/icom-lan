<script lang="ts">
  import { onMount } from 'svelte';
  import {
    WaterfallRenderer,
    defaultWaterfallOptions,
    type WaterfallOptions,
  } from '../../lib/renderers/waterfall-renderer';
  import { gesture } from '../../lib/gestures/use-gesture';
  import { getChannel, sendCommand } from '../../lib/transport/ws-client';
  import { getRadioState } from '../../lib/stores/radio.svelte';
  import { vibrate } from '../../lib/utils/haptics';

  interface Props {
    data: Uint8Array | null;
    options?: WaterfallOptions;
    onFreqClick?: (hz: number) => void;
    onRegisterPush?: (fn: (data: Uint8Array) => void) => void;
  }

  let { data, options = defaultWaterfallOptions, onFreqClick, onRegisterPush }: Props = $props();

  let canvas: HTMLCanvasElement;
  let renderer = $state<WaterfallRenderer | null>(null);

  // Accumulated pan offset in Hz (applied on drag end)
  let panOffsetHz = $state(0);

  // Direct push function — called by parent SpectrumPanel for each scope frame.
  // Svelte 5 reactivity cannot reliably track Uint8Array prop changes at 100+ fps,
  // so we bypass it entirely with a direct function call.
  function directPush(pixels: Uint8Array): void {
    renderer?.pushRow(pixels);
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

    // Register direct push callback with parent
    onRegisterPush?.(directPush);

    // ALSO subscribe directly to scope binary — belt and suspenders.
    // Svelte prop reactivity drops Uint8Array updates at high frame rates.
    const scopeCh = getChannel('scope');
    const unsubBinary = scopeCh.onBinary((buf: ArrayBuffer) => {
      if (!renderer || buf.byteLength < 16) return;
      const view = new DataView(buf);
      if (view.getUint8(0) !== 0x01) return;
      const pxCount = view.getUint16(14, true);
      if (16 + pxCount > buf.byteLength) return;
      renderer.pushRow(new Uint8Array(buf, 16, pxCount));
    });

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
      unsubBinary();
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
